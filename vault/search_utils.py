"""Shared search constants and small utility helpers."""

from __future__ import annotations

import re

DEFAULT_KEYWORD_MIN_SCORE = 0.34
MAX_LIMIT = 500
MAX_GRAPH_EXPAND_DEPTH = 5


def _normalize_text(value: str) -> str:
    """Normalize text for best-effort claim matching."""
    return re.sub(r"\s+", " ", (value or "").strip().lower())
