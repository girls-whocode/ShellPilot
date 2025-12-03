# shellpilot/utils/ls_colors.py

from __future__ import annotations

import os
import stat as statmod
from pathlib import Path
from typing import Dict

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


def _ansi_seq_to_style(seq: str) -> str:
    """
    Convert something like '01;34' from LS_COLORS into a Rich style string,
    e.g. 'bold blue'.
    """
    parts = [p for p in seq.split(";") if p]
    style_bits: list[str] = []

    i = 0
    while i < len(parts):
        p = parts[i]
        if p == "0":
            # reset
            style_bits.clear()
        elif p == "1":
            style_bits.append("bold")
        elif p in _ANSI_COLOR_MAP:
            style_bits.append(_ANSI_COLOR_MAP[p])
        elif p == "38" and i + 2 < len(parts) and parts[i + 1] == "5":
            # 256-color foreground: 38;5;<idx>
            try:
                idx = int(parts[i + 2])
            except ValueError:
                idx = -1
            # Cheap mapping: treat 8–15 as bright base colors
            if 8 <= idx <= 15:
                base = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"][idx - 8]
                style_bits.append(f"bright_{base}")
            i += 2
        i += 1

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_bits: list[str] = []
    for b in style_bits:
        if b not in seen:
            seen.add(b)
            unique_bits.append(b)

    return " ".join(unique_bits)


def _parse_ls_colors(env: str | None = None) -> Dict[str, str]:
    """
    Parse $LS_COLORS into a mapping like:
        { 'di': 'bold blue', 'ln': 'bold cyan', '*.py': 'bold bright_green', ... }
    """
    if env is None:
        env = os.environ.get("LS_COLORS", "") or ""

    mapping: Dict[str, str] = {}
    if not env:
        return mapping

    for chunk in env.split(":"):
        if "=" not in chunk:
            continue
        key, val = chunk.split("=", 1)
        key = key.strip()
        if not key:
            continue
        style = _ansi_seq_to_style(val.strip())
        if style:
            mapping[key] = style
    return mapping


# --- Built-in schemes ----------------------------------------------------------

_DEFAULT_SCHEMES: Dict[str, Dict[str, str]] = {
    # Roughly "classic ls" colors
    "classic": {
        "di": "bold blue",
        "ln": "bold cyan",
        "ex": "bold green",
        "pi": "bold magenta",
        "so": "bold magenta",
        "bd": "bold yellow",
        "cd": "bold yellow",
    },
    # High contrast for dark backgrounds
    "high_contrast": {
        "di": "bold bright_cyan",
        "ln": "bold bright_magenta",
        "ex": "bold bright_green",
        "pi": "bold bright_yellow",
        "so": "bold bright_yellow",
        "bd": "bold bright_red",
        "cd": "bold bright_red",
    },
    # Softer, more pastel-ish palette
    "pastel": {
        "di": "bold sky_blue1",
        "ln": "bold plum1",
        "ex": "bold chartreuse1",
        "pi": "medium_purple",
        "so": "medium_purple",
        "bd": "gold1",
        "cd": "gold1",
    },
}


def _boost_for_dark_background(mapping: Dict[str, str]) -> Dict[str, str]:
    """Turn 'blue' into 'bright_blue', etc, for dark backgrounds."""
    boosted: Dict[str, str] = {}
    for key, style in mapping.items():
        bits = style.split()
        new_bits: list[str] = []
        for b in bits:
            if b in ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"):
                new_bits.append(f"bright_{b}")
            else:
                new_bits.append(b)
        boosted[key] = " ".join(new_bits)
    return boosted


def _effective_map(mode: str, scheme: str, dark_background: bool) -> Dict[str, str]:
    """
    Compute the effective LS_COLORS map for the given mode/scheme.
    mode:
      - "env"            → use $LS_COLORS as-is
      - "env_with_boost" → use $LS_COLORS, but brighten for dark backgrounds
      - "scheme"         → ignore env and use built-in scheme
    """
    if mode in ("env", "env_with_boost"):
        base = _parse_ls_colors()
        if not base:
            base = _DEFAULT_SCHEMES["classic"].copy()
    elif mode == "scheme":
        base = _DEFAULT_SCHEMES.get(scheme, _DEFAULT_SCHEMES["classic"]).copy()
    else:
        base = _DEFAULT_SCHEMES["classic"].copy()

    if dark_background and mode in ("env_with_boost", "scheme"):
        base = _boost_for_dark_background(base)

    return base


def style_for_path(
    path: Path,
    *,
    mode: str = "env_with_boost",
    scheme: str = "classic",
    dark_background: bool = True,
) -> str:
    """
    Return a Rich/Textual style string for this path based on:

    - $LS_COLORS (if mode starts with "env")
    - built-in schemes (if mode == "scheme")
    - dark_background hint (boosts dark colors)
    """
    colors_map = _effective_map(mode, scheme, dark_background)

    # Try to stat once
    try:
        st = path.lstat()
        stat_mode = st.st_mode
    except OSError:
        st = None
        stat_mode = 0

    is_dir = statmod.S_ISDIR(stat_mode) if st else path.is_dir()
    is_symlink = statmod.S_ISLNK(stat_mode) if st else path.is_symlink()
    is_file = statmod.S_ISREG(stat_mode) if st else path.is_file()

    # Directories
    if is_dir:
        return colors_map.get("di", "blue")

    # Symlinks
    if is_symlink:
        return colors_map.get("ln", "cyan")

    # Special files (block/char devices, sockets, pipes)
    if st:
        if statmod.S_ISBLK(stat_mode) and "bd" in colors_map:
            return colors_map["bd"]
        if statmod.S_ISCHR(stat_mode) and "cd" in colors_map:
            return colors_map["cd"]
        if statmod.S_ISFIFO(stat_mode) and "pi" in colors_map:
            return colors_map["pi"]
        if statmod.S_ISSOCK(stat_mode) and "so" in colors_map:
            return colors_map["so"]

    # Executables
    try:
        if is_file and os.access(path, os.X_OK):
            return colors_map.get("ex", "bold green")
    except Exception:
        pass

    # Extension patterns from LS_COLORS, e.g. '*.py'
    if is_file:
        suffix = path.suffix  # includes leading dot, e.g. ".py"
        if suffix:
            key = f"*{suffix}"
            if key in colors_map:
                return colors_map[key]

    # Default: no special style
    return ""
