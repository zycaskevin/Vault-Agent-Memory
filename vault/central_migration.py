"""Backend-to-backend Central Memory Station migration helpers.

Migration here means copying Central Memory Station candidate inbox rows between
backend adapters, or packaging reviewed active-memory snapshots for a new host.
It does not directly write active memory, promote candidates, or turn any
backend into a multi-master source of truth.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from .central_candidate_store import (
    CENTRAL_CANDIDATE_TABLE,
    list_central_candidate_rows_local,
    upsert_central_candidate_row_local,
)
from .central_store import build_active_memory_snapshot, _project_key
from .db import VaultDB
from .memory import create_candidate
from .remote_candidates import _get_supabase_client


MIGRATION_DIRECTIONS = {"supabase-to-self-host", "self-host-to-supabase"}
SNAPSHOT_BUNDLE_TYPE = "vault_reviewed_snapshot_bundle"
SNAPSHOT_BUNDLE_VERSION = 1


def migrate_central_candidate_inbox(
    project_dir: str | Path,
    *,
    direction: str,
    limit: int = 100,
    apply: bool = False,
    sb_client: Any | None = None,
) -> dict[str, Any]:
    """Copy pending central candidate inbox rows between backend adapters."""
    normalized_direction = _normalize_direction(direction)
    project = Path(project_dir).expanduser().resolve()
    effective_limit = max(1, min(int(limit or 100), 500))
    started_at = _now()

    if normalized_direction == "supabase-to-self-host":
        source_rows = _select_supabase_candidate_rows(sb_client, limit=effective_limit)
        write_result = (
            _write_rows_to_self_host(project, source_rows)
            if apply
            else {"inserted_count": 0, "updated_count": 0, "skipped_count": 0, "items": []}
        )
    else:
        source_rows = list_central_candidate_rows_local(project, limit=effective_limit)
        write_result = (
            _write_rows_to_supabase(source_rows, sb_client=sb_client)
            if apply
            else {"inserted_count": 0, "updated_count": 0, "skipped_count": 0, "items": []}
        )

    completed_at = _now()
    return {
        "ok": True,
        "action": "migrate-candidates",
        "central_memory_station": True,
        "direction": normalized_direction,
        "source_backend": normalized_direction.split("-to-")[0],
        "target_backend": normalized_direction.split("-to-")[1],
        "project_dir": str(project),
        "table": CENTRAL_CANDIDATE_TABLE,
        "apply": bool(apply),
        "dry_run": not bool(apply),
        "count": len(source_rows),
        "inserted_count": int(write_result.get("inserted_count") or 0),
        "updated_count": int(write_result.get("updated_count") or 0),
        "skipped_count": int(write_result.get("skipped_count") or 0),
        "started_at": started_at,
        "completed_at": completed_at,
        "safety": {
            "candidate_inbox_only": True,
            "writes_active_memory": False,
            "writes_local_review_queue": False,
            "promotes_candidates": False,
            "multi_master_active_memory": False,
            "requires_apply_for_writes": True,
            "includes_raw_candidate_content": False,
        },
        "candidates": [_preview_row(row) for row in source_rows],
        "write_items": write_result.get("items", []),
        "next_action": _next_action(apply=apply, count=len(source_rows)),
    }


def export_reviewed_snapshot_bundle(
    project_dir: str | Path,
    *,
    bundle_path: str | Path,
    db_path: str | Path | None = None,
    include_content: bool = False,
    limit: int = 1000,
) -> dict[str, Any]:
    """Export reviewed local active-memory snapshots to a portable bundle file."""
    project = Path(project_dir).expanduser().resolve()
    db_file = Path(db_path).expanduser().resolve() if db_path else project / "vault.db"
    output = Path(bundle_path).expanduser()
    if not output.is_absolute():
        output = project / output
    output = output.resolve()
    effective_limit = max(1, min(int(limit or 1000), 10000))
    started_at = _now()
    project_key = _project_key(project)
    rows = _load_local_active_rows(db_file, limit=effective_limit)
    snapshots = [
        build_active_memory_snapshot(
            row,
            project_key=project_key,
            include_content=bool(include_content),
        )
        for row in rows
    ]
    bundle_id = _bundle_id(project_key, snapshots)
    manifest = _snapshot_bundle_manifest(
        db_file,
        project_key=project_key,
        snapshots=snapshots,
        include_content=bool(include_content),
    )
    bundle = {
        "bundle_type": SNAPSHOT_BUNDLE_TYPE,
        "bundle_version": SNAPSHOT_BUNDLE_VERSION,
        "bundle_id": bundle_id,
        "exported_at": _now(),
        "project_key": project_key,
        "source_of_truth": "local_sqlite",
        "include_content": bool(include_content),
        "count": len(snapshots),
        "manifest": manifest,
        "safety": _snapshot_safety(include_content=bool(include_content), import_apply=False),
        "snapshots": snapshots,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    completed_at = _now()
    return {
        "ok": True,
        "action": "export-snapshots",
        "central_memory_station": True,
        "project_dir": str(project),
        "db_path": str(db_file),
        "bundle_path": str(output),
        "bundle_type": SNAPSHOT_BUNDLE_TYPE,
        "bundle_version": SNAPSHOT_BUNDLE_VERSION,
        "bundle_id": bundle_id,
        "include_content": bool(include_content),
        "count": len(snapshots),
        "manifest": manifest,
        "started_at": started_at,
        "completed_at": completed_at,
        "safety": _snapshot_safety(include_content=bool(include_content), import_apply=False),
        "snapshots": [_preview_snapshot(snapshot) for snapshot in snapshots],
        "next_action": (
            "Move the bundle to the target trusted host and run memory-sync import-snapshots. "
            "Use --include-content only for trusted, encrypted transfer paths."
        ),
    }


def import_reviewed_snapshot_bundle(
    project_dir: str | Path,
    *,
    bundle_path: str | Path,
    apply: bool = False,
    reviewer_agent: str = "",
    limit: int = 1000,
) -> dict[str, Any]:
    """Preview or import reviewed snapshots as local memory candidates."""
    project = Path(project_dir).expanduser().resolve()
    bundle_file = Path(bundle_path).expanduser()
    if not bundle_file.is_absolute():
        bundle_file = project / bundle_file
    bundle_file = bundle_file.resolve()
    started_at = _now()
    bundle = _read_snapshot_bundle(bundle_file)
    effective_limit = max(1, min(int(limit or 1000), 10000))
    snapshots = [dict(item) for item in bundle.get("snapshots", [])[:effective_limit] if isinstance(item, dict)]
    write_items: list[dict[str, Any]] = []
    created_count = 0
    skipped_count = 0
    rejected_count = 0
    if apply:
        with VaultDB(project / "vault.db") as db:
            for snapshot in snapshots:
                result = _write_snapshot_as_candidate(
                    db,
                    snapshot,
                    bundle_id=str(bundle.get("bundle_id") or ""),
                    reviewer_agent=reviewer_agent,
                )
                status = str(result.get("status") or "")
                if status == "candidate_created":
                    created_count += 1
                elif status == "rejected":
                    rejected_count += 1
                else:
                    skipped_count += 1
                write_items.append(result)
    else:
        skipped_count = 0
    completed_at = _now()
    return {
        "ok": True,
        "action": "import-snapshots",
        "central_memory_station": True,
        "project_dir": str(project),
        "bundle_path": str(bundle_file),
        "bundle_type": str(bundle.get("bundle_type") or ""),
        "bundle_version": int(bundle.get("bundle_version") or 0),
        "bundle_id": str(bundle.get("bundle_id") or ""),
        "source_project_key": str(bundle.get("project_key") or ""),
        "apply": bool(apply),
        "dry_run": not bool(apply),
        "count": len(snapshots),
        "created_count": created_count,
        "rejected_count": rejected_count,
        "skipped_count": skipped_count,
        "started_at": started_at,
        "completed_at": completed_at,
        "safety": _snapshot_safety(
            include_content=bool(bundle.get("include_content")),
            import_apply=bool(apply),
        ),
        "snapshots": [_preview_snapshot(snapshot) for snapshot in snapshots],
        "write_items": write_items,
        "next_action": _snapshot_import_next_action(
            apply=bool(apply),
            created_count=created_count,
            snapshots=snapshots,
        ),
    }


def verify_reviewed_snapshot_bundle(
    project_dir: str | Path,
    *,
    bundle_path: str | Path,
    require_content: bool = False,
) -> dict[str, Any]:
    """Verify a reviewed snapshot bundle without writing memory."""
    project = Path(project_dir).expanduser().resolve()
    bundle_file = Path(bundle_path).expanduser()
    if not bundle_file.is_absolute():
        bundle_file = project / bundle_file
    bundle_file = bundle_file.resolve()
    started_at = _now()
    errors: list[str] = []
    warnings: list[str] = []
    try:
        bundle = _read_snapshot_bundle(bundle_file)
    except RuntimeError as exc:
        return {
            "ok": False,
            "action": "verify-snapshots",
            "central_memory_station": True,
            "bundle_path": str(bundle_file),
            "errors": [str(exc)],
            "warnings": [],
            "safety": _snapshot_safety(include_content=False, import_apply=False),
            "started_at": started_at,
            "completed_at": _now(),
        }
    snapshots = [dict(item) for item in bundle.get("snapshots", []) if isinstance(item, dict)]
    manifest = bundle.get("manifest") if isinstance(bundle.get("manifest"), dict) else {}
    count = len(snapshots)
    declared_count = int(bundle.get("count") or 0)
    if declared_count != count:
        errors.append("bundle count does not match snapshots length")
    manifest_count = int(manifest.get("snapshot_count") or -1)
    if manifest_count != count:
        errors.append("manifest snapshot_count does not match snapshots length")
    expected_digest = str(manifest.get("snapshots_digest") or "")
    actual_digest = _snapshots_digest(snapshots)
    if expected_digest and expected_digest != actual_digest:
        errors.append("snapshot digest mismatch")
    elif not expected_digest:
        warnings.append("manifest snapshots_digest missing")
    missing_content = 0
    content_hash_mismatches = 0
    for snapshot in snapshots:
        content = str(snapshot.get("content") or "")
        if not content.strip():
            missing_content += 1
            continue
        actual_hash = _short_content_hash(content)
        declared_hash = str(snapshot.get("content_hash") or "")
        if declared_hash and declared_hash != actual_hash:
            content_hash_mismatches += 1
    if content_hash_mismatches:
        errors.append("one or more snapshot content hashes do not match raw content")
    if require_content and missing_content:
        errors.append("raw content is required but one or more snapshots omit content")
    elif missing_content:
        warnings.append("one or more snapshots omit raw content; import can preview but cannot create those candidates")
    completed_at = _now()
    return {
        "ok": not errors,
        "action": "verify-snapshots",
        "central_memory_station": True,
        "project_dir": str(project),
        "bundle_path": str(bundle_file),
        "bundle_type": str(bundle.get("bundle_type") or ""),
        "bundle_version": int(bundle.get("bundle_version") or 0),
        "bundle_id": str(bundle.get("bundle_id") or ""),
        "count": count,
        "declared_count": declared_count,
        "missing_content_count": missing_content,
        "content_hash_mismatch_count": content_hash_mismatches,
        "manifest": _preview_manifest(manifest),
        "errors": errors,
        "warnings": warnings,
        "started_at": started_at,
        "completed_at": completed_at,
        "safety": _snapshot_safety(
            include_content=bool(bundle.get("include_content")),
            import_apply=False,
        ),
        "next_action": _snapshot_verify_next_action(errors=errors, warnings=warnings, require_content=require_content),
    }


def _normalize_direction(direction: str) -> str:
    value = str(direction or "").strip().lower().replace("_", "-")
    if value not in MIGRATION_DIRECTIONS:
        raise ValueError(
            "direction must be one of: " + ", ".join(sorted(MIGRATION_DIRECTIONS))
        )
    return value


def _select_supabase_candidate_rows(sb_client: Any | None, *, limit: int) -> list[dict[str, Any]]:
    client = sb_client or _get_supabase_client(service_role=True)
    if client is None:
        raise RuntimeError(
            "Supabase client is missing; set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY on a trusted sync host."
        )
    rows: list[dict[str, Any]] = []
    for status in ("candidate", "submitted"):
        query = client.table(CENTRAL_CANDIDATE_TABLE).select("*").eq("status", status)
        if hasattr(query, "order"):
            query = query.order("created_at", desc=False)
        query = query.limit(max(1, min(int(limit or 100), 500)))
        rows.extend(_response_rows(query.execute()))
    return _dedupe_rows(rows)[: max(1, min(int(limit or 100), 500))]


def _write_rows_to_self_host(project: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    inserted = 0
    updated = 0
    skipped = 0
    items: list[dict[str, Any]] = []
    for row in rows:
        if not str(row.get("title") or "").strip() or not str(row.get("content") or "").strip():
            skipped += 1
            items.append({"candidate_key": _candidate_key(row), "status": "skipped_missing_content"})
            continue
        result = upsert_central_candidate_row_local(project, row)
        if result.get("status") == "inserted":
            inserted += 1
        elif result.get("status") == "updated":
            updated += 1
        else:
            skipped += 1
        items.append(
            {
                "candidate_key": result.get("candidate_key", _candidate_key(row)),
                "status": result.get("status", ""),
                "target": "self-host",
            }
        )
    return {
        "inserted_count": inserted,
        "updated_count": updated,
        "skipped_count": skipped,
        "items": items,
    }


def _write_rows_to_supabase(rows: list[dict[str, Any]], *, sb_client: Any | None) -> dict[str, Any]:
    client = sb_client or _get_supabase_client(service_role=True)
    if client is None:
        raise RuntimeError(
            "Supabase client is missing; set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY on a trusted sync host."
        )
    inserted = 0
    updated = 0
    skipped = 0
    items: list[dict[str, Any]] = []
    for row in rows:
        if not str(row.get("title") or "").strip() or not str(row.get("content") or "").strip():
            skipped += 1
            items.append({"candidate_key": _candidate_key(row), "status": "skipped_missing_content"})
            continue
        payload = _supabase_row_payload(row)
        existing = _select_supabase_candidate_by_key(client, payload["candidate_key"])
        if existing:
            client.table(CENTRAL_CANDIDATE_TABLE).update(payload).eq(
                "candidate_key",
                payload["candidate_key"],
            ).execute()
            updated += 1
            status = "updated"
        else:
            client.table(CENTRAL_CANDIDATE_TABLE).insert(payload).execute()
            inserted += 1
            status = "inserted"
        items.append(
            {
                "candidate_key": payload["candidate_key"],
                "status": status,
                "target": "supabase",
            }
        )
    return {
        "inserted_count": inserted,
        "updated_count": updated,
        "skipped_count": skipped,
        "items": items,
    }


def _select_supabase_candidate_by_key(client: Any, candidate_key: str) -> dict[str, Any] | None:
    rows = _response_rows(
        client.table(CENTRAL_CANDIDATE_TABLE)
        .select("*")
        .eq("candidate_key", candidate_key)
        .limit(1)
        .execute()
    )
    return rows[0] if rows else None


def _supabase_row_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_key": _candidate_key(row),
        "title": str(row.get("title") or ""),
        "content": str(row.get("content") or ""),
        "reason": str(row.get("reason") or ""),
        "category": str(row.get("category") or "general"),
        "tags": _json_list(row.get("tags")),
        "trust": float(row.get("trust") or 0.0),
        "scope": str(row.get("scope") or "project"),
        "sensitivity": str(row.get("sensitivity") or "low"),
        "owner_agent": str(row.get("owner_agent") or ""),
        "allowed_agents": _json_list(row.get("allowed_agents")),
        "from_agent": str(row.get("from_agent") or ""),
        "source_ref": str(row.get("source_ref") or ""),
        "memory_type": str(row.get("memory_type") or "remote_candidate"),
        "status": _candidate_status(row),
        "idempotency_key": str(row.get("idempotency_key") or _candidate_key(row)),
        "hmac_key_id": str(row.get("hmac_key_id") or ""),
        "hmac_algorithm": str(row.get("hmac_algorithm") or ""),
        "payload_hash": str(row.get("payload_hash") or ""),
        "hmac_signature": str(row.get("hmac_signature") or ""),
    }


def _preview_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_key": _candidate_key(row),
        "status": _candidate_status(row),
        "created_at": str(row.get("created_at") or ""),
        "from_agent": str(row.get("from_agent") or ""),
        "title": str(row.get("title") or ""),
        "category": str(row.get("category") or "general"),
        "trust": float(row.get("trust") or 0.0),
        "scope": str(row.get("scope") or "project"),
        "sensitivity": str(row.get("sensitivity") or "low"),
        "memory_type": str(row.get("memory_type") or "remote_candidate"),
        "source_ref": str(row.get("source_ref") or ""),
        "has_content": bool(str(row.get("content") or "").strip()),
    }


def _candidate_key(row: dict[str, Any]) -> str:
    return str(row.get("candidate_key") or row.get("idempotency_key") or row.get("id") or "").strip()


def _candidate_status(row: dict[str, Any]) -> str:
    status = str(row.get("status") or "candidate").strip().lower()
    return status if status in {"candidate", "submitted"} else "candidate"


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for row in rows:
        key = _candidate_key(row)
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        unique.append(dict(row))
    return unique


def _load_local_active_rows(db_path: Path, *, limit: int) -> list[dict[str, Any]]:
    with VaultDB(db_path) as db:
        rows = db.conn.execute(
            """SELECT id, title, category, tags, content_raw, summary, content_hash,
                      scope, sensitivity, owner_agent, allowed_agents, status, created_at, updated_at
                 FROM knowledge
                WHERE COALESCE(status, 'active') != 'archived'
                ORDER BY id ASC
                LIMIT ?""",
            (max(1, min(int(limit or 1000), 10000)),),
        ).fetchall()
        return [dict(row) for row in rows]


def _bundle_id(project_key: str, snapshots: list[dict[str, Any]]) -> str:
    seed = json.dumps(
        {
            "project_key": project_key,
            "memory_keys": [str(item.get("memory_key") or "") for item in snapshots],
            "content_hashes": [str(item.get("content_hash") or "") for item in snapshots],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"snapshot-bundle-{digest}"


def _snapshot_bundle_manifest(
    db_path: Path,
    *,
    project_key: str,
    snapshots: list[dict[str, Any]],
    include_content: bool,
) -> dict[str, Any]:
    history = _history_manifest(db_path)
    return {
        "project_key": project_key,
        "snapshot_count": len(snapshots),
        "snapshots_digest": _snapshots_digest(snapshots),
        "content_policy": "raw_content_included" if include_content else "metadata_summary_hash_only",
        "includes_raw_memory_content": bool(include_content),
        "content_hashes": [str(item.get("content_hash") or "") for item in snapshots],
        "history": history,
        "dr_contract": {
            "verify_command": "vault memory-sync verify-snapshots --bundle <path>",
            "restore_path": "import_as_candidates_only",
            "writes_active_memory": False,
            "promotes_candidates": False,
        },
    }


def _history_manifest(db_path: Path) -> dict[str, Any]:
    with VaultDB(db_path) as db:
        revision_count = _table_count(db, "memory_revisions")
        audit_event_count = _table_count(db, "memory_audit_log")
        feedback_event_count = _table_count(db, "memory_feedback_events")
        history_rows = []
        if revision_count:
            history_rows.extend(
                dict(row)
                for row in db.conn.execute(
                    """SELECT id, created_at, revision_hash, content_hash, operation, status
                       FROM memory_revisions
                       ORDER BY created_at DESC
                       LIMIT 100"""
                ).fetchall()
            )
        if audit_event_count:
            history_rows.extend(
                dict(row)
                for row in db.conn.execute(
                    """SELECT id, created_at, action, target_type, target_id, revision_id
                       FROM memory_audit_log
                       ORDER BY id DESC
                       LIMIT 100"""
                ).fetchall()
            )
    return {
        "memory_revisions": revision_count,
        "memory_audit_log": audit_event_count,
        "memory_feedback_events": feedback_event_count,
        "history_digest": _stable_digest(history_rows),
        "history_digest_scope": "latest_100_revisions_and_audit_events_metadata_only",
        "contains_raw_audit_payloads": False,
    }


def _table_count(db: VaultDB, table: str) -> int:
    try:
        return int(db.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except Exception:
        return 0


def _snapshots_digest(snapshots: list[dict[str, Any]]) -> str:
    canonical = [
        {
            "memory_key": str(item.get("memory_key") or ""),
            "local_knowledge_id": item.get("local_knowledge_id"),
            "title": str(item.get("title") or ""),
            "summary": str(item.get("summary") or ""),
            "category": str(item.get("category") or "general"),
            "tags": _json_list(item.get("tags")),
            "scope": str(item.get("scope") or "project"),
            "sensitivity": str(item.get("sensitivity") or "low"),
            "owner_agent": str(item.get("owner_agent") or ""),
            "allowed_agents": _json_list(item.get("allowed_agents")),
            "status": str(item.get("status") or "active"),
            "content_hash": str(item.get("content_hash") or ""),
            "has_content": bool(str(item.get("content") or "").strip()),
        }
        for item in snapshots
    ]
    return _stable_digest(canonical)


def _stable_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _short_content_hash(content: str) -> str:
    return hashlib.sha256(str(content or "").encode("utf-8")).hexdigest()[:16]


def _read_snapshot_bundle(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"snapshot bundle not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid snapshot bundle JSON: {path}") from exc
    if not isinstance(data, dict):
        raise RuntimeError("snapshot bundle must be a JSON object")
    if data.get("bundle_type") != SNAPSHOT_BUNDLE_TYPE:
        raise RuntimeError(f"unsupported snapshot bundle type: {data.get('bundle_type')!r}")
    if int(data.get("bundle_version") or 0) != SNAPSHOT_BUNDLE_VERSION:
        raise RuntimeError(f"unsupported snapshot bundle version: {data.get('bundle_version')!r}")
    snapshots = data.get("snapshots")
    if not isinstance(snapshots, list):
        raise RuntimeError("snapshot bundle must contain a snapshots list")
    return data


def _write_snapshot_as_candidate(
    db: VaultDB,
    snapshot: dict[str, Any],
    *,
    bundle_id: str,
    reviewer_agent: str = "",
) -> dict[str, Any]:
    memory_key = str(snapshot.get("memory_key") or "").strip()
    source_ref = f"snapshot_bundle:{bundle_id}:{memory_key}" if bundle_id else f"snapshot_bundle:{memory_key}"
    title = str(snapshot.get("title") or "").strip()
    content = str(snapshot.get("content") or "").strip()
    if not memory_key:
        return {"memory_key": "", "status": "skipped_missing_memory_key"}
    if not title or not content:
        return {
            "memory_key": memory_key,
            "status": "skipped_missing_content",
            "has_content": bool(content),
        }
    existing = db.conn.execute(
        "SELECT id, status FROM memory_candidates WHERE source_ref=? LIMIT 1",
        (source_ref,),
    ).fetchone()
    if existing:
        return {
            "memory_key": memory_key,
            "candidate_id": existing["id"],
            "status": "skipped_existing_source_ref",
            "candidate_status": existing["status"],
        }
    result = create_candidate(
        db,
        title=title,
        content=content,
        layer="L3",
        category=str(snapshot.get("category") or "general"),
        tags=_json_list(snapshot.get("tags")),
        trust=0.8,
        source="snapshot_bundle_import",
        source_ref=source_ref,
        reason="Imported reviewed snapshot bundle as a candidate for local review.",
        scope=str(snapshot.get("scope") or "project"),
        sensitivity=str(snapshot.get("sensitivity") or "low"),
        owner_agent=str(snapshot.get("owner_agent") or reviewer_agent or ""),
        allowed_agents=_json_list(snapshot.get("allowed_agents")),
        memory_type="snapshot_import_candidate",
    )
    return {
        "memory_key": memory_key,
        "candidate_id": result.get("candidate_id"),
        "status": result.get("status"),
        "gates": result.get("gates", {}),
    }


def _preview_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "memory_key": str(snapshot.get("memory_key") or ""),
        "local_knowledge_id": snapshot.get("local_knowledge_id"),
        "title": str(snapshot.get("title") or ""),
        "category": str(snapshot.get("category") or "general"),
        "scope": str(snapshot.get("scope") or "project"),
        "sensitivity": str(snapshot.get("sensitivity") or "low"),
        "status": str(snapshot.get("status") or "active"),
        "content_hash": str(snapshot.get("content_hash") or ""),
        "has_content": bool(str(snapshot.get("content") or "").strip()),
        "reviewed_at": snapshot.get("reviewed_at"),
    }


def _preview_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    history = manifest.get("history") if isinstance(manifest.get("history"), dict) else {}
    return {
        "snapshot_count": int(manifest.get("snapshot_count") or 0),
        "snapshots_digest": str(manifest.get("snapshots_digest") or ""),
        "content_policy": str(manifest.get("content_policy") or ""),
        "includes_raw_memory_content": bool(manifest.get("includes_raw_memory_content")),
        "history": {
            "memory_revisions": int(history.get("memory_revisions") or 0),
            "memory_audit_log": int(history.get("memory_audit_log") or 0),
            "memory_feedback_events": int(history.get("memory_feedback_events") or 0),
            "history_digest": str(history.get("history_digest") or ""),
            "contains_raw_audit_payloads": bool(history.get("contains_raw_audit_payloads")),
        },
    }


def _snapshot_safety(*, include_content: bool, import_apply: bool) -> dict[str, Any]:
    return {
        "reviewed_snapshot_bundle": True,
        "source_of_truth": "local_sqlite",
        "candidate_first_import": True,
        "writes_active_memory": False,
        "writes_local_review_queue": bool(import_apply),
        "promotes_candidates": False,
        "multi_master_active_memory": False,
        "requires_apply_for_memory_writes": True,
        "includes_raw_memory_content_in_bundle": bool(include_content),
        "includes_raw_memory_content_in_cli_output": False,
    }


def _snapshot_import_next_action(
    *,
    apply: bool,
    created_count: int,
    snapshots: list[dict[str, Any]],
) -> str:
    missing_content = sum(1 for item in snapshots if not str(item.get("content") or "").strip())
    if not apply:
        if missing_content:
            return "This bundle is preview-only unless re-exported with --include-content on a trusted transfer path."
        return "Review the preview, then rerun with --apply to write local memory_candidates."
    if created_count:
        return "Review imported candidates with memory-review inbox; promote only after normal review."
    if missing_content:
        return "No candidates were created because the bundle lacks raw content; re-export with --include-content if appropriate."
    return "No new candidates were created; check write_items for existing source refs or gate rejections."


def _snapshot_verify_next_action(
    *,
    errors: list[str],
    warnings: list[str],
    require_content: bool,
) -> str:
    if errors:
        return "Do not import this bundle. Re-export from the source host and verify again."
    if require_content:
        return "Bundle is verified for candidate import. Run import-snapshots --apply on the trusted target host."
    if warnings:
        return "Bundle metadata is valid, but raw content may be missing. Use --require-content before disaster-recovery import."
    return "Bundle is verified. Import still writes review candidates only, not active memory."


def _response_rows(response: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in (getattr(response, "data", None) or [])]


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


def _next_action(*, apply: bool, count: int) -> str:
    if not count:
        return "No pending central candidate rows were found for this migration direction."
    if not apply:
        return "Dry run complete. Rerun with --apply on a trusted host to copy candidate inbox rows."
    return "Migration copied candidate inbox rows only. Pull/review/promote candidates through the normal review flow."


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
