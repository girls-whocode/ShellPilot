from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static, Input, Button, Select, Checkbox

from shellpilot.config import load_config
from shellpilot.ai.config import load_ai_config

@dataclass
class SettingsResult:
    hf_token: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    copilot_api_key: Optional[str] = None
    selfhost_base_url: Optional[str] = None
    selfhost_api_key: Optional[str] = None
    selfhost_model: Optional[str] = None

    # New: LS_COLORS-related preferences
    ls_colors_mode: Optional[str] = None
    ls_colors_scheme: Optional[str] = None
    ls_dark_background: Optional[bool] = None

class SettingsScreen(ModalScreen[dict[str, Any] | None]):
    """Simple settings dialog for ShellPilot (AI + LS_COLORS settings)."""

    CSS = """
    SettingsScreen {
        align: center middle;
    }

    #settings-dialog {
        width: 70%;
        max-width: 90;
        max-height: 80%;
        padding: 1 2;
        border: round $accent;
        background: $panel;
        overflow-y: auto;
    }

    #settings-title {
        content-align: center middle;
        padding-bottom: 1;
        text-style: bold;
    }

    #settings-subtitle {
        color: $text-muted;
        padding-bottom: 1;
        height: auto;
    }

    /* Section headings (Hugging Face, OpenAI, LS_COLORS, etc) */
    .settings-section-title {
        padding-top: 1;
        padding-bottom: 0;
        text-style: bold;
        color: $accent;
    }

    /* Labels above inputs */
    .settings-label {
        padding-top: 1;
        padding-bottom: 0;
        color: $text-muted;
    }

     /* Inputs & selects: keep them neat and full-width */
    Input {
        width: 100%;
        padding: 0 1;
        border: tall $accent;
    }
    
    Select {
        width: 100%;
        padding: 0 1;
        height: 5;
        border: tall $accent;
    }

    /* Make sure text inside selects is visible */
    Select {
        color: $text;
    }

    /* Focus styling */
    Input:focus, Select:focus {
        border: heavy $accent;
    }

    /* Dropdown popup: shorter and scrollable */
    Select > .select-overlay {
        max-height: 8;
        overflow-y: auto;
        border: round $accent;
        background: $panel;
    }

    #hf-token-input {
        border: heavy $accent;
    }

    #buttons-row {
        padding-top: 2;
        height: auto;
        content-align: center middle;
    }

    .settings-button {
        margin: 0 1;
        min-width: 10;
    }

    #ls-colors-dark-checkbox {
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        cfg = load_config()
        ai_cfg = load_ai_config()

        hf_token = cfg.hf_token or ""
        openai_key = ai_cfg.get("openai_api_key") or ""
        gemini_key = ai_cfg.get("gemini_api_key") or ""
        copilot_key = ai_cfg.get("copilot_api_key") or ""
        selfhost_base_url = ai_cfg.get("selfhost_base_url") or ""
        selfhost_api_key = ai_cfg.get("selfhost_api_key") or ""
        selfhost_model = ai_cfg.get("selfhost_model") or ""

        # New LS_COLORS defaults – pick whatever you like as defaults
        ls_colors_mode = getattr(cfg, "ls_colors_mode", None) or "env_with_boost"
        ls_colors_scheme = getattr(cfg, "ls_colors_scheme", None) or "classic"
        ls_dark_background = getattr(cfg, "ls_dark_background", None)
        if ls_dark_background is None:
            ls_dark_background = True

        with VerticalScroll(id="settings-dialog"):
            yield Static("Settings", id="settings-title")
            yield Static(
                "Configure ShellPilot options. Hugging Face and AI provider keys are "
                "stored locally on this machine.\n\n"
                "To get a Hugging Face token, visit https://huggingface.co/settings/tokens.",
                id="settings-subtitle",
            )

            # --- Hugging Face ----------------------------------------------------
            yield Static("Hugging Face", classes="settings-section-title")
            yield Static(
                "Hugging Face access token (for gated GGUF downloads):", id="hf-token-label", classes="settings-label")
            yield Input(
                value=hf_token,
                password=True,
                placeholder="hf_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                id="hf-token-input",
            )

            # --- OpenAI / GPT ----------------------------------------------------
            yield Static("OpenAI / GPT", classes="settings-section-title")
            yield Static("OpenAI API key (GPT):", id="openai-label", classes="settings-label")
            yield Input(
                value=openai_key,
                password=True,
                placeholder="sk-...",
                id="openai-input",
            )

            # --- Google Gemini ---------------------------------------------------
            yield Static("Google Gemini", classes="settings-section-title")
            yield Static("Google Gemini API key:", id="gemini-label", classes="settings-label")
            yield Input(
                value=gemini_key,
                password=True,
                placeholder="AIza...",
                id="gemini-input",
            )

            # --- GitHub Copilot --------------------------------------------------
            yield Static("GitHub Copilot", classes="settings-section-title")
            yield Static("GitHub Copilot API token (if using a custom gateway):", id="copilot-label", classes="settings-label")
            yield Input(
                value=copilot_key,
                password=True,
                placeholder="ghp_...",
                id="copilot-input",
            )

            # --- Self-hosted backend --------------------------------------------
            yield Static(
                "Self-hosted OpenAI-compatible backend (vLLM / Ollama / LM Studio):",
                id="selfhost-title",
            )

            yield Static("Base URL (e.g. http://127.0.0.1:8000/v1):", id="selfhost-url-label")
            yield Input(
                value=selfhost_base_url,
                password=False,
                placeholder="http://HOST:PORT/v1",
                id="selfhost-url-input",
            )

            yield Static("Default model id:", id="selfhost-model-label")
            yield Input(
                value=selfhost_model,
                password=False,
                placeholder="deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
                id="selfhost-model-input",
            )

            yield Static("Self-host API key (if required):", id="selfhost-key-label")
            yield Input(
                value=selfhost_api_key,
                password=True,
                placeholder="(optional; some backends ignore this)",
                id="selfhost-key-input",
            )

            # --- LS_COLORS / file-color scheme ------------------------------------
            yield Static(
                "File color scheme (LS_COLORS):",
                id="ls-colors-title",
            )

            # Mode selector
            yield Static("Mode:", id="ls-colors-mode-label")
            yield Select(
                options=[
                    ("Use terminal LS_COLORS", "env"),
                    ("Use terminal LS_COLORS (brighten for dark background)", "env_with_boost"),
                    ("Use built-in scheme", "scheme"),
                ],
                value=ls_colors_mode,
                id="ls-colors-mode-select",
            )

            # Scheme selector (only used when mode == 'scheme', but we keep it visible for simplicity)
            yield Static("Built-in scheme:", id="ls-colors-scheme-label")
            yield Select(
                options=[
                    ("Classic", "classic"),
                    ("High contrast (dark screens)", "high_contrast"),
                    ("Pastel", "pastel"),
                ],
                value=ls_colors_scheme,
                id="ls-colors-scheme-select",
            )

            # Dark background hint
            yield Checkbox(
                "Assume dark background (brighten dark colors)",
                value=ls_dark_background,
                id="ls-colors-dark-checkbox",
            )

            with Horizontal(id="buttons-row"):
                yield Button("Save", id="btn-save", variant="primary", classes="settings-button")
                yield Button("Cancel", id="btn-cancel", variant="default", classes="settings-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
            return

        if event.button.id == "btn-save":
            hf_input = self.query_one("#hf-token-input", Input)
            openai_input = self.query_one("#openai-input", Input)
            gemini_input = self.query_one("#gemini-input", Input)
            copilot_input = self.query_one("#copilot-input", Input)
            selfhost_url_input = self.query_one("#selfhost-url-input", Input)
            selfhost_model_input = self.query_one("#selfhost-model-input", Input)
            selfhost_key_input = self.query_one("#selfhost-key-input", Input)

            # New LS_COLORS widgets
            mode_select = self.query_one("#ls-colors-mode-select", Select)
            scheme_select = self.query_one("#ls-colors-scheme-select", Select)
            dark_checkbox = self.query_one("#ls-colors-dark-checkbox", Checkbox)

            self.dismiss(
                {
                    "hf_token": hf_input.value.strip() or None,
                    "openai_api_key": openai_input.value.strip() or None,
                    "gemini_api_key": gemini_input.value.strip() or None,
                    "copilot_api_key": copilot_input.value.strip() or None,
                    "selfhost_base_url": selfhost_url_input.value.strip() or None,
                    "selfhost_model": selfhost_model_input.value.strip() or None,
                    "selfhost_api_key": selfhost_key_input.value.strip() or None,

                    # LS_COLORS fields
                    "ls_colors_mode": (mode_select.value or "env_with_boost"),
                    "ls_colors_scheme": (scheme_select.value or "classic"),
                    "ls_dark_background": bool(dark_checkbox.value),
                }
            )

    def key_escape(self) -> None:
        self.dismiss(None)
