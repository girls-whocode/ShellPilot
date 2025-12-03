from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Input, Button

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
        ai_cfg = load_ai_config()

        hf_token = cfg.hf_token or ""
        openai_key = ai_cfg.get("openai_api_key") or ""
        gemini_key = ai_cfg.get("gemini_api_key") or ""
        copilot_key = ai_cfg.get("copilot_api_key") or ""
        selfhost_base_url = ai_cfg.get("selfhost_base_url") or ""
        selfhost_api_key = ai_cfg.get("selfhost_api_key") or ""
        selfhost_model = ai_cfg.get("selfhost_model") or ""

        with Vertical(id="settings-dialog"):
            yield Static("Settings", id="settings-title")
            yield Static(
                "Configure ShellPilot options. Hugging Face and AI provider keys are "
                "stored locally on this machine.\n\n"
                "To get a Hugging Face token, visit https://huggingface.co/settings/tokens.",
                id="settings-subtitle",
            )

            # --- Hugging Face ----------------------------------------------------
            yield Static(
                "Hugging Face access token (for gated GGUF downloads):",
                id="hf-token-label",
            )
            yield Input(
                value=hf_token,
                password=True,
                placeholder="hf_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                id="hf-token-input",
            )

            # --- OpenAI / GPT ----------------------------------------------------
            yield Static("OpenAI API key (GPT):", id="openai-label")
            yield Input(
                value=openai_key,
                password=True,
                placeholder="sk-...",
                id="openai-input",
            )

            # --- Google Gemini ---------------------------------------------------
            yield Static("Google Gemini API key:", id="gemini-label")
            yield Input(
                value=gemini_key,
                password=True,
                placeholder="AIza...",
                id="gemini-input",
            )

            # --- GitHub Copilot --------------------------------------------------
            yield Static("GitHub Copilot API token (if using a custom gateway):", id="copilot-label")
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

            self.dismiss(
                {
                    "hf_token": hf_input.value.strip() or None,
                    "openai_api_key": openai_input.value.strip() or None,
                    "gemini_api_key": gemini_input.value.strip() or None,
                    "copilot_api_key": copilot_input.value.strip() or None,
                    "selfhost_base_url": selfhost_url_input.value.strip() or None,
                    "selfhost_model": selfhost_model_input.value.strip() or None,
                    "selfhost_api_key": selfhost_key_input.value.strip() or None,
                }
            )


    def key_escape(self) -> None:
        self.dismiss(None)
