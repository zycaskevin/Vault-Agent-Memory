"""Parity reporting for legacy Gateway and provider-backed Memory API adapters."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def provider_adapter_parity_report(
    project_dir: str | Path,
    *,
    agent_id: str,
    search_probes: list[dict[str, Any]] | None = None,
    read_probes: list[dict[str, Any]] | None = None,
    include_private: bool = False,
    max_sensitivity: str = "low",
) -> dict[str, Any]:
    """Compare legacy and provider preview adapters without returning memory content."""
    search_results = [
        _search_probe(
            project_dir,
            probe,
            default_agent_id=agent_id,
            default_include_private=include_private,
            default_max_sensitivity=max_sensitivity,
        )
        for probe in (search_probes or [])
    ]
    read_results = [
        _read_probe(
            project_dir,
            probe,
            default_agent_id=agent_id,
            default_include_private=include_private,
            default_max_sensitivity=max_sensitivity,
        )
        for probe in (read_probes or [])
    ]
    mismatches = [probe for probe in [*search_results, *read_results] if not probe.get("matches")]
    return {
        "status": "ok" if not mismatches else "mismatch",
        "ok": not mismatches,
        "adapter_status": "preview",
        "default_authority": "legacy_gateway_policy_filtered",
        "provider_authority_under_test": "provider_policy_filtered",
        "summary": {
            "search_probes": len(search_results),
            "search_matches": sum(1 for probe in search_results if probe.get("matches")),
            "read_probes": len(read_results),
            "read_matches": sum(1 for probe in read_results if probe.get("matches")),
            "mismatches": len(mismatches),
        },
        "search": search_results,
        "read": read_results,
        "safety": {
            "report_only": True,
            "changes_default_authority": False,
            "returns_raw_memory_content": False,
            "returns_provider_raw_rows": False,
            "candidate_first_writes": True,
            "writes_active_knowledge": False,
        },
    }


def _search_probe(
    project_dir: str | Path,
    probe: dict[str, Any],
    *,
    default_agent_id: str,
    default_include_private: bool,
    default_max_sensitivity: str,
) -> dict[str, Any]:
    from .gateway_memory_api import gateway_memory_search

    query = str(probe.get("query", "") or "")
    agent_id = str(probe.get("agent_id") or default_agent_id or "")
    mode = str(probe.get("mode", "keyword") or "keyword")
    limit = _int_value(probe.get("limit"), 10)
    include_private = _bool_value(probe.get("include_private"), default_include_private)
    max_sensitivity = str(probe.get("max_sensitivity") or default_max_sensitivity or "low")
    legacy = gateway_memory_search(
        project_dir,
        query=query,
        agent_id=agent_id,
        mode=mode,
        limit=limit,
        include_private=include_private,
        max_sensitivity=max_sensitivity,
    )
    provider = gateway_memory_search(
        project_dir,
        query=query,
        agent_id=agent_id,
        mode=mode,
        limit=limit,
        include_private=include_private,
        max_sensitivity=max_sensitivity,
        result_adapter="provider",
    )
    legacy_ids = _result_ids(legacy)
    provider_ids = _result_ids(provider)
    return {
        "type": "search",
        "query_hash": _text_hash(query),
        "query_chars": len(query),
        "agent_id": agent_id,
        "mode": mode,
        "limit": limit,
        "include_private": include_private,
        "max_sensitivity": max_sensitivity,
        "legacy_status": legacy.get("status", ""),
        "provider_status": provider.get("status", ""),
        "legacy_ids": legacy_ids,
        "provider_ids": provider_ids,
        "ordered_match": legacy_ids == provider_ids,
        "missing_ids": [memory_id for memory_id in legacy_ids if memory_id not in provider_ids],
        "extra_ids": [memory_id for memory_id in provider_ids if memory_id not in legacy_ids],
        "matches": legacy_ids == provider_ids and legacy.get("status") == provider.get("status"),
    }


def _read_probe(
    project_dir: str | Path,
    probe: dict[str, Any],
    *,
    default_agent_id: str,
    default_include_private: bool,
    default_max_sensitivity: str,
) -> dict[str, Any]:
    from .gateway_memory_api import gateway_memory_get

    memory_id = _int_value(probe.get("memory_id"), 0)
    agent_id = str(probe.get("agent_id") or default_agent_id or "")
    line_start = _int_value(probe.get("line_start"), 1)
    line_end = _int_value(probe.get("line_end"), 40)
    max_lines = _int_value(probe.get("max_lines"), 80)
    include_private = _bool_value(probe.get("include_private"), default_include_private)
    max_sensitivity = str(probe.get("max_sensitivity") or default_max_sensitivity or "low")
    legacy = gateway_memory_get(
        project_dir,
        memory_id=memory_id,
        agent_id=agent_id,
        line_start=line_start,
        line_end=line_end,
        max_lines=max_lines,
        include_private=include_private,
        max_sensitivity=max_sensitivity,
    )
    provider = gateway_memory_get(
        project_dir,
        memory_id=memory_id,
        agent_id=agent_id,
        line_start=line_start,
        line_end=line_end,
        max_lines=max_lines,
        include_private=include_private,
        max_sensitivity=max_sensitivity,
        result_adapter="provider",
    )
    legacy_allowed = legacy.get("status") == "ok"
    provider_allowed = provider.get("status") == "ok"
    allowed_match = legacy_allowed == provider_allowed
    metadata_match = (
        not legacy_allowed
        or (
            legacy.get("entry_id") == provider.get("entry_id")
            and legacy.get("range") == provider.get("range")
            and legacy.get("content_hash") == provider.get("content_hash")
        )
    )
    return {
        "type": "read",
        "memory_id": memory_id,
        "agent_id": agent_id,
        "range": f"L{line_start}-L{line_end}",
        "include_private": include_private,
        "max_sensitivity": max_sensitivity,
        "legacy_status": legacy.get("status", ""),
        "provider_status": provider.get("status", ""),
        "legacy_error": legacy.get("error", ""),
        "provider_error": provider.get("error", ""),
        "allowed_match": allowed_match,
        "entry_id_match": (not legacy_allowed) or legacy.get("entry_id") == provider.get("entry_id"),
        "range_match": (not legacy_allowed) or legacy.get("range") == provider.get("range"),
        "content_hash_match": (not legacy_allowed) or legacy.get("content_hash") == provider.get("content_hash"),
        "legacy_content_hash": legacy.get("content_hash", "") if legacy_allowed else "",
        "provider_content_hash": provider.get("content_hash", "") if provider_allowed else "",
        "matches": allowed_match and metadata_match,
    }


def _result_ids(payload: dict[str, Any]) -> list[int]:
    ids: list[int] = []
    for row in payload.get("results", []):
        if isinstance(row, dict) and str(row.get("id") or "").isdigit():
            ids.append(int(row["id"]))
    return ids


def _int_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _bool_value(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return bool(default)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _text_hash(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()
