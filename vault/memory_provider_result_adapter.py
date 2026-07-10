"""Opt-in provider-backed result adapters for Vault Memory API."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .gui_format import compact_knowledge
from .memory_provider import sqlite_memory_provider
from .search_utils import validate_search_query


def provider_memory_search(
    project_dir: str | Path,
    *,
    query: str,
    agent_id: str,
    mode: str,
    limit: int,
    include_private: bool,
    max_sensitivity: str,
) -> dict[str, Any]:
    """Return compact search results from the provider preview adapter."""
    agent = _agent_id(agent_id)
    if not agent:
        return _error("agent_id_required", "agent_id is required")
    query_text, query_error = validate_search_query(query)
    if query_error is not None:
        return query_error
    mode_name = str(mode or "keyword").strip().lower() or "keyword"
    if mode_name not in {"auto", "keyword"}:
        return {
            "status": "unsupported",
            "error": "provider_result_adapter_mode_unsupported",
            "message": "provider result adapter currently supports keyword search only",
            "mode": mode_name,
            "supported_modes": ["auto", "keyword"],
            "memory_api": _provider_search_memory_api_payload(),
            "safety": _provider_search_safety(include_private, max_sensitivity),
        }

    provider = sqlite_memory_provider(project_dir)
    rows = provider.search_active(
        query_text,
        limit=limit,
        agent_id=agent,
        include_private=include_private,
        max_sensitivity=max_sensitivity,
    )
    return {
        "status": "ok",
        "query": query_text,
        "mode": "keyword",
        "agent_id": agent,
        "results": [compact_knowledge(row) for row in rows],
        "memory_api": {
            **_provider_search_memory_api_payload(),
            "provider_id": provider.provider_id,
            "backend_type": provider.backend_type,
            "result_count": len(rows),
        },
        "safety": _provider_search_safety(include_private, max_sensitivity),
    }


def provider_memory_get(
    project_dir: str | Path,
    *,
    memory_id: int,
    agent_id: str,
    line_start: int,
    line_end: int,
    max_lines: int,
    include_private: bool,
    max_sensitivity: str,
) -> dict[str, Any]:
    """Return a provider-policy-filtered bounded read payload."""
    agent = _agent_id(agent_id)
    if not agent:
        return _error("agent_id_required", "agent_id is required")
    provider = sqlite_memory_provider(project_dir)
    row = provider.get_memory(
        int(memory_id),
        agent_id=agent,
        include_private=include_private,
        max_sensitivity=max_sensitivity,
    )
    if row is None:
        payload = _error(
            "not_found_or_not_readable",
            "memory id was not found or is not readable under the provided agent policy",
        )
        payload["memory_api"] = _provider_read_memory_api_payload(
            memory_id=int(memory_id),
            provider_id=provider.provider_id,
            backend_type=provider.backend_type,
        )
        payload["safety"] = _provider_read_safety(include_private, max_sensitivity)
        return payload
    bounded = _bounded_provider_memory_read(row, line_start=line_start, line_end=line_end, max_lines=max_lines)
    if bounded.get("status") == "error":
        bounded["memory_api"] = _provider_read_memory_api_payload(
            memory_id=int(memory_id),
            provider_id=provider.provider_id,
            backend_type=provider.backend_type,
        )
        bounded["safety"] = _provider_read_safety(include_private, max_sensitivity)
        return bounded
    bounded.update(
        {
            "status": "ok",
            "agent_id": agent,
            "memory_api": _provider_read_memory_api_payload(
                memory_id=int(memory_id),
                provider_id=provider.provider_id,
                backend_type=provider.backend_type,
            ),
            "safety": _provider_read_safety(include_private, max_sensitivity),
        }
    )
    return bounded


def _provider_search_memory_api_payload() -> dict[str, Any]:
    return {
        "endpoint": "/memory/search",
        "facade": True,
        "legacy_equivalent": "/search",
        "read_surface": "active_reviewed_memory",
        "result_adapter": "provider",
        "provider_backed_result_adapter": True,
        "adapter_status": "preview",
        "default_result_adapter": False,
        "default_authority": "legacy_gateway_policy_filtered",
        "results_authority": "provider_policy_filtered",
        "read_policy_filtering": True,
        "returns_provider_raw_rows": False,
    }


def _provider_search_safety(include_private: bool, max_sensitivity: str) -> dict[str, Any]:
    return {
        "read_policy_active": True,
        "include_private": bool(include_private),
        "max_sensitivity": max_sensitivity or "low",
        "search_returns_raw_content": False,
        "returns_raw_content": False,
        "candidate_first_writes": True,
        "writes_active_knowledge": False,
    }


def _provider_read_memory_api_payload(
    *,
    memory_id: int,
    provider_id: str,
    backend_type: str,
) -> dict[str, Any]:
    return {
        "endpoint": "/memory/{id}",
        "facade": True,
        "legacy_equivalent": "/read-range",
        "bounded_read": True,
        "memory_id": int(memory_id),
        "result_adapter": "provider",
        "provider_backed_result_adapter": True,
        "adapter_status": "preview",
        "default_result_adapter": False,
        "default_authority": "legacy_gateway_read_range",
        "results_authority": "provider_policy_filtered",
        "provider_id": provider_id,
        "backend_type": backend_type,
        "read_policy_filtering": True,
        "returns_provider_raw_row": False,
        "returns_full_raw_content": False,
    }


def _provider_read_safety(include_private: bool, max_sensitivity: str) -> dict[str, Any]:
    return {
        "bounded_read": True,
        "read_policy_active": True,
        "include_private": bool(include_private),
        "max_sensitivity": max_sensitivity or "low",
        "returns_full_raw_content": False,
        "writes_active_knowledge": False,
        "candidate_first_writes": True,
    }


def _bounded_provider_memory_read(
    row: dict[str, Any],
    *,
    line_start: int,
    line_end: int,
    max_lines: int,
) -> dict[str, Any]:
    try:
        start = int(line_start or 0)
        end = int(line_end or 0)
    except (TypeError, ValueError):
        return _error("invalid_range", "line_start and line_end must be integers")
    try:
        max_i = int(max_lines or 80)
    except (TypeError, ValueError):
        max_i = 80
    if max_i <= 0:
        max_i = 80
    if start <= 0 or end <= 0 or end < start:
        return _error("invalid_range", "Range must be a positive START-END span")
    line_count = end - start + 1
    if line_count > max_i:
        return _error(
            "range_too_large",
            f"Requested {line_count} lines exceeds max {max_i}. Please split into smaller ranges.",
            max_lines=max_i,
            requested_lines=line_count,
        )
    content_raw = str(row.get("content_raw") or row.get("content") or "")
    lines = content_raw.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        return _error("empty_content", "Knowledge entry has no content_raw lines")
    if start > total_lines or end > total_lines:
        return _error(
            "range_outside_content",
            f"Requested L{start}-L{end} exceeds content length L1-L{total_lines}",
            total_lines=total_lines,
        )
    content = "\n".join(f"{line_number}|{lines[line_number - 1]}" for line_number in range(start, end + 1))
    entry_id = int(row.get("id") or 0)
    title = str(row.get("title") or "")
    citation = f"#{entry_id} {title} L{start}-L{end}"
    return {
        "entry_id": entry_id,
        "title": title,
        "range": f"L{start}-L{end}",
        "line_start": start,
        "line_end": end,
        "citation": citation,
        "content": content,
        "content_hash": _line_hash(lines, start, end),
        "node_uid": "",
        "path": "",
        "next_action": {
            "tool": "final_answer",
            "citation": citation,
            "instruction": "Use this exact citation when relying on this range.",
        },
    }


def _line_hash(lines: list[str], line_start: int, line_end: int) -> str:
    text = "\n".join(lines[line_start - 1 : line_end])
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _agent_id(value: Any) -> str:
    return str(value or "").strip().lower()


def _error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"status": "error", "error": code, "message": message, **extra}
