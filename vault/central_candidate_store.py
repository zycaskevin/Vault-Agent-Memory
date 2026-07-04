"""Self-hosted Central Memory Station candidate inbox.

This module backs the Gateway / Remote Server path when Supabase is not used.
It stores incoming candidate memory in a small local SQLite database, then a
trusted host can import those rows into the normal local ``memory_candidates``
review queue.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

from .db import VaultDB
from .memory import create_candidate
from .multi_host import detect_candidate_conflicts, record_memory_revision
from .remote_candidates import build_remote_candidate_request
from .sync_integrity import (
    sign_sync_payload,
    sync_hmac_primary_secret_from_env,
    sync_hmac_secret_from_env,
    sync_hmac_secrets_from_env,
    verify_sync_payload,
)


CENTRAL_CANDIDATE_DB = "vault-central.db"
CENTRAL_CANDIDATE_TABLE = "vault_memory_candidates_central"


def submit_central_candidate_local(
    project_dir: str | Path,
    *,
    hmac_secret: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Submit a candidate into the self-hosted central candidate inbox."""
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

    row = _central_candidate_row(payload)
    with _connect(project_dir) as conn:
        existing = conn.execute(
            f"SELECT id, created_at FROM {CENTRAL_CANDIDATE_TABLE} WHERE candidate_key=?",
            (row["candidate_key"],),
        ).fetchone()
        now = _now()
        if existing:
            row["updated_at"] = now
            _update_candidate_row(conn, str(existing["id"]), row)
            status = "updated"
            candidate_id = str(existing["id"])
            created_at = str(existing["created_at"] or "")
        else:
            row["created_at"] = now
            row["updated_at"] = now
            _insert_candidate_row(conn, row)
            status = "candidate"
            candidate_id = str(
                conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
            )
            created_at = now
    return {
        "ok": True,
        "status": status,
        "id": candidate_id,
        "candidate_key": row["candidate_key"],
        "created_at": created_at,
        "central_candidate_table": CENTRAL_CANDIDATE_TABLE,
        "central_candidate_db": str(_db_path(project_dir)),
        "request": {key: value for key, value in payload.items() if key != "content"},
    }


def pull_central_candidates_local(
    project_dir: str | Path,
    *,
    agent_id: str = "",
    limit: int = 20,
    apply: bool = False,
    auto_promote_low_risk: bool = False,
    hmac_secret: str | None = None,
    require_hmac: bool | None = None,
) -> dict[str, Any]:
    """Pull self-hosted central candidates into local memory_candidates."""
    rows = _select_candidate_rows(project_dir, limit=limit)
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
        "central_candidate_inbox": {
            "mode": "self_hosted_sqlite",
            "db_path": str(_db_path(project_dir)),
            "table": CENTRAL_CANDIDATE_TABLE,
            "count": len(rows),
        },
        "integrity": _integrity_summary(
            rows,
            hmac_secret=hmac_secret,
            require_hmac=require_hmac,
        ),
        "requests": [],
    }
    if not apply:
        payload["requests"] = [_preview(row) for row in rows]
        return payload

    project = Path(project_dir).expanduser().resolve()
    imported_candidate_ids: list[str] = []
    revision_by_candidate_id: dict[str, str] = {}
    with VaultDB(project / "vault.db") as db:
        for row in rows:
            item = _preview(row)
            request_id = str(row.get("id") or "")
            source_ref = str(row.get("source_ref") or "").strip() or _source_ref(row)
            try:
                integrity = _verify(row, hmac_secret=hmac_secret, require_hmac=require_hmac)
                item["integrity"] = integrity
                if not integrity.get("ok", False):
                    payload["skipped_count"] += 1
                    item["status"] = "signature_invalid"
                    item["error"] = str(integrity.get("error") or "signature_invalid")
                    _mark_candidate(
                        project,
                        request_id,
                        status="signature_invalid",
                        error=item["error"],
                    )
                    payload["requests"].append(item)
                    continue
                if _local_candidate_exists(db, source_ref):
                    payload["skipped_count"] += 1
                    item["status"] = "already_imported"
                    _mark_candidate(project, request_id, status="already_imported")
                    payload["requests"].append(item)
                    continue
                result = create_candidate(
                    db,
                    title=str(row.get("title") or ""),
                    content=str(row.get("content") or ""),
                    reason=str(row.get("reason") or ""),
                    category=str(row.get("category") or "general"),
                    tags=_json_list(row.get("tags")),
                    trust=float(row.get("trust") or 0.5),
                    source="central_memory_candidate",
                    source_ref=source_ref,
                    scope=str(row.get("scope") or "project"),
                    sensitivity=str(row.get("sensitivity") or "low"),
                    owner_agent=str(row.get("owner_agent") or row.get("from_agent") or agent_id),
                    allowed_agents=_json_list(row.get("allowed_agents")),
                    memory_type=str(row.get("memory_type") or "remote_candidate"),
                )
                candidate_id = str(result.get("candidate_id") or "")
                if candidate_id:
                    imported_candidate_ids.append(candidate_id)
                revision = record_memory_revision(
                    db,
                    title=str(row.get("title") or ""),
                    content=str(row.get("content") or ""),
                    operation="central_candidate_imported",
                    status=str(result.get("status") or ""),
                    candidate_id=candidate_id,
                    remote_request_id=request_id,
                    source_agent=str(row.get("from_agent") or agent_id or ""),
                    payload={"gates": result.get("gates", {}), "remote_status": "imported"},
                )
                item["local_candidate_id"] = candidate_id
                item["local_status"] = result.get("status")
                item["revision_id"] = revision["revision_id"]
                revision_by_candidate_id[candidate_id] = revision["revision_id"]
                item["conflicts"] = detect_candidate_conflicts(
                    db,
                    candidate_id=candidate_id,
                    revision_id=revision["revision_id"],
                )
                item["status"] = "imported"
                payload["imported_count"] += 1
                _mark_candidate(
                    project,
                    request_id,
                    status="imported",
                    local_candidate_id=candidate_id,
                )
                payload["requests"].append(item)
            except Exception as exc:
                payload["skipped_count"] += 1
                item["status"] = "error"
                item["error"] = str(exc)
                _mark_candidate(project, request_id, status="error", error=str(exc))
                payload["requests"].append(item)
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
                        operation="central_candidate_promoted",
                        status="promoted",
                        knowledge_id=promoted.get("knowledge_id"),
                        candidate_id=candidate_id,
                        remote_request_id=str(request["id"]),
                        parent_revision_id=revision_by_candidate_id.get(candidate_id, ""),
                        source_agent=str(request.get("from_agent") or agent_id or ""),
                        payload={"promotion_status": promoted.get("promotion_status")},
                    )
                    request["promotion_revision_id"] = promotion_revision["revision_id"]
                    _mark_candidate(
                        project,
                        str(request["id"]),
                        status="promoted_locally",
                        local_candidate_id=candidate_id,
                    )
    return payload


def central_candidate_inbox_status(project_dir: str | Path, *, limit: int = 20) -> dict[str, Any]:
    """Return a compact self-hosted central candidate inbox status."""
    rows = _select_candidate_rows(project_dir, limit=limit)
    return {
        "ok": True,
        "mode": "self_hosted_sqlite",
        "db_path": str(_db_path(project_dir)),
        "table": CENTRAL_CANDIDATE_TABLE,
        "count": len(rows),
        "requests": [_preview(row) for row in rows],
    }


def _connect(project_dir: str | Path) -> sqlite3.Connection:
    path = _db_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {CENTRAL_CANDIDATE_TABLE} (
            id integer primary key autoincrement,
            candidate_key text not null unique,
            title text not null default '',
            content text not null default '',
            reason text not null default '',
            category text not null default 'general',
            tags text not null default '[]',
            trust real not null default 0,
            scope text not null default 'project',
            sensitivity text not null default 'low',
            owner_agent text not null default '',
            allowed_agents text not null default '[]',
            from_agent text not null default '',
            source_ref text not null default '',
            memory_type text not null default 'remote_candidate',
            status text not null default 'candidate',
            gate_status text not null default '{{}}',
            idempotency_key text not null default '',
            hmac_key_id text not null default '',
            hmac_algorithm text not null default '',
            payload_hash text not null default '',
            hmac_signature text not null default '',
            local_candidate_id text not null default '',
            error text not null default '',
            created_at text not null default '',
            updated_at text not null default ''
        )
        """
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{CENTRAL_CANDIDATE_TABLE}_status "
        f"ON {CENTRAL_CANDIDATE_TABLE} (status, created_at)"
    )
    return conn


def _db_path(project_dir: str | Path) -> Path:
    return Path(project_dir).expanduser().resolve() / CENTRAL_CANDIDATE_DB


def _central_candidate_row(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_key": payload.get("idempotency_key") or "",
        "title": payload.get("title", ""),
        "content": payload.get("content", ""),
        "reason": payload.get("reason", ""),
        "category": payload.get("category", "general"),
        "tags": json.dumps(payload.get("tags") or [], ensure_ascii=False),
        "trust": float(payload.get("trust") or 0.0),
        "scope": payload.get("scope", "project"),
        "sensitivity": payload.get("sensitivity", "low"),
        "owner_agent": payload.get("owner_agent", ""),
        "allowed_agents": json.dumps(payload.get("allowed_agents") or [], ensure_ascii=False),
        "from_agent": payload.get("from_agent", ""),
        "source_ref": payload.get("source_ref", ""),
        "memory_type": payload.get("memory_type", "remote_candidate"),
        "status": "candidate",
        "idempotency_key": payload.get("idempotency_key", ""),
        "hmac_key_id": payload.get("hmac_key_id", ""),
        "hmac_algorithm": payload.get("hmac_algorithm", ""),
        "payload_hash": payload.get("payload_hash", ""),
        "hmac_signature": payload.get("hmac_signature", ""),
        "gate_status": "{}",
        "local_candidate_id": "",
        "error": "",
    }


def _insert_candidate_row(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    columns = list(row)
    placeholders = ", ".join("?" for _ in columns)
    conn.execute(
        f"INSERT INTO {CENTRAL_CANDIDATE_TABLE} ({', '.join(columns)}) VALUES ({placeholders})",
        [row[column] for column in columns],
    )
    conn.commit()


def _update_candidate_row(conn: sqlite3.Connection, row_id: str, row: dict[str, Any]) -> None:
    columns = [column for column in row if column not in {"created_at"}]
    conn.execute(
        f"UPDATE {CENTRAL_CANDIDATE_TABLE} SET "
        + ", ".join(f"{column}=?" for column in columns)
        + " WHERE id=?",
        [row[column] for column in columns] + [row_id],
    )
    conn.commit()


def _select_candidate_rows(project_dir: str | Path, *, limit: int) -> list[dict[str, Any]]:
    with _connect(project_dir) as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM {CENTRAL_CANDIDATE_TABLE}
            WHERE status IN ('candidate', 'submitted')
            ORDER BY created_at ASC, id ASC
            LIMIT ?
            """,
            (max(1, min(int(limit or 20), 100)),),
        ).fetchall()
    return [_row_to_payload(row) for row in rows]


def _row_to_payload(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload["id"] = str(payload.get("id") or "")
    payload["tags"] = _json_list(payload.get("tags"))
    payload["allowed_agents"] = _json_list(payload.get("allowed_agents"))
    return payload


def _mark_candidate(
    project_dir: str | Path,
    row_id: str,
    *,
    status: str,
    local_candidate_id: str = "",
    error: str = "",
) -> None:
    with _connect(project_dir) as conn:
        conn.execute(
            f"""
            UPDATE {CENTRAL_CANDIDATE_TABLE}
            SET status=?, local_candidate_id=?, error=?, updated_at=?
            WHERE id=?
            """,
            (status, local_candidate_id, error[:500], _now(), row_id),
        )
        conn.commit()


def _preview(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or ""),
        "candidate_key": row.get("candidate_key", ""),
        "status": row.get("status", ""),
        "created_at": row.get("created_at", ""),
        "from_agent": row.get("from_agent", ""),
        "title": row.get("title", ""),
        "category": row.get("category", "general"),
        "trust": float(row.get("trust") or 0.0),
        "scope": row.get("scope", "project"),
        "sensitivity": row.get("sensitivity", "low"),
        "memory_type": row.get("memory_type", "remote_candidate"),
        "source_ref": row.get("source_ref", ""),
        "reason": row.get("reason", ""),
    }


def _verify(
    row: dict[str, Any],
    *,
    hmac_secret: str | None = None,
    require_hmac: bool | None = None,
) -> dict[str, Any]:
    if hmac_secret is not None:
        secret: str | list[dict[str, str]] = hmac_secret
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
    checks = [_verify(row, hmac_secret=hmac_secret, require_hmac=require_hmac) for row in rows]
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
        "verified_count": sum(1 for item in checks if item.get("status") == "verified"),
        "unsigned_count": sum(1 for item in checks if item.get("status") == "unsigned"),
        "invalid_count": sum(1 for item in checks if not item.get("ok", False)),
    }


def _local_candidate_exists(db: VaultDB, source_ref: str) -> bool:
    row = db.conn.execute(
        "SELECT 1 FROM memory_candidates WHERE source_ref=? LIMIT 1",
        (source_ref,),
    ).fetchone()
    return bool(row)


def _source_ref(row: dict[str, Any]) -> str:
    key = str(row.get("candidate_key") or row.get("id") or "").strip()
    return f"central_candidate:{key}"


def _json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, list):
            return [str(item).strip() for item in decoded if str(item).strip()]
    return [part.strip() for part in text.split(",") if part.strip()]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
