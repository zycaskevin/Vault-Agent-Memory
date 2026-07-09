"""Remote semantic MCP helpers for the Supabase central vector read layer."""

from __future__ import annotations

import os
from typing import Any

from .mcp_remote import (
    MCP_SEARCH_MAX_LIMIT,
    _clamp_int,
    _get_supabase_client,
    _remote_doctor_safe_detail,
    _remote_error,
    _supabase_rpc,
)

REMOTE_SEMANTIC_VECTOR_DIMENSION = 1536
REMOTE_SEMANTIC_SEARCH_RPC = "vault_match_readable_memory_embeddings"
REMOTE_SNAPSHOT_READ_RPC = "vault_get_readable_memory_snapshot"
REMOTE_SEMANTIC_DEFAULT_EMBEDDING_PROVIDER = "openai"
REMOTE_SEMANTIC_DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
REMOTE_SEMANTIC_EXTERNAL_PROVIDERS = {"openai", "cohere", "voyage"}


def _pgvector_literal(vector: list[float]) -> str:
    values = ",".join(str(float(value)) for value in vector)
    return f"[{values}]"


def remote_semantic_query_provider_disclosure(*, query_embedding_precomputed: bool = False) -> dict[str, Any]:
    """Return safe metadata about the remote semantic query embedding provider."""
    provider_env = os.getenv("VAULT_REMOTE_SEMANTIC_EMBEDDING_PROVIDER", "").strip()
    provider = (provider_env or REMOTE_SEMANTIC_DEFAULT_EMBEDDING_PROVIDER).strip().lower()
    model_env = os.getenv("VAULT_REMOTE_SEMANTIC_EMBEDDING_MODEL", "").strip()
    openai_model_env = os.getenv("OPENAI_EMBEDDING_MODEL", "").strip()
    model_key = model_env or openai_model_env or REMOTE_SEMANTIC_DEFAULT_EMBEDDING_MODEL
    external_provider = provider in REMOTE_SEMANTIC_EXTERNAL_PROVIDERS
    query_text_sent = not bool(query_embedding_precomputed)
    warnings: list[str] = []
    privacy_warning = ""
    if query_text_sent and provider == "openai":
        warnings.append("remote_semantic_query_text_sent_to_openai")
        privacy_warning = (
            "Remote Semantic Search sends query text to OpenAI by default. "
            "Use VAULT_REMOTE_SEMANTIC_EMBEDDING_PROVIDER for a local or trusted provider."
        )
    elif query_text_sent and external_provider:
        warnings.append("remote_semantic_query_text_sent_to_external_embedding_provider")
        privacy_warning = (
            "Remote Semantic Search sends query text to the configured external embedding provider. "
            "Use a local or trusted provider for sensitive deployments."
        )
    return {
        "provider": provider,
        "model": model_key,
        "provider_defaulted": not bool(provider_env),
        "model_defaulted": not bool(model_env or openai_model_env),
        "default_provider": REMOTE_SEMANTIC_DEFAULT_EMBEDDING_PROVIDER,
        "default_model": REMOTE_SEMANTIC_DEFAULT_EMBEDDING_MODEL,
        "query_text_sent_to_embedding_provider": query_text_sent,
        "query_text_sent_to_external_provider": query_text_sent and external_provider,
        "external_provider": external_provider,
        "warnings": warnings,
        "privacy_warning": privacy_warning,
    }


def _create_remote_semantic_query_provider():
    from .embed import create_embedding_provider

    disclosure = remote_semantic_query_provider_disclosure()
    return create_embedding_provider(provider=disclosure["provider"], model_key=disclosure["model"])


def _query_embedding_from_provider(query: str, provider: Any) -> list[float]:
    vectors = provider.encode([query])
    if not vectors:
        raise RuntimeError("embedding provider returned no vectors")
    vector = [float(value) for value in vectors[0]]
    if len(vector) != REMOTE_SEMANTIC_VECTOR_DIMENSION:
        raise RuntimeError(
            f"central semantic search expects {REMOTE_SEMANTIC_VECTOR_DIMENSION} dimensions, got {len(vector)}"
        )
    return vector


def _remote_semantic_search_result(row: dict, *, compact: bool = True) -> dict:
    read_handle = row.get("read_handle") or row.get("memory_key")
    item = {
        "memory_key": row.get("memory_key"),
        "revision": row.get("revision"),
        "similarity": row.get("similarity"),
        "title": row.get("title"),
        "summary": row.get("summary"),
        "category": row.get("category"),
        "tags": row.get("tags"),
        "scope": row.get("scope"),
        "sensitivity": row.get("sensitivity"),
        "read_handle": read_handle,
        "recommended_next_tool": "vault_remote_snapshot_read",
    }
    if read_handle:
        item["next_action"] = {
            "tool": "vault_remote_snapshot_read",
            "arguments": {"read_handle": read_handle, "compact": True},
        }
    if compact:
        keep = {
            "memory_key",
            "revision",
            "similarity",
            "title",
            "summary",
            "scope",
            "sensitivity",
            "read_handle",
            "recommended_next_tool",
            "next_action",
        }
        item = {key: value for key, value in item.items() if key in keep}
    return {key: value for key, value in item.items() if value is not None}


def _vault_remote_semantic_search_payload(
    query: str = "",
    *,
    agent_id: str = "",
    project_id: str = "",
    max_sensitivity: str = "medium",
    limit: int = 10,
    min_similarity: float = 0.0,
    compact: bool = True,
    sb_client=None,
    embedding_provider=None,
    query_embedding: list[float] | None = None,
) -> dict:
    limit = _clamp_int(limit, default=10, minimum=1, maximum=MCP_SEARCH_MAX_LIMIT)
    query = str(query or "").strip()
    provider_disclosure = remote_semantic_query_provider_disclosure(
        query_embedding_precomputed=query_embedding is not None
    )
    if not query:
        return _remote_error(
            "remote_semantic_query_required",
            "query is required for central semantic search.",
        )

    sb_client = sb_client or _get_supabase_client()
    if sb_client is None:
        return _remote_error(
            "remote_client_missing",
            "SUPABASE_URL and SUPABASE_ANON_KEY/SUPABASE_KEY are required for remote semantic search.",
        )

    if query_embedding is None:
        try:
            provider = embedding_provider or _create_remote_semantic_query_provider()
            query_embedding = _query_embedding_from_provider(query, provider)
        except Exception as exc:
            return _remote_error(
                "remote_semantic_embedding_failed",
                "Unable to create a query embedding for central semantic search.",
                detail=_remote_doctor_safe_detail(exc),
                next_action={
                    "tool": "vault_remote_search",
                    "arguments": {"query": query, "agent_id": agent_id, "max_sensitivity": max_sensitivity},
                },
            )
    elif len(query_embedding) != REMOTE_SEMANTIC_VECTOR_DIMENSION:
        return _remote_error(
            "remote_semantic_embedding_dimension_mismatch",
            f"query_embedding must be {REMOTE_SEMANTIC_VECTOR_DIMENSION} dimensions.",
        )

    try:
        min_similarity = float(min_similarity)
    except (TypeError, ValueError):
        min_similarity = 0.0

    params = {
        "p_agent_id": str(agent_id or ""),
        "p_query_embedding": _pgvector_literal(query_embedding),
        "p_project_id": str(project_id or "") or None,
        "p_match_count": limit,
        "p_max_sensitivity": str(max_sensitivity or "medium"),
        "p_min_similarity": max(0.0, min(min_similarity, 1.0)),
    }
    try:
        rows = _supabase_rpc(sb_client, REMOTE_SEMANTIC_SEARCH_RPC, params)
    except Exception:
        return _remote_error(
            "remote_semantic_search_failed",
            "Unable to call Supabase RPC vault_match_readable_memory_embeddings. Apply supabase/migrations/20260708_central_vector_index.sql first, then retry.",
            next_action={
                "tool": "vault_remote_search",
                "arguments": {"query": query, "agent_id": agent_id, "max_sensitivity": max_sensitivity},
            },
        )

    return {
        "source": "supabase",
        "rpc": REMOTE_SEMANTIC_SEARCH_RPC,
        "query": query,
        "project_id": str(project_id or ""),
        "count": len(rows),
        "result_type": "safe_semantic_preview",
        "safety": {
            "returns_raw_memory_content": False,
            "returns_embedding_values": False,
            "candidate_first": True,
            "query_text_sent_to_embedding_provider": provider_disclosure["query_text_sent_to_embedding_provider"],
            "query_embedding_provider": provider_disclosure["provider"],
            "query_embedding_model": provider_disclosure["model"],
            "query_text_sent_to_external_provider": provider_disclosure["query_text_sent_to_external_provider"],
            "query_provider_privacy_warnings": provider_disclosure["warnings"],
        },
        "results": [
            _remote_semantic_search_result(row, compact=compact)
            for row in rows
        ],
    }


def _remote_snapshot_read_result(row: dict, *, compact: bool = True) -> dict:
    item = {
        "memory_key": row.get("memory_key"),
        "revision": row.get("revision"),
        "title": row.get("title"),
        "summary": row.get("summary"),
        "content_preview": row.get("content_preview"),
        "content_source": row.get("content_source"),
        "truncated": row.get("truncated"),
        "max_chars": row.get("max_chars"),
        "category": row.get("category"),
        "tags": row.get("tags"),
        "scope": row.get("scope"),
        "sensitivity": row.get("sensitivity"),
        "content_hash": row.get("content_hash"),
        "updated_at": row.get("updated_at"),
    }
    if compact:
        keep = {
            "memory_key",
            "revision",
            "title",
            "content_preview",
            "content_source",
            "truncated",
            "scope",
            "sensitivity",
        }
        item = {key: value for key, value in item.items() if key in keep}
    return {key: value for key, value in item.items() if value is not None}


def _vault_remote_snapshot_read_payload(
    read_handle: str = "",
    *,
    agent_id: str = "",
    project_id: str = "",
    max_sensitivity: str = "medium",
    max_chars: int = 2000,
    compact: bool = True,
    sb_client=None,
) -> dict:
    read_handle = str(read_handle or "").strip()
    if not read_handle:
        return _remote_error(
            "remote_snapshot_read_handle_required",
            "read_handle is required for central snapshot reads.",
        )

    max_chars = _clamp_int(max_chars, default=2000, minimum=1, maximum=8000)
    sb_client = sb_client or _get_supabase_client()
    if sb_client is None:
        return _remote_error(
            "remote_client_missing",
            "SUPABASE_URL and SUPABASE_ANON_KEY/SUPABASE_KEY are required for remote snapshot reads.",
        )

    params = {
        "p_agent_id": str(agent_id or ""),
        "p_read_handle": read_handle,
        "p_project_id": str(project_id or "") or None,
        "p_max_sensitivity": str(max_sensitivity or "medium"),
        "p_max_chars": max_chars,
    }
    try:
        rows = _supabase_rpc(sb_client, REMOTE_SNAPSHOT_READ_RPC, params)
    except Exception:
        return _remote_error(
            "remote_snapshot_read_failed",
            "Unable to call Supabase RPC vault_get_readable_memory_snapshot. Apply supabase/migrations/20260708_central_vector_index.sql first, then retry.",
            next_action={"tool": "vault_remote_semantic_search", "arguments": {"query": read_handle}},
        )
    if not rows:
        return _remote_error(
            "remote_snapshot_not_found",
            "No readable central snapshot matched this read_handle and policy filter.",
            read_handle=read_handle,
            next_action={"tool": "vault_remote_semantic_search", "arguments": {"query": read_handle}},
        )

    return {
        "source": "supabase",
        "rpc": REMOTE_SNAPSHOT_READ_RPC,
        "read_handle": read_handle,
        "result_type": "bounded_central_snapshot_preview",
        "safety": {
            "returns_embedding_values": False,
            "candidate_first": True,
            "bounded_preview": True,
        },
        "result": _remote_snapshot_read_result(rows[0], compact=compact),
    }
