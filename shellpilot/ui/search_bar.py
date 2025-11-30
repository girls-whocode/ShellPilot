from __future__ import annotations

from textual.widget import Widget
from textual.message import Message
from textual.reactive import reactive
from textual.containers import Horizontal
from textual.widgets import Input, Static

from shellpilot.core.search import SearchMode, FileTypeFilter, SearchQuery


class SearchBar(Widget):
    """Bottom search bar for `/` UX."""

    DEFAULT_CSS = """
    SearchBar {
        height: 3;
        dock: bottom;
        background: $surface-darken-1;
    }

    SearchBar > Horizontal {
        height: 3;
        padding: 0 1;
    }

    SearchBar .label {
        width: auto;
        content-align: left middle;
    }

    SearchBar .value {
        width: auto;
        content-align: left middle;
        color: $accent;
    }

    SearchBar Input {
        width: 1fr;
        margin-right: 1;
    }
    """

    class Submitted(Message):
        """Emitted when the user submits the search (Enter)."""

        def __init__(self, sender: SearchBar, query: SearchQuery) -> None:
            super().__init__(sender)
            self.query = query

    class Cancelled(Message):
        """Emitted when the user cancels the search (Esc)."""

        pass

    query = reactive(SearchQuery())

    def compose(self):
        yield Horizontal(
            Static("Search:", classes="label"),
            Input(placeholder="Type to filter… (Enter = apply, Esc = clear)", id="search-input"),
            Static("Mode:", classes="label"),
            Static("", id="mode-label", classes="value"),
            Static("Type:", classes="label"),
            Static("", id="type-label", classes="value"),
            Static("Case:", classes="label"),
            Static("", id="case-label", classes="value"),
        )

    def on_mount(self):
        self._update_labels()
        self.query = self.query  # trigger reactive update

    def watch_query(self, query: SearchQuery) -> None:
        self._update_labels()

    def _update_labels(self) -> None:
        mode_label = self.query.mode.name.capitalize()
        type_label = self.query.type_filter.name.capitalize()
        case_label = "on" if self.query.case_sensitive else "off"

        self.query_one("#mode-label", Static).update(mode_label)
        self.query_one("#type-label", Static).update(type_label)
        self.query_one("#case-label", Static).update(case_label)

    # ---- Keyboard handling ----

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value or ""
        self.query = SearchQuery(
            text=text,
            mode=self.query.mode,
            type_filter=self.query.type_filter,
            case_sensitive=self.query.case_sensitive,
        )
        self.post_message(self.Submitted(self, self.query))

    def on_input_key(self, event: Input.Key) -> None:
        if event.key == "escape":
            # Clear everything and cancel
            self.query = SearchQuery()
            self.post_message(self.Cancelled(self))
            event.stop()
        elif event.key == "f2":
            self.query = SearchQuery(
                text=self.query.text,
                mode=_next_mode(self.query.mode),
                type_filter=self.query.type_filter,
                case_sensitive=self.query.case_sensitive,
            )
            event.stop()
        elif event.key == "f3":
            self.query = SearchQuery(
                text=self.query.text,
                mode=self.query.mode,
                type_filter=_next_type(self.query.type_filter),
                case_sensitive=self.query.case_sensitive,
            )
            event.stop()
        elif event.key == "f4":
            self.query = SearchQuery(
                text=self.query.text,
                mode=self.query.mode,
                type_filter=self.query.type_filter,
                case_sensitive=not self.query.case_sensitive,
            )
            event.stop()


def _next_mode(mode: SearchMode) -> SearchMode:
    order = [SearchMode.PLAIN, SearchMode.FUZZY, SearchMode.REGEX]
    idx = order.index(mode)
    return order[(idx + 1) % len(order)]


def _next_type(t: FileTypeFilter) -> FileTypeFilter:
    order = [
        FileTypeFilter.ANY,
        FileTypeFilter.CODE,
        FileTypeFilter.TEXT,
        FileTypeFilter.IMAGE,
        FileTypeFilter.DIR,
    ]
    idx = order.index(t)
    return order[(idx + 1) % len(order)]
