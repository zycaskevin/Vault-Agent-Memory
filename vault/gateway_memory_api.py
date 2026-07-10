"""Vault Memory API facade helpers for the Gateway.

This module keeps the HTTP server in ``gateway.py`` thin while exposing the
additive ``/memory/*`` namespace over the existing candidate-first Gateway
behavior.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs

from .db import VaultDB
from .gateway_errors import gateway_error_suggestions
from .memory_provider import sqlite_memory_provider
from .memory_provider_result_adapter import provider_memory_get, provider_memory_search
from .multi_host import list_audit_log, record_audit_event


AppendGatewayAudit = Callable[..., None]


def gateway_memory_search(
    project_dir: str | Path,
    *,
    query: str,
    agent_id: str,
    mode: str = "keyword",
    limit: int = 10,
    include_private: bool = False,
    max_sensitivity: str = "low",
    result_adapter: str = "legacy",
    search_func: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Vault Memory API facade for governed active-memory search."""
    if _result_adapter(result_adapter) == "provider":
        return provider_memory_search(
            project_dir,
            query=query,
            agent_id=agent_id,
            mode=mode,
            limit=limit,
            include_private=include_private,
            max_sensitivity=max_sensitivity,
        )
    if search_func is None:
        from .gateway import gateway_search as search_func

    payload = search_func(
        project_dir,
        query=query,
        agent_id=agent_id,
        mode=mode,
        limit=limit,
        include_private=include_private,
        max_sensitivity=max_sensitivity,
    )
    payload["memory_api"] = {
        "endpoint": "/memory/search",
        "facade": True,
        "legacy_equivalent": "/search",
        "read_surface": "active_reviewed_memory",
        "result_adapter": "legacy",
        "default_result_adapter": True,
    }
    _attach_provider_search_probe(
        payload,
        project_dir,
        agent_id=agent_id,
        include_private=include_private,
        max_sensitivity=max_sensitivity,
    )
    return payload


def gateway_memory_create(
    project_dir: str | Path,
    *,
    body: dict[str, Any],
    agent_id: str,
    allow_shared_candidates: bool = False,
    allow_private_candidates: bool = False,
    allow_high_sensitivity_candidates: bool = False,
    allow_restricted_candidates: bool = False,
    submit_candidate_func: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Vault Memory API facade for candidate-first memory creation."""
    if submit_candidate_func is None:
        from .gateway import gateway_submit_candidate as submit_candidate_func

    agent = _agent_id(agent_id)
    payload = submit_candidate_func(
        project_dir,
        title=str(body.get("title", "")),
        content=str(body.get("content", "")),
        agent_id=agent,
        reason=_memory_reason(body, "Submitted through Vault Memory API; review before promotion."),
        layer=str(body.get("layer", "L3") or "L3"),
        category=str(body.get("category", "general") or "general"),
        tags=str(body.get("tags", "") or ""),
        trust=_float_value(body.get("trust"), 0.5),
        scope=_memory_scope(body),
        sensitivity=str(body.get("sensitivity", "low") or "low"),
        owner_agent=_memory_owner_agent(body, agent),
        allowed_agents=str(body.get("allowed_agents", "") or ""),
        memory_type=str(body.get("memory_type", "knowledge") or "knowledge"),
        source_ref=_memory_source_ref(body, agent, action="create"),
        allow_shared_candidates=allow_shared_candidates,
        allow_private_candidates=allow_private_candidates,
        allow_high_sensitivity_candidates=allow_high_sensitivity_candidates,
        allow_restricted_candidates=allow_restricted_candidates,
    )
    _mark_memory_api_candidate_payload(payload, endpoint="/memory/create", legacy_equivalent="/submit-candidate")
    _record_memory_api_event(
        project_dir,
        actor_agent=agent,
        action="memory_api:create_candidate",
        target_id=_candidate_id_from_payload(payload),
        payload={
            "endpoint": "/memory/create",
            "status": payload.get("status", ""),
            "writes_active_knowledge": False,
        },
    )
    return payload


def gateway_memory_get(
    project_dir: str | Path,
    *,
    memory_id: int,
    agent_id: str,
    line_start: int = 1,
    line_end: int = 40,
    max_lines: int = 80,
    include_private: bool = False,
    max_sensitivity: str = "low",
    result_adapter: str = "legacy",
    read_range_func: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Vault Memory API facade for bounded memory reads."""
    if int(memory_id or 0) <= 0:
        return _error("memory_id_invalid", "memory id must be a positive integer")
    if _result_adapter(result_adapter) == "provider":
        return provider_memory_get(
            project_dir,
            memory_id=int(memory_id),
            agent_id=agent_id,
            line_start=line_start,
            line_end=line_end,
            max_lines=max_lines,
            include_private=include_private,
            max_sensitivity=max_sensitivity,
        )
    if read_range_func is None:
        from .gateway import gateway_read_range as read_range_func

    payload = read_range_func(
        project_dir,
        knowledge_id=int(memory_id),
        agent_id=agent_id,
        line_start=line_start,
        line_end=line_end,
        max_lines=max_lines,
        include_private=include_private,
        max_sensitivity=max_sensitivity,
    )
    payload["memory_api"] = {
        "endpoint": "/memory/{id}",
        "facade": True,
        "legacy_equivalent": "/read-range",
        "bounded_read": True,
        "memory_id": int(memory_id),
        "result_adapter": "legacy",
        "default_result_adapter": True,
    }
    _attach_provider_get_probe(
        payload,
        project_dir,
        memory_id=int(memory_id),
        agent_id=agent_id,
        include_private=include_private,
        max_sensitivity=max_sensitivity,
    )
    return payload


def gateway_memory_update_request(
    project_dir: str | Path,
    *,
    memory_id: int,
    body: dict[str, Any],
    agent_id: str,
    allow_shared_candidates: bool = False,
    allow_private_candidates: bool = False,
    allow_high_sensitivity_candidates: bool = False,
    allow_restricted_candidates: bool = False,
    submit_candidate_func: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Submit an update request as a candidate; never edits active memory."""
    if submit_candidate_func is None:
        from .gateway import gateway_submit_candidate as submit_candidate_func

    project = Path(project_dir)
    db_path = project / "vault.db"
    agent = _agent_id(agent_id)
    if int(memory_id or 0) <= 0:
        return _error("memory_id_invalid", "memory id must be a positive integer")
    if not db_path.exists():
        return _error("db_not_found", "vault.db missing", status="blocked")
    if not agent:
        return _error("agent_id_required", "Vault Memory API update requires agent_id")
    with VaultDB(db_path) as db:
        current = db.get_knowledge(int(memory_id))
    if not current:
        return _error("memory_not_found", f"memory not found: {int(memory_id)}", status="blocked")
    proposed = _memory_update_content(current, body)
    if not proposed:
        return _error("update_payload_required", "PATCH /memory/{id} requires content, proposed_content, or patch")
    payload = submit_candidate_func(
        project,
        title=str(body.get("title") or f"Update request: {current.get('title', '')}")[:240],
        content=proposed,
        agent_id=agent,
        reason=_memory_reason(body, f"Update request for memory {int(memory_id)}; review before promotion."),
        layer=str(body.get("layer", current.get("layer") or "L3") or "L3"),
        category=str(body.get("category", "memory_update") or "memory_update"),
        tags=str(body.get("tags", "memory-api,update") or "memory-api,update"),
        trust=_float_value(body.get("trust"), 0.5),
        scope=_memory_scope(body, fallback=str(current.get("scope") or "project")),
        sensitivity=str(body.get("sensitivity", current.get("sensitivity") or "low") or "low"),
        owner_agent=_memory_owner_agent(body, agent),
        allowed_agents=str(body.get("allowed_agents", current.get("allowed_agents") or "") or ""),
        memory_type="memory_update_candidate",
        source_ref=f"memory-api:update:knowledge:{int(memory_id)}",
        allow_shared_candidates=allow_shared_candidates,
        allow_private_candidates=allow_private_candidates,
        allow_high_sensitivity_candidates=allow_high_sensitivity_candidates,
        allow_restricted_candidates=allow_restricted_candidates,
    )
    _mark_memory_api_candidate_payload(
        payload,
        endpoint="/memory/{id}",
        legacy_equivalent="/submit-candidate",
        target_memory_id=int(memory_id),
        update_request=True,
    )
    _record_memory_api_event(
        project,
        actor_agent=agent,
        action="memory_api:update_requested",
        target_id=str(int(memory_id)),
        payload={
            "candidate_id": _candidate_id_from_payload(payload),
            "status": payload.get("status", ""),
            "writes_active_knowledge": False,
        },
    )
    return payload


def gateway_memory_delete_request(
    project_dir: str | Path,
    *,
    memory_id: int,
    body: dict[str, Any] | None = None,
    agent_id: str,
    allow_shared_candidates: bool = False,
    allow_private_candidates: bool = False,
    allow_high_sensitivity_candidates: bool = False,
    allow_restricted_candidates: bool = False,
    submit_candidate_func: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Submit a soft-delete request as a candidate; never hard-deletes memory."""
    if submit_candidate_func is None:
        from .gateway import gateway_submit_candidate as submit_candidate_func

    body = body or {}
    project = Path(project_dir)
    db_path = project / "vault.db"
    agent = _agent_id(agent_id)
    if int(memory_id or 0) <= 0:
        return _error("memory_id_invalid", "memory id must be a positive integer")
    if not db_path.exists():
        return _error("db_not_found", "vault.db missing", status="blocked")
    if not agent:
        return _error("agent_id_required", "Vault Memory API delete requires agent_id")
    with VaultDB(db_path) as db:
        current = db.get_knowledge(int(memory_id))
    if not current:
        return _error("memory_not_found", f"memory not found: {int(memory_id)}", status="blocked")
    reason = str(body.get("reason", "") or "").strip() or "Reviewer should decide whether this memory should be tombstoned."
    content = (
        f"Decision request: soft-delete active memory knowledge:{int(memory_id)} through review.\n\n"
        "This is a reversible tombstone request, not a hard delete. "
        "The Gateway facade does not remove active memory directly.\n\n"
        f"Current title: {current.get('title', '')}\n"
        f"Reason: {reason}"
    )
    payload = submit_candidate_func(
        project,
        title=f"Soft-delete request: {current.get('title', '')}"[:240],
        content=content,
        agent_id=agent,
        reason=_memory_reason(body, f"Soft-delete request for memory {int(memory_id)}; review before tombstone."),
        layer=str(current.get("layer") or "L3"),
        category="memory_delete",
        tags=str(body.get("tags", "memory-api,delete,soft-delete") or "memory-api,delete,soft-delete"),
        trust=_float_value(body.get("trust"), 0.5),
        scope=_memory_scope(body, fallback=str(current.get("scope") or "project")),
        sensitivity=str(body.get("sensitivity", current.get("sensitivity") or "low") or "low"),
        owner_agent=_memory_owner_agent(body, agent),
        allowed_agents=str(body.get("allowed_agents", current.get("allowed_agents") or "") or ""),
        memory_type="memory_delete_candidate",
        source_ref=f"memory-api:delete:knowledge:{int(memory_id)}",
        allow_shared_candidates=allow_shared_candidates,
        allow_private_candidates=allow_private_candidates,
        allow_high_sensitivity_candidates=allow_high_sensitivity_candidates,
        allow_restricted_candidates=allow_restricted_candidates,
    )
    _mark_memory_api_candidate_payload(
        payload,
        endpoint="/memory/{id}",
        legacy_equivalent="/submit-candidate",
        target_memory_id=int(memory_id),
        soft_delete_request=True,
    )
    _record_memory_api_event(
        project,
        actor_agent=agent,
        action="memory_api:soft_delete_requested",
        target_id=str(int(memory_id)),
        payload={
            "candidate_id": _candidate_id_from_payload(payload),
            "status": payload.get("status", ""),
            "hard_delete": False,
            "writes_active_knowledge": False,
        },
    )
    return payload


def gateway_memory_audit(
    project_dir: str | Path,
    *,
    agent_id: str,
    memory_id: int | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Return metadata-only memory audit rows."""
    project = Path(project_dir)
    db_path = project / "vault.db"
    agent = _agent_id(agent_id)
    if not db_path.exists():
        return _error("db_not_found", "vault.db missing", status="blocked")
    if not agent:
        return _error("agent_id_required", "Vault Memory API audit requires agent_id")
    limit_i = max(1, min(_int_value(limit, 20), 100))
    with VaultDB(db_path) as db:
        rows = list_audit_log(db, limit=max(limit_i * 3, limit_i))
    filtered = []
    memory_id_text = str(memory_id or "")
    for row in rows:
        if memory_id_text and str(row.get("target_id") or "") != memory_id_text:
            continue
        filtered.append(_compact_audit_row(row))
        if len(filtered) >= limit_i:
            break
    return {
        "status": "ok",
        "agent_id": agent,
        "memory_id": int(memory_id) if memory_id else None,
        "events": filtered,
        "count": len(filtered),
        "memory_api": {"endpoint": "/memory/audit", "facade": True, "metadata_only": True},
        "safety": {"returns_raw_audit_payloads": False, "writes_active_knowledge": False},
    }


def gateway_memory_timeline(
    project_dir: str | Path,
    *,
    agent_id: str,
    memory_id: int,
    limit: int = 20,
    include_private: bool = False,
    max_sensitivity: str = "low",
    read_range_func: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return metadata-only timeline rows for one memory id."""
    if read_range_func is None:
        from .gateway import gateway_read_range as read_range_func

    project = Path(project_dir)
    db_path = project / "vault.db"
    agent = _agent_id(agent_id)
    if int(memory_id or 0) <= 0:
        return _error("memory_id_invalid", "memory id must be a positive integer")
    if not db_path.exists():
        return _error("db_not_found", "vault.db missing", status="blocked")
    if not agent:
        return _error("agent_id_required", "Vault Memory API timeline requires agent_id")
    policy_probe = read_range_func(
        project,
        knowledge_id=int(memory_id),
        agent_id=agent,
        line_start=1,
        line_end=1,
        max_lines=1,
        include_private=include_private,
        max_sensitivity=max_sensitivity,
    )
    if policy_probe.get("error"):
        return policy_probe
    limit_i = max(1, min(_int_value(limit, 20), 100))
    with VaultDB(db_path) as db:
        current = db.get_knowledge(int(memory_id))
        revisions = db.conn.execute(
            """SELECT id, created_at, operation, status, source_agent, revision_hash, content_hash
               FROM memory_revisions
               WHERE knowledge_id=?
               ORDER BY created_at DESC
               LIMIT ?""",
            (int(memory_id), limit_i),
        ).fetchall()
        audits = [
            _compact_audit_row(row)
            for row in list_audit_log(db, limit=max(limit_i * 3, limit_i))
            if str(row.get("target_id") or "") == str(int(memory_id))
        ][:limit_i]
    current_meta = {
        key: current.get(key)
        for key in (
            "id",
            "title",
            "layer",
            "category",
            "scope",
            "sensitivity",
            "owner_agent",
            "memory_type",
            "status",
            "updated_at",
            "valid_from",
            "valid_until",
            "expires_at",
        )
    } if current else {}
    return {
        "status": "ok",
        "agent_id": agent,
        "memory_id": int(memory_id),
        "current": current_meta,
        "revisions": [dict(row) for row in revisions],
        "audit_events": audits,
        "memory_api": {"endpoint": "/memory/timeline", "facade": True, "metadata_only": True},
        "safety": {"returns_raw_memory_content": False, "returns_raw_audit_payloads": False},
    }


def gateway_memory_http_get(
    parsed: Any,
    project_dir: str | Path,
    *,
    append_audit: AppendGatewayAudit,
    audit_context: dict[str, Any],
) -> dict[str, Any] | None:
    agent = _request_agent({}, parsed)
    if parsed.path == "/memory/audit":
        payload = gateway_memory_audit(
            project_dir,
            agent_id=agent,
            memory_id=_optional_int_query(parsed, "memory_id"),
            limit=_int_query(parsed, "limit", 20),
        )
        append_audit(Path(project_dir), "memory_api_audit", agent, payload.get("status", "ok"), **audit_context)
        return payload
    if parsed.path == "/memory/timeline":
        memory_id = _int_query(parsed, "memory_id", 0)
        payload = gateway_memory_timeline(
            project_dir,
            agent_id=agent,
            memory_id=memory_id,
            limit=_int_query(parsed, "limit", 20),
            include_private=_bool_query(parsed, "include_private", False),
            max_sensitivity=_str_query(parsed, "max_sensitivity", "low"),
        )
        append_audit(
            Path(project_dir),
            "memory_api_timeline",
            agent,
            payload.get("status", "ok"),
            memory_id=memory_id,
            **audit_context,
        )
        return payload
    memory_id = _memory_id_from_path(parsed.path)
    if memory_id is None:
        return None
    payload = gateway_memory_get(
        project_dir,
        memory_id=memory_id,
        agent_id=agent,
        line_start=_int_query(parsed, "line_start", 1),
        line_end=_int_query(parsed, "line_end", 40),
        max_lines=_int_query(parsed, "max_lines", 80),
        include_private=_bool_query(parsed, "include_private", False),
        max_sensitivity=_str_query(parsed, "max_sensitivity", "low"),
        result_adapter=_str_query(parsed, "result_adapter", "legacy"),
    )
    append_audit(
        Path(project_dir),
        "memory_api_get",
        agent,
        payload.get("status", "ok"),
        memory_id=memory_id,
        **audit_context,
    )
    return payload


def gateway_memory_http_post(
    parsed: Any,
    project_dir: str | Path,
    *,
    body: dict[str, Any],
    agent_id: str,
    append_audit: AppendGatewayAudit,
    audit_context: dict[str, Any],
    allow_shared_candidates: bool = False,
    allow_private_candidates: bool = False,
    allow_high_sensitivity_candidates: bool = False,
    allow_restricted_candidates: bool = False,
) -> dict[str, Any] | None:
    if parsed.path == "/memory/search":
        payload = gateway_memory_search(
            project_dir,
            query=str(body.get("query", "")),
            agent_id=agent_id,
            mode=str(body.get("mode", "keyword")),
            limit=_int_value(body.get("limit"), 10),
            include_private=_bool_value(body.get("include_private"), False),
            max_sensitivity=str(body.get("max_sensitivity", "low") or "low"),
            result_adapter=str(body.get("result_adapter", "legacy") or "legacy"),
        )
        append_audit(
            Path(project_dir),
            "memory_api_search",
            agent_id,
            payload.get("status", "ok"),
            query=str(body.get("query", "")),
            **audit_context,
        )
        return payload
    if parsed.path == "/memory/create":
        payload = gateway_memory_create(
            project_dir,
            body=body,
            agent_id=agent_id,
            allow_shared_candidates=allow_shared_candidates,
            allow_private_candidates=allow_private_candidates,
            allow_high_sensitivity_candidates=allow_high_sensitivity_candidates,
            allow_restricted_candidates=allow_restricted_candidates,
        )
        candidate = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else {}
        append_audit(
            Path(project_dir),
            "memory_api_create",
            agent_id,
            payload.get("status", "ok"),
            candidate_id=candidate.get("candidate_id", ""),
            title=str(body.get("title", "")),
            **audit_context,
        )
        return payload
    return None


def gateway_memory_http_patch(
    parsed: Any,
    project_dir: str | Path,
    *,
    body: dict[str, Any],
    agent_id: str,
    append_audit: AppendGatewayAudit,
    audit_context: dict[str, Any],
    allow_shared_candidates: bool = False,
    allow_private_candidates: bool = False,
    allow_high_sensitivity_candidates: bool = False,
    allow_restricted_candidates: bool = False,
) -> dict[str, Any] | None:
    memory_id = _memory_id_from_path(parsed.path)
    if memory_id is None:
        return None
    payload = gateway_memory_update_request(
        project_dir,
        memory_id=memory_id,
        body=body,
        agent_id=agent_id,
        allow_shared_candidates=allow_shared_candidates,
        allow_private_candidates=allow_private_candidates,
        allow_high_sensitivity_candidates=allow_high_sensitivity_candidates,
        allow_restricted_candidates=allow_restricted_candidates,
    )
    candidate = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else {}
    append_audit(
        Path(project_dir),
        "memory_api_update_request",
        agent_id,
        payload.get("status", "ok"),
        memory_id=memory_id,
        candidate_id=candidate.get("candidate_id", ""),
        **audit_context,
    )
    return payload


def gateway_memory_http_delete(
    parsed: Any,
    project_dir: str | Path,
    *,
    body: dict[str, Any] | None,
    agent_id: str,
    append_audit: AppendGatewayAudit,
    audit_context: dict[str, Any],
    allow_shared_candidates: bool = False,
    allow_private_candidates: bool = False,
    allow_high_sensitivity_candidates: bool = False,
    allow_restricted_candidates: bool = False,
) -> dict[str, Any] | None:
    memory_id = _memory_id_from_path(parsed.path)
    if memory_id is None:
        return None
    payload = gateway_memory_delete_request(
        project_dir,
        memory_id=memory_id,
        body=body or {},
        agent_id=agent_id,
        allow_shared_candidates=allow_shared_candidates,
        allow_private_candidates=allow_private_candidates,
        allow_high_sensitivity_candidates=allow_high_sensitivity_candidates,
        allow_restricted_candidates=allow_restricted_candidates,
    )
    candidate = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else {}
    append_audit(
        Path(project_dir),
        "memory_api_soft_delete_request",
        agent_id,
        payload.get("status", "ok"),
        memory_id=memory_id,
        candidate_id=candidate.get("candidate_id", ""),
        **audit_context,
    )
    return payload


def _agent_id(value: Any) -> str:
    return str(value or "").strip().lower()


def _result_adapter(value: Any) -> str:
    adapter = str(value or "legacy").strip().lower()
    return adapter if adapter in {"legacy", "provider"} else "legacy"


def _request_agent(body: dict[str, Any], parsed: Any) -> str:
    query = parse_qs(parsed.query)
    return _agent_id(body.get("agent_id") or (query.get("agent_id") or [""])[0])


def _memory_id_from_path(path: str) -> int | None:
    prefix = "/memory/"
    if not path.startswith(prefix):
        return None
    raw = path[len(prefix):].strip("/")
    if not raw or "/" in raw or raw in {"search", "create", "audit", "timeline", "promote", "link", "sync"}:
        return None
    try:
        return int(raw)
    except ValueError:
        return 0


def _int_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _float_value(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


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


def _str_query(parsed: Any, name: str, default: str) -> str:
    query = parse_qs(parsed.query)
    return str((query.get(name) or [default])[0] or default)


def _int_query(parsed: Any, name: str, default: int) -> int:
    return _int_value(_str_query(parsed, name, str(default)), default)


def _optional_int_query(parsed: Any, name: str) -> int | None:
    query = parse_qs(parsed.query)
    if name not in query:
        return None
    value = _int_value((query.get(name) or ["0"])[0], 0)
    return value if value > 0 else None


def _bool_query(parsed: Any, name: str, default: bool) -> bool:
    query = parse_qs(parsed.query)
    if name not in query:
        return bool(default)
    return _bool_value((query.get(name) or [""])[0], default)


def _memory_scope(body: dict[str, Any], *, fallback: str = "project") -> str:
    return str(body.get("scope") or body.get("permission_scope") or fallback or "project")


def _memory_owner_agent(body: dict[str, Any], agent: str) -> str:
    return str(body.get("owner_agent") or body.get("created_by_agent") or agent or "")


def _memory_source_ref(body: dict[str, Any], agent: str, *, action: str) -> str:
    explicit = str(body.get("source_ref", "") or "").strip()
    if explicit:
        return explicit
    source_app = str(body.get("source_app", "") or "").strip() or "unknown-app"
    workspace = str(body.get("workspace_id", "") or "").strip() or "local"
    return f"memory-api:{action}:{source_app}:{workspace}:{agent or 'unknown-agent'}"


def _memory_reason(body: dict[str, Any], default: str) -> str:
    reason = str(body.get("reason", "") or "").strip() or default
    metadata = {
        key: str(body.get(key, "") or "").strip()
        for key in ("owner_user", "workspace_id", "source_app", "source_device", "permission_scope")
        if str(body.get(key, "") or "").strip()
    }
    if not metadata:
        return reason
    return f"{reason} Metadata: {json.dumps(metadata, ensure_ascii=False, sort_keys=True)}"


def _memory_update_content(current: dict[str, Any], body: dict[str, Any]) -> str:
    content = str(body.get("proposed_content") or body.get("content") or "").strip()
    patch = body.get("patch") if isinstance(body.get("patch"), dict) else {}
    if not content and not patch:
        patch = {
            key: body.get(key)
            for key in ("title", "summary", "category", "tags", "valid_from", "valid_until", "expires_at")
            if body.get(key) not in (None, "")
        }
    if not content and patch:
        content = "Proposed patch JSON:\n" + json.dumps(patch, ensure_ascii=False, sort_keys=True, indent=2)
    if not content:
        return ""
    return (
        f"Decision request: update active memory knowledge:{current.get('id')} through review.\n\n"
        "The Gateway facade records this as a candidate and does not edit active memory directly.\n\n"
        f"Current title: {current.get('title', '')}\n\n"
        f"{content}"
    )


def _candidate_id_from_payload(payload: dict[str, Any]) -> str:
    candidate = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else {}
    return str(candidate.get("candidate_id") or candidate.get("id") or "")


def _mark_memory_api_candidate_payload(
    payload: dict[str, Any],
    *,
    endpoint: str,
    legacy_equivalent: str,
    target_memory_id: int | None = None,
    update_request: bool = False,
    soft_delete_request: bool = False,
) -> None:
    payload["memory_api"] = {
        "endpoint": endpoint,
        "facade": True,
        "legacy_equivalent": legacy_equivalent,
        "target_memory_id": target_memory_id,
    }
    safety = payload.setdefault("safety", {})
    safety.update(
        {
            "vault_memory_api_facade": True,
            "writes_active_knowledge": False,
            "candidate_first": True,
            "update_request": bool(update_request),
            "soft_delete_request": bool(soft_delete_request),
            "hard_delete": False,
        }
    )


def _record_memory_api_event(
    project_dir: str | Path,
    *,
    actor_agent: str,
    action: str,
    target_id: str,
    payload: dict[str, Any],
) -> None:
    try:
        db_path = Path(project_dir) / "vault.db"
        if not db_path.exists():
            return
        with VaultDB(db_path) as db:
            record_audit_event(
                db,
                actor_agent=actor_agent,
                action=action,
                target_type="knowledge" if target_id.isdigit() else "candidate",
                target_id=target_id,
                payload=payload,
            )
    except Exception:
        return


def _attach_provider_search_probe(
    payload: dict[str, Any],
    project_dir: str | Path,
    *,
    agent_id: str,
    include_private: bool,
    max_sensitivity: str,
) -> None:
    """Attach metadata-only provider read adoption details without changing policy results."""
    if payload.get("status") != "ok":
        return
    try:
        provider = sqlite_memory_provider(project_dir)
        returned_ids = {
            int(row.get("id"))
            for row in payload.get("results", [])
            if isinstance(row, dict) and str(row.get("id") or "").isdigit()
        }
        provider_ids = {
            memory_id
            for memory_id in returned_ids
            if provider.get_memory(
                memory_id,
                agent_id=agent_id,
                include_private=include_private,
                max_sensitivity=max_sensitivity,
            ) is not None
        }
        payload.setdefault("memory_api", {})["provider_read"] = {
            "provider_id": provider.provider_id,
            "backend_type": provider.backend_type,
            "mode": "shadow_metadata_probe",
            "policy_authority": "legacy_gateway_search",
            "results_authority": "legacy_gateway_policy_filtered",
            "read_policy_filtering": True,
            "include_private": bool(include_private),
            "max_sensitivity": max_sensitivity or "low",
            "returned_result_count": len(returned_ids),
            "returned_ids_present_in_provider": sorted(returned_ids & provider_ids),
            "probes_returned_ids_only": True,
            "returns_provider_raw_rows": False,
        }
    except Exception:
        payload.setdefault("memory_api", {})["provider_read"] = {
            "mode": "shadow_metadata_probe",
            "status": "skipped",
            "reason": "provider_probe_failed",
            "returns_provider_raw_rows": False,
        }


def _attach_provider_get_probe(
    payload: dict[str, Any],
    project_dir: str | Path,
    *,
    memory_id: int,
    agent_id: str,
    include_private: bool,
    max_sensitivity: str,
) -> None:
    """Attach provider metadata for a bounded read after the legacy policy gate."""
    if payload.get("status") != "ok":
        return
    try:
        provider = sqlite_memory_provider(project_dir)
        row = provider.get_memory(
            memory_id,
            agent_id=agent_id,
            include_private=include_private,
            max_sensitivity=max_sensitivity,
        )
        payload.setdefault("memory_api", {})["provider_read"] = {
            "provider_id": provider.provider_id,
            "backend_type": provider.backend_type,
            "mode": "metadata_probe_after_legacy_policy_gate",
            "policy_authority": "legacy_gateway_read_range",
            "read_policy_filtering": True,
            "include_private": bool(include_private),
            "max_sensitivity": max_sensitivity or "low",
            "metadata_only": True,
            "memory_exists": bool(row),
            "memory_status": row.get("status", "") if row else "",
            "memory_type": row.get("memory_type", "") if row else "",
            "scope": row.get("scope", "") if row else "",
            "sensitivity": row.get("sensitivity", "") if row else "",
            "returns_provider_raw_content": False,
        }
    except Exception:
        payload.setdefault("memory_api", {})["provider_read"] = {
            "mode": "metadata_probe_after_legacy_policy_gate",
            "status": "skipped",
            "reason": "provider_probe_failed",
            "returns_provider_raw_content": False,
        }


def _compact_audit_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "created_at": row.get("created_at", ""),
        "actor_agent": row.get("actor_agent", ""),
        "action": row.get("action", ""),
        "target_type": row.get("target_type", ""),
        "target_id": row.get("target_id", ""),
        "revision_id": row.get("revision_id", ""),
    }


def _error(code: str, message: str, *, status: str = "error") -> dict[str, Any]:
    payload: dict[str, Any] = {"status": status, "error": code, "message": message}
    suggestions = gateway_error_suggestions(code)
    if suggestions:
        payload.update(suggestions)
    return payload
