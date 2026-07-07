"""Read-only status surface for the central derived vector index."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .db import VaultDB


HIGH_RISK_SENSITIVITIES = {"high", "restricted"}


def _scalar(db: VaultDB, sql: str, params: tuple[Any, ...] = ()) -> int:
    row = db.conn.execute(sql, params).fetchone()
    return int(row[0] or 0)


def _provider_breakdown(db: VaultDB) -> list[dict[str, Any]]:
    rows = db.conn.execute(
        """SELECT provider_id, dimension, vector_kind,
                  count(*) AS vector_rows,
                  count(DISTINCT knowledge_id) AS indexed_knowledge_rows,
                  min(NULLIF(updated_at, '')) AS oldest_updated_at,
                  max(NULLIF(updated_at, '')) AS newest_updated_at
             FROM semantic_vectors
            GROUP BY provider_id, dimension, vector_kind
            ORDER BY provider_id, dimension, vector_kind"""
    ).fetchall()
    return [
        {
            "provider_id": row["provider_id"],
            "dimension": int(row["dimension"]),
            "vector_kind": row["vector_kind"],
            "vector_rows": int(row["vector_rows"]),
            "indexed_knowledge_rows": int(row["indexed_knowledge_rows"]),
            "oldest_updated_at": row["oldest_updated_at"],
            "newest_updated_at": row["newest_updated_at"],
        }
        for row in rows
    ]


def central_vector_index_status(db_path: str | Path) -> dict[str, Any]:
    """Return a JSON-safe local status report for the derived vector index.

    The current implementation treats `semantic_vectors` as the local derived
    vector index. It intentionally reports governance and staleness posture
    without creating a remote index or changing search behavior.
    """
    db_path = Path(db_path)
    with VaultDB(db_path) as db:
        total_knowledge = _scalar(db, "SELECT count(*) FROM knowledge")
        active_knowledge = _scalar(
            db,
            "SELECT count(*) FROM knowledge WHERE COALESCE(status, 'active') = 'active'",
        )
        default_indexable = _scalar(
            db,
            """SELECT count(*) FROM knowledge
                WHERE COALESCE(status, 'active') = 'active'
                  AND lower(COALESCE(scope, 'project')) != 'private'
                  AND lower(COALESCE(sensitivity, 'low')) NOT IN ('high', 'restricted')""",
        )
        vector_rows = _scalar(db, "SELECT count(*) FROM semantic_vectors")
        indexed_knowledge_any = _scalar(
            db,
            "SELECT count(DISTINCT knowledge_id) FROM semantic_vectors",
        )
        stale_vectors = _scalar(
            db,
            """SELECT count(*)
                 FROM semantic_vectors AS sv
                 JOIN knowledge AS k ON k.id = sv.knowledge_id
                WHERE COALESCE(sv.content_hash, '') != ''
                  AND COALESCE(k.content_hash, '') != ''
                  AND sv.content_hash != k.content_hash""",
        )
        orphan_vectors = _scalar(
            db,
            """SELECT count(*)
                 FROM semantic_vectors AS sv
            LEFT JOIN knowledge AS k ON k.id = sv.knowledge_id
                WHERE k.id IS NULL""",
        )
        shared_index_risk_rows = _scalar(
            db,
            """SELECT count(*)
                 FROM semantic_vectors AS sv
                 JOIN knowledge AS k ON k.id = sv.knowledge_id
                WHERE COALESCE(k.status, 'active') != 'active'
                   OR lower(COALESCE(k.scope, 'project')) = 'private'
                   OR lower(COALESCE(k.sensitivity, 'low')) IN ('high', 'restricted')""",
        )
        indexed_default_knowledge = _scalar(
            db,
            """SELECT count(DISTINCT sv.knowledge_id)
                 FROM semantic_vectors AS sv
                 JOIN knowledge AS k ON k.id = sv.knowledge_id
                WHERE COALESCE(k.status, 'active') = 'active'
                  AND lower(COALESCE(k.scope, 'project')) != 'private'
                  AND lower(COALESCE(k.sensitivity, 'low')) NOT IN ('high', 'restricted')""",
        )
        cache_rows = _scalar(db, "SELECT count(*) FROM embedding_cache")
        provider_breakdown = _provider_breakdown(db)

    missing_indexable_any = max(default_indexable - indexed_default_knowledge, 0)
    ok_for_local_search = vector_rows > 0 and stale_vectors == 0 and orphan_vectors == 0
    ready_for_shared_remote_read = (
        ok_for_local_search
        and shared_index_risk_rows == 0
        and missing_indexable_any == 0
        and vector_rows > 0
    )

    if vector_rows == 0:
        status = "empty"
    elif stale_vectors or orphan_vectors:
        status = "stale"
    elif missing_indexable_any:
        status = "partial"
    else:
        status = "ready_local"

    next_actions: list[str] = []
    if vector_rows == 0:
        next_actions.append("Run `vault semantic rebuild` after choosing an embedding provider.")
    if stale_vectors or orphan_vectors:
        next_actions.append("Run `vault semantic rebuild --changed-only` or a full rebuild to refresh stale vectors.")
    if missing_indexable_any:
        next_actions.append("Rebuild missing reviewed active memory before using the index for shared retrieval.")
    if shared_index_risk_rows:
        next_actions.append("Keep the index local-only or rebuild with a shared-read policy before exposing remote vector search.")
    if not next_actions:
        next_actions.append("Use Search QA before changing hybrid/vector ranking or exposing remote read paths.")

    return {
        "schema_version": 1,
        "artifact_type": "central_derived_vector_index_status",
        "status": status,
        "db_path": str(db_path),
        "source_of_truth": "local_sqlite_markdown",
        "index_role": "derived_rebuildable_cache",
        "local_only": True,
        "remote_read_enabled": False,
        "remote_write_enabled": False,
        "remote_writes_policy": "candidate_first_only",
        "security_boundary": "vault_access_policy_filter_after_retrieval",
        "counts": {
            "knowledge_rows": total_knowledge,
            "active_knowledge_rows": active_knowledge,
            "default_indexable_active_rows": default_indexable,
            "semantic_vector_rows": vector_rows,
            "indexed_knowledge_rows_any_policy": indexed_knowledge_any,
            "indexed_default_policy_rows": indexed_default_knowledge,
            "missing_default_policy_rows": missing_indexable_any,
            "stale_vector_rows": stale_vectors,
            "orphan_vector_rows": orphan_vectors,
            "shared_remote_risk_vector_rows": shared_index_risk_rows,
            "embedding_cache_rows": cache_rows,
        },
        "provider_breakdown": provider_breakdown,
        "readiness": {
            "local_vector_search": ok_for_local_search,
            "shared_remote_vector_read": ready_for_shared_remote_read,
            "reason": (
                "remote vector read is intentionally disabled until Gateway/Remote Server access-policy tests exist"
                if not ready_for_shared_remote_read
                else "local index is complete under the default shared-read policy, but remote serving is still disabled"
            ),
        },
        "policy": {
            "index_candidates": False,
            "index_rejected_candidates": False,
            "index_private_shared": False,
            "index_high_or_restricted_shared": False,
            "index_archived_normal_search": False,
            "fail_closed_on_missing_metadata": True,
        },
        "next_actions": next_actions,
    }


def add_vector_index_parser(sub) -> None:
    parser = sub.add_parser("vector-index", help="中央衍生向量索引狀態與安全檢查")
    vector_sub = parser.add_subparsers(dest="vector_index_action")

    sp = vector_sub.add_parser("status", help="檢查 local derived vector index 狀態")
    sp.add_argument("--db-path", help="SQLite DB 路徑（預設 project_dir/vault.db）")
    sp.add_argument("--json", action="store_true", help="輸出 JSON")
    sp.add_argument("--pretty", action="store_true", help="縮排 JSON 輸出")

    sp = vector_sub.add_parser("doctor", help="檢查 index 是否可安全作為 shared read 基礎")
    sp.add_argument("--db-path", help="SQLite DB 路徑（預設 project_dir/vault.db）")
    sp.add_argument("--json", action="store_true", help="輸出 JSON")
    sp.add_argument("--pretty", action="store_true", help="縮排 JSON 輸出")


def cmd_vector_index(args, *, find_project_dir, json_print) -> None:
    action = args.vector_index_action
    if action not in {"status", "doctor"}:
        print("error: vector-index requires action: status or doctor", file=sys.stderr)
        raise SystemExit(2)

    db_path = Path(args.db_path) if args.db_path else find_project_dir() / "vault.db"
    payload = central_vector_index_status(db_path)
    payload["action"] = action
    if action == "doctor":
        payload["ok"] = bool(payload["readiness"]["local_vector_search"])

    if args.json:
        json_print(payload, pretty=args.pretty)
        return

    print(f"Vector index status: {payload['status']}")
    print(f"  source_of_truth: {payload['source_of_truth']}")
    print(f"  index_role: {payload['index_role']}")
    print(f"  semantic_vector_rows: {payload['counts']['semantic_vector_rows']}")
    print(f"  indexed_default_policy_rows: {payload['counts']['indexed_default_policy_rows']}")
    print(f"  missing_default_policy_rows: {payload['counts']['missing_default_policy_rows']}")
    print(f"  stale_vector_rows: {payload['counts']['stale_vector_rows']}")
    print(f"  shared_remote_risk_vector_rows: {payload['counts']['shared_remote_risk_vector_rows']}")
    print(f"  local_vector_search: {payload['readiness']['local_vector_search']}")
    print(f"  shared_remote_vector_read: {payload['readiness']['shared_remote_vector_read']}")
    if payload["next_actions"]:
        print("  next_actions:")
        for action_text in payload["next_actions"]:
            print(f"    - {action_text}")
