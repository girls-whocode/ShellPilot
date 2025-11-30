from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Input, Button

from shellpilot.config import load_config


@dataclass
class SettingsResult:
    hf_token: Optional[str] = None


class SettingsScreen(ModalScreen[dict[str, Any] | None]):
    """Simple settings dialog for ShellPilot (currently: Hugging Face token)."""

    CSS = """
    SettingsScreen {
        align: center middle;
    }

    #settings-dialog {
        width: 70%;
        max-width: 90;
        padding: 1 2;
        border: round $accent;
        background: $panel;
    }

    #settings-title {
        content-align: center middle;
        padding-bottom: 1;
    }

    #settings-subtitle {
        color: $text-muted;
        padding-bottom: 1;
    }

    #hf-token-label {
        padding-top: 1;
        padding-bottom: 1;
    }

    #hf-token-input {
        border: heavy $accent;
    }

    #buttons-row {
        padding-top: 1;
        height: auto;
        content-align: center middle;
    }

    .settings-button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        cfg = load_config()
        hf_token = cfg.hf_token or ""

        with Vertical(id="settings-dialog"):
            yield Static("Settings", id="settings-title")
            yield Static(
                "Configure ShellPilot options. Your Hugging Face token is stored "
                "locally on this machine.\n\n"
                "To get a token, visit https://huggingface.co/settings/tokens.",
                id="settings-subtitle",
            )

            yield Static("Hugging Face access token (for gated models):", id="hf-token-label")
            yield Input(
                value=hf_token,
                password=True,  # hide as you type
                placeholder="hf_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                id="hf-token-input",
            )

            with Horizontal(id="buttons-row"):
                yield Button("Save", id="btn-save", variant="primary", classes="settings-button")
                yield Button("Cancel", id="btn-cancel", variant="default", classes="settings-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
            return

        if event.button.id == "btn-save":
            token_input = self.query_one("#hf-token-input", Input)
            token = token_input.value.strip() or None

            self.dismiss(
                {
                    "hf_token": token,
                }
            )

    def key_escape(self) -> None:
        self.dismiss(None)
