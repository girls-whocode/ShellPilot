from __future__ import annotations
from pathlib import Path
from typing import List

def list_dir(path: Path) -> List[Path]:
    """Return sorted directory contents (dirs first, then files)."""
    entries = list(path.iterdir())
    dirs = sorted([e for e in entries if e.is_dir()])
    files = sorted([e for e in entries if e.is_file()])
    return dirs + files

def rename_entry(path: Path, new_name: str) -> Path:
    """Rename a file or directory to `new_name` within the same parent."""
    target = path.with_name(new_name)
    path.rename(target)
    return target

def chmod_entry(path: Path, mode: int) -> None:
    """Apply chmod(mode) to the path."""
    path.chmod(mode)

def mkdir_entry(parent: Path, name: str) -> Path:
    """Create a subdirectory `name` beneath `parent`."""
    new_dir = parent / name
    new_dir.mkdir(parents=False, exist_ok=False)
    return new_dir

def touch_entry(path: Path) -> Path:
    """Create an empty file (or update mtime) at `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    return path
