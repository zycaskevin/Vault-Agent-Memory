"""Supabase-backed candidate request sync.

Remote hosts may submit candidate requests, but active knowledge remains local
and candidate-first. A trusted sync host pulls requests into the local
``memory_candidates`` queue for normal review/promotion.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .db import VaultDB
from .memory import create_candidate
from .multi_host import detect_candidate_conflicts, record_memory_revision
from .sync_integrity import (
    sign_sync_payload,
    sync_hmac_primary_secret_from_env,
    sync_hmac_secret_from_env,
    sync_hmac_secrets_from_env,
    verify_sync_payload,
)

REMOTE_CANDIDATE_TABLE = "vault_memory_write_requests"
CENTRAL_CANDIDATE_TABLE = "vault_memory_candidates_central"
REMOTE_CANDIDATE_RPC = "vault_submit_memory_request"
_VALID_SCOPES = {"project", "shared", "public"}
_VALID_SENSITIVITIES = {"low", "medium"}


def _clamp_text(value: Any, *, max_len: int) -> str:
    text = str(value or "").strip()
    if len(text) > max_len:
        return text[:max_len]
    return text


def _parse_csv_or_json(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = None
            if isinstance(data, list):
                return [str(item).strip() for item in data if str(item).strip()]
        return [part.strip() for part in text.split(",") if part.strip()]
    return [str(value).strip()] if str(value).strip() else []


def _normalize_scope(value: Any) -> str:
    scope = str(value or "project").strip().lower()
    return scope if scope in _VALID_SCOPES else "project"


def _normalize_sensitivity(value: Any) -> str:
    sensitivity = str(value or "low").strip().lower()
    return sensitivity if sensitivity in _VALID_SENSITIVITIES else "low"


def _source_ref_for_request(request_id: str) -> str:
    return f"remote_write_request:{request_id}"


def _idempotency_key(payload: dict[str, Any]) -> str:
    basis = json.dumps(
        {
            "from_agent": payload.get("from_agent", ""),
            "title": payload.get("title", ""),
            "content": payload.get("content", ""),
            "source_ref": payload.get("source_ref", ""),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32]


def build_remote_candidate_request(
    *,
    title: str,
    content: str,
    from_agent: str = "",
    reason: str = "",
    category: str = "general",
    tags: str | list[str] = "",
    trust: float = 0.5,
    scope: str = "project",
    sensitivity: str = "low",
    owner_agent: str = "",
    allowed_agents: str | list[str] = "",
    memory_type: str = "remote_candidate",
    source_ref: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Normalize a remote candidate request before sending it to Supabase."""
    try:
        trust_f = max(0.0, min(1.0, float(trust)))
    except (TypeError, ValueError):
        trust_f = 0.5
    payload = {
        "title": _clamp_text(title, max_len=240),
        "content": _clamp_text(content, max_len=20_000),
        "from_agent": _clamp_text(from_agent, max_len=80),
        "reason": _clamp_text(reason, max_len=1_000),
        "category": _clamp_text(category or "general", max_len=80) or "general",
        "tags": _parse_csv_or_json(tags)[:20],
        "trust": trust_f,
        "scope": _normalize_scope(scope),
        "sensitivity": _normalize_sensitivity(sensitivity),
        "owner_agent": _clamp_text(owner_agent, max_len=80),
        "allowed_agents": _parse_csv_or_json(allowed_agents)[:20],
        "memory_type": _clamp_text(memory_type or "remote_candidate", max_len=80)
        or "remote_candidate",
        "source_ref": _clamp_text(source_ref, max_len=500),
    }
    payload["idempotency_key"] = (
        _clamp_text(idempotency_key, max_len=120) or _idempotency_key(payload)
    )
    return payload


def _get_supabase_client(*, service_role: bool):
    url = os.getenv("SUPABASE_URL")
    key = None
    if service_role:
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    else:
        key = (
            os.getenv("SUPABASE_ANON_KEY")
            or os.getenv("SUPABASE_PUBLISHABLE_KEY")
            or os.getenv("SUPABASE_KEY")
        )
    if not url or not key:
        return None
    from supabase import create_client

    return create_client(url, key)


def _response_rows(response: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in (getattr(response, "data", None) or [])]


def submit_remote_candidate_request(
    *,
    sb_client: Any | None = None,
    hmac_secret: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Submit a memory candidate request through the guarded Supabase RPC."""
    payload = build_remote_candidate_request(**kwargs)
    if not payload["title"] or not payload["content"]:
        return {
            "ok": False,
            "error": "invalid_request",
            "message": "remote candidate requests require non-empty title and content",
        }
    if hmac_secret is not None:
        signature = sign_sync_payload(payload, hmac_secret)
    else:
        primary_key = sync_hmac_primary_secret_from_env()
        signature = sign_sync_payload(
            payload,
            primary_key.get("secret", ""),
            key_id=primary_key.get("key_id", ""),
        )
    if signature:
        payload.update(signature)

    client = sb_client or _get_supabase_client(service_role=False)
    if client is None:
        return {
            "ok": False,
            "error": "remote_client_missing",
            "message": "Set SUPABASE_URL and SUPABASE_ANON_KEY or SUPABASE_PUBLISHABLE_KEY.",
        }

    params = {f"p_{key}": value for key, value in payload.items()}
    rows = _response_rows(client.rpc(REMOTE_CANDIDATE_RPC, params).execute())
    row = rows[0] if rows else {}
    return {
        "ok": True,
        "status": row.get("status", "submitted"),
        "id": row.get("id", ""),
        "created_at": row.get("created_at", ""),
        "request": {key: value for key, value in payload.items() if key != "content"},
    }


def submit_central_candidate_request(
    *,
    sb_client: Any | None = None,
    hmac_secret: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Submit a memory candidate request directly to the central candidate table."""
    payload = build_remote_candidate_request(**kwargs)
    if not payload["title"] or not payload["content"]:
        return {
            "ok": False,
            "error": "invalid_request",
            "message": "central candidate requests require non-empty title and content",
        }
    if hmac_secret is not None:
        signature = sign_sync_payload(payload, hmac_secret)
    else:
        primary_key = sync_hmac_primary_secret_from_env()
        signature = sign_sync_payload(
            payload,
            primary_key.get("secret", ""),
            key_id=primary_key.get("key_id", ""),
        )
    if signature:
        payload.update(signature)

    client = sb_client or _get_supabase_client(service_role=False)
    if client is None:
        return {
            "ok": False,
            "error": "remote_client_missing",
            "message": "Set SUPABASE_URL and SUPABASE_ANON_KEY or SUPABASE_PUBLISHABLE_KEY.",
        }

    row = _central_candidate_payload(payload)
    existing = _select_central_candidate_by_key(client, row["candidate_key"])
    if existing:
        client.table(CENTRAL_CANDIDATE_TABLE).update(row).eq(
            "candidate_key",
            row["candidate_key"],
        ).execute()
        status = "updated"
        request_id = existing.get("id", "")
        created_at = existing.get("created_at", "")
    else:
        inserted = _response_rows(
            client.table(CENTRAL_CANDIDATE_TABLE).insert(row).execute()
        )
        stored = inserted[0] if inserted else row
        status = stored.get("status", "candidate")
        request_id = stored.get("id", "")
        created_at = stored.get("created_at", "")
    return {
        "ok": True,
        "status": status,
        "id": request_id,
        "candidate_key": row["candidate_key"],
        "created_at": created_at,
        "central_candidate_table": CENTRAL_CANDIDATE_TABLE,
        "request": {key: value for key, value in payload.items() if key != "content"},
    }


def _select_submitted_requests(client: Any, *, limit: int) -> list[dict[str, Any]]:
    query = (
        client.table(REMOTE_CANDIDATE_TABLE)
        .select("*")
        .eq("status", "submitted")
        .order("created_at", desc=False)
        .limit(max(1, min(int(limit or 20), 100)))
    )
    return _response_rows(query.execute())


def _select_central_candidate_by_key(
    client: Any,
    candidate_key: str,
) -> dict[str, Any] | None:
    rows = _response_rows(
        client.table(CENTRAL_CANDIDATE_TABLE)
        .select("*")
        .eq("candidate_key", candidate_key)
        .limit(1)
        .execute()
    )
    return rows[0] if rows else None


def _select_central_candidate_requests(
    client: Any,
    *,
    limit: int,
) -> tuple[list[dict[str, Any]], str]:
    rows: list[dict[str, Any]] = []
    try:
        for status in ("candidate", "submitted"):
            query = (
                client.table(CENTRAL_CANDIDATE_TABLE)
                .select("*")
                .eq("status", status)
                .order("created_at", desc=False)
                .limit(max(1, min(int(limit or 20), 100)))
            )
            rows.extend(_response_rows(query.execute()))
    except Exception as exc:
        return [], str(exc)
    seen = set()
    unique = []
    for row in rows:
        key = str(row.get("id") or row.get("candidate_key") or "")
        if key and key not in seen:
            seen.add(key)
            row["__source_table"] = CENTRAL_CANDIDATE_TABLE
            unique.append(row)
    return unique[: max(1, min(int(limit or 20), 100))], ""


def _update_remote_request(
    client: Any,
    request_id: str,
    payload: dict[str, Any],
    *,
    table_name: str = REMOTE_CANDIDATE_TABLE,
) -> None:
    client.table(table_name).update(payload).eq("id", request_id).execute()


def _central_candidate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_key": payload.get("idempotency_key") or _idempotency_key(payload),
        "title": payload.get("title", ""),
        "content": payload.get("content", ""),
        "reason": payload.get("reason", ""),
        "category": payload.get("category", "general"),
        "tags": _parse_csv_or_json(payload.get("tags")),
        "trust": float(payload.get("trust") or 0.0),
        "scope": _normalize_scope(payload.get("scope")),
        "sensitivity": _normalize_sensitivity(payload.get("sensitivity")),
        "owner_agent": payload.get("owner_agent", ""),
        "allowed_agents": _parse_csv_or_json(payload.get("allowed_agents")),
        "from_agent": payload.get("from_agent", ""),
        "source_ref": payload.get("source_ref", ""),
        "memory_type": payload.get("memory_type", "remote_candidate"),
        "status": "candidate",
        "idempotency_key": payload.get("idempotency_key", ""),
        "hmac_key_id": payload.get("hmac_key_id", ""),
        "hmac_algorithm": payload.get("hmac_algorithm", ""),
        "payload_hash": payload.get("payload_hash", ""),
        "hmac_signature": payload.get("hmac_signature", ""),
    }


def _local_candidate_exists(db: VaultDB, source_ref: str) -> bool:
    row = db.conn.execute(
        "SELECT 1 FROM memory_candidates WHERE source_ref=? LIMIT 1",
        (source_ref,),
    ).fetchone()
    return bool(row)


def pull_remote_candidate_requests(
    project_dir: str | Path,
    *,
    agent_id: str = "",
    limit: int = 20,
    apply: bool = False,
    auto_promote_low_risk: bool = False,
    hmac_secret: str | None = None,
    require_hmac: bool | None = None,
    sb_client: Any | None = None,
) -> dict[str, Any]:
    """Pull submitted remote requests into the local candidate queue."""
    client = sb_client or _get_supabase_client(service_role=True)
    if client is None:
        return {
            "ok": False,
            "error": "service_role_missing",
            "message": "Pulling remote candidate requests requires SUPABASE_SERVICE_ROLE_KEY on a trusted sync host.",
        }

    legacy_error = ""
    try:
        rows = _select_submitted_requests(client, limit=limit)
    except Exception as exc:
        rows = []
        legacy_error = str(exc)
    central_rows, central_error = _select_central_candidate_requests(client, limit=limit)
    rows = [*rows, *central_rows]
    payload: dict[str, Any] = {
        "ok": True,
        "apply": bool(apply),
        "count": len(rows),
        "imported_count": 0,
        "skipped_count": 0,
        "auto_promote": {
            "enabled": bool(auto_promote_low_risk),
            "status": "not_run",
            "would_promote_count": 0,
            "promoted_count": 0,
        },
        "integrity": _integrity_summary(
            rows,
            hmac_secret=hmac_secret,
            require_hmac=require_hmac,
        ),
        "legacy_candidate_inbox": {
            "table": REMOTE_CANDIDATE_TABLE,
            "count": len(rows) - len(central_rows),
            "error": legacy_error,
        },
        "central_candidate_inbox": {
            "table": CENTRAL_CANDIDATE_TABLE,
            "count": len(central_rows),
            "error": central_error,
        },
        "requests": [],
    }
    if not apply:
        payload["requests"] = [_preview_request(row) for row in rows]
        return payload

    project = Path(project_dir)
    db = VaultDB(project / "vault.db").connect()
    imported_candidate_ids: list[str] = []
    revision_by_candidate_id: dict[str, str] = {}
    try:
        for row in rows:
            request_id = str(row.get("id") or "").strip()
            source_table = str(row.get("__source_table") or REMOTE_CANDIDATE_TABLE)
            source_ref = str(row.get("source_ref") or "").strip() or _source_ref_for_row(row)
            item = _preview_request(row)
            try:
                integrity = _verify_request_integrity(
                    row,
                    hmac_secret=hmac_secret,
                    require_hmac=require_hmac,
                )
                item["integrity"] = integrity
                if not integrity.get("ok", False):
                    payload["skipped_count"] += 1
                    item["status"] = "signature_invalid"
                    item["error"] = str(integrity.get("error") or "signature_invalid")
                    payload["requests"].append(item)
                    if request_id:
                        _update_remote_request(
                            client,
                            request_id,
                            {"status": "signature_invalid", "error": item["error"][:500]},
                            table_name=source_table,
                        )
                    continue
                if _local_candidate_exists(db, source_ref):
                    payload["skipped_count"] += 1
                    item["status"] = "already_imported"
                    _update_remote_request(
                        client,
                        request_id,
                        {"status": "already_imported", "error": "", "local_candidate_id": ""},
                        table_name=source_table,
                    )
                else:
                    result = create_candidate(
                        db,
                        title=row.get("title", ""),
                        content=row.get("content", ""),
                        reason=row.get("reason", ""),
                        category=row.get("category", "general"),
                        tags=_parse_csv_or_json(row.get("tags")),
                        trust=row.get("trust", 0.5),
                        source="central_memory_candidate" if source_table == CENTRAL_CANDIDATE_TABLE else "remote_write_request",
                        source_ref=source_ref,
                        scope=_normalize_scope(row.get("scope")),
                        sensitivity=_normalize_sensitivity(row.get("sensitivity")),
                        owner_agent=row.get("owner_agent") or row.get("from_agent") or agent_id or "",
                        allowed_agents=_parse_csv_or_json(row.get("allowed_agents")),
                        memory_type=row.get("memory_type") or "remote_candidate",
                    )
                    candidate_id = str(result.get("candidate_id") or "")
                    if candidate_id:
                        imported_candidate_ids.append(candidate_id)
                    item["local_candidate_id"] = candidate_id
                    item["local_status"] = result.get("status")
                    item["gates"] = result.get("gates", {})
                    remote_status = (
                        "rejected_by_local_gates"
                        if result.get("status") == "rejected"
                        else "imported"
                    )
                    revision = record_memory_revision(
                        db,
                        title=row.get("title", ""),
                        content=row.get("content", ""),
                        operation="central_candidate_imported" if source_table == CENTRAL_CANDIDATE_TABLE else "remote_candidate_imported",
                        status=str(result.get("status") or ""),
                        candidate_id=candidate_id,
                        remote_request_id=request_id,
                        source_agent=row.get("from_agent") or agent_id or "",
                        payload={"gates": result.get("gates", {}), "remote_status": remote_status},
                    )
                    item["revision_id"] = revision["revision_id"]
                    revision_by_candidate_id[candidate_id] = revision["revision_id"]
                    item["conflicts"] = detect_candidate_conflicts(
                        db,
                        candidate_id=candidate_id,
                        revision_id=revision["revision_id"],
                    )
                    payload["imported_count"] += 1
                    item["status"] = remote_status
                    _update_remote_request(
                        client,
                        request_id,
                        {
                            "status": remote_status,
                            "local_candidate_id": candidate_id,
                            "error": "",
                        },
                        table_name=source_table,
                    )
                payload["requests"].append(item)
            except Exception as exc:
                payload["skipped_count"] += 1
                item["status"] = "error"
                item["error"] = str(exc)
                payload["requests"].append(item)
                if request_id:
                    _update_remote_request(
                        client,
                        request_id,
                        {"status": "error", "error": str(exc)[:500]},
                        table_name=source_table,
                    )
        if auto_promote_low_risk:
            from .automation_lifecycle import _auto_promote_low_risk_candidates
            from .automation_policy import load_policy

            policy = load_policy(project)
            auto_promote = _auto_promote_low_risk_candidates(
                db,
                project=project,
                policy=policy,
                apply=True,
                candidate_ids=imported_candidate_ids,
            )
            payload["auto_promote"] = auto_promote
            promoted_by_candidate = {
                str(item.get("candidate_id") or ""): item
                for item in auto_promote.get("items", [])
                if item.get("promotion_status") == "promoted"
            }
            for request in payload["requests"]:
                candidate_id = str(request.get("local_candidate_id") or "")
                promoted = promoted_by_candidate.get(candidate_id)
                if promoted and request.get("id"):
                    request["status"] = "promoted_locally"
                    request["knowledge_id"] = promoted.get("knowledge_id")
                    promoted_candidate = db.get_memory_candidate(candidate_id) or {}
                    promotion_revision = record_memory_revision(
                        db,
                        title=str(promoted_candidate.get("title") or request.get("title") or ""),
                        content=str(promoted_candidate.get("content") or ""),
                        operation="remote_candidate_promoted",
                        status="promoted",
                        knowledge_id=promoted.get("knowledge_id"),
                        candidate_id=candidate_id,
                        remote_request_id=str(request["id"]),
                        parent_revision_id=revision_by_candidate_id.get(candidate_id, ""),
                        source_agent=str(request.get("from_agent") or agent_id or ""),
                        payload={"promotion_status": promoted.get("promotion_status")},
                    )
                    request["promotion_revision_id"] = promotion_revision["revision_id"]
                    _update_remote_request(
                        client,
                        str(request["id"]),
                        {
                            "status": "promoted_locally",
                            "local_candidate_id": candidate_id,
                            "error": "",
                        },
                        table_name=str(request.get("source_table") or REMOTE_CANDIDATE_TABLE),
                    )
    finally:
        db.close()
    return payload


def _preview_request(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id", ""),
        "status": row.get("status", ""),
        "created_at": row.get("created_at", ""),
        "from_agent": row.get("from_agent", ""),
        "title": row.get("title", ""),
        "category": row.get("category", "general"),
        "trust": float(row.get("trust") or 0.0),
        "scope": _normalize_scope(row.get("scope")),
        "sensitivity": _normalize_sensitivity(row.get("sensitivity")),
        "memory_type": row.get("memory_type", "remote_candidate"),
        "source_ref": row.get("source_ref", ""),
        "reason": row.get("reason", ""),
        "source_table": row.get("__source_table") or REMOTE_CANDIDATE_TABLE,
        "integrity": _verify_request_integrity(row),
    }


def _source_ref_for_row(row: dict[str, Any]) -> str:
    source_table = str(row.get("__source_table") or REMOTE_CANDIDATE_TABLE)
    request_id = str(row.get("id") or "").strip()
    if source_table == CENTRAL_CANDIDATE_TABLE:
        key = str(row.get("candidate_key") or request_id or row.get("idempotency_key") or "").strip()
        return f"central_candidate:{key}"
    return _source_ref_for_request(request_id)


def _verify_request_integrity(
    row: dict[str, Any],
    *,
    hmac_secret: str | None = None,
    require_hmac: bool | None = None,
) -> dict[str, Any]:
    secret: str | list[dict[str, str]]
    if hmac_secret is not None:
        secret = hmac_secret
        configured = bool(hmac_secret)
    else:
        keys = sync_hmac_secrets_from_env()
        secret = keys if keys else sync_hmac_secret_from_env()
        configured = bool(keys or secret)
    require = configured if require_hmac is None else bool(require_hmac)
    return verify_sync_payload(row, secret, require_signature=require)


def _integrity_summary(
    rows: list[dict[str, Any]],
    *,
    hmac_secret: str | None = None,
    require_hmac: bool | None = None,
) -> dict[str, Any]:
    checks = [
        _verify_request_integrity(row, hmac_secret=hmac_secret, require_hmac=require_hmac)
        for row in rows
    ]
    verified = sum(1 for item in checks if item.get("status") == "verified")
    unsigned = sum(1 for item in checks if item.get("status") == "unsigned")
    invalid = sum(1 for item in checks if not item.get("ok", False))
    keys = [] if hmac_secret is not None else sync_hmac_secrets_from_env()
    secret = hmac_secret if hmac_secret is not None else sync_hmac_secret_from_env()
    configured = bool(hmac_secret if hmac_secret is not None else (keys or secret))
    require = configured if require_hmac is None else bool(require_hmac)
    return {
        "hmac_supported": True,
        "hmac_required": require,
        "secret_configured": configured,
        "active_key_count": 1 if hmac_secret is not None and hmac_secret else len(keys),
        "key_ids": [] if hmac_secret is not None else [item["key_id"] for item in keys],
        "verified_count": verified,
        "unsigned_count": unsigned,
        "invalid_count": invalid,
    }
