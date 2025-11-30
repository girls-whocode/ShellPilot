# shellpilot/utils/log_highlighter.py

from __future__ import annotations

import re
import socket
from typing import Iterable, Optional

from rich.text import Text


class LogHighlighter:
    """
    Highlighter for log content.

    Roughly equivalent to your old Enhanced BASH v3 Perl patterns, but in Python/Rich.
    """

    def __init__(self, hostname: Optional[str] = None) -> None:
        self.hostname = hostname or socket.gethostname()
        self._rules = self._build_rules()

    def _build_rules(self) -> list[tuple[re.Pattern[str], str]]:
        """
        Build regex → style mapping.

        Styles are Rich style strings (e.g. 'bold yellow', 'black on yellow').
        """
        # Date formats
        date_ymd_dash = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
        date_ymd_slash = re.compile(r"\b\d{4}/\d{2}/\d{2}\b")
        date_d_mmm_yyyy = re.compile(
            r"\b\d{2}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{4}\b"
        )
        date_mmm_d_yyyy = re.compile(
            r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2}\s+\d{4}\b"
        )
        date_mmm_d = re.compile(
            r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2}\b"
        )

        # Time
        time_hms = re.compile(r"\b\d{2}:\d{2}:\d{2}\b")

        # Brackets + quoted strings
        bracket_open = re.compile(r"\[")
        bracket_close = re.compile(r"\]")
        quoted_string = re.compile(r'"[^"]*"')

        # Hostname
        hostname_pattern = re.compile(re.escape(self.hostname))

        # Log markers
        log_started = re.compile(r"\bLog\s+started:\b")
        log_ended = re.compile(r"\bLog\s+ended:\b")

        # Levels
        warning = re.compile(r"\b(WARNING|WARN)\b")
        error = re.compile(r"\b(ERROR|ERR|error)\b")
        severe = re.compile(r"\bSEVERE\b")
        info = re.compile(r"\bINFO\b")
        cmd = re.compile(r"\bCMD\b")
        _list = re.compile(r"\bLIST\b")

        # Debug levels
        debug = re.compile(r"\b(DEBUG|DBG|debug)\b")
        debug1 = re.compile(r"\b(debug1|DEBUG1)\b")
        debug2 = re.compile(r"\b(debug2|DEBUG2)\b")
        debug3 = re.compile(r"\b(debug3|DEBUG3)\b")

        # systemd-style verbs
        started = re.compile(r"\bStarted\b")
        reached = re.compile(r"\bReached\b")
        mounted = re.compile(r"\bMounted\b")
        listening = re.compile(r"\bListening\b")
        finished = re.compile(r"\bFinished\b")

        # separators (===== / ----- style lines)
        separators = re.compile(r"^.*(=|─|-){5,}.*$")

        return [
            # bracket + meta
            (bracket_open, "bold yellow"),
            (bracket_close, "bold yellow"),
            (quoted_string, "yellow"),
            # dates
            (date_ymd_dash, "bold bright_blue"),
            (date_ymd_slash, "bold bright_blue"),
            (date_d_mmm_yyyy, "bold bright_blue"),
            (date_mmm_d_yyyy, "bold bright_blue"),
            (date_mmm_d, "bold bright_blue"),
            # time
            (time_hms, "bright_blue"),
            # hostname
            (hostname_pattern, "bold green"),
            # log lifecycle
            (log_started, "cyan"),
            (log_ended, "cyan"),
            # levels
            (warning, "bold bright_yellow"),
            (error, "bold bright_red"),
            (severe, "bold bright_red"),
            (info, "bold cyan"),
            (cmd, "black on yellow"),
            (_list, "black on magenta"),
            # debug levels
            (debug3, "bold red"),          # most noisy → loudest color
            (debug2, "bold cyan"),
            (debug1, "bold yellow"),
            (debug, "bright_black"),
            # systemd verbs
            (started, "black on green"),
            (mounted, "black on green"),
            (finished, "black on green"),
            (reached, "black on cyan"),
            (listening, "black on magenta"),
            # separators
            (separators, "bold green"),
        ]

    def highlight_line(self, line: str, search_term: Optional[str] = None) -> Text:
        """
        Highlight a single log line and return a Rich Text object.
        """
        text = Text(line.rstrip("\n"))

        for pattern, style in self._rules:
            text.highlight_regex(pattern, style)

        if search_term:
            # Match literally, ignore regex metacharacters
            escaped = re.escape(search_term)
            text.highlight_regex(escaped, "black on bright_yellow")

        return text

    def highlight_lines(
        self, lines: Iterable[str], search_term: Optional[str] = None
    ) -> Text:
        """
        Highlight an iterable of lines as a single Text block.
        """
        result = Text()
        for i, line in enumerate(lines):
            if i:
                result.append("\n")
            result.append(self.highlight_line(line, search_term))
        return result

    def highlight_file(
        self, path: str, search_term: Optional[str] = None, max_lines: int = 5000
    ) -> Text:
        """
        Convenience helper for a whole file.

        max_lines: safety cutoff so we don't try to render a 300k-line log.
        """
        with open(path, "r", errors="replace") as f:
            lines: list[str] = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                lines.append(line)
        return self.highlight_lines(lines, search_term)
