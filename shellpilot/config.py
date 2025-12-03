from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os
from typing import Optional


def _default_config_path() -> Path:
    # Allow override via env var; otherwise use ~/.config/shellpilot/config.json
    env_path = os.getenv("SHELLPILOT_CONFIG")
    if env_path:
        return Path(env_path).expanduser()

    return Path.home() / ".config" / "shellpilot" / "config.json"


CONFIG_PATH = _default_config_path()


@dataclass
class AppConfig:
    """ShellPilot persistent configuration."""

    # Existing --------------------------------------------------
    hf_token: Optional[str] = None  # Hugging Face token for gated models

    # NEW: LS_COLORS / file color theme settings ----------------
    # Mode: 'env', 'env_with_boost', or 'scheme'
    ls_colors_mode: str = "env_with_boost"

    # Built-in scheme name (only used when mode='scheme')
    ls_colors_scheme: str = "classic"

    # If True, boost dark terminal colors for better readability
    ls_dark_background: bool = True


def load_config() -> AppConfig:
    """Load config from disk, or return defaults if missing/invalid."""
    try:
        if CONFIG_PATH.is_file():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

            # Merge disk data with defaults safely:
            # Missing fields will take the dataclass defaults.
            return AppConfig(**data)
    except Exception:
        # Don't crash ShellPilot if config is corrupt.
        pass

    return AppConfig()


def save_config(cfg: AppConfig) -> None:
    """Persist config to disk."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(asdict(cfg), indent=2),
        encoding="utf-8",
    )
