"""Small shared normalization helpers for Vault runtime modules."""

from __future__ import annotations

import json
from typing import Any


def as_list(value: Any) -> list[Any]:
    """Return ``value`` as a list without coercing item types."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def clean_string_list(value: Any) -> list[str]:
    """Return a trimmed string list, dropping empty items."""
    if value is None or value == "":
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    stripped = str(value).strip()
    return [stripped] if stripped else []


def jsonable(value: Any) -> Any:
    """Convert common non-JSON values into deterministic JSON-safe shapes."""
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, dict):
            return {str(k): jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [jsonable(v) for v in value]
        return str(value)
