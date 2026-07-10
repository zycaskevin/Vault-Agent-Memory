"""Read-only status surface for the central derived vector index."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

from .db import VaultDB


HIGH_RISK_SENSITIVITIES = {"high", "restricted"}
REMOTE_VECTOR_TABLE = "vault_memory_embeddings"
REMOTE_VECTOR_STATUS_RPC = "vault_central_vector_index_status"
REMOTE_VECTOR_MIGRATION = "supabase/migrations/20260708_central_vector_index.sql"


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


def _generated_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _response_rows(response: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in (getattr(response, "data", None) or [])]


def _get_remote_vector_client() -> Any | None:
    from .mcp_remote import _get_supabase_client

    return _get_supabase_client()


def _safe_remote_error(exc: Exception) -> str:
    try:
        from .mcp_remote import _remote_doctor_safe_detail

        return _remote_doctor_safe_detail(exc)
    except Exception:
        detail = str(exc or "")
        detail = re.sub(r"(?i)(token|key|secret|password)=([^\s&]+)", r"\1=[REDACTED]", detail)
        detail = re.sub(r"https://[^\s]+\.supabase\.co", "https://[SUPABASE_PROJECT].supabase.co", detail)
        return detail[:300]


def _remote_vector_schema_missing(detail: str) -> bool:
    lowered = detail.lower()
    return any(
        marker in lowered
        for marker in (
            "pgrst202",
            "could not find the function",
            "function public.vault_central_vector_index_status",
            "function vault_central_vector_index_status",
            "does not exist",
            "schema cache",
            'relation "public.vault_memory_embeddings"',
            f"relation {REMOTE_VECTOR_TABLE}",
        )
    )


def central_remote_vector_index_status(sb_client: Any | None = None) -> dict[str, Any]:
    """Return a metadata-only status for the Supabase central vector index."""
    payload: dict[str, Any] = {
        "schema_version": 1,
        "artifact_type": "central_remote_vector_index_status",
        "generated_at": _generated_at(),
        "backend": "supabase",
        "migration": REMOTE_VECTOR_MIGRATION,
        "table": REMOTE_VECTOR_TABLE,
        "status_rpc": REMOTE_VECTOR_STATUS_RPC,
        "ok": False,
        "status": "not_configured",
        "installed": False,
        "remote_read_enabled": False,
        "remote_write_enabled": False,
        "source_of_truth": "local_sqlite_markdown",
        "index_role": "derived_remote_read_cache",
        "counts": {
            "vector_rows": 0,
            "latest_vector_rows": 0,
            "embedding_models": 0,
            "project_count": 0,
        },
        "timestamps": {
            "oldest_updated_at": "",
            "newest_updated_at": "",
        },
        "safety": {
            "candidate_first": True,
            "active_memory_source_of_truth": "local_sqlite",
            "trusted_sync_host_writes_only": True,
            "direct_remote_agent_table_writes": False,
            "returns_embedding_values": False,
            "returns_raw_memory_content": False,
        },
        "next_actions": [],
    }
    try:
        client = sb_client if sb_client is not None else _get_remote_vector_client()
    except Exception as exc:
        payload["error"] = _safe_remote_error(exc)
        payload["status"] = "unavailable"
        payload["next_actions"] = [
            "Install or repair the Supabase Python client, then rerun `vault vector-index central-status --json`.",
            f"Apply `{REMOTE_VECTOR_MIGRATION}` on the Supabase project if it is not installed yet.",
        ]
        return payload
    if client is None:
        payload["next_actions"] = [
            "Set SUPABASE_URL and SUPABASE_ANON_KEY/SUPABASE_KEY, then run `vault vector-index central-status --json`.",
            f"Apply `{REMOTE_VECTOR_MIGRATION}` on the Supabase project.",
        ]
        return payload

    try:
        rows = _response_rows(client.rpc(REMOTE_VECTOR_STATUS_RPC, {}).execute())
    except Exception as exc:
        detail = _safe_remote_error(exc)
        payload["error"] = detail
        payload["status"] = "schema_missing" if _remote_vector_schema_missing(detail) else "unavailable"
        payload["next_actions"] = [
            f"Apply `{REMOTE_VECTOR_MIGRATION}` on the Supabase project.",
            "Reload the Supabase/PostgREST schema cache after applying the migration.",
        ]
        return payload

    row = rows[0] if rows else {}
    installed = bool(row.get("installed"))
    vector_rows = int(row.get("vector_rows") or 0)
    latest_rows = int(row.get("latest_vector_rows") or 0)
    payload.update(
        {
            "ok": installed,
            "status": "installed_empty" if installed and vector_rows == 0 else ("installed" if installed else "schema_missing"),
            "installed": installed,
            "remote_read_enabled": bool(row.get("remote_read_enabled", False)),
            "remote_write_enabled": bool(row.get("remote_write_enabled", False)),
            "source_of_truth": row.get("source_of_truth") or payload["source_of_truth"],
            "index_role": row.get("index_role") or payload["index_role"],
            "counts": {
                "vector_rows": vector_rows,
                "latest_vector_rows": latest_rows,
                "embedding_models": int(row.get("embedding_models") or 0),
                "project_count": int(row.get("project_count") or 0),
            },
            "timestamps": {
                "oldest_updated_at": row.get("oldest_updated_at") or "",
                "newest_updated_at": row.get("newest_updated_at") or "",
            },
        }
    )
    if not installed:
        payload["next_actions"] = [f"Apply `{REMOTE_VECTOR_MIGRATION}` on the Supabase project."]
    elif vector_rows == 0:
        payload["next_actions"] = [
            "Central vector schema is installed. Run `vault memory-sync run-once --push-central-store --push-central-vectors --json` on a trusted sync host.",
        ]
    elif not payload["remote_read_enabled"]:
        payload["next_actions"] = [
            f"Central vector rows exist. Reapply `{REMOTE_VECTOR_MIGRATION}` to create the policy-aware semantic preview RPC.",
        ]
    else:
        payload["next_actions"] = [
            "Central vector rows exist and the policy-aware semantic preview RPC is available. Next step: wire a bounded MCP/Gateway semantic search tool.",
        ]
    return payload


def _relative_to_project(project: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project))
    except ValueError:
        return str(path.expanduser().resolve().relative_to(project.expanduser().resolve()))


def _md_text(value: Any) -> str:
    return str(value if value is not None else "").replace("\n", " ").replace("|", "\\|")


def _md_row(values: list[Any]) -> str:
    return "| " + " | ".join(_md_text(value) for value in values) + " |"


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
         LEFT JOIN knowledge_nodes AS n
                ON sv.vector_kind = 'node'
               AND n.knowledge_id = sv.knowledge_id
               AND n.node_uid = sv.item_uid
         LEFT JOIN knowledge_claims AS c
                ON sv.vector_kind = 'claim'
               AND c.knowledge_id = sv.knowledge_id
               AND c.claim_uid = sv.item_uid
             WHERE COALESCE(sv.content_hash, '') != ''
               AND (
                    (n.id IS NOT NULL AND sv.content_hash != COALESCE(n.content_hash, ''))
                 OR (c.id IS NOT NULL AND sv.content_hash != COALESCE(c.content_hash, ''))
                 OR (
                        n.id IS NULL
                    AND c.id IS NULL
                    AND COALESCE(k.content_hash, '') != ''
                    AND sv.content_hash != k.content_hash
                    )
               ){vector_filter}
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
        "generated_at": _generated_at(),
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
            LEFT JOIN knowledge_nodes AS n
                   ON sv.vector_kind = 'node'
                  AND n.knowledge_id = sv.knowledge_id
                  AND n.node_uid = sv.item_uid
            LEFT JOIN knowledge_claims AS c
                   ON sv.vector_kind = 'claim'
                  AND c.knowledge_id = sv.knowledge_id
                  AND c.claim_uid = sv.item_uid
                WHERE COALESCE(sv.content_hash, '') != ''
                  AND (
                       (n.id IS NOT NULL AND sv.content_hash != COALESCE(n.content_hash, ''))
                    OR (c.id IS NOT NULL AND sv.content_hash != COALESCE(c.content_hash, ''))
                    OR (
                           n.id IS NULL
                       AND c.id IS NULL
                       AND COALESCE(k.content_hash, '') != ''
                       AND sv.content_hash != k.content_hash
                       )
                  )""",
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
        "generated_at": _generated_at(),
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


def central_vector_index_repair(
    project: str | Path,
    db_path: str | Path,
    *,
    apply: bool = False,
    changed_only: bool = True,
    limit: int = 20,
    batch_size: int = 0,
    allow_hash: bool = False,
    hash_dim: int = 8,
    persist_cache: bool = True,
) -> dict[str, Any]:
    """Return a dry-run or applied repair wrapper for the derived vector index.

    When ``batch_size > 0`` and ``apply`` is True with ``changed_only=True``,
    the repair runs in auto-batch mode: it keeps processing batches until no
    more stale/missing rows remain. This avoids needing multiple manual calls
    for large knowledge bases.
    """
    project = Path(project)
    db_path = Path(db_path)
    before_status = central_vector_index_status(db_path)
    before_plan = central_vector_index_plan(db_path, limit=limit)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "artifact_type": "central_derived_vector_index_repair",
        "generated_at": _generated_at(),
        "action": "repair",
        "dry_run": not bool(apply),
        "apply": bool(apply),
        "db_path": str(db_path),
        "source_of_truth": "local_sqlite_markdown",
        "index_role": "derived_rebuildable_cache",
        "remote_read_enabled": False,
        "remote_write_enabled": False,
        "options": {
            "changed_only": bool(changed_only),
            "limit": int(limit),
            "allow_hash": bool(allow_hash),
            "hash_dim": int(hash_dim),
            "persist_cache": bool(persist_cache),
        },
        "before": _compact_repair_status(before_status, before_plan),
        "rebuild": None,
        "after": None,
        "safety": {
            "writes_candidates": False,
            "active_memory_writes": False,
            "semantic_vector_writes": bool(apply),
            "embedding_cache_writes": bool(apply and persist_cache),
            "remote_vector_read": False,
            "remote_vector_write": False,
            "raw_memory_content_included": False,
        },
        "next_actions": [],
        "notes": [
            "Repair uses the existing semantic rebuild workflow.",
            "Remote vector read remains disabled after repair.",
        ],
    }
    if not apply:
        payload["next_actions"] = [
            "Review the dry-run plan before applying vector-index repair.",
            _repair_command(project, changed_only=changed_only, limit=limit, allow_hash=allow_hash, hash_dim=hash_dim),
        ]
        return payload

    from .db import VaultDB
    from .embed import create_embedding_provider
    from .semantic import (
        DeterministicHashEmbeddingProvider,
        PersistentCachedEmbeddingProvider,
        rebuild_semantic_index,
        validate_embedding_provider,
    )

    batch_size_i = max(0, int(batch_size or 0))
    use_batching = batch_size_i > 0 and changed_only and apply
    pass_limit = batch_size_i if use_batching else int(limit)
    total_repaired = 0
    total_node_vectors = 0
    total_claim_vectors = 0
    total_batches = 0
    last_stats = None
    cache_stats: dict[str, Any] = {}

    with VaultDB(db_path) as db:
        if allow_hash:
            provider = DeterministicHashEmbeddingProvider(dim=hash_dim)
        else:
            provider_name = db.get_config("embedding_provider", "auto")
            model_key = db.get_config("embedding_model", "mix")
            provider = create_embedding_provider(provider=provider_name, model_key=model_key)
        provider = validate_embedding_provider(provider, require_semantic=not allow_hash, allow_hash=allow_hash)
        if persist_cache:
            provider = PersistentCachedEmbeddingProvider(provider, db)
        try:
            if use_batching:
                # Auto-batch mode: keep going until no more rows need repair
                while True:
                    stats = rebuild_semantic_index(
                        db,
                        provider,
                        require_semantic=not allow_hash,
                        allow_hash=allow_hash,
                        changed_only=True,
                        limit=pass_limit,
                    )
                    total_batches += 1
                    total_repaired += int(stats.knowledge_rows)
                    total_node_vectors += int(stats.node_vectors)
                    total_claim_vectors += int(stats.claim_vectors)
                    last_stats = stats
                    if int(stats.knowledge_rows) < pass_limit:
                        break  # Finished all pending rows
            else:
                # Single pass (either full rebuild or limited changed-only)
                last_stats = rebuild_semantic_index(
                    db,
                    provider,
                    require_semantic=not allow_hash,
                    allow_hash=allow_hash,
                    changed_only=changed_only,
                    limit=None if (not changed_only and batch_size_i <= 0) else pass_limit,
                )
                total_repaired = int(last_stats.knowledge_rows)
                total_batches = 1

            final_stats = last_stats
            payload["rebuild"] = {
                "provider_id": provider.provider_id,
                "is_semantic": bool(provider.is_semantic),
                "dimension": int(provider.dim),
                "knowledge_rows": total_repaired,
                "node_vectors": total_node_vectors if use_batching else int(getattr(final_stats, "node_vectors", 0)),
                "claim_vectors": total_claim_vectors if use_batching else int(getattr(final_stats, "claim_vectors", 0)),
                "changed_only": bool(getattr(final_stats, "changed_only", False)),
                "candidate_rows": int(getattr(final_stats, "candidate_rows", 0)),
                "skipped_rows": int(getattr(final_stats, "skipped_rows", 0)),
                "batches": total_batches,
                "batch_size": batch_size_i if use_batching else 0,
            }
            if persist_cache:
                cache_stats = {
                    "memory_rows": int(getattr(provider, "cache_size", 0)),
                    "persistent_hits": int(getattr(provider, "persistent_hits", 0)),
                    "persistent_misses": int(getattr(provider, "persistent_misses", 0)),
                    "writes": int(getattr(provider, "writes", 0)),
                }
                payload["rebuild"]["persistent_cache"] = cache_stats
        finally:
            close = getattr(provider, "close", None)
            if callable(close):
                close()

    after_status = central_vector_index_status(db_path)
    after_plan = central_vector_index_plan(db_path, limit=limit)
    payload["after"] = _compact_repair_status(after_status, after_plan)
    payload["next_actions"] = [
        "Run Search QA before changing hybrid/vector ranking.",
        "Keep remote vector read disabled until access-policy tests cover the serving path.",
    ]
    return payload


def _compact_repair_status(status: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    counts = status.get("counts") or {}
    plan_counts = plan.get("counts") or {}
    return {
        "status": status.get("status", ""),
        "semantic_vector_rows": int(counts.get("semantic_vector_rows") or 0),
        "indexed_default_policy_rows": int(counts.get("indexed_default_policy_rows") or 0),
        "missing_default_policy_rows": int(counts.get("missing_default_policy_rows") or 0),
        "stale_vector_rows": int(counts.get("stale_vector_rows") or 0),
        "orphan_vector_rows": int(counts.get("orphan_vector_rows") or 0),
        "shared_remote_risk_vector_rows": int(counts.get("shared_remote_risk_vector_rows") or 0),
        "local_vector_search": bool((status.get("readiness") or {}).get("local_vector_search", False)),
        "shared_remote_vector_read": bool((status.get("readiness") or {}).get("shared_remote_vector_read", False)),
        "repair_rows_sampled": int(plan_counts.get("repair_rows_sampled") or 0),
        "cleanup_rows_sampled": int(plan_counts.get("cleanup_rows_sampled") or 0),
        "recommended_commands": plan.get("recommended_commands", []),
    }


def _repair_command(
    project: Path,
    *,
    changed_only: bool,
    limit: int,
    allow_hash: bool,
    hash_dim: int,
) -> str:
    parts = [
        "vault vector-index repair",
        f"--project-dir {shlex.quote(str(project))}",
        "--apply",
        f"--limit {int(limit)}",
    ]
    if not changed_only:
        parts.append("--full")
    if allow_hash:
        parts += ["--allow-hash", f"--hash-dim {int(hash_dim)}"]
    return " ".join(parts)


def _resolve_vector_index_report_path(project: Path, action: str, report_path: str | Path = "") -> Path:
    report_dir = project / "reports" / "vector-index"
    report_dir.mkdir(parents=True, exist_ok=True)
    if report_path:
        raw = Path(report_path)
        json_path = raw if raw.is_absolute() else project / raw
        resolved = json_path.expanduser().resolve()
        allowed = report_dir.expanduser().resolve()
        if allowed != resolved and allowed not in resolved.parents:
            raise ValueError("vector-index report path must stay under reports/vector-index")
        return resolved
    safe_action = action if action in {"status", "doctor", "plan", "repair", "central-status"} else "status"
    return report_dir / f"{safe_action}-latest.json"


def write_vector_index_report(
    project: str | Path,
    payload: dict[str, Any],
    *,
    action: str,
    report_path: str | Path = "",
) -> dict[str, str]:
    """Write JSON and Markdown reports for vector-index status/plan artifacts."""
    project = Path(project)
    json_path = _resolve_vector_index_report_path(project, action, report_path)
    markdown_path = json_path.with_suffix(".md")
    data = dict(payload)
    data["paths"] = {
        "json": _relative_to_project(project, json_path),
        "markdown": _relative_to_project(project, markdown_path),
    }
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_vector_index_markdown(data), encoding="utf-8")
    return data["paths"]


def render_vector_index_markdown(payload: dict[str, Any]) -> str:
    if payload.get("artifact_type") == "central_derived_vector_index_repair":
        return _render_vector_index_repair_markdown(payload)
    if payload.get("artifact_type") == "central_derived_vector_index_plan":
        return _render_vector_index_plan_markdown(payload)
    return _render_vector_index_status_markdown(payload)


def _render_vector_index_status_markdown(payload: dict[str, Any]) -> str:
    if payload.get("artifact_type") == "central_remote_vector_index_status":
        return _render_remote_vector_index_status_markdown(payload)
    counts = payload.get("counts") or {}
    readiness = payload.get("readiness") or {}
    lines = [
        "# Vault Vector Index Status",
        "",
        f"- generated_at: `{_md_text(payload.get('generated_at', ''))}`",
        f"- action: `{_md_text(payload.get('action', 'status'))}`",
        f"- status: `{_md_text(payload.get('status', ''))}`",
        f"- source_of_truth: `{_md_text(payload.get('source_of_truth', ''))}`",
        f"- index_role: `{_md_text(payload.get('index_role', ''))}`",
        f"- local_only: `{str(bool(payload.get('local_only', True))).lower()}`",
        f"- remote_read_enabled: `{str(bool(payload.get('remote_read_enabled', False))).lower()}`",
        f"- remote_write_enabled: `{str(bool(payload.get('remote_write_enabled', False))).lower()}`",
        "",
        "## Counts",
        "",
        _md_row(["metric", "value"]),
        _md_row(["---", "---"]),
    ]
    for key in sorted(counts):
        lines.append(_md_row([key, counts.get(key)]))
    lines += [
        "",
        "## Readiness",
        "",
        f"- local vector search: `{str(bool(readiness.get('local_vector_search', False))).lower()}`",
        f"- shared remote vector read: `{str(bool(readiness.get('shared_remote_vector_read', False))).lower()}`",
        f"- reason: {_md_text(readiness.get('reason', ''))}",
        "",
        "## Provider Breakdown",
        "",
    ]
    providers = payload.get("provider_breakdown") or []
    if providers:
        lines += [
            _md_row(["provider_id", "dimension", "vector_kind", "vector_rows", "indexed_rows"]),
            _md_row(["---", "---", "---", "---", "---"]),
        ]
        for item in providers[:20]:
            lines.append(
                _md_row(
                    [
                        item.get("provider_id", ""),
                        item.get("dimension", ""),
                        item.get("vector_kind", ""),
                        item.get("vector_rows", 0),
                        item.get("indexed_knowledge_rows", 0),
                    ]
                )
            )
    else:
        lines.append("No semantic vector providers found.")
    lines += [
        "",
        "## Next Actions",
        "",
    ]
    for action in payload.get("next_actions") or []:
        lines.append(f"- {_md_text(action)}")
    lines += [
        "",
        "## Safety",
        "",
        "- derived rebuildable cache only",
        "- no raw memory content",
        "- no vector source text",
        "- remote vector read remains disabled",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _render_remote_vector_index_status_markdown(payload: dict[str, Any]) -> str:
    counts = payload.get("counts") or {}
    timestamps = payload.get("timestamps") or {}
    lines = [
        "# Vault Central Vector Index Status",
        "",
        f"- generated_at: `{_md_text(payload.get('generated_at', ''))}`",
        f"- status: `{_md_text(payload.get('status', ''))}`",
        f"- installed: `{str(bool(payload.get('installed', False))).lower()}`",
        f"- backend: `{_md_text(payload.get('backend', ''))}`",
        f"- table: `{_md_text(payload.get('table', ''))}`",
        f"- status_rpc: `{_md_text(payload.get('status_rpc', ''))}`",
        f"- migration: `{_md_text(payload.get('migration', ''))}`",
        f"- source_of_truth: `{_md_text(payload.get('source_of_truth', ''))}`",
        f"- index_role: `{_md_text(payload.get('index_role', ''))}`",
        f"- remote_read_enabled: `{str(bool(payload.get('remote_read_enabled', False))).lower()}`",
        f"- remote_write_enabled: `{str(bool(payload.get('remote_write_enabled', False))).lower()}`",
        "",
        "## Counts",
        "",
        _md_row(["metric", "value"]),
        _md_row(["---", "---"]),
    ]
    for key in sorted(counts):
        lines.append(_md_row([key, counts.get(key)]))
    lines += [
        "",
        "## Timestamps",
        "",
        f"- oldest_updated_at: `{_md_text(timestamps.get('oldest_updated_at', ''))}`",
        f"- newest_updated_at: `{_md_text(timestamps.get('newest_updated_at', ''))}`",
        "",
        "## Next Actions",
        "",
    ]
    for action in payload.get("next_actions") or []:
        lines.append(f"- {_md_text(action)}")
    lines += [
        "",
        "## Safety",
        "",
        "- derived remote read cache only",
        "- trusted sync host writes only",
        "- no embedding values in status",
        "- no raw memory content in status",
        "- remote semantic search remains disabled",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _render_vector_index_plan_markdown(payload: dict[str, Any]) -> str:
    counts = payload.get("counts") or {}
    filters = payload.get("filters") or {}
    lines = [
        "# Vault Vector Index Plan",
        "",
        f"- generated_at: `{_md_text(payload.get('generated_at', ''))}`",
        f"- action: `{_md_text(payload.get('action', 'plan'))}`",
        f"- dry_run: `{str(bool(payload.get('dry_run', True))).lower()}`",
        f"- provider_id: `{_md_text(filters.get('provider_id', ''))}`",
        f"- dimension: `{_md_text(filters.get('dimension', ''))}`",
        f"- vector_kind: `{_md_text(filters.get('vector_kind', ''))}`",
        f"- limit: `{_md_text(filters.get('limit', ''))}`",
        "",
        "## Counts",
        "",
        _md_row(["metric", "value"]),
        _md_row(["---", "---"]),
    ]
    for key in sorted(counts):
        lines.append(_md_row([key, counts.get(key)]))
    lines += [
        "",
        "## Recommended Commands",
        "",
    ]
    for command in payload.get("recommended_commands") or []:
        lines.append(f"- `{_md_text(command)}`")

    groups = payload.get("groups") or {}
    group_titles = {
        "missing_default_policy": "Missing Default Policy",
        "stale": "Stale",
        "shared_remote_risk": "Shared Remote Risk",
        "orphan_vectors": "Orphan Vectors",
    }
    for group_key, title in group_titles.items():
        rows = groups.get(group_key) or []
        lines += ["", f"## {title}", ""]
        if not rows:
            lines.append("No rows sampled.")
            continue
        keys = _plan_markdown_keys(group_key)
        lines += [_md_row(keys), _md_row(["---"] * len(keys))]
        for row in rows[:20]:
            lines.append(_md_row([row.get(key, "") for key in keys]))

    lines += [
        "",
        "## Safety",
        "",
        "- metadata-only dry run",
        "- no raw memory content",
        "- no vector source text",
        "- no rebuild or cleanup mutation",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _plan_markdown_keys(group_key: str) -> list[str]:
    if group_key == "orphan_vectors":
        return ["vector_id", "knowledge_id", "provider_id", "dimension", "vector_kind", "updated_at", "reason"]
    return ["knowledge_id", "title", "source", "layer", "scope", "sensitivity", "status", "updated_at", "reason"]


def _render_vector_index_repair_markdown(payload: dict[str, Any]) -> str:
    before = payload.get("before") or {}
    after = payload.get("after") or {}
    rebuild = payload.get("rebuild") or {}
    lines = [
        "# Vault Vector Index Repair",
        "",
        f"- generated_at: `{_md_text(payload.get('generated_at', ''))}`",
        f"- dry_run: `{str(bool(payload.get('dry_run', True))).lower()}`",
        f"- apply: `{str(bool(payload.get('apply', False))).lower()}`",
        f"- remote_read_enabled: `{str(bool(payload.get('remote_read_enabled', False))).lower()}`",
        f"- remote_write_enabled: `{str(bool(payload.get('remote_write_enabled', False))).lower()}`",
        "",
        "## Before",
        "",
        _repair_status_table(before),
        "",
    ]
    if after:
        lines += ["## After", "", _repair_status_table(after), ""]
    if rebuild:
        lines += [
            "## Rebuild",
            "",
            f"- provider_id: `{_md_text(rebuild.get('provider_id', ''))}`",
            f"- is_semantic: `{str(bool(rebuild.get('is_semantic', False))).lower()}`",
            f"- dimension: `{int(rebuild.get('dimension') or 0)}`",
            f"- knowledge_rows: `{int(rebuild.get('knowledge_rows') or 0)}`",
            f"- node_vectors: `{int(rebuild.get('node_vectors') or 0)}`",
            f"- claim_vectors: `{int(rebuild.get('claim_vectors') or 0)}`",
            f"- changed_only: `{str(bool(rebuild.get('changed_only', False))).lower()}`",
            "",
        ]
    lines += ["## Next Actions", ""]
    for action in payload.get("next_actions") or []:
        lines.append(f"- `{_md_text(action)}`" if action.startswith("vault ") else f"- {_md_text(action)}")
    lines += [
        "",
        "## Safety",
        "",
        "- no active memory writes",
        "- no candidate writes",
        "- no raw memory content",
        "- remote vector read remains disabled",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _repair_status_table(payload: dict[str, Any]) -> str:
    keys = [
        "status",
        "semantic_vector_rows",
        "missing_default_policy_rows",
        "stale_vector_rows",
        "orphan_vector_rows",
        "shared_remote_risk_vector_rows",
        "repair_rows_sampled",
        "cleanup_rows_sampled",
    ]
    return "\n".join([_md_row(["metric", "value"]), _md_row(["---", "---"]), *[_md_row([key, payload.get(key, "")]) for key in keys]])


def add_vector_index_parser(sub) -> None:
    parser = sub.add_parser("vector-index", help="中央衍生向量索引狀態與安全檢查")
    vector_sub = parser.add_subparsers(dest="vector_index_action")

    def add_report_args(sp) -> None:
        sp.add_argument("--write-report", action="store_true", help="write reports/vector-index/<action>-latest.json and .md")
        sp.add_argument("--report-path", default="", help="custom reports/vector-index/*.json path")

    def add_plan_filters(sp) -> None:
        sp.add_argument("--db-path", help="SQLite DB 路徑（預設 project_dir/vault.db）")
        sp.add_argument("--provider-id", help="只檢查指定 embedding provider")
        sp.add_argument("--dimension", type=int, help="只檢查指定 embedding 維度")
        sp.add_argument("--vector-kind", choices=["claim", "node"], help="只檢查指定 semantic vector kind")
        sp.add_argument("--limit", type=int, default=20, help="每組最多回傳幾筆 metadata rows")
        sp.add_argument("--json", action="store_true", help="輸出 JSON")
        sp.add_argument("--pretty", action="store_true", help="縮排 JSON 輸出")
        add_report_args(sp)

    sp = vector_sub.add_parser("status", help="檢查 local derived vector index 狀態")
    sp.add_argument("--db-path", help="SQLite DB 路徑（預設 project_dir/vault.db）")
    sp.add_argument("--json", action="store_true", help="輸出 JSON")
    sp.add_argument("--pretty", action="store_true", help="縮排 JSON 輸出")
    add_report_args(sp)

    sp = vector_sub.add_parser("doctor", help="檢查 index 是否可安全作為 shared read 基礎")
    sp.add_argument("--db-path", help="SQLite DB 路徑（預設 project_dir/vault.db）")
    sp.add_argument("--json", action="store_true", help="輸出 JSON")
    sp.add_argument("--pretty", action="store_true", help="縮排 JSON 輸出")
    add_report_args(sp)

    sp = vector_sub.add_parser("plan", help="產生 read-only rebuild/cleanup dry-run plan")
    add_plan_filters(sp)

    sp = vector_sub.add_parser("central-status", help="檢查 Supabase 中央向量索引 schema 狀態")
    sp.add_argument("--json", action="store_true", help="輸出 JSON")
    sp.add_argument("--pretty", action="store_true", help="縮排 JSON 輸出")
    add_report_args(sp)

    sp = vector_sub.add_parser("repair", help="dry-run or apply safe semantic vector-index repair")
    sp.add_argument("--db-path", help="SQLite DB 路徑（預設 project_dir/vault.db）")
    sp.add_argument("--apply", action="store_true", help="apply semantic rebuild repair; default is dry-run")
    sp.add_argument("--full", action="store_true", help="full rebuild instead of changed-only repair")
    sp.add_argument("--limit", type=int, default=20, help="maximum rows to repair in one pass (default: 20)")
    sp.add_argument("--batch-size", type=int, default=0, help="auto-batch mode: process all pending rows in batches of this size (0=disabled)")
    sp.add_argument("--allow-hash", action="store_true", help="allow deterministic hash vectors for local tests")
    sp.add_argument("--hash-dim", type=int, default=8, help="deterministic hash vector dimension")
    sp.add_argument("--no-persist-cache", action="store_true", help="disable persistent embedding cache during apply")
    sp.add_argument("--json", action="store_true", help="輸出 JSON")
    sp.add_argument("--pretty", action="store_true", help="縮排 JSON 輸出")
    add_report_args(sp)


def cmd_vector_index(args, *, find_project_dir, json_print) -> None:
    action = args.vector_index_action
    if action not in {"status", "doctor", "plan", "repair", "central-status"}:
        print("error: vector-index requires action: status, doctor, plan, repair, or central-status", file=sys.stderr)
        raise SystemExit(2)

    project_dir = find_project_dir()
    if action == "central-status":
        payload = central_remote_vector_index_status()
        payload["action"] = action
        if getattr(args, "write_report", False):
            payload["paths"] = write_vector_index_report(
                project_dir,
                payload,
                action="central-status",
                report_path=getattr(args, "report_path", ""),
            )
        if args.json:
            json_print(payload, pretty=args.pretty)
            return
        print(f"Central vector index: {payload.get('status', '')}")
        print(f"  installed: {'yes' if payload.get('installed') else 'no'}")
        print(f"  table: {payload.get('table', '')}")
        print(f"  status_rpc: {payload.get('status_rpc', '')}")
        counts = payload.get("counts") or {}
        print(f"  vector_rows: {counts.get('vector_rows', 0)}")
        if payload.get("paths"):
            print(f"  report_json: {payload['paths']['json']}")
            print(f"  report_markdown: {payload['paths']['markdown']}")
        return

    db_path = Path(args.db_path) if args.db_path else project_dir / "vault.db"
    if action == "repair":
        payload = central_vector_index_repair(
            project_dir,
            db_path,
            apply=bool(getattr(args, "apply", False)),
            changed_only=not bool(getattr(args, "full", False)),
            limit=getattr(args, "limit", 20),
            batch_size=getattr(args, "batch_size", 0),
            allow_hash=bool(getattr(args, "allow_hash", False)),
            hash_dim=getattr(args, "hash_dim", 8),
            persist_cache=not bool(getattr(args, "no_persist_cache", False)),
        )
        if getattr(args, "write_report", False):
            payload["paths"] = write_vector_index_report(
                project_dir,
                payload,
                action=action,
                report_path=getattr(args, "report_path", ""),
            )
        if args.json:
            json_print(payload, pretty=args.pretty)
            return
        print(f"Vector index repair: {'apply' if payload['apply'] else 'dry-run'}")
        before = payload.get("before") or {}
        after = payload.get("after") or {}
        print(f"  before_status: {before.get('status', '')}")
        print(f"  repair_rows_sampled: {before.get('repair_rows_sampled', 0)}")
        print(f"  cleanup_rows_sampled: {before.get('cleanup_rows_sampled', 0)}")
        if after:
            print(f"  after_status: {after.get('status', '')}")
            print(f"  after_semantic_vector_rows: {after.get('semantic_vector_rows', 0)}")
        if payload.get("paths"):
            print(f"  report_json: {payload['paths']['json']}")
            print(f"  report_markdown: {payload['paths']['markdown']}")
        return

    if action == "plan":
        payload = central_vector_index_plan(
            db_path,
            limit=args.limit,
            provider_id=args.provider_id,
            dimension=args.dimension,
            vector_kind=args.vector_kind,
        )
        payload["action"] = action
        if getattr(args, "write_report", False):
            payload["paths"] = write_vector_index_report(
                project_dir,
                payload,
                action=action,
                report_path=getattr(args, "report_path", ""),
            )
        if args.json:
            json_print(payload, pretty=args.pretty)
            return
        print("Vector index plan: dry-run")
        for key, value in payload["counts"].items():
            print(f"  {key}: {value}")
        print("  recommended_commands:")
        for command in payload["recommended_commands"]:
            print(f"    - {command}")
        if payload.get("paths"):
            print(f"  report_json: {payload['paths']['json']}")
            print(f"  report_markdown: {payload['paths']['markdown']}")
        return

    payload = central_vector_index_status(db_path)
    payload["action"] = action
    if action == "doctor":
        payload["ok"] = bool(payload["readiness"]["local_vector_search"])
    if getattr(args, "write_report", False):
        payload["paths"] = write_vector_index_report(
            project_dir,
            payload,
            action=action,
            report_path=getattr(args, "report_path", ""),
        )

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
    if payload.get("paths"):
        print(f"  report_json: {payload['paths']['json']}")
        print(f"  report_markdown: {payload['paths']['markdown']}")
