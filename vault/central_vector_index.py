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


def _vector_filter_sql(
    *,
    alias: str = "sv",
    provider_id: str | None = None,
    dimension: int | None = None,
    vector_kind: str | None = None,
) -> tuple[str, list[Any]]:
    filters: list[str] = []
    params: list[Any] = []
    if provider_id:
        filters.append(f"{alias}.provider_id=?")
        params.append(provider_id)
    if dimension is not None:
        filters.append(f"{alias}.dimension=?")
        params.append(int(dimension))
    if vector_kind:
        filters.append(f"{alias}.vector_kind=?")
        params.append(vector_kind)
    return (" AND " + " AND ".join(filters), params) if filters else ("", [])


def _plan_rows(db: VaultDB, sql: str, params: list[Any], *, limit: int) -> list[dict[str, Any]]:
    rows = db.conn.execute(f"{sql} LIMIT ?", [*params, int(limit)]).fetchall()
    return [dict(row) for row in rows]


def central_vector_index_plan(
    db_path: str | Path,
    *,
    limit: int = 20,
    provider_id: str | None = None,
    dimension: int | None = None,
    vector_kind: str | None = None,
) -> dict[str, Any]:
    """Return a dry-run rebuild and cleanup plan for the derived vector index."""
    db_path = Path(db_path)
    vector_filter, vector_params = _vector_filter_sql(
        provider_id=provider_id,
        dimension=dimension,
        vector_kind=vector_kind,
    )
    exists_filter, exists_params = _vector_filter_sql(
        alias="existing",
        provider_id=provider_id,
        dimension=dimension,
        vector_kind=vector_kind,
    )
    with VaultDB(db_path) as db:
        missing_sql = f"""
            SELECT k.id AS knowledge_id, k.title, k.source, k.layer, k.scope,
                   k.sensitivity, k.status, k.updated_at,
                   'missing_default_policy_vector' AS reason
              FROM knowledge AS k
             WHERE COALESCE(k.status, 'active') = 'active'
               AND lower(COALESCE(k.scope, 'project')) != 'private'
               AND lower(COALESCE(k.sensitivity, 'low')) NOT IN ('high', 'restricted')
               AND NOT EXISTS (
                   SELECT 1 FROM semantic_vectors AS existing
                    WHERE existing.knowledge_id = k.id{exists_filter}
               )
             ORDER BY k.updated_at DESC, k.id DESC
        """
        missing_rows = _plan_rows(db, missing_sql, exists_params, limit=limit)

        stale_sql = f"""
            SELECT DISTINCT k.id AS knowledge_id, k.title, k.source, k.layer,
                   k.scope, k.sensitivity, k.status, k.updated_at,
                   'stale_content_hash' AS reason
              FROM semantic_vectors AS sv
              JOIN knowledge AS k ON k.id = sv.knowledge_id
             WHERE COALESCE(sv.content_hash, '') != ''
               AND COALESCE(k.content_hash, '') != ''
               AND sv.content_hash != k.content_hash{vector_filter}
             ORDER BY k.updated_at DESC, k.id DESC
        """
        stale_rows = _plan_rows(db, stale_sql, vector_params, limit=limit)

        risk_sql = f"""
            SELECT DISTINCT k.id AS knowledge_id, k.title, k.source, k.layer,
                   k.scope, k.sensitivity, k.status, k.updated_at,
                   CASE
                     WHEN COALESCE(k.status, 'active') != 'active' THEN 'non_active_memory_indexed'
                     WHEN lower(COALESCE(k.scope, 'project')) = 'private' THEN 'private_memory_indexed'
                     WHEN lower(COALESCE(k.sensitivity, 'low')) IN ('high', 'restricted') THEN 'sensitive_memory_indexed'
                     ELSE 'non_default_shared_read_vector'
                   END AS reason
              FROM semantic_vectors AS sv
              JOIN knowledge AS k ON k.id = sv.knowledge_id
             WHERE (
                   COALESCE(k.status, 'active') != 'active'
                OR lower(COALESCE(k.scope, 'project')) = 'private'
                OR lower(COALESCE(k.sensitivity, 'low')) IN ('high', 'restricted')
             ){vector_filter}
             ORDER BY k.updated_at DESC, k.id DESC
        """
        risk_rows = _plan_rows(db, risk_sql, vector_params, limit=limit)

        orphan_sql = f"""
            SELECT sv.id AS vector_id, sv.knowledge_id, sv.provider_id,
                   sv.dimension, sv.vector_kind, sv.item_uid, sv.updated_at,
                   'orphan_vector' AS reason
              FROM semantic_vectors AS sv
         LEFT JOIN knowledge AS k ON k.id = sv.knowledge_id
             WHERE k.id IS NULL{vector_filter}
             ORDER BY sv.updated_at DESC, sv.id DESC
        """
        orphan_rows = _plan_rows(db, orphan_sql, vector_params, limit=limit)

    repair_count = len(missing_rows) + len(stale_rows)
    cleanup_count = len(risk_rows) + len(orphan_rows)
    recommended_commands: list[str] = []
    if repair_count:
        recommended_commands.append("vault semantic rebuild --changed-only")
    if cleanup_count:
        recommended_commands.append("keep risky/orphan vectors local-only until cleanup support is implemented")
    if not recommended_commands:
        recommended_commands.append("run Search QA before changing hybrid/vector ranking")

    return {
        "schema_version": 1,
        "artifact_type": "central_derived_vector_index_plan",
        "dry_run": True,
        "db_path": str(db_path),
        "filters": {
            "provider_id": provider_id,
            "dimension": dimension,
            "vector_kind": vector_kind,
            "limit": int(limit),
        },
        "counts": {
            "missing_default_policy_rows_sampled": len(missing_rows),
            "stale_rows_sampled": len(stale_rows),
            "shared_remote_risk_rows_sampled": len(risk_rows),
            "orphan_vector_rows_sampled": len(orphan_rows),
            "repair_rows_sampled": repair_count,
            "cleanup_rows_sampled": cleanup_count,
        },
        "groups": {
            "missing_default_policy": missing_rows,
            "stale": stale_rows,
            "shared_remote_risk": risk_rows,
            "orphan_vectors": orphan_rows,
        },
        "recommended_commands": recommended_commands,
        "notes": [
            "This plan is metadata-only and does not include raw memory content.",
            "Remote vector read remains disabled; cleanup is a prerequisite for shared remote exposure.",
        ],
    }


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

    def add_plan_filters(sp) -> None:
        sp.add_argument("--db-path", help="SQLite DB 路徑（預設 project_dir/vault.db）")
        sp.add_argument("--provider-id", help="只檢查指定 embedding provider")
        sp.add_argument("--dimension", type=int, help="只檢查指定 embedding 維度")
        sp.add_argument("--vector-kind", choices=["claim", "node"], help="只檢查指定 semantic vector kind")
        sp.add_argument("--limit", type=int, default=20, help="每組最多回傳幾筆 metadata rows")
        sp.add_argument("--json", action="store_true", help="輸出 JSON")
        sp.add_argument("--pretty", action="store_true", help="縮排 JSON 輸出")

    sp = vector_sub.add_parser("status", help="檢查 local derived vector index 狀態")
    sp.add_argument("--db-path", help="SQLite DB 路徑（預設 project_dir/vault.db）")
    sp.add_argument("--json", action="store_true", help="輸出 JSON")
    sp.add_argument("--pretty", action="store_true", help="縮排 JSON 輸出")

    sp = vector_sub.add_parser("doctor", help="檢查 index 是否可安全作為 shared read 基礎")
    sp.add_argument("--db-path", help="SQLite DB 路徑（預設 project_dir/vault.db）")
    sp.add_argument("--json", action="store_true", help="輸出 JSON")
    sp.add_argument("--pretty", action="store_true", help="縮排 JSON 輸出")

    sp = vector_sub.add_parser("plan", help="產生 read-only rebuild/cleanup dry-run plan")
    add_plan_filters(sp)


def cmd_vector_index(args, *, find_project_dir, json_print) -> None:
    action = args.vector_index_action
    if action not in {"status", "doctor", "plan"}:
        print("error: vector-index requires action: status, doctor, or plan", file=sys.stderr)
        raise SystemExit(2)

    db_path = Path(args.db_path) if args.db_path else find_project_dir() / "vault.db"
    if action == "plan":
        payload = central_vector_index_plan(
            db_path,
            limit=args.limit,
            provider_id=args.provider_id,
            dimension=args.dimension,
            vector_kind=args.vector_kind,
        )
        payload["action"] = action
        if args.json:
            json_print(payload, pretty=args.pretty)
            return
        print("Vector index plan: dry-run")
        for key, value in payload["counts"].items():
            print(f"  {key}: {value}")
        print("  recommended_commands:")
        for command in payload["recommended_commands"]:
            print(f"    - {command}")
        return

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
