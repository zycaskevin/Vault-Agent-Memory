"""Trusted sync-host writer for the Supabase central vector index."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .central_store import (
    ACTIVE_SNAPSHOT_TABLE,
    _get_service_client,
    _load_active_rows,
    _parse_tags,
    _project_key,
    _utc_now,
    build_active_memory_snapshot,
)
from .privacy import scan_privacy
from .semantic import SemanticEmbeddingProvider, embedding_text_hash


CENTRAL_VECTOR_TABLE = "vault_memory_embeddings"
CENTRAL_VECTOR_DIMENSION = 1536
CENTRAL_VECTOR_KIND = "safe_summary"
CENTRAL_VECTOR_POLICY = "shared_reviewed_safe_summary_v1"
CENTRAL_VECTOR_SOURCE_TABLE = ACTIVE_SNAPSHOT_TABLE


def sync_memory_embeddings(
    project_dir: str | Path,
    *,
    db_path: str | Path | None = None,
    sb_client: Any | None = None,
    provider: SemanticEmbeddingProvider | None = None,
    provider_name: str = "openai",
    model_key: str = "text-embedding-3-small",
    agent_id: str = "",
    limit: int = 1000,
) -> dict[str, Any]:
    """Push reviewed safe-summary embeddings into the central vector table.

    This writer is intentionally narrower than active snapshot sync: it indexes
    safe summary text only, skips candidates/private/high/restricted memory, and
    requires a 1536-dimensional provider matching the Supabase pgvector schema.
    """
    project = Path(project_dir).expanduser().resolve()
    db_file = Path(db_path).expanduser().resolve() if db_path else project / "vault.db"
    trusted_marker = os.getenv("VAULT_SUPABASE_TRUSTED_SYNC_HOST", "").strip().lower()
    if sb_client is None and trusted_marker not in {"1", "true", "yes", "on"}:
        return {
            "ok": False,
            "error": "trusted_sync_host_marker_missing",
            "message": "Set VAULT_SUPABASE_TRUSTED_SYNC_HOST=1 before writing central vector embeddings.",
        }
    client = sb_client or _get_service_client()
    if client is None:
        return {
            "ok": False,
            "error": "central_vector_client_missing",
            "message": "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY on a trusted sync host.",
        }

    if provider is None:
        provider_check = _central_vector_provider_preflight(provider_name=provider_name, model_key=model_key)
        if provider_check is not None:
            return provider_check
        provider = _create_central_vector_provider(provider_name=provider_name, model_key=model_key)
    dimension = int(getattr(provider, "dim", 0) or 0)
    provider_id = str(getattr(provider, "provider_id", provider.__class__.__name__))
    if dimension != CENTRAL_VECTOR_DIMENSION:
        return {
            "ok": False,
            "error": "central_vector_dimension_mismatch",
            "message": f"Central vector index requires {CENTRAL_VECTOR_DIMENSION} dimensions, got {dimension}.",
            "provider_id": provider_id,
            "dimension": dimension,
        }

    project_key = _project_key(project)
    rows = _load_active_rows(db_file, limit=limit)
    payload: dict[str, Any] = {
        "ok": True,
        "project_dir": str(project),
        "db_path": str(db_file),
        "table": CENTRAL_VECTOR_TABLE,
        "source_table": CENTRAL_VECTOR_SOURCE_TABLE,
        "project_key": project_key,
        "provider_id": provider_id,
        "dimension": dimension,
        "vector_kind": CENTRAL_VECTOR_KIND,
        "index_policy": CENTRAL_VECTOR_POLICY,
        "count": len(rows),
        "inserted_count": 0,
        "updated_count": 0,
        "unchanged_count": 0,
        "skipped_count": 0,
        "failed_count": 0,
        "items": [],
        "started_at": _utc_now(),
        "safety": {
            "trusted_sync_host_writes_only": True,
            "source_of_truth": "local_sqlite_reviewed_memory",
            "index_candidates": False,
            "index_private": False,
            "index_high_or_restricted": False,
            "uses_raw_content": False,
            "returns_embedding_values": False,
        },
    }

    for row in rows:
        snapshot = build_active_memory_snapshot(row, project_key=project_key, include_content=False)
        item_base = {
            "memory_key": snapshot["memory_key"],
            "local_knowledge_id": snapshot["local_knowledge_id"],
            "title": snapshot["title"],
        }
        try:
            central_snapshot = _select_one(
                client,
                ACTIVE_SNAPSHOT_TABLE,
                {"memory_key": snapshot["memory_key"]},
                columns="id,revision,content_hash,status",
            )
            if not central_snapshot:
                payload["skipped_count"] += 1
                payload["items"].append({**item_base, "action": "skipped", "reason": "central_snapshot_missing"})
                continue

            indexable, reason = _snapshot_is_indexable(snapshot)
            if not indexable:
                payload["skipped_count"] += 1
                payload["items"].append({**item_base, "action": "skipped", "reason": reason})
                continue

            remote_text = build_remote_search_text(snapshot)
            if not remote_text:
                payload["skipped_count"] += 1
                payload["items"].append({**item_base, "action": "skipped", "reason": "safe_remote_search_text_empty"})
                continue
            if scan_privacy(remote_text).get("status") == "fail":
                payload["skipped_count"] += 1
                payload["items"].append({**item_base, "action": "skipped", "reason": "safe_text_privacy_gate_failed"})
                continue

            vector = provider.encode([remote_text])[0]
            if len(vector) != CENTRAL_VECTOR_DIMENSION:
                raise ValueError(
                    f"central vector dimension mismatch: expected {CENTRAL_VECTOR_DIMENSION}, got {len(vector)}"
                )
            record = build_memory_embedding_record(
                snapshot,
                central_snapshot=central_snapshot,
                project_key=project_key,
                provider_id=provider_id,
                vector=[float(value) for value in vector],
                remote_search_text=remote_text,
            )
            result = _upsert_embedding(client, record)
            payload[f"{result['action']}_count"] += 1
            payload["items"].append(
                {
                    **item_base,
                    "action": result["action"],
                    "revision": record["revision"],
                    "remote_search_text_hash": record["remote_search_text_hash"],
                }
            )
        except Exception as exc:
            payload["failed_count"] += 1
            payload["items"].append({**item_base, "action": "failed", "error": str(exc)})

    payload["completed_at"] = _utc_now()
    payload["ok"] = payload["failed_count"] == 0
    payload["status"] = "ok" if payload["ok"] else "partial"
    payload["actor_agent_id"] = agent_id or ""
    return payload


def build_remote_search_text(snapshot: dict[str, Any], *, max_chars: int = 2000) -> str:
    """Build the central index text from safe metadata, not raw content."""
    tags = _parse_tags(snapshot.get("tags"))
    parts = [
        str(snapshot.get("title") or "").strip(),
        str(snapshot.get("summary") or "").strip(),
        str(snapshot.get("category") or "").strip(),
        " ".join(tags),
    ]
    text = "\n".join(part for part in parts if part)
    return text[: max(1, int(max_chars))]


def build_memory_embedding_record(
    snapshot: dict[str, Any],
    *,
    central_snapshot: dict[str, Any],
    project_key: str,
    provider_id: str,
    vector: list[float],
    remote_search_text: str,
) -> dict[str, Any]:
    now = _utc_now()
    revision = int(central_snapshot.get("revision") or 1)
    text_hash = embedding_text_hash(remote_search_text)
    return {
        "memory_key": snapshot["memory_key"],
        "revision": revision,
        "project_id": project_key,
        "embedding_model": provider_id,
        "embedding_dimension": CENTRAL_VECTOR_DIMENSION,
        "vector_kind": CENTRAL_VECTOR_KIND,
        "embedding": vector,
        "remote_search_text": remote_search_text,
        "remote_search_text_hash": text_hash,
        "content_hash": str(central_snapshot.get("content_hash") or snapshot.get("content_hash") or ""),
        "embedding_hash": _hash_vector(vector),
        "scope": str(snapshot.get("scope") or "project"),
        "sensitivity": str(snapshot.get("sensitivity") or "low"),
        "owner_agent": str(snapshot.get("owner_agent") or ""),
        "allowed_agents": [],
        "source_table": CENTRAL_VECTOR_SOURCE_TABLE,
        "index_policy": CENTRAL_VECTOR_POLICY,
        "is_latest": True,
        "superseded_at": None,
        "updated_at": now,
        "created_at": now,
    }


def _snapshot_is_indexable(snapshot: dict[str, Any]) -> tuple[bool, str]:
    if str(snapshot.get("status") or "active").lower() != "active":
        return False, "non_active_memory"
    if str(snapshot.get("scope") or "project").lower() not in {"public", "shared", "project"}:
        return False, "scope_not_remote_indexable"
    if str(snapshot.get("sensitivity") or "low").lower() not in {"low", "medium"}:
        return False, "sensitivity_not_remote_indexable"
    return True, ""


def _upsert_embedding(client: Any, record: dict[str, Any]) -> dict[str, Any]:
    existing = _select_one(
        client,
        CENTRAL_VECTOR_TABLE,
        {
            "memory_key": record["memory_key"],
            "revision": record["revision"],
            "embedding_model": record["embedding_model"],
            "vector_kind": record["vector_kind"],
        },
        columns="id,embedding_hash,remote_search_text_hash",
    )
    if existing:
        if (
            str(existing.get("embedding_hash") or "") == record["embedding_hash"]
            and str(existing.get("remote_search_text_hash") or "") == record["remote_search_text_hash"]
        ):
            action = "unchanged"
        else:
            _update_by_id(client, CENTRAL_VECTOR_TABLE, str(existing["id"]), record)
            action = "updated"
    else:
        _insert(client, CENTRAL_VECTOR_TABLE, record)
        action = "inserted"

    _supersede_old_latest_rows(client, record)
    return {"action": action}


def _supersede_old_latest_rows(client: Any, record: dict[str, Any]) -> None:
    latest_rows = _select_many(
        client,
        CENTRAL_VECTOR_TABLE,
        {
            "memory_key": record["memory_key"],
            "embedding_model": record["embedding_model"],
            "vector_kind": record["vector_kind"],
            "is_latest": True,
        },
        columns="id,revision",
    )
    now = _utc_now()
    for row in latest_rows:
        if int(row.get("revision") or 0) != int(record["revision"]):
            _update_by_id(
                client,
                CENTRAL_VECTOR_TABLE,
                str(row["id"]),
                {"is_latest": False, "superseded_at": now, "updated_at": now},
            )


def _select_one(client: Any, table: str, filters: dict[str, Any], *, columns: str = "*") -> dict[str, Any] | None:
    rows = _select_many(client, table, filters, columns=columns, limit=1)
    return rows[0] if rows else None


def _select_many(
    client: Any,
    table: str,
    filters: dict[str, Any],
    *,
    columns: str = "*",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    query = client.table(table).select(columns)
    for field, value in filters.items():
        query = query.eq(field, value)
    if limit is not None:
        query = query.limit(limit)
    return _response_rows(query.execute())


def _insert(client: Any, table: str, payload: dict[str, Any]) -> None:
    client.table(table).insert(payload).execute()


def _update_by_id(client: Any, table: str, row_id: str, payload: dict[str, Any]) -> None:
    client.table(table).update(payload).eq("id", row_id).execute()


def _response_rows(response: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in (getattr(response, "data", None) or [])]


def _hash_vector(vector: list[float]) -> str:
    stable = json.dumps([round(float(value), 8) for value in vector], separators=(",", ":"))
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _create_central_vector_provider(*, provider_name: str, model_key: str) -> SemanticEmbeddingProvider:
    from .embed import create_embedding_provider

    return create_embedding_provider(provider=provider_name or "openai", model_key=model_key or "text-embedding-3-small")


def _central_vector_provider_preflight(*, provider_name: str, model_key: str) -> dict[str, Any] | None:
    provider = (provider_name or "openai").strip().lower()
    model = model_key or "text-embedding-3-small"
    if provider == "openai" and not os.getenv("OPENAI_API_KEY", "").strip():
        return {
            "ok": False,
            "error": "embedding_provider_credentials_missing",
            "provider_name": "openai",
            "model_key": model,
            "required_env_var": "OPENAI_API_KEY",
            "message": (
                "Set OPENAI_API_KEY on the trusted sync host before pushing central "
                "vector embeddings."
            ),
        }
    return None
