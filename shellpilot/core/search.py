from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional, TypeVar, Sequence, Callable, List
import difflib
import re

T = TypeVar("T")

class SearchMode(Enum):
    PLAIN = auto()
    FUZZY = auto()
    REGEX = auto()

class FileTypeFilter(Enum):
    ANY = auto()
    CODE = auto()
    TEXT = auto()
    IMAGE = auto()
    DIR = auto()

@dataclass
class SearchQuery:
    text: str = ""
    mode: SearchMode = SearchMode.PLAIN
    type_filter: FileTypeFilter = FileTypeFilter.ANY
    case_sensitive: bool = False
    recursive: bool = False

    @property
    def is_active(self) -> bool:
        return bool(self.text.strip()) or self.type_filter is not FileTypeFilter.ANY

# ──────────────────────────────────────────────
# Fuzzy search helpers
# ──────────────────────────────────────────────

def _normalize(s: str, *, case_sensitive: bool) -> str:
    return s if case_sensitive else s.casefold()


def fuzzy_score(query: str, text: str, *, case_sensitive: bool = False) -> float:
    """
    Return a score between 0 and 1 for how well `text` matches `query`.

    Heuristics:
    - Exact match -> 1.0
    - Substring match -> 0.7–0.95 depending on length/density
    - Otherwise: difflib ratio
    """
    q = _normalize(query, case_sensitive=case_sensitive)
    t = _normalize(text, case_sensitive=case_sensitive)

    if not q:
        return 1.0

    if q == t:
        return 1.0

    if q in t:
        density = len(q) / max(len(t), len(q))
        return 0.7 + 0.25 * density  # 0.7–0.95

    return difflib.SequenceMatcher(None, q, t).ratio()

@dataclass
class SearchResult(List[T]):
    item: T
    score: float

def fuzzy_filter(
    query: str,
    items: Sequence[T],
    *,
    key: Callable[[T], str],
    min_score: float = 0.55,
    case_sensitive: bool = False,
    limit: Optional[int] = None,
) -> List[SearchResult]:
    """
    Fuzzy-filter items using `key(item)` as the text to match.

    Returns SearchResult objects with (item, score), sorted best-first.
    """
    q = query.strip()
    if not q:
        # Treat everything as a neutral "match" when query is empty
        return [SearchResult(item=i, score=1.0) for i in items]

    results: List[SearchResult] = []
    for item in items:
        s = fuzzy_score(q, key(item), case_sensitive=case_sensitive)
        if s >= min_score:
            results.append(SearchResult(item=item, score=s))

    results.sort(key=lambda r: r.score, reverse=True)

    if limit is not None:
        results = results[:limit]

    return results

# ──────────────────────────────────────────────
# High-level helper: apply_search()
# ──────────────────────────────────────────────

def apply_search(
    items: Sequence[T],
    query: Optional[SearchQuery],
    *,
    key: Callable[[T], str],
    get_type: Optional[Callable[[T], FileTypeFilter]] = None,
    fuzzy_min_score: float = 0.55,
) -> List[T]:
    """
    Apply the full SearchQuery (mode + text + type filter) to a sequence.

    - `key(item)` gives the text to match (e.g. filename)
    - `get_type(item)` (optional) returns FileTypeFilter for that item
    - Returns a filtered *list* of items (no scores; ordered best-first for fuzzy)
    """
    if query is None or not query.is_active:
        # No query: pass-through
        return list(items)

    text = query.text.strip()
    case_sensitive = query.case_sensitive

    # 1) Type filter pass (if provided)
    working: List[T] = list(items)
    if query.type_filter is not FileTypeFilter.ANY and get_type is not None:
        working = [
            item for item in working
            if get_type(item) == query.type_filter
        ]

    # If type-only search, no text criteria:
    if not text:
        return working

    # 2) Text search: PLAIN / FUZZY / REGEX
    if query.mode is SearchMode.PLAIN:
        if not case_sensitive:
            lt = text.casefold()
            return [
                item for item in working
                if lt in key(item).casefold()
            ]
        else:
            return [
                item for item in working
                if text in key(item)
            ]

    if query.mode is SearchMode.FUZZY:
        results = fuzzy_filter(
            text,
            working,
            key=key,
            min_score=fuzzy_min_score,
            case_sensitive=case_sensitive,
        )
        return [r.item for r in results]

    if query.mode is SearchMode.REGEX:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(text, flags=flags)
        except re.error:
            # Bad regex: fail soft and just return original list
            return working

        return [
            item for item in working
            if pattern.search(key(item)) is not None
        ]

    # Failsafe: unknown mode → no extra filtering
    return working
