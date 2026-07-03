"""Shared search constants and small utility helpers."""

from __future__ import annotations

import re

DEFAULT_KEYWORD_MIN_SCORE = 0.34
MAX_LIMIT = 500
MAX_GRAPH_EXPAND_DEPTH = 5
MAX_SEARCH_QUERY_CHARS = 1000


def _normalize_text(value: str) -> str:
    """Normalize text for best-effort claim matching."""
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def normalize_search_limit(value: object, *, default: int = 10, maximum: int = MAX_LIMIT) -> int:
    """Return a safe search/list limit.

    User-facing CLI parsers reject non-positive limits where appropriate. This
    helper protects lower-level Python and MCP paths too: a non-positive value
    means "return no rows", never "SQLite LIMIT -1".
    """
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = int(default)
    if parsed <= 0:
        return 0
    return min(parsed, int(maximum))


def validate_search_query(value: object, *, maximum: int = MAX_SEARCH_QUERY_CHARS) -> tuple[str, dict | None]:
    """Return a normalized query and an error payload when it is too long."""
    query = str(value or "")
    if len(query) <= int(maximum):
        return query, None
    return query, {
        "ok": False,
        "status": "error",
        "error": "query_too_long",
        "message": f"search query is too long; maximum is {int(maximum)} characters",
        "max_query_chars": int(maximum),
        "query_chars": len(query),
        "try": [
            "Shorten the query to the main keywords or one concrete question.",
            "Put long source text into `vault add` or `vault remember`, then search for a short phrase.",
        ],
        "next_action": "Retry with a query under 1000 characters.",
    }
