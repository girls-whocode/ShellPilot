# shellpilot/utils/preview.py
from __future__ import annotations
from pathlib import Path
from typing import Optional, Iterable
import os
import bz2
import gzip
import lzma

from rich.console import Group
from rich.text import Text

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None


LOG_SUFFIXES = {".log", ".journal"}  # “text” log-ish suffixes
LOG_LIKE_NAMES = {"messages", "syslog", "dmesg", "kern.log", "secure"}
LOG_HINT_KEYWORDS = {"log", "error", "errors", "warn", "warning", "journal"}
COMPRESSED_LOG_SUFFIXES = {".gz", ".xz", ".bz2", ".lzma"}

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
CODE_SUFFIXES = {
    ".py", ".sh", ".bash", ".zsh", ".c", ".h", ".cpp", ".hpp", ".cc",
    ".js", ".ts", ".tsx", ".rs", ".go", ".rb", ".php", ".java",
}
TEXT_SUFFIXES = {
    ".txt", ".log", ".cfg", ".conf", ".ini", ".md", ".rst",
    ".yaml", ".yml", ".json", ".csv",
}


def is_image_file(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_SUFFIXES


def is_code_file(path: Path) -> bool:
    return path.suffix.lower() in CODE_SUFFIXES


def is_text_file(path: Path) -> bool:
    sfx = path.suffix.lower()
    return sfx in TEXT_SUFFIXES or is_code_file(path)


def language_for_path(path: Path) -> Optional[str]:
    """Map file extensions to Rich/pygments lexer names."""
    suffix = path.suffix.lower()

    # Code-ish
    if suffix == ".py":
        return "python"
    if suffix in {".sh", ".bash"}:
        return "bash"
    if suffix == ".js":
        return "javascript"
    if suffix == ".ts":
        return "typescript"
    if suffix == ".rs":
        return "rust"
    if suffix == ".go":
        return "go"
    if suffix == ".c":
        return "c"
    if suffix in {".cpp", ".cc", ".cxx"}:
        return "cpp"

    # Config / data
    if suffix == ".json":
        return "json"
    if suffix in {".yml", ".yaml"}:
        return "yaml"
    if suffix == ".toml":
        return "toml"
    if suffix in {".ini", ".cfg", ".conf"}:
        return "ini"

    # Markup / docs
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix in {".html", ".htm"}:
        return "html"
    if suffix == ".css":
        return "css"

    # Plain-ish text
    if suffix in {".txt", ".log"}:
        return "text"
    if suffix == ".csv":
        return "csv"

    return None


def pillow_rich_image(path: Path, max_width_chars: int = 40) -> Optional[Group]:
    """
    Render an image as a Rich Group using Pillow, for terminals that don't have rich.image.

    Uses background-colored spaces as pixels. max_width_chars controls horizontal size.
    """
    if PILImage is None:
        return None

    try:
        img = PILImage.open(path).convert("RGB")
    except Exception:
        return None

    w, h = img.size

    if w > max_width_chars:
        new_w = max_width_chars
        new_h = max(1, int(h * (new_w / w)))
        img = img.resize((new_w, new_h))
        w, h = img.size

    lines: list[Text] = []

    for y in range(h):
        line = Text()
        for x in range(w):
            r, g, b = img.getpixel((x, y))
            style = f"on #{r:02x}{g:02x}{b:02x}"
            line.append("  ", style=style)
        lines.append(line)

    header = Text(f"[IMAGE] {path.name}", style="bold magenta")
    return Group(header, Text("\n"), *lines)


def is_binary_file(path: Path, sample_size: int = 2048) -> bool:
    """Heuristic: decide if a file is binary by sampling bytes."""
    try:
        with path.open("rb") as f:
            chunk = f.read(sample_size)
    except Exception:
        return False

    if not chunk:
        return False

    if b"\x00" in chunk:
        return True

    text_bytes = set(range(32, 127)) | {9, 10, 13}
    nontext = sum(1 for b in chunk if b not in text_bytes)

    return nontext / len(chunk) > 0.30


def hex_dump(path: Path, max_bytes: int = 4096) -> str:
    """Produce a classic hex+ASCII dump of the first max_bytes of the file."""
    try:
        with path.open("rb") as f:
            data = f.read(max_bytes)
    except Exception as e:
        return f"<< Failed to read file for hex dump: {e} >>"

    lines: list[str] = []
    length = len(data)

    for offset in range(0, length, 16):
        chunk = data[offset : offset + 16]
        hex_bytes = " ".join(f"{b:02x}" for b in chunk)
        hex_bytes = hex_bytes.ljust(16 * 3 - 1)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{offset:08x}  {hex_bytes}  |{ascii_part}|")

    if length == max_bytes:
        lines.append(f"... truncated at {max_bytes} bytes ...")

    return "\n".join(lines)


def is_log_file(path: Path) -> bool:
    """
    Heuristic to decide whether something is “log-like”.
    """
    name = path.name
    name_lower = name.lower()

    if name in LOG_LIKE_NAMES:
        return True

    suffixes = [s.lower() for s in path.suffixes]
    if any(s in LOG_SUFFIXES for s in suffixes):
        return True

    if name_lower.startswith("syslog.") or name_lower.startswith("messages."):
        return True

    if any(part.lower() in {"log", "logs"} for part in path.parts):
        return True

    if any(hint in name_lower for hint in LOG_HINT_KEYWORDS):
        if not any(name_lower.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")):
            return True

    return False


def read_log_text(path: Path, max_bytes: int = 512 * 1024) -> str:
    """
    Read up to max_bytes of a (possibly compressed) log file as text.
    """
    suffixes = [s.lower() for s in path.suffixes]
    last = suffixes[-1] if suffixes else ""

    try:
        if last == ".gz":
            with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
                return f.read(max_bytes)
        elif last in {".xz", ".lzma"}:
            with lzma.open(path, "rt", encoding="utf-8", errors="replace") as f:
                return f.read(max_bytes)
        elif last == ".bz2":
            with bz2.open(path, "rt", encoding="utf-8", errors="replace") as f:
                return f.read(max_bytes)
        else:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                return f.read(max_bytes)
    except PermissionError:
        raise
