# shellpilot/utils/ls_colors.py

from __future__ import annotations

import os
from pathlib import Path

# Map basic ANSI color codes to Rich/Textual color names
_ANSI_COLOR_MAP = {
    "30": "black",
    "31": "red",
    "32": "green",
    "33": "yellow",
    "34": "blue",
    "35": "magenta",
    "36": "cyan",
    "37": "white",
    "90": "bright_black",
    "91": "bright_red",
    "92": "bright_green",
    "93": "bright_yellow",
    "94": "bright_blue",
    "95": "bright_magenta",
    "96": "bright_cyan",
    "97": "bright_white",
}


def _ansi_to_style(code_str: str) -> str:
    """
    Convert something like '01;34' from LS_COLORS into a Rich style string,
    e.g. 'bold blue'.
    """
    parts = code_str.split(";")
    style_bits: list[str] = []

    for p in parts:
        if p == "1":
            style_bits.append("bold")
        elif p in _ANSI_COLOR_MAP:
            style_bits.append(_ANSI_COLOR_MAP[p])

    return " ".join(style_bits)


def _parse_ls_colors() -> dict[str, str]:
    """
    Parse $LS_COLORS into a simple mapping:
        { 'di': 'bold blue', 'ln': 'bold cyan', ... }
    We ignore extension patterns (e.g. '*.py') for now.
    """
    env = os.environ.get("LS_COLORS", "")
    result: dict[str, str] = {}

    if not env:
        return result

    for chunk in env.split(":"):
        if "=" not in chunk:
            continue
        key, val = chunk.split("=", 1)
        # Only handle simple types like 'di', 'ln', 'ex' for now.
        if key and not key.startswith("*."):
            style = _ansi_to_style(val)
            if style:
                result[key] = style

    return result


_LS_COLORS_MAP = _parse_ls_colors()


def style_for_path(path: Path) -> str:
    """
    Return a Rich/Textual style string for this path based on LS_COLORS,
    with sensible fallbacks for directories (and a couple of extras).
    """
    # Directories
    if path.is_dir():
        if "di" in _LS_COLORS_MAP:
            return _LS_COLORS_MAP["di"]
        return "bold blue"

    # Symlinks
    if path.is_symlink():
        if "ln" in _LS_COLORS_MAP:
            return _LS_COLORS_MAP["ln"]
        return "cyan"

    # Executables
    try:
        if path.is_file() and os.access(path, os.X_OK):
            if "ex" in _LS_COLORS_MAP:
                return _LS_COLORS_MAP["ex"]
            return "bold green"
    except Exception:
        pass

    # Default: no special style
    return ""
