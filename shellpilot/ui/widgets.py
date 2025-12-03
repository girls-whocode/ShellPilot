# shellpilot/ui/widgets.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Optional
import os
import stat as statmod
import pwd
import grp
import fnmatch
import re

from rich.syntax import Syntax
from rich.console import Group
from rich.text import Text

from textual.widgets import Static, ListView, ListItem

from shellpilot.core.fs_browser import list_dir
from shellpilot.core.commands import ShellCommand
from shellpilot.utils.ls_colors import style_for_path
from shellpilot.core.search import SearchQuery, SearchMode, FileTypeFilter, fuzzy_score
from shellpilot.utils.preview import (
    is_code_file,
    is_text_file,
    is_image_file,
)

def format_mode(mode: int) -> str:
    """Return a string like '-rw-r--r--'."""
    return statmod.filemode(mode)

def icon_for_entry(path: Path) -> str:
    """Return a simple icon based on file type."""
    if path.is_dir():
        return "📁"
    if path.is_symlink():
        return "🔗"

    suffix = path.suffix.lower()
    if suffix == ".py":
        return "🐍"
    if suffix in {".sh", ".bash"}:
        return ""
    if suffix in {".md", ".txt"}:
        return "📄"
    if suffix in {".json", ".yml", ".yaml", ".toml"}:
        return "🧾"
    return "📃"

class FileList(ListView):
    """ListView specialized for displaying filesystem entries."""

    def __init__(self, path: Path, *args, **kwargs):
        self.current_path = path
        self._filter_text: str = ""
        self._search_query: SearchQuery = SearchQuery(
            mode=SearchMode.FUZZY
        )
        super().__init__(*args, **kwargs)

    def on_mount(self) -> None:
        self.refresh_entries()

    def set_filter(self, text: str) -> None:
        """Set a name filter (fuzzy by default; wildcard if * or ? present)."""
        raw = text.strip()

        recursive = False
        if raw.startswith("//"):
            recursive = True
            raw = raw[2:].lstrip()

        self._filter_text = raw
        q = self._search_query
        q.text = self._filter_text
        q.recursive = recursive

        if any(ch in self._filter_text for ch in ("*", "?")):
            q.mode = SearchMode.PLAIN
        else:
            q.mode = SearchMode.FUZZY

        self.refresh_entries()

    def set_search_query(self, query: SearchQuery) -> None:
        """Accept a SearchQuery object from the app and refresh entries."""
        self._search_query = query
        self._filter_text = (getattr(query, "text", "") or "").strip()
        self.refresh_entries()

    def refresh_entries(self) -> None:
        """Populate the list with entries from current_path, honoring filter."""
        # Don't try to mount children before the FileList is attached

        if not self.is_attached:
            return

        self.clear()
        current = self.current_path

        q = self._search_query
        recursive = getattr(q, "recursive", False)

        parent: Path | None = None

        try:
            if current.parent != current:
                parent = current.parent
        except Exception:
            parent = None

        if parent is not None and not recursive:
            try:
                st = parent.stat()
                mode_str = format_mode(st.st_mode)
                try:
                    owner = pwd.getpwuid(st.st_uid).pw_name
                except KeyError:
                    owner = str(st.st_uid)
                try:
                    group = grp.getgrgid(st.st_gid).gr_name
                except KeyError:
                    group = str(st.st_gid)

            except Exception:
                mode_str = "d?????????"
                owner = "?"
                group = "?"

            meta = f"{mode_str} {owner:8} {group:8} dir  "

            parent_style = style_for_path(parent)
            if parent_style:
                name_part = f"[{parent_style}]📁 ..[/{parent_style}]"
            else:
                name_part = "📁 .."

            label = f"[dim]{meta}[/dim]  {name_part}"

            item = ListItem(Static(label))
            item.data = str(parent)
            self.append(item)

        if not recursive:
            for entry in list_dir(current):
                if not self._matches_filter(entry):
                    continue

                try:
                    st = entry.stat()
                except FileNotFoundError:
                    mode_str = "??????????"
                    owner = "?"
                    group = "?"
                else:
                    mode_str = format_mode(st.st_mode)
                    try:
                        owner = pwd.getpwuid(st.st_uid).pw_name
                    except KeyError:
                        owner = str(st.st_uid)
                    try:
                        group = grp.getgrgid(st.st_gid).gr_name
                    except KeyError:
                        group = str(st.st_gid)

                if entry.is_dir():
                    ftype = "dir"
                elif entry.is_symlink():
                    ftype = "link"
                elif entry.is_file():
                    ftype = "file"
                else:
                    ftype = "other"

                icon = icon_for_entry(entry)
                name_display = f"{entry.name}/" if entry.is_dir() else entry.name

                meta = f"{mode_str} {owner:8} {group:8} {ftype:5}"

                style = style_for_path(entry)
                if style:
                    name_part = f"[{style}]{icon} {name_display}[/{style}]"
                else:
                    name_part = f"{icon} {name_display}"

                label = f"[dim]{meta}[/dim]  {name_part}"

                item = ListItem(Static(label))
                item.data = str(entry)
                self.append(item)

        else:
            max_results = 1000
            count = 0

            for root, dirs, files in os.walk(current):
                root_path = Path(root)
                names = sorted(dirs) + sorted(files)

                for name in names:
                    entry = root_path / name

                    if not self._matches_filter(entry):
                        continue

                    try:
                        st = entry.stat()
                    except FileNotFoundError:
                        mode_str = "??????????"
                        owner = "?"
                        group = "?"
                    else:
                        mode_str = format_mode(st.st_mode)
                        try:
                            owner = pwd.getpwuid(st.st_uid).pw_name
                        except KeyError:
                            owner = str(st.st_uid)
                        try:
                            group = grp.getgrgid(st.st_gid).gr_name
                        except KeyError:
                            group = str(st.st_gid)

                    if entry.is_dir():
                        ftype = "dir"
                    elif entry.is_symlink():
                        ftype = "link"
                    elif entry.is_file():
                        ftype = "file"
                    else:
                        ftype = "other"

                    icon = icon_for_entry(entry)
                    rel = entry.relative_to(current)
                    rel_str = rel.as_posix()
                    name_display = f"{rel_str}/" if entry.is_dir() else rel_str

                    meta = f"{mode_str} {owner:8} {group:8} {ftype:5}"

                    style = style_for_path(entry)
                    if style:
                        name_part = f"[{style}]{icon} {name_display}[/{style}]"
                    else:
                        name_part = f"{icon} {name_display}"

                    label = f"[dim]{meta}[/dim]  {name_part}"

                    item = ListItem(Static(label))
                    item.data = str(entry)
                    self.append(item)

                    count += 1
                    if count >= max_results:
                        break

                if count >= max_results:
                    break

    def _matches_filter(self, path: Path) -> bool:
        q = getattr(self, "_search_query", SearchQuery())

        if q.type_filter is not FileTypeFilter.ANY:
            if q.type_filter is FileTypeFilter.DIR:
                if not path.is_dir():
                    return False
            else:
                if path.is_dir():
                    return False
                if q.type_filter is FileTypeFilter.CODE and not is_code_file(path):
                    return False
                if q.type_filter is FileTypeFilter.TEXT and not is_text_file(path):
                    return False
                if q.type_filter is FileTypeFilter.IMAGE and not is_image_file(path):
                    return False

        raw = (q.text or "").strip()
        if not raw:
            return True

        name = path.name
        case_sensitive = q.case_sensitive

        if q.mode is SearchMode.REGEX:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                pattern = re.compile(raw, flags=flags)
            except re.error:
                return False
            return pattern.search(name) is not None

        if q.mode is SearchMode.FUZZY:
            score = fuzzy_score(raw, name, case_sensitive=case_sensitive)
            return score >= 0.55

        tokens = raw.split()
        include_patterns: list[str] = []
        exclude_patterns: list[str] = []

        for token in tokens:
            if token.startswith("-") and len(token) > 1:
                exclude_patterns.append(token[1:])
            else:
                include_patterns.append(token)

        if not case_sensitive:
            name_cmp = name.lower()
            include_patterns = [p.lower() for p in include_patterns]
            exclude_patterns = [p.lower() for p in exclude_patterns]
        else:
            name_cmp = name

        def matches_patterns(patterns: list[str], require_match: bool) -> bool:
            if require_match and not patterns:
                return True

            matched = False
            for pat in patterns:
                if any(ch in pat for ch in "*?[]"):
                    if fnmatch.fnmatchcase(name_cmp, pat):
                        matched = True
                else:
                    if pat in name_cmp:
                        matched = True

                if matched:
                    return True if require_match else True

            return matched if require_match else False

        if include_patterns and not matches_patterns(include_patterns, True):
            return False

        if exclude_patterns and matches_patterns(exclude_patterns, False):
            return False

        return True

    def get_selected_path(self) -> Optional[Path]:
        """Return the full Path of the currently selected entry, if any."""
        if self.index is None:
            return None

        try:
            item = self.children[self.index]
        except IndexError:
            return None

        # Adjust this depending on how you're storing the path.
        # If your ListItem has a .data or .path attribute, prefer that.
        if hasattr(item, "data") and isinstance(item.data, Path):
            return item.data
        if hasattr(item, "path") and isinstance(item.path, Path):
            return item.path

        # Fallback: use the label text with current_path
        label = getattr(item, "label", None)
        if label is None:
            return None

        name = str(label).strip()
        if not name:
            return None

        # Handle ".." parent entry if you use it
        if name == "..":
            return self.current_path.parent

        return self.current_path / name

class CommandPreview(Static):
    """Shows the current command explanation and planned command."""

    def show_command(self, cmd: ShellCommand) -> None:
        warning = ""
        if cmd.dangerous:
            warning = (
                "\n[red][b]Warning:[/b] This command can change or delete data. "
                "You will be asked to confirm before it runs.[/red]"
            )

        text = (
            f"[b]{cmd.description}[/b]\n\n"
            f"{cmd.explanation}\n\n"
            f"[b]Command that will be used:[/b]\n"
            f"[code]{cmd.full_display()}[/code]"
            f"{warning}\n\n"
            "Press [b]Enter[/b] to run this command."
        )
        self.update(text)

class OutputPanel(Static):
    """Displays real command execution results OR syntax-highlighted code."""

    def show_result(self, stdout: str, stderr: str, rc: int) -> None:
        text = f"[b]Exit status:[/b] {rc}\n\n"
        if stdout:
            text += f"[b]STDOUT:[/b]\n{stdout}\n"
        if stderr:
            text += f"\n[b]STDERR:[/b]\n{stderr}"
        if not stdout and not stderr:
            text += "[i](No output)[/i]"
        self.update(text)

    def show_code(self, code: str, path: Path, language: str) -> None:
        header = Text(f"[{language.upper()}] {path.name}", style="bold magenta")
        try:
            syntax = Syntax(
                code,
                language,
                theme="monokai",
                line_numbers=True,
                word_wrap=False,
            )
            renderable = Group(header, Text("\n"), syntax)
        except Exception:
            body = Text(code)
            renderable = Group(header, Text("\n"), body)

        self.update(renderable)

    def show_hexdump(self, dump: str, path: Path) -> None:
        header = Text(
            f"[BINARY] {path.name} (hex preview, first bytes)",
            style="bold yellow",
        )
        try:
            syntax = Syntax(
                dump,
                "asm",
                theme="monokai",
                line_numbers=False,
                word_wrap=False,
            )
            renderable = Group(header, Text("\n"), syntax)
        except Exception:
            body = Text(dump)
            renderable = Group(header, Text("\n"), body)

        self.update(renderable)
