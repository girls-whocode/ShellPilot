from __future__ import annotations
from pathlib import Path
import os
import stat as statmod
import subprocess
import json
import shutil
import uuid
import sys
import threading
from typing import Any, Optional
from datetime import datetime

from rich.syntax import Syntax
from rich.console import Group
from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Footer, Input, ListView
from textual.containers import Horizontal, Vertical, VerticalScroll

from shellpilot.core.fs_browser import list_dir  # still used in action menu
from shellpilot.core.commands import (
    build_ls_command,
    build_view_file_command,
    ShellCommand,
)
from shellpilot.utils.shell import run_shell_command
from shellpilot.ui.action_menu import ActionMenu
from shellpilot.utils.ls_colors import style_for_path
from shellpilot.utils.log_highlighter import LogHighlighter
from shellpilot.core.search import SearchQuery, SearchMode, FileTypeFilter, fuzzy_score
from shellpilot.ai.engine import get_engine

from shellpilot.core.git import is_git_repo, get_git_status
from shellpilot.ui.widgets import FileList, CommandPreview, OutputPanel
from shellpilot.utils.preview import (
    is_log_file,
    read_log_text,
    is_binary_file,
    hex_dump,
    language_for_path,
    pillow_rich_image,
)

log_highlighter = LogHighlighter()

def _has_passwordless_sudo() -> bool:
    """
    Return True if the current user appears to have passwordless sudo.

    We use `sudo -n true`:
      - exit 0 → sudo allowed without password
      - exit != 0 → either not in sudoers or password required
    """
    try:
        result = subprocess.run(
            ["sudo", "-n", "true"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except FileNotFoundError:
        # no sudo installed
        return False
    except Exception:
        return False

class ShellPilotApp(App):
    """Main Textual application for ShellPilot."""

    CSS_PATH = "app.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("enter", "run_command", "Run command"),
        ("left", "up_directory", "Up dir"),
        ("right", "enter_selected", "Enter / preview"),
        ("h", "go_home", "Home (~)"),
        ("t", "go_trash", "Trash"),
        ("delete", "trash_selected", "Move to trash"),
        ("/", "focus_search", "Filter"),
        ("ctrl+b", "add_bookmark", "Bookmark dir"),
        ("ctrl+j", "next_bookmark", "Next bookmark"),
        ("e", "open_in_editor", "Edit file"),
        ("?", "toggle_help", "Toggle help"),
        Binding(":", "open_action_menu", "Command"),
        Binding("a", "ai_explain_file", "AI Explain", show=True),
    ]

    def __init__(self, start_path: Optional[Path] = None, **kwargs):
        # Session persistence
        self._session_path = Path.home() / ".config" / "shellpilot" / "session.json"
        saved_dir, saved_bookmarks, saved_help_visible = self._load_session()

        effective_start = start_path or (Path(saved_dir) if saved_dir else Path.cwd())
        self.start_path = effective_start

        # Initialize trash before App startup
        self.trash_dir, self.trash_index_path = self._init_trash_dir()
        self.trash_index: dict[str, dict] = self._load_trash_index()

        super().__init__(**kwargs)
        
        self._search_query: SearchQuery = SearchQuery()
        self.file_list: Optional[FileList] = None
        self.preview: Optional[CommandPreview] = None
        self.output: Optional[OutputPanel] = None
        self.breadcrumb: Optional[Static] = None
        self.search_input: Optional[Input] = None
        self.status: Optional[Static] = None
        self.preview_container: Optional[VerticalScroll] = None
        self.footer_bar: Optional[Footer] = None

        self._last_command: Optional[ShellCommand] = None

        # For syntax-highlighted code preview
        self._last_file_path: Optional[Path] = None
        self._last_file_language: Optional[str] = None

        # Bookmarks: paths + current index
        self.bookmarks: list[Path] = saved_bookmarks
        self.current_bookmark_index: Optional[int] = None

        self._help_visible: bool = saved_help_visible

        # Status + Git integration
        self._base_status: str = ""
        self.in_git_repo: bool = False
        self.git_status: Optional[dict[str, Any]] = None

    # ---------- Session helpers ----------
    def _load_session(self) -> tuple[Optional[str], list[Path], bool]:
        """Load last directory, bookmarks, and help visibility from disk, if present."""
        try:
            data = json.loads(self._session_path.read_text())
            last_dir = data.get("last_dir")
            bookmarks = [Path(p) for p in data.get("bookmarks", [])]
            help_visible = bool(data.get("help_visible", True))
            return last_dir, bookmarks, help_visible
        except FileNotFoundError:
            # First run: no session yet → default help visible
            return None, [], True
        except Exception:
            # Corrupt / unreadable session; ignore and use safe defaults.
            return None, [], True

    def _save_session(self) -> None:
        """Persist last directory, bookmarks, and help visibility."""
        try:
            self._session_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "last_dir": str(self._current_dir()),
                "bookmarks": [str(p) for p in self.bookmarks],
                "help_visible": self._help_visible,
            }
            self._session_path.write_text(json.dumps(data, indent=2))
        except Exception:
            # Don't crash the app if saving session fails.
            pass

    # ---------- Thread helper for background work ----------
    def call_in_thread(self, func, *args, **kwargs) -> None:
        """Tiny compatibility shim: run *func* in a background thread.

        Newer Textual versions have App.call_in_thread; older ones don’t.
        This shim keeps our AI worker code working everywhere.
        """
        import threading

        thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        thread.start()

    # --- Utility: bridge helpers used by the action menu ---
    def get_current_entry_path(self) -> Path | None:
        """Return the currently highlighted entry (file/dir) as a Path."""
        return self._get_selected_path()

    def get_current_directory(self) -> Path:
        """Return the current directory in the file browser."""
        return self._current_dir()

    def refresh_browser(self) -> None:
        """Refresh directory listing after FS change."""
        if self.file_list:
            self.file_list.refresh_entries()
        self._update_breadcrumb()

    def _set_status(self, msg: str) -> None:
        """Set the base status text (keys/help/etc) and merge Git info."""
        self._base_status = msg
        self._update_status_with_git()

    def _format_git_status_summary(self) -> str:
        """Return a short Git summary for the status bar, or '' if not in a repo."""
        if not self.in_git_repo or not self.git_status:
            return ""

        gs = self.git_status
        branch = gs.get("branch") or "?"

        # You can tweak this string however you like
        return (
            f" {branch}  "
            f"+{gs.get('added', 0)} "
            f"~{gs.get('modified', 0)} "
            f"-{gs.get('deleted', 0)} "
            f"?{gs.get('untracked', 0)}"
        )

    def _update_status_with_git(self) -> None:
        """Render the current base status plus Git info into the status widget."""
        if not self.status:
            return

        git_part = self._format_git_status_summary()
        if git_part:
            full = f"{self._base_status}    |    {git_part}"
        else:
            full = self._base_status

        self.status.update(full)

    # ---------- Trash helpers ----------
    def _init_trash_dir(self) -> tuple[Path, Path]:
        """
        Ensure a trash directory exists and return (trash_dir, index_path).

        We follow XDG-ish style:
          $XDG_DATA_HOME/shellpilot/trash
        or fallback to:
          ~/.local/share/shellpilot/trash
        """
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            base = Path(xdg_data_home)
        else:
            base = Path.home() / ".local" / "share"

        trash_dir = base / "shellpilot" / "trash"
        trash_dir.mkdir(parents=True, exist_ok=True)

        index_path = trash_dir / "index.json"
        return trash_dir, index_path

    def _load_trash_index(self) -> dict[str, dict]:
        """Load JSON index of trashed files -> original paths."""
        try:
            data = json.loads(self.trash_index_path.read_text())
            # validate a bit
            if isinstance(data, dict):
                return data
        except FileNotFoundError:
            return {}
        except Exception:
            return {}
        return {}

    def _save_trash_index(self) -> None:
        """Persist trash index to disk."""
        try:
            self.trash_index_path.parent.mkdir(parents=True, exist_ok=True)
            self.trash_index_path.write_text(json.dumps(self.trash_index, indent=2))
        except Exception:
            # don't crash the app if saving fails
            pass

    def _in_trash_view(self) -> bool:
        """Return True if the current directory is the trash directory."""
        try:
            return self._current_dir().resolve() == self.trash_dir.resolve()
        except Exception:
            return False
        
    def _update_footer_bindings_visibility(self) -> None:
        """
        Show 'r' / 'E' in the footer only when viewing the trash.

        The bindings still exist everywhere, but their labels are hidden
        from the Footer outside trash view.
        """
        in_trash = self._in_trash_view()

        # Try to be compatible across Textual versions:
        # - Some expose `self.bindings` (BindingMap / Bindings)
        # - Some use `self._bindings`
        bindings_obj = getattr(self, "bindings", None) or getattr(self, "_bindings", None)
        if bindings_obj is None:
            return

        # Many versions expose the actual list as `.bindings`
        seq = getattr(bindings_obj, "bindings", None)
        if seq is None:
            # Fallback: maybe the object itself is iterable
            seq = bindings_obj

        try:
            for binding in seq:
                # binding is a textual.binding.Binding
                if getattr(binding, "key", None) in ("r", "E"):
                    # Only show in trash view
                    setattr(binding, "show", in_trash)
        except TypeError:
            # bindings_obj wasn't iterable after all; bail quietly
            return

        # Ask the Footer to re-render with updated show flags
        if self.footer_bar:
            self.footer_bar.refresh()

    # ---------- Layout ----------
    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        with Horizontal():
            # LEFT PANE: breadcrumb + search + file list
            with Vertical(id="left-pane"):
                self.breadcrumb = Static("", id="breadcrumb")
                yield self.breadcrumb

                self.search_input = Input(
                    placeholder="Filter files (e.g. '*.log', 'error', '// for recursive)…",
                    id="search",
                )
                yield self.search_input

                self.file_list = FileList(self.start_path, id="files")
                yield self.file_list

            # MIDDLE: actual output of the last command / code preview
            with VerticalScroll(id="output-container"):
                self.output = OutputPanel("No command executed yet.")
                yield self.output

            # RIGHT: help / command explanation (less in-your-face)
            with VerticalScroll(id="preview-container") as preview_container:
                self.preview = CommandPreview(
                    "Select a directory or file to see a command."
                )
                yield self.preview
            self.preview_container = preview_container

        # STATUS BAR
        self.status = Static("", id="status")
        yield self.status

        self.footer_bar = Footer()
        yield self.footer_bar

    def on_mount(self) -> None:
        """App mounted: show an initial command for the start directory."""
        self._update_breadcrumb()
        if self.preview:
            cmd = build_ls_command(self.start_path)
            self._last_command = cmd
            self.preview.show_command(cmd)

        # Focus file list by default
        if self.file_list:
            self.set_focus(self.file_list)

        # Start with empty filter
        if self.search_input:
            self.search_input.value = ""

        # Initial status line
        self._update_search_status()

        # 🔹 Initialize Git state for the starting directory
        self._refresh_git_state(self._current_dir())

        # Apply persisted help visibility on startup
        if self.preview_container:
            self.preview_container.display = self._help_visible

        try:
            left_pane = self.query_one("#left-pane", Vertical)
            output_container = self.query_one("#output-container", VerticalScroll)
        except Exception:
            # If the layout hasn't fully settled for some reason, just force a refresh
            self.refresh(layout=True)
        else:
            if self._help_visible:
                # Three-column mode: left | output | help
                left_pane.styles.width = "1fr"
                output_container.styles.width = "1fr"
            else:
                # Two-column mode: left | output (help hidden)
                left_pane.styles.width = "1fr"
                output_container.styles.width = "2fr"

            self.refresh(layout=True)

        self._update_footer_bindings_visibility()

    # ---------- Helpers ----------
    def _show_ai_response(self, title: str, body: str) -> None:
        """Render AI response in the main output panel (middle column)."""
        panel = Panel.fit(
            body,
            title=title,
            border_style="cyan",
        )

        # Show AI result in the middle OutputPanel so it's always visible
        if getattr(self, "output", None) is not None:
            self.output.update(panel)

    def _current_dir(self) -> Path:
        if self.file_list:
            return self.file_list.current_path
        return self.start_path

    def _update_breadcrumb(self) -> None:
        """Update the breadcrumb display with the current path."""
        if not self.breadcrumb:
            return
        path = self._current_dir()
        self.breadcrumb.update(f"[b]Path:[/b] {path}")

    def _refresh_git_state(self, path: Path) -> None:
        """
        Update Git state (in/out of repo + status summary) for the given path.
        """
        try:
            self.in_git_repo = is_git_repo(path)
        except Exception:
            self.in_git_repo = False

        if self.in_git_repo:
            try:
                self.git_status = get_git_status(path)
            except Exception:
                self.git_status = None
        else:
            self.git_status = None

        # Re-render the status bar with the new Git info
        self._update_status_with_git()

    def _set_directory(self, path: Path) -> None:
        """Centralized place to change directory and refresh UI."""
        if not self.file_list:
            return

        # Keep old path so we can roll back if we can't enter the new one
        old_path = self.file_list.current_path

        # Reset last file preview when changing dirs
        self._last_file_path = None
        self._last_file_language = None

        try:
            self.file_list.current_path = path
            self.file_list.refresh_entries()
        except PermissionError:
            # Roll back to previous directory
            self.file_list.current_path = old_path

            # Figure out who we are + whether we likely have sudo
            euid = os.geteuid() if hasattr(os, "geteuid") else -1
            has_pwless_sudo = _has_passwordless_sudo()

            if self.output:
                if euid == 0:
                    # Running as root but still blocked → ACLs / SELinux / mount perms
                    self.output.update(
                        "[b]Permission denied listing directory, even as root.[/b]\n\n"
                        f"Path: {path}\n\n"
                        "This is likely due to ACLs, SELinux, or special mount options.\n"
                        "Try:\n"
                        "  • [code]ls -ld {path}[/code]\n"
                        "  • [code]getfacl {path}[/code]\n"
                        "  • [code]ls -Z {path}[/code] (for SELinux)\n"
                    )
                    self._set_status("Permission denied entering directory (root)")
                else:
                    # Non-root user
                    if has_pwless_sudo:
                        hint = (
                            "It looks like you can use sudo *without* a password.\n\n"
                            "To inspect this directory, you can run:\n"
                            f"  [code]sudo ls -l {path}[/code]\n\n"
                            "Or restart ShellPilot with elevated privileges if you intend "
                            "to browse protected system directories a lot:\n\n"
                            "  [code]sudo shellpilot[/code]\n"
                        )
                    else:
                        hint = (
                            "You do not have permission to list this directory.\n\n"
                            "To inspect it, try one of:\n"
                            f"  • [code]sudo ls -l {path}[/code]\n"
                            f"  • [code]sudo find {path} -maxdepth 1 -ls[/code]\n\n"
                            "If you frequently need to browse system logs, you may want to "
                            "run ShellPilot under sudo explicitly."
                        )

                    self.output.update(
                        "[b]Permission denied entering directory.[/b]\n\n"
                        f"Path: {path}\n\n" + hint
                    )
                    self._set_status("Permission denied entering directory")

            return  # Don't update breadcrumb/session on failure

        # If we got here, directory listing succeeded
        self._update_breadcrumb()

        # Refresh Git state for this directory
        self._refresh_git_state(path)

        if self.preview:
            cmd = build_ls_command(path)
            self._last_command = cmd
            self.preview.show_command(cmd)

        if self.output:
            self.output.update(
                "(Select a file to preview, or press Enter to list this directory)"
            )

        self._set_status(f"In directory: {path}")
        self._save_session()
        self._update_footer_bindings_visibility()

    def _get_selected_path(self) -> Optional[Path]:
        """Return the Path of the currently selected item in the file list."""
        if not self.file_list or not self.file_list.children:
            return None
        index = self.file_list.index
        if index is None:
            return None
        try:
            item = self.file_list.children[index]
        except IndexError:
            return None
        data = getattr(item, "data", None)
        if not data:
            return None
        return Path(data)

    # ---------- Events ----------
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Navigate into directory or preview file content when selection changes."""
        if not self.file_list or not self.preview:
            return

        entry_path = Path(event.item.data)

        if entry_path.is_dir():
            # Navigate immediately into the directory
            self._set_directory(entry_path)
        else:
            # Preview file content immediately
            self._preview_file(entry_path)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search/filter submission."""
        if self.search_input and event.input.id == "search":
            raw = event.value.strip()

            # Parse into our app-level SearchQuery
            q = self._search_query

            # Prefix // → recursive search
            recursive = False
            if raw.startswith("//"):
                recursive = True
                raw = raw[2:].lstrip()

            q.text = raw
            q.recursive = recursive

            # Wildcards → PLAIN, otherwise FUZZY
            if any(ch in raw for ch in ("*", "?")):
                q.mode = SearchMode.PLAIN
            else:
                q.mode = SearchMode.FUZZY

            # Push down into FileList and refresh
            self._apply_search_query()

            # After filtering, focus back to file list
            if self.file_list:
                self.set_focus(self.file_list)

    # ---------- Core preview logic ----------
    def _preview_file(self, entry_path: Path) -> None:
        """Shared logic to preview a file (images, binary, code, or plain text)."""
        if not self.preview:
            return

        suffix = entry_path.suffix.lower()
        is_image = suffix in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

        # 1) Image preview path
        if is_image:
            if self.output:
                renderable = None

                # First try rich.image if available
                try:
                    from rich.image import Image as RichImage  # type: ignore
                except ModuleNotFoundError:
                    # No rich.image; try our Pillow renderer
                    renderable = pillow_rich_image(entry_path)
                else:
                    # rich.image exists; try to render with it
                    try:
                        img = RichImage.from_path(str(entry_path))
                        header = Text(f"[IMAGE] {entry_path.name}", style="bold magenta")
                        renderable = Group(header, Text("\n"), img)
                    except Exception:
                        # If RichImage fails for any reason, fall back to Pillow
                        renderable = pillow_rich_image(entry_path)

                if renderable is not None:
                    self.output.update(renderable)
                    self._set_status(f"Previewing image: {entry_path.name}")
                else:
                    self.output.update(
                        "[b]Image preview not available[/b]\n\n"
                        "Tried both `rich.image` and a Pillow-based fallback but neither is usable.\n"
                        "If you haven't already, install Pillow inside your venv:\n"
                        "  pip install pillow\n\n"
                        f"File path:\n  {entry_path}"
                    )
                    self._set_status(f"Image preview unavailable for: {entry_path.name}")

            # For images we don't track code-language preview
            self._last_file_path = None
            self._last_file_language = None

            # Still show a shell-style view command in the help pane
            cmd = build_view_file_command(entry_path)
            self._last_command = cmd
            self.preview.show_command(cmd)
            return

        # 2) Binary preview: hex dump instead of mojibake
        is_binary = is_binary_file(entry_path)
        if is_binary and self.output:
            dump = hex_dump(entry_path)
            self.output.show_hexdump(dump, entry_path)
            self._last_file_path = None
            self._last_file_language = None

            # In the help pane, show a real hexdump command they can run
            cmd = ShellCommand(
                description=f"Hex dump of {entry_path.name}",
                explanation=(
                    "This command shows the first part of the file in hex + ASCII:\n"
                    "  • Offsets on the left\n"
                    "  • Hex bytes in the middle\n"
                    "  • Printable characters on the right\n\n"
                    "Useful for inspecting binaries, compiled files, and unknown formats."
                ),
                command=f"hexdump -C -- {entry_path.name}",
                cwd=entry_path.parent,
                dangerous=False,
            )
            self._last_command = cmd
            self.preview.show_command(cmd)
            self._set_status(f"Previewing binary (hex): {entry_path.name}")
            return

        # 3) Log preview: use our LogHighlighter instead of generic syntax highlight
        if is_log_file(entry_path) and self.output:
            try:
                text = read_log_text(entry_path)
            except PermissionError:
                euid = os.geteuid() if hasattr(os, "geteuid") else -1
                has_pwless_sudo = _has_passwordless_sudo()

                if euid != 0:
                    # Not root
                    if has_pwless_sudo:
                        hint = (
                            "It looks like you can use sudo *without* a password.\n"
                            "You can restart ShellPilot with full access:\n\n"
                            f"  [code]sudo {os.path.basename(sys.argv[0])}[/code]\n"
                            "or view this specific log with:\n\n"
                            f"  [code]sudo less {entry_path}[/code]\n"
                        )
                    else:
                        hint = (
                            "You are not running as root, so some logs under /var/log "
                            "or system services may be unreadable.\n\n"
                            "To see this log, run one of:\n"
                            f"  • [code]sudo less {entry_path}[/code]\n"
                            f"  • [code]sudo tail -n 80 {entry_path}[/code]\n"
                            "or restart ShellPilot with sudo.\n"
                        )

                    self.output.update(
                        "[b]Permission denied reading log file.[/b]\n\n"
                        f"Path: {entry_path}\n\n"
                        + hint
                    )
                    self._set_status("Permission denied for log (not root)")
                else:
                    # Root but still denied: SELinux/ACL/etc.
                    self.output.update(
                        "[b]Permission denied reading log file, even as root.[/b]\n\n"
                        f"Path: {entry_path}\n\n"
                        "This is likely due to SELinux, ACLs, or special journal permissions.\n"
                        "Check:\n"
                        "  • getfacl\n"
                        "  • ls -Z (SELinux context)\n"
                    )
                    self._set_status("Permission denied for log (root)")
                return
            except Exception as e:
                self.output.update(
                    f"[b]Failed to read log file:[/b] {e}\n\nPath: {entry_path}"
                )
                self._set_status("Failed to preview log")
                return

            # Highlight with LogHighlighter
            rich_text = log_highlighter.highlight_lines(text.splitlines(True))
            self.output.update(rich_text)

            # Don't treat logs as “code files” for re-run behavior
            self._last_file_path = None
            self._last_file_language = None

            # Keep your tailored ShellCommand in the preview pane
            if suffix == ".csv":
                # (unlikely here, but just in case you add CSV logging)
                pass
            else:
                cmd = ShellCommand(
                    description=f"Tail of {entry_path.name}",
                    explanation=(
                        "Shows the *end* of the log using `tail -n 80`:\n"
                        "  • Useful for recent errors or activity\n"
                        "  • Does not modify the file in any way\n"
                    ),
                    command=f"tail -n 80 -- {entry_path.name}",
                    cwd=entry_path.parent,
                    dangerous=False,
                )
                self._last_command = cmd
                self.preview.show_command(cmd)

            self._set_status(f"Previewing log with highlighting: {entry_path.name}")
            return

        lang = language_for_path(entry_path)

        # Choose a helper command based on file type
        if suffix == ".log":
            cmd = ShellCommand(
                description=f"Tail of {entry_path.name}",
                explanation=(
                    "Shows the *end* of the log using `tail -n 80`:\n"
                    "  • Useful for recent errors or activity\n"
                    "  • Does not modify the file in any way\n"
                ),
                command=f"tail -n 80 -- {entry_path.name}",
                cwd=entry_path.parent,
                dangerous=False,
            )
        elif suffix == ".csv":
            cmd = ShellCommand(
                description=f"Pretty-print CSV {entry_path.name}",
                explanation=(
                    "Shows the first rows of the CSV as a simple table:\n"
                    "  • `head -n 40` limits output to 40 lines\n"
                    "  • `column -s, -t` aligns columns on commas\n"
                    "This is read-only and safe to run."
                ),
                command=f"head -n 40 -- {entry_path.name} | column -s, -t",
                cwd=entry_path.parent,
                dangerous=False,
            )
        else:
            # Default safe 'view file' helper (your existing behavior)
            cmd = build_view_file_command(entry_path)

        self._last_command = cmd
        self.preview.show_command(cmd)

        if lang is not None and self.output:
            # Syntax-highlighted preview
            try:
                text = entry_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = entry_path.read_text(errors="replace")

            self._last_file_path = entry_path
            self._last_file_language = lang
            self.output.show_code(text, entry_path, lang)
            self._set_status(f"Previewing [{lang}] {entry_path.name}")
        else:
            # Fallback: run shell preview command and show raw result
            self._last_file_path = None
            self._last_file_language = None
            rc, stdout, stderr = run_shell_command(cmd, dry_run=False)
            if self.output:
                self.output.show_result(stdout, stderr, rc)
            self._set_status(f"Previewing file: {entry_path.name}")

    # ---------- Actions ----------
    def action_open_action_menu(self) -> None:
        """Open the floating command palette."""
        self.push_screen(ActionMenu(), self._handle_action_menu_result)

    def action_go_home(self) -> None:
        """Jump directly to the user's home directory (~)."""
        home = Path.home()
        self._set_directory(home)
        self._set_status(f"In home directory: {home}")

    def action_focus_search(self) -> None:
        """Focus the filter input above the file list."""
        if self.search_input is not None:
            # Directly focus the Input widget
            self.search_input.focus()
            self._set_status(
                "Filter: type a pattern, Enter to apply. Submit empty to clear."
            )
        else:
            self._set_status("Search not available (no search input widget found)")

    def action_run_command(self) -> None:
        """Execute the last built command or refresh code preview."""
        if not self.output or not self._last_command:
            return

        # If we have a code file tracked, re-read and re-highlight it
        if self._last_file_path is not None and self._last_file_language is not None:
            try:
                text = self._last_file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = self._last_file_path.read_text(errors="replace")
            self.output.show_code(
                text, self._last_file_path, self._last_file_language
            )
            self._set_status(f"Refreshed code view: {self._last_file_path.name}")
            return

        # Otherwise, run the shell command and show its output
        rc, stdout, stderr = run_shell_command(self._last_command, dry_run=False)
        self.output.show_result(stdout, stderr, rc)
        self._set_status(f"Command finished with exit status {rc}")

    def action_up_directory(self) -> None:
        """Move one directory up in the file browser."""
        current = self._current_dir()
        parent = current.parent
        self._set_directory(parent)

    def action_enter_selected(self) -> None:
        """
        Right-arrow behavior: enter directory or re-preview file.

        This is ranger-style: left = up, right = go in.
        """
        entry_path = self._get_selected_path()
        if entry_path is None:
            return

        if entry_path.is_dir():
            self._set_directory(entry_path)
        else:
            self._preview_file(entry_path)

    def action_add_bookmark(self) -> None:
        """Bookmark the current directory."""
        current = self._current_dir()
        if current not in self.bookmarks:
            self.bookmarks.append(current)
        self.current_bookmark_index = self.bookmarks.index(current)

        self._save_session()

        if self.output:
            self.output.update(
                "[b]Bookmark added:[/b]\n"
                + "\n".join(f"- {p}" for p in self.bookmarks)
            )
        self._set_status(f"Bookmarked: {current}")

    def action_next_bookmark(self) -> None:
        """Jump to the next bookmarked directory."""
        if not self.bookmarks:
            if self.output:
                self.output.update(
                    "[b]No bookmarks yet.[/b]\nUse Ctrl+B to bookmark the current directory."
                )
            self._set_status("No bookmarks yet")
            return

        if self.current_bookmark_index is None:
            self.current_bookmark_index = 0
        else:
            self.current_bookmark_index = (
                self.current_bookmark_index + 1
            ) % len(self.bookmarks)

        target = self.bookmarks[self.current_bookmark_index]
        self._set_directory(target)
        self._set_status(f"Jumped to bookmark: {target}")

    def action_open_in_editor(self) -> None:
        """
        Open the selected file in an external editor.

        Uses $VISUAL, then $EDITOR, then falls back to xdg-open.
        """
        entry_path = self._get_selected_path()
        if entry_path is None or not entry_path.is_file():
            if self.output:
                self.output.update(
                    "[b]Open in editor:[/b] No file selected (or selection is a directory)."
                )
            self._set_status("Open in editor failed: no file selected")
            return

        editor = (
            os.environ.get("VISUAL")
            or os.environ.get("EDITOR")
            or "xdg-open"
        )

        try:
            subprocess.Popen([editor, str(entry_path)])
            if self.output:
                self.output.update(
                    f"[b]Opening in editor:[/b] {editor} {entry_path}"
                )
            self._set_status(f"Opening in editor: {editor} {entry_path.name}")
        except Exception as e:
            if self.output:
                self.output.update(
                    f"[b]Failed to open editor:[/b] {e}"
                )
            self._set_status("Failed to open editor (see output)")

    def action_toggle_help(self) -> None:
        """Show/hide the help pane and adjust column widths accordingly."""
        self._help_visible = not self._help_visible

        # 1) Actually hide/show the right-hand help scroll container
        if self.preview_container:
            # display=False removes it from layout; True re-adds it
            self.preview_container.display = self._help_visible

        # 2) Resize the main columns (the containers):
        #    - left-pane (breadcrumb + search + file list)
        #    - output-container (command output / code)
        try:
            left_pane = self.query_one("#left-pane", Vertical)
            output_container = self.query_one("#output-container", VerticalScroll)
        except Exception:
            # If for some reason the query fails, don't crash the app
            self.refresh(layout=True)
            return

        if self._help_visible:
            # Three-column mode: left | output | help
            left_pane.styles.width = "1fr"
            output_container.styles.width = "1fr"
            # preview-container stays at 1fr via CSS
        else:
            # Two-column mode: left | output (help hidden)
            left_pane.styles.width = "1fr"
            output_container.styles.width = "2fr"  # or "3fr" if you want it huge

        # Ask Textual to recompute layout with new widths
        self.refresh(layout=True)

        # Persist the new state
        self._save_session()

    def action_trash_selected(self) -> None:
        """
        Move the selected file or directory into ShellPilot's trash.

        This is a safe 'delete': nothing is permanently removed yet.
        """
        entry_path = self._get_selected_path()
        if entry_path is None:
            if self.output:
                self.output.update("[b]Trash:[/b] No item selected.")
            self._set_status("Trash: no item selected")
            return

        # Don't let people trash the trash
        try:
            if entry_path.resolve().is_relative_to(self.trash_dir.resolve()):
                if self.output:
                    self.output.update(
                        "[b]Trash:[/b] This item is already inside the trash directory."
                    )
                self._set_status("Item already in trash")
                return
        except Exception:
            pass

        if not entry_path.exists():
            if self.output:
                self.output.update("[b]Trash:[/b] Selected item no longer exists.")
            self._set_status("Trash: item not found on disk")
            return

        entry_id = uuid.uuid4().hex
        trash_name = f"{entry_id}__{entry_path.name}"
        dest = self.trash_dir / trash_name

        try:
            shutil.move(str(entry_path), str(dest))
        except Exception as e:
            if self.output:
                self.output.update(f"[b]Failed to move to trash:[/b] {e}")
            self._set_status("Failed to move to trash (see output)")
            return

        # Record in index
        self.trash_index[entry_id] = {
            "orig_path": str(entry_path),
            "trash_name": trash_name,
            "name": entry_path.name,
            "trashed_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._save_trash_index()

        # Refresh current directory
        self.file_list and self.file_list.refresh_entries()
        self._set_status(f"Moved to trash: {entry_path}")

        if self.output:
            self.output.update(
                "[b]Moved to trash:[/b]\n"
                f"- Original: {entry_path}\n"
                f"- Trash: {dest}\n\n"
                "Use 't' to open the trash, 'r' to restore, and 'E' to empty the trash (while in trash)."
            )

    def action_go_trash(self) -> None:
        """Jump directly to the ShellPilot trash directory."""
        self._set_directory(self.trash_dir)
        self._set_status(f"In trash: {self.trash_dir}")

    def action_restore_from_trash(self) -> None:
        """
        Restore the selected trashed item to its original path.

        Only works when the current view is the trash directory.
        """
        if not self._in_trash_view():
            if self.output:
                self.output.update(
                    "[b]Restore:[/b] You must be viewing the trash to restore items.\n"
                    "Press 't' to jump to the trash."
                )
            self._set_status("Restore: not in trash view")
            return

        entry_path = self._get_selected_path()
        if entry_path is None or not entry_path.exists():
            if self.output:
                self.output.update(
                    "[b]Restore:[/b] No valid trashed item selected."
                )
            self._set_status("Restore: no valid item selected")
            return

        # filename format is "<id>__<name>"
        name = entry_path.name
        if "__" not in name:
            if self.output:
                self.output.update(
                    "[b]Restore:[/b] Selected file is not a managed trash entry."
                )
            self._set_status("Restore: not a managed trash item")
            return

        entry_id, _ = name.split("__", 1)
        meta = self.trash_index.get(entry_id)
        if not meta:
            if self.output:
                self.output.update(
                    "[b]Restore:[/b] No metadata found for this trash entry."
                )
            self._set_status("Restore: metadata missing")
            return

        orig_path = Path(meta["orig_path"])
        target_dir = orig_path.parent

        # Make sure parent directory exists
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # if parent can't be created, bail
            if self.output:
                self.output.update(
                    f"[b]Restore failed:[/b] Could not create parent directory {target_dir}"
                )
            self._set_status("Restore failed: cannot create parent dir")
            return

        # If something already exists at the original path, add a suffix
        restore_path = orig_path
        if restore_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            restore_path = orig_path.with_name(f"{orig_path.name}.restored-{timestamp}")

        try:
            shutil.move(str(entry_path), str(restore_path))
        except Exception as e:
            if self.output:
                self.output.update(f"[b]Restore failed:[/b] {e}")
            self._set_status("Restore failed (see output)")
            return

        # Update index
        self.trash_index.pop(entry_id, None)
        self._save_trash_index()

        # Refresh trash view
        self.file_list and self.file_list.refresh_entries()
        self._set_status(f"Restored: {restore_path}")

        if self.output:
            self.output.update(
                "[b]Restored from trash:[/b]\n"
                f"- Restored to: {restore_path}\n"
                f"- Original path: {orig_path}"
                + ("\n\nNote: original path was occupied, so a '.restored-<timestamp>' suffix was added."
                   if restore_path != orig_path else "")
            )

    # ---------- AI helpers ----------

    def _build_dir_manifest(self, path: Path, max_entries: int = 256) -> str:
        """Return a short text manifest of a directory tree."""
        lines: list[str] = []
        base = path

        for root, dirs, files in os.walk(base):
            rel_root = os.path.relpath(root, base)
            rel_root = "." if rel_root == "." else rel_root

            for d in sorted(dirs):
                if len(lines) >= max_entries:
                    break
                entry = d if rel_root == "." else f"{rel_root}/{d}"
                lines.append(f"[DIR]  {entry}")

            for f in sorted(files):
                if len(lines) >= max_entries:
                    break
                entry = f if rel_root == "." else f"{rel_root}/{f}"
                lines.append(f"      {entry}")

            if len(lines) >= max_entries:
                lines.append(f"... (truncated after {max_entries} entries)")
                break

        return "\n".join(lines) if lines else "(directory is empty)"

    def action_ai_explain_file(self) -> None:
        """Use the local AI model to explain the selected file or directory."""
        entry_path = self._get_selected_path()
        if entry_path is None:
            self._set_status("AI: no item selected")
            if self.output:
                self.output.update("[b]AI:[/b] No file or directory selected.")
            return

        if entry_path.is_dir():
            # Directory mode
            try:
                manifest = self._build_dir_manifest(entry_path)
            except Exception as exc:
                self._show_ai_error(f"Failed to scan directory: {exc}")
                return

            self._set_status(f"AI: analyzing directory {entry_path.name}")
            if self.output:
                panel = Panel.fit(
                    f"[b]AI explain (directory):[/b]\n\n"
                    f"Analyzing [magenta]{entry_path}[/magenta]...\n\n"
                    "This may take several seconds on CPU-only mode.\n"
                    "You can continue browsing while the analysis runs.\n\n"
                    "[b]Directory manifest (truncated):[/b]\n"
                    f"{manifest[:2000]}",
                    title=f"AI: {entry_path.name}",
                    border_style="cyan",
                )
                self.output.update(panel)

            # 1) Show stage 1: directory has been scanned / summarized
            self._show_ai_progress(entry_path, stage=1)

            # Background worker
            self.call_in_thread(self._ai_explain_dir_worker, entry_path, manifest)

            return

        # File mode
        try:
            # Cap content length to avoid context explosions
            content = entry_path.read_text(encoding="utf-8", errors="ignore")
            max_chars = 16_000
            if len(content) > max_chars:
                content = content[:max_chars]
        except Exception as exc:
            self._show_ai_error(f"Failed to read file: {exc}")
            return

        self._set_status(f"AI: analyzing file {entry_path.name}")
        if self.output:
            panel = Panel.fit(
                f"[b]AI explain (file):[/b]\n\n"
                f"Analyzing [magenta]{entry_path}[/magenta]...\n\n"
                "This may take several seconds on CPU-only mode.\n"
                "You can continue browsing while the analysis runs.",
                title=f"AI: {entry_path.name}",
                border_style="cyan",
            )
            self.output.update(panel)

        # 2) Stage 1: we now have the content ready for the model
        self._show_ai_progress(entry_path, stage=1)

        # 3) Kick work to a background thread so the TUI stays responsive
        self.call_in_thread(self._ai_explain_file_worker, entry_path, content)

    def _show_ai_progress(self, path: Path, stage: int) -> None:
        """
        Render a friendly, step-based 'AI is working' panel.

        stage:
          1 = just finished reading/summarizing
          2 = currently running the LLM
          3 = finished and formatting (usually very brief before final output)
        """
        if not self.output:
            return

        is_dir = path.is_dir()
        kind = "directory" if is_dir else "file"

        def mark(n: int, label: str) -> str:
            if stage > n:
                prefix = "✅"
            elif stage == n:
                prefix = "⏳"
            else:
                prefix = "•"
            return f"{prefix} [b]Step {n}/3:[/b] {label}"

        lines: list[str] = [
            f"[b]AI explain ({kind}):[/b] {path}",
            "",
            mark(1, "Read and summarize contents"),
            mark(2, "Analyze with local AI model"),
            mark(3, "Organize explanation for display"),
            "",
            "You can continue browsing files/directories while this runs.",
        ]

        body = "\n".join(lines)

        from rich.panel import Panel
        panel = Panel.fit(body, title="AI: working…", border_style="cyan")

        self.output.update(panel)
        self._set_status(f"AI: analyzing {kind} {path.name} (stage {stage}/3)")

    # ---------- Background workers ----------

    def _ai_explain_file_worker(self, path: Path, content: str) -> None:
        """Run the file explanation LLM in a background thread."""
        try:
            engine = get_engine()
        except FileNotFoundError as exc:
            self.call_from_thread(self._show_ai_error, str(exc))
            return
        except Exception as exc:
            self.call_from_thread(self._show_ai_error, f"AI init error: {exc}")
            return

        # Stage 2: model is actually running now
        self.call_from_thread(self._show_ai_progress, path, 2)

        try:
            answer = engine.analyze_file(path, content)
        except Exception as exc:
            self.call_from_thread(self._show_ai_error, f"AI inference error: {exc}")
            return

        # Stage 3: we’re done computing, about to render
        self.call_from_thread(self._show_ai_progress, path, 3)

        self.call_from_thread(self._show_ai_success, path, answer)

    def _ai_explain_dir_worker(self, path: Path, manifest: str) -> None:
        """Run the directory explanation LLM in a background thread."""
        try:
            engine = get_engine()
        except FileNotFoundError as exc:
            self.call_from_thread(self._show_ai_error, str(exc))
            return
        except Exception as exc:
            self.call_from_thread(self._show_ai_error, f"AI init error: {exc}")
            return

        # Stage 2: model running on directory summary
        self.call_from_thread(self._show_ai_progress, path, 2)

        try:
            # Prefer a dedicated directory method if the engine has one
            if hasattr(engine, "analyze_directory"):
                answer = engine.analyze_directory(path, manifest)
            else:
                # Fallback: treat the manifest like a text "file"
                answer = engine.analyze_file(path, manifest)
        except Exception as exc:
            self.call_from_thread(self._show_ai_error, f"AI inference error: {exc}")
            return
        
        self.call_from_thread(self._show_ai_progress, path, 3)
        self.call_from_thread(self._show_ai_success, path, answer)

    def _show_ai_error(self, message: str) -> None:
        """Render an AI-related error in the output pane + status bar."""
        self._set_status(f"AI: {message}")
        if self.output:
            panel = Panel.fit(
                f"[b]AI error:[/b]\n\n{message}",
                title="AI",
                border_style="red",
            )
            self.output.update(panel)

    def _show_ai_success(self, path: Path, answer: str) -> None:
        """Render the AI explanation in the output pane and status bar."""
        self._set_status(f"AI: analysis complete for {path.name}")

        if self.output:
            # Use Markdown so lists/headings render nicely
            md = Markdown(answer)
            panel = Panel.fit(
                md,
                title=f"AI: {path.name}",
                border_style="cyan",
            )
            self.output.update(panel)

        if getattr(self, "preview", None) is not None:
            # Short mirrored note in the help pane
            self.preview.update(
                Panel.fit(
                    f"AI summary for [magenta]{path.name}[/magenta].\n\n"
                    "Press [b]a[/b] on another file or directory to analyze again.",
                    title="AI helper",
                    border_style="cyan",
                )
            )

    def action_empty_trash(self) -> None:
        """
        Permanently delete all items in the ShellPilot trash.

        Only works while viewing the trash directory.
        """
        if not self._in_trash_view():
            if self.output:
                self.output.update(
                    "[b]Empty trash:[/b] You must be viewing the trash.\n"
                    "Press 't' to jump to the trash first."
                )
            self._set_status("Empty trash: not in trash view")
            return

        # Danger, but user explicitly invoked it from trash view
        errors: list[str] = []
        for child in self.trash_dir.iterdir():
            if child == self.trash_index_path:
                continue
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            except Exception as e:
                errors.append(f"{child}: {e}")

        self.trash_index = {}
        self._save_trash_index()
        self.file_list and self.file_list.refresh_entries()

        if errors:
            if self.output:
                self.output.update(
                    "[b]Empty trash completed with errors:[/b]\n"
                    + "\n".join(f"- {line}" for line in errors)
                )
            self._set_status("Empty trash: some items could not be removed")
        else:
            if self.output:
                self.output.update("[b]Trash emptied.[/b]")
            self._set_status("Trash emptied")

    def _apply_search_query(self) -> None:
        """Push the current SearchQuery down into the FileList and update status."""
        if not self.file_list:
            return

        self.file_list.set_search_query(self._search_query)
        self._update_search_status()

    def _update_search_status(self) -> None:
        """Update the status bar to reflect the current search query."""
        if not self.status:
            return

        q = self._search_query
        text = (getattr(q, "text", "") or "").strip()
        recursive = getattr(q, "recursive", False)
        in_trash = self._in_trash_view()

        if text:
            suffix = " (recursive)" if recursive else ""
            # Search status is global; no need to mention trash-specific keys here
            self._set_status(
                f"Search{suffix}: {text!r}  •  Enter: re-run  •  /: edit  •  Esc: clear"
            )
        else:
            if in_trash:
                # Trash bar: only here do we advertise r / E
                self._set_status(
                    "←: up dir • →: enter/preview • h: home (~) • t: trash view "
                    "• r: restore • E: empty trash • Enter: run "
                    "• /: filter • e: edit • Ctrl+B: bookmark • Ctrl+J: next bookmark • ?: toggle help"
                )
            else:
                # 🌱 Main bar: no restore/empty hints here
                self._set_status(
                    "←: up dir • →: enter/preview • h: home (~) • t: trash view • Delete: move to trash "
                    "• Enter: run • /: filter • e: edit • Ctrl+B: bookmark • Ctrl+J: next bookmark • ?: toggle help"
                )

    def _handle_action_menu_result(self, result: dict[str, Any] | None) -> None:
        if result is None:
            return  # user cancelled with Esc

        from shellpilot.core import fs_browser

        action = result.get("action")

        try:
            if action == "rename":
                target = self.get_current_entry_path()
                if not target:
                    self._set_status("No file selected to rename.")
                    return
                new_name = result["new_name"]
                new_path = fs_browser.rename_entry(target, new_name)
                self._set_status(f"Renamed to {new_path.name}")

            elif action == "chmod":
                target = self.get_current_entry_path()
                if not target:
                    self._set_status("No file selected to chmod.")
                    return
                mode_str = result["mode"]
                mode = int(mode_str, 8)  # e.g. "755" -> 0o755
                fs_browser.chmod_entry(target, mode)
                self._set_status(f"chmod {mode_str} {target.name}")

            elif action == "mkdir":
                parent = self.get_current_directory()
                name = result["name"]
                new_dir = fs_browser.mkdir_entry(parent, name)
                self._set_status(f"Created directory {new_dir.name}")

            elif action == "touch":
                parent = self.get_current_directory()
                name = result["name"]
                new_file = fs_browser.touch_entry(parent / name)
                self._set_status(f"Touched {new_file.name}")

            else:
                self._set_status(f"Unknown command: {action}")
                return

            # refresh directory listing
            self.refresh_browser()

        except Exception as exc:
            # eventually we can route this to OutputPanel too
            self._set_status(f"[error] {exc}")
