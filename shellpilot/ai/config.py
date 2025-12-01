# shellpilot/ai/config.py

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Literal, Tuple
import json
import os

Provider = Literal["local", "selfhost", "gpt", "gemini", "copilot"]

CONFIG_DIR = Path.home() / ".config" / "shellpilot"
CONFIG_PATH = CONFIG_DIR / "ai.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    # "local" | "selfhost" | "gpt" | "gemini" | "copilot"
    "provider": "local",

    # Local provider (e.g. llama.cpp / CPU-GPU local models)
    "local_model_id": None,

    # Cloud-ish providers
    "openai_api_key": None,
    "gemini_api_key": None,
    "copilot_api_key": None,

    # Self-hosted OpenAI-compatible backend (vLLM, Ollama, etc.)
    "selfhost_base_url": None,   # e.g. "http://103.196.86.137:11293/v1"
    "selfhost_api_key": None,    # often a dummy like "shellpilot-local"
    "selfhost_model": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
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

    NOTE: For selfhost, prefer set_selfhost_config(), since we also
    care about base_url + model. This still lets you assign a selfhost_api_key
    if you really want to drive it the old way.
    """
    cfg = load_ai_config()

    field_map = {
        "gpt": "openai_api_key",
        "gemini": "gemini_api_key",
        "copilot": "copilot_api_key",
        "selfhost": "selfhost_api_key",
    }

    if provider != "local":
        field = field_map[provider]
        if cfg.get(field) and not overwrite:
            return False, field
        cfg[field] = api_key.strip()

    cfg["provider"] = provider
    save_ai_config(cfg)
    return True, ""


def set_selfhost_config(
    base_url: str,
    api_key: str | None = None,
    model_id: str | None = None,
    overwrite: bool = False,
) -> Tuple[bool, str]:
    """
    Configure the selfhost provider (base_url, api_key, model_id) and
    set it as active.

    Returns (changed, reason_field). If changed is False, reason_field
    indicates which field was protected from overwrite.
    """
    cfg = load_ai_config()

    base_url = base_url.strip().rstrip("/")
    if not base_url:
        return False, "selfhost_base_url"

    # Check existing values if overwrite=False
    if not overwrite:
        if cfg.get("selfhost_base_url") and cfg["selfhost_base_url"] != base_url:
            return False, "selfhost_base_url"
        if api_key and cfg.get("selfhost_api_key") and cfg["selfhost_api_key"] != api_key:
            return False, "selfhost_api_key"
        if model_id and cfg.get("selfhost_model") and cfg["selfhost_model"] != model_id:
            return False, "selfhost_model"

    cfg["selfhost_base_url"] = base_url
    if api_key is not None:
        cfg["selfhost_api_key"] = api_key.strip() or None
    if model_id is not None:
        cfg["selfhost_model"] = model_id.strip() or None

    cfg["provider"] = "selfhost"
    save_ai_config(cfg)
    return True, ""


def get_effective_ai_settings() -> Dict[str, Any]:
    """
    Resolve AI settings with this precedence:

    1. Environment variables
       - SHELLPILOT_AI_PROVIDER
       - SHELLPILOT_AI_BASE_URL
       - SHELLPILOT_AI_API_KEY
       - SHELLPILOT_AI_MODEL

    2. ai.json config file

    3. DEFAULT_CONFIG
    """
    cfg = load_ai_config()

    provider = os.getenv("SHELLPILOT_AI_PROVIDER", cfg.get("provider", "local"))

    # Selfhost defaults from config
    selfhost_base = cfg.get("selfhost_base_url")
    selfhost_key = cfg.get("selfhost_api_key") or "shellpilot-local"
    selfhost_model = cfg.get("selfhost_model") or "deepseek-ai/DeepSeek-R1-Distill-Llama-8B"

    base_url = os.getenv("SHELLPILOT_AI_BASE_URL", selfhost_base or "")
    api_key = os.getenv("SHELLPILOT_AI_API_KEY", selfhost_key)
    model = os.getenv("SHELLPILOT_AI_MODEL", None)

    if not model:
        if provider == "selfhost":
            model = selfhost_model
        else:
            # For other providers, we let the caller pick the model by name,
            # or they can also use SHELLPILOT_AI_MODEL.
            model = cfg.get("local_model_id")  # reasonable fallback for now

    return {
        "provider": provider,
        "base_url": base_url or None,
        "api_key": api_key or None,
        "model": model,
    }
