from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Literal, Tuple
import json
import os

Provider = Literal["local", "gpt", "gemini", "copilot"]

CONFIG_DIR = Path.home() / ".config" / "shellpilot"
CONFIG_PATH = CONFIG_DIR / "ai.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "provider": "local",              # "local" | "gpt" | "gemini" | "copilot"
    "local_model_id": "phi-3.5-mini-q4",
    "openai_api_key": None,
    "gemini_api_key": None,
    "copilot_api_key": None,
}


def load_ai_config() -> Dict[str, Any]:
    """Load AI provider configuration from ~/.config/shellpilot/ai.json."""
    cfg = DEFAULT_CONFIG.copy()
    try:
        if CONFIG_PATH.is_file():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
    except Exception:
        # Corrupt config? Start with defaults but don't crash the app.
        pass
    return cfg


def save_ai_config(cfg: Dict[str, Any]) -> None:
    """Persist AI provider configuration to disk with 0600 perms."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    tmp.replace(CONFIG_PATH)
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except Exception:
        # Best-effort; ignore chmod failures on weird filesystems.
        pass


def set_provider_and_key(
    provider: Provider,
    api_key: str,
    overwrite: bool = False,
) -> Tuple[bool, str]:
    """
    Set the active provider and its API key.

    Returns (changed, message_key):
      - changed == True  → config updated
      - changed == False → key already existed and overwrite=False
                           message_key is the config field name (e.g. "openai_api_key")
    """
    cfg = load_ai_config()

    field_map = {
        "gpt": "openai_api_key",
        "gemini": "gemini_api_key",
        "copilot": "copilot_api_key",
    }

    if provider != "local":
        field = field_map[provider]
        if cfg.get(field) and not overwrite:
            return False, field
        cfg[field] = api_key.strip()

    cfg["provider"] = provider
    save_ai_config(cfg)
    return True, ""
