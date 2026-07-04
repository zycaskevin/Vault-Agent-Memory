"""Supabase Central Memory Station table sync helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .db import VaultDB
from .privacy import scan_privacy


ACTIVE_SNAPSHOT_TABLE = "vault_active_memory_snapshots"
REVISION_TABLE = "vault_memory_revisions"
EVENT_TABLE = "vault_memory_events"
SYNC_CURSOR_TABLE = "vault_sync_cursors"


def sync_active_memory_snapshots(
    project_dir: str | Path,
    *,
    db_path: str | Path | None = None,
    sb_client: Any | None = None,
    agent_id: str = "",
    device_id: str = "",
    include_content: bool = False,
    limit: int = 1000,
) -> dict[str, Any]:
    """Push reviewed local active memory into Central Memory Station tables."""
    project = Path(project_dir).expanduser().resolve()
    db_file = Path(db_path).expanduser().resolve() if db_path else project / "vault.db"
    client = sb_client or _get_service_client()
    if client is None:
        return {
            "ok": False,
            "error": "central_store_client_missing",
            "message": "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY on a trusted sync host.",
        }

    started_at = _utc_now()
    project_key = _project_key(project)
    rows = _load_active_rows(db_file, limit=limit)
    payload: dict[str, Any] = {
        "ok": True,
        "project_dir": str(project),
        "db_path": str(db_file),
        "table": ACTIVE_SNAPSHOT_TABLE,
        "project_key": project_key,
        "include_content": bool(include_content),
        "count": len(rows),
        "inserted_count": 0,
        "updated_count": 0,
        "unchanged_count": 0,
        "failed_count": 0,
        "items": [],
        "started_at": started_at,
    }
    latest_updated_at = ""

    for row in rows:
        snapshot = build_active_memory_snapshot(row, project_key=project_key, include_content=include_content)
        latest_updated_at = max(latest_updated_at, str(row.get("updated_at") or row.get("created_at") or ""))
        try:
            result = _upsert_snapshot(client, snapshot, actor_agent_id=agent_id)
            payload[f"{result['action']}_count"] += 1
            payload["items"].append(
                {
                    "memory_key": snapshot["memory_key"],
                    "local_knowledge_id": snapshot["local_knowledge_id"],
                    "title": snapshot["title"],
                    "action": result["action"],
                    "revision": result["revision"],
                }
            )
        except Exception as exc:
            payload["failed_count"] += 1
            payload["items"].append(
                {
                    "memory_key": snapshot["memory_key"],
                    "local_knowledge_id": snapshot["local_knowledge_id"],
                    "title": snapshot["title"],
                    "action": "failed",
                    "error": str(exc),
                }
            )

    completed_at = _utc_now()
    payload["completed_at"] = completed_at
    payload["ok"] = payload["failed_count"] == 0
    payload["status"] = "ok" if payload["ok"] else "partial"

    try:
        _append_event(
            client,
            {
                "event_type": "active_snapshots_synced",
                "actor_agent_id": agent_id or "",
                "device_id": device_id or "",
                "memory_key": "",
                "source_ref": f"project:{project_key}",
                "payload": {
                    "count": payload["count"],
                    "inserted_count": payload["inserted_count"],
                    "updated_count": payload["updated_count"],
                    "unchanged_count": payload["unchanged_count"],
                    "failed_count": payload["failed_count"],
                },
                "created_at": completed_at,
            },
        )
        _upsert_sync_cursor(
            client,
            agent_id=agent_id or "central-sync",
            device_id=device_id or "",
            cursor_name="active_snapshots",
            cursor_value=latest_updated_at or completed_at,
            last_synced_at=completed_at,
        )
    except Exception as exc:
        payload["event_error"] = str(exc)

    return payload


def build_active_memory_snapshot(
    row: dict[str, Any],
    *,
    project_key: str,
    include_content: bool = False,
) -> dict[str, Any]:
    """Map one local knowledge row to the central active snapshot schema."""
    local_id = int(row.get("id") or 0)
    title = str(row.get("title") or "")
    content = str(row.get("content_raw") or row.get("content") or "")
    summary = str(row.get("summary") or "")
    content_hash = str(row.get("content_hash") or "").strip() or _hash_text("\n".join([title, content, summary]))
    include_raw = bool(include_content and _content_allowed_for_remote("\n".join([title, content, summary])))
    return {
        "memory_key": f"{project_key}:knowledge:{local_id}",
        "local_knowledge_id": local_id,
        "title": title,
        "content": content if include_raw else "",
        "summary": summary,
        "category": str(row.get("category") or "general"),
        "tags": _parse_tags(row.get("tags")),
        "scope": str(row.get("scope") or "project"),
        "sensitivity": str(row.get("sensitivity") or "low"),
        "owner_agent": str(row.get("owner_agent") or ""),
        "status": str(row.get("status") or "active"),
        "content_hash": content_hash,
        "reviewed_at": row.get("updated_at") or row.get("created_at") or None,
        "updated_at": _utc_now(),
    }


def _load_active_rows(db_path: Path, *, limit: int) -> list[dict[str, Any]]:
    with VaultDB(db_path) as db:
        rows = db.conn.execute(
            """SELECT id, title, category, tags, content_raw, summary, content_hash,
                      scope, sensitivity, owner_agent, status, created_at, updated_at
                 FROM knowledge
                WHERE COALESCE(status, 'active') != 'archived'
                ORDER BY id ASC
                LIMIT ?""",
            (max(1, min(int(limit or 1000), 10000)),),
        ).fetchall()
        return [dict(row) for row in rows]


def _upsert_snapshot(client: Any, snapshot: dict[str, Any], *, actor_agent_id: str = "") -> dict[str, Any]:
    existing = _select_one(client, ACTIVE_SNAPSHOT_TABLE, "memory_key", snapshot["memory_key"], columns="id,revision,content_hash")
    if existing:
        previous_hash = str(existing.get("content_hash") or "")
        previous_revision = int(existing.get("revision") or 1)
        revision = previous_revision + 1 if previous_hash != snapshot["content_hash"] else previous_revision
        payload = {**snapshot, "revision": revision}
        _update_by_id(client, ACTIVE_SNAPSHOT_TABLE, str(existing["id"]), payload)
        action = "updated" if previous_hash != snapshot["content_hash"] else "unchanged"
    else:
        revision = 1
        payload = {**snapshot, "revision": revision}
        _insert(client, ACTIVE_SNAPSHOT_TABLE, payload)
        action = "inserted"

    _upsert_revision(
        client,
        {
            "memory_key": snapshot["memory_key"],
            "revision": revision,
            "parent_revision": revision - 1 if revision > 1 else None,
            "actor_agent_id": actor_agent_id or "",
            "operation": f"snapshot_{action}",
            "content_hash": snapshot["content_hash"],
            "payload": {
                "local_knowledge_id": snapshot["local_knowledge_id"],
                "title": snapshot["title"],
                "status": snapshot["status"],
            },
            "created_at": _utc_now(),
        },
    )
    return {"action": action, "revision": revision}


def _upsert_revision(client: Any, payload: dict[str, Any]) -> None:
    existing = (
        client.table(REVISION_TABLE)
        .select("id")
        .eq("memory_key", payload["memory_key"])
        .eq("revision", payload["revision"])
        .limit(1)
        .execute()
    )
    rows = _response_rows(existing)
    if rows:
        _update_by_id(client, REVISION_TABLE, str(rows[0]["id"]), payload)
    else:
        _insert(client, REVISION_TABLE, payload)


def _append_event(client: Any, payload: dict[str, Any]) -> None:
    _insert(client, EVENT_TABLE, payload)


def _upsert_sync_cursor(
    client: Any,
    *,
    agent_id: str,
    device_id: str,
    cursor_name: str,
    cursor_value: str,
    last_synced_at: str,
) -> None:
    payload = {
        "agent_id": agent_id,
        "device_id": device_id,
        "cursor_name": cursor_name,
        "cursor_value": cursor_value,
        "last_synced_at": last_synced_at,
        "updated_at": _utc_now(),
        "payload": {},
    }
    existing = (
        client.table(SYNC_CURSOR_TABLE)
        .select("id")
        .eq("agent_id", agent_id)
        .eq("device_id", device_id)
        .eq("cursor_name", cursor_name)
        .limit(1)
        .execute()
    )
    rows = _response_rows(existing)
    if rows:
        _update_by_id(client, SYNC_CURSOR_TABLE, str(rows[0]["id"]), payload)
    else:
        _insert(client, SYNC_CURSOR_TABLE, payload)


def _select_one(client: Any, table: str, field: str, value: Any, *, columns: str = "*") -> dict[str, Any] | None:
    response = client.table(table).select(columns).eq(field, value).limit(1).execute()
    rows = _response_rows(response)
    return rows[0] if rows else None


def _insert(client: Any, table: str, payload: dict[str, Any]) -> None:
    client.table(table).insert(payload).execute()


def _update_by_id(client: Any, table: str, row_id: str, payload: dict[str, Any]) -> None:
    client.table(table).update(payload).eq("id", row_id).execute()


def _response_rows(response: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in (getattr(response, "data", None) or [])]


def _get_service_client() -> Any | None:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        return None
    from supabase import create_client

    return create_client(url, key)


def _project_key(project: Path) -> str:
    explicit = os.getenv("VAULT_CENTRAL_PROJECT_ID", "").strip()
    if explicit:
        return _slug(explicit)
    resolved = str(project.expanduser().resolve())
    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:12]
    return f"{_slug(project.name or 'vault')}:{digest}"


def _parse_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
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


def _content_allowed_for_remote(text: str) -> bool:
    return scan_privacy(text or "").get("status") != "fail"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip().lower()).strip("-")
    return slug or "vault"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
