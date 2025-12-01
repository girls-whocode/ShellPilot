# shellpilot/ai/config.py

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
    "local_model_id": None,           # last-used local model
    "openai_api_key": None,
    "gemini_api_key": None,
    "copilot_api_key": None,
}


def load_ai_config() -> Dict[str, Any]:
    cfg = DEFAULT_CONFIG.copy()
    try:
        if CONFIG_PATH.is_file():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
    except Exception:
        # Corrupt/invalid config → ignore and use defaults
        pass
    return cfg


def save_ai_config(cfg: Dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    tmp.replace(CONFIG_PATH)
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except Exception:
        # Non-POSIX / weird FS – best effort only
        pass


def set_provider_and_key(
    provider: Provider,
    api_key: str,
    overwrite: bool = False,
) -> Tuple[bool, str]:
    """
    Set active provider + its API key.

    Returns (changed, field_name). If changed is False, we *did not* overwrite.
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
