# shellpilot/ui/action_menu.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from textual.events import Key
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static, ListView, ListItem

@dataclass
class ActionDefinition:
    name: str
    syntax: str
    description: str

ACTIONS: list[ActionDefinition] = [
    ActionDefinition(
        "rename",
        "rename <new_name>",
        "Rename the selected file or directory.",
    ),
    ActionDefinition(
        "chmod",
        "chmod <mode>",
        "Change permissions of the selected file (octal, e.g. 755).",
    ),
    ActionDefinition(
        "mkdir",
        "mkdir <dirname>",
        "Create a new directory in the current folder.",
    ),
    ActionDefinition(
        "touch",
        "touch <filename>",
        "Create an empty file (or update mtime) in the current folder.",
    ),
    ActionDefinition(
        "aimodel",
        "aimodel <id-or-index>",
        "Switch local AI model (by id or numeric index). Downloads if missing.",
    ),
    ActionDefinition(
        "aimodel gpt",
        "aimodel gpt <API_KEY>",
        "Configure OpenAI GPT provider (stores API key on first use).",
    ),
    ActionDefinition(
        "aimodel gemini",
        "aimodel gemini <API_KEY>",
        "Configure Google Gemini provider (stores API key on first use).",
    ),
    ActionDefinition(
        "aimodel copilot",
        "aimodel copilot <API_KEY>",
        "Configure GitHub Copilot provider (stores API key on first use).",
    ),
    ActionDefinition(
        "aimodel selfhost",
        "aimodel selfhost <URL> <API_KEY>",
        "Configure a selfhosted LLM on your own server (stores URL and API key on first use, use again to change it).",
    ),
    ActionDefinition(
        "settings",
        "settings",
        "Open ShellPilot settings (HF token, AI providers, etc.).",
    ),
]

class ActionMenu(ModalScreen[dict[str, Any] | None]):
    """Floating command palette opened with ':'."""

    CSS = """
    ActionMenu {
        align: center middle;
    }

    #dialog {
        width: 60%;
        max-width: 80;
        padding: 1 2;
        border: round $accent;
        background: $panel;
    }

    #title {
        content-align: center middle;
        padding-bottom: 1;
    }

    #subtitle {
        color: $text-muted;
        padding-bottom: 1;
    }

    #command-input {
        border: heavy $accent;
    }

    #actions-list {
        height: auto;
        max-height: 10;
        margin-top: 1;
        overflow-y: auto;
    }

    #hint {
        color: $text-muted;
        padding-top: 1;
        text-style: italic;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Command Palette", id="title")
            yield Static(
                "Type a command (rename, chmod, mkdir, touch, aimodel)…",
                id="subtitle",
            )
            yield Input(
                placeholder="e.g. rename new_name  or  aimodel 1",
                id="command-input",
            )
            yield ListView(
                *[
                    ListItem(
                        Static(
                            f"[b]{a.syntax}[/b]\n[a]{a.description}[/a]",
                            markup=True,
                        )
                    )
                    for a in ACTIONS
                ],
                id="actions-list",
            )
            yield Static("Press Esc to cancel.", id="hint")

    def on_mount(self) -> None:
        self.query_one("#command-input", Input).focus()

    # --- Filtering suggestions as the user types ---

    def on_input_changed(self, event: Input.Changed) -> None:
        text = event.value.strip().lower()
        listview = self.query_one("#actions-list", ListView)
        listview.clear()

        for a in ACTIONS:
            if (
                not text
                or a.name.startswith(text)
                or text in a.syntax.lower()
            ):
                listview.append(
                    ListItem(
                        Static(
                            f"[b]{a.syntax}[/b]\n[a]{a.description}[/a]",
                            markup=True,
                        )
                    )
                )

    def on_key(self, event: Key) -> None:
        """Handle Tab for autocomplete while the palette is open."""
        if event.key == "tab":
            self._autocomplete_command()
            event.stop()  # stop Tab from inserting a literal tab into the Input
            return

        # For all other keys, do NOTHING here.
        # Let them bubble to the focused Input widget as normal.
        return

    # --- Tab-based autocomplete for command names ---

    def _autocomplete_command(self) -> None:
        """Autocomplete the first word in the command input from ACTIONS."""
        input_widget = self.query_one("#command-input", Input)
        raw = input_widget.value

        # Preserve any leading spaces (just in case)
        stripped = raw.lstrip()
        leading = raw[: len(raw) - len(stripped)]

        if not stripped:
            return

        parts = stripped.split(maxsplit=1)
        prefix = parts[0]
        rest = parts[1] if len(parts) > 1 else ""

        # Build list of command names (e.g. rename, chmod, aimodel, ai, etc.)
        command_names = sorted({a.name for a in ACTIONS})

        matches = [name for name in command_names if name.startswith(prefix)]
        if not matches:
            return

        # If multiple matches, use the longest common prefix; fall back to first
        def common_prefix(strings: list[str]) -> str:
            if not strings:
                return ""
            cp = strings[0]
            for s in strings[1:]:
                i = 0
                while i < len(cp) and i < len(s) and cp[i] == s[i]:
                    i += 1
                cp = cp[:i]
                if not cp:
                    break
            return cp

        cp = common_prefix(matches)
        if cp and len(cp) > len(prefix):
            completed = cp
        else:
            completed = matches[0]

        # Rebuild the line: completed command + existing args (if any)
        new_value = leading + completed
        if rest:
            new_value += " " + rest
        else:
            # Add a trailing space so you can immediately type args
            new_value += " "

        input_widget.value = new_value
        input_widget.cursor_position = len(new_value)


    # --- Submit command on Enter ---

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value
        result = self._parse_command(raw)
        if result is None:
            # Lightweight feedback: shake or update subtitle would be nice later
            subtitle = self.query_one("#subtitle", Static)
            subtitle.update(
                "[red]Invalid command or missing argument.[/red] "
                "Try e.g. 'rename new_name' or 'mkdir test'."
            )
            return

        self.dismiss(result)

    # --- Escape closes the palette ---

    def key_escape(self) -> None:
        self.dismiss(None)

    # --- Parsing logic ---

    def _parse_command(self, raw: str) -> dict[str, Any] | None:
        parts = raw.strip().split()
        if not parts:
            return None

        cmd, *args = parts

        cmd = cmd.lower()

        if cmd == "rename":
            if not args:
                return None
            return {
                "action": "rename",
                "new_name": " ".join(args),
            }

        if cmd == "chmod":
            if not args:
                return None
            mode = args[0]
            # basic validation: must be octal digits
            if not all(ch in "01234567" for ch in mode):
                return None
            return {
                "action": "chmod",
                "mode": mode,
            }

        if cmd == "mkdir":
            if not args:
                return None
            return {
                "action": "mkdir",
                "name": " ".join(args),
            }

        if cmd == "touch":
            if not args:
                return None
            return {
                "action": "touch",
                "name": " ".join(args),
            }
        
        if cmd == "settings":
            return {
                "action": "settings",
            }

        if cmd in {"ai", "aimodel"}:
            # No args OR "status" → show AI config + model list
            if not args or args[0].lower() == "status":
                return {
                    "action": "ai_status",
                }

            sub = args[0].lower()

            if cmd in {"ai", "aimodel", "aimodels"}:
                if len(args) == 0:
                    return {"action": "aimodels"}  # already in your code
                sub = args[0].lower()

                # Quick provider switch back to local engine
                if sub == "local" and len(args) == 1:
                    return {
                        "action": "aimodel_provider_switch",
                        "provider": "local",
                    }

                # selfhost support
                if sub == "selfhost":
                    url = args[1] if len(args) >= 2 else None
                    api_key = " ".join(args[2:]) if len(args) >= 3 else None
                    return {
                        "action": "aimodel_selfhost",
                        "url": url,
                        "api_key": api_key,
                    }

                # Remote providers that need/stored API keys
                if sub in {"gpt", "gemini", "copilot"}:
                    # Two modes:
                    #   aimodel gemini <API_KEY>  -> set key + switch
                    #   aimodel gemini           -> just switch (reuse stored key)
                    if len(args) == 1:
                        return {
                            "action": "aimodel_provider_switch",
                            "provider": sub,
                        }
                    else:
                        return {
                            "action": "aimodel_provider",
                            "provider": sub,
                            "api_key": " ".join(args[1:]),
                        }

                # Local model selection (id or index)
                return {
                    "action": "aimodel",
                    "target": " ".join(args),
                }

            # selfhost support
            if sub == "selfhost":
                url = args[1] if len(args) >= 2 else None
                api_key = " ".join(args[2:]) if len(args) >= 3 else None
                return {
                    "action": "aimodel_selfhost",
                    "url": url,
                    "api_key": api_key,
                }

            # Remote providers that need/stored API keys
            if sub in {"gpt", "gemini", "copilot"}:
                # Two modes:
                #   aimodel gemini <API_KEY>  -> set key + switch
                #   aimodel gemini           -> just switch (reuse stored key)
                if len(args) == 1:
                    return {
                        "action": "aimodel_provider_switch",
                        "provider": sub,
                    }
                else:
                    return {
                        "action": "aimodel_provider",
                        "provider": sub,
                        "api_key": " ".join(args[1:]),
                    }

            # Local model selection (id or index)
            return {
                "action": "aimodel",
                "target": " ".join(args),
            }

