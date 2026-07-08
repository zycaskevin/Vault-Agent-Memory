"""Gateway helpers for the central semantic remote read chain."""

from __future__ import annotations

from typing import Any

from .mcp_remote_semantic import (
    _vault_remote_semantic_search_payload,
    _vault_remote_snapshot_read_payload,
)
from .search_utils import validate_search_query


REMOTE_SEMANTIC_ENDPOINTS = ["/remote-semantic-search", "/remote-snapshot-read"]


def remote_semantic_health_info() -> dict[str, Any]:
    return {
        "enabled": True,
        "semantic_search_endpoint": "/remote-semantic-search",
        "snapshot_read_endpoint": "/remote-snapshot-read",
        "source_of_truth": "trusted_sync_host_reviewed_snapshots",
        "writes_active_knowledge": False,
        "candidate_first_writes": True,
        "returns_embedding_values": False,
    }


def remote_semantic_openapi_paths() -> dict[str, Any]:
    return {
        "/remote-semantic-search": {
            "post": {
                "summary": "Search the central derived vector read layer and return safe previews only.",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/RemoteSemanticSearchRequest"}
                        }
                    }
                },
                "responses": {"200": {"description": "Safe semantic preview rows with read handles"}},
            }
        },
        "/remote-snapshot-read": {
            "post": {
                "summary": "Read a bounded preview from an approved central snapshot read handle.",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/RemoteSnapshotReadRequest"}
                        }
                    }
                },
                "responses": {"200": {"description": "Bounded approved snapshot preview"}},
            }
        },
    }


def remote_semantic_openapi_schemas(max_query_chars: int) -> dict[str, Any]:
    return {
        "RemoteSemanticSearchRequest": {
            "type": "object",
            "required": ["agent_id", "query"],
            "properties": {
                "agent_id": {"type": "string"},
                "query": {"type": "string", "maxLength": max_query_chars},
                "project_id": {"type": "string"},
                "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                "max_sensitivity": {"type": "string", "default": "medium"},
                "min_similarity": {"type": "number", "default": 0.0, "minimum": 0.0, "maximum": 1.0},
                "compact": {"type": "boolean", "default": True},
            },
        },
        "RemoteSnapshotReadRequest": {
            "type": "object",
            "required": ["agent_id", "read_handle"],
            "properties": {
                "agent_id": {"type": "string"},
                "read_handle": {"type": "string"},
                "project_id": {"type": "string"},
                "max_sensitivity": {"type": "string", "default": "medium"},
                "max_chars": {"type": "integer", "default": 2000, "minimum": 1, "maximum": 8000},
                "compact": {"type": "boolean", "default": True},
            },
        },
    }


def remote_semantic_safety_flags() -> dict[str, Any]:
    return {
        "central_semantic_read": True,
        "remote_semantic_search_returns_raw_content": False,
        "remote_semantic_search_returns_embedding_values": False,
        "remote_snapshot_read_bounded": True,
    }


def gateway_remote_semantic_search(
    *,
    query: str,
    agent_id: str,
    project_id: str = "",
    max_sensitivity: str = "medium",
    limit: int = 10,
    min_similarity: float = 0.0,
    compact: bool = True,
) -> dict[str, Any]:
    """Search the central semantic read layer through Gateway's HTTP contract."""
    agent = _agent_id(agent_id)
    if not agent:
        return _error("agent_id_required", "Gateway remote semantic search requires agent_id")
    query_text, query_error = validate_search_query(query)
    if query_error:
        return query_error
    payload = _vault_remote_semantic_search_payload(
        query_text,
        agent_id=agent,
        project_id=str(project_id or ""),
        max_sensitivity=max_sensitivity or "medium",
        limit=limit,
        min_similarity=min_similarity,
        compact=compact,
    )
    _mark_gateway_safe(payload, agent, raw_content=False, bounded_preview=False)
    return payload


def gateway_remote_snapshot_read(
    *,
    read_handle: str,
    agent_id: str,
    project_id: str = "",
    max_sensitivity: str = "medium",
    max_chars: int = 2000,
    compact: bool = True,
) -> dict[str, Any]:
    """Read a bounded central snapshot preview through Gateway's HTTP contract."""
    agent = _agent_id(agent_id)
    if not agent:
        return _error("agent_id_required", "Gateway remote snapshot read requires agent_id")
    payload = _vault_remote_snapshot_read_payload(
        read_handle,
        agent_id=agent,
        project_id=str(project_id or ""),
        max_sensitivity=max_sensitivity or "medium",
        max_chars=max_chars,
        compact=compact,
    )
    _mark_gateway_safe(payload, agent, raw_content=None, bounded_preview=True)
    return payload


def gateway_remote_semantic_post(path: str, body: dict[str, Any], agent: str) -> tuple[str, dict, dict] | None:
    if path == "/remote-semantic-search":
        payload = gateway_remote_semantic_search(
            query=str(body.get("query", "")),
            agent_id=agent,
            project_id=str(body.get("project_id", "") or ""),
            limit=_int_value(body.get("limit"), 10),
            max_sensitivity=str(body.get("max_sensitivity", "medium") or "medium"),
            min_similarity=_float_value(body.get("min_similarity"), 0.0),
            compact=_bool_value(body.get("compact"), True),
        )
        return "remote_semantic_search", payload, {
            "query": str(body.get("query", "")),
            "count": payload.get("count", 0),
        }
    if path == "/remote-snapshot-read":
        read_handle = str(body.get("read_handle", ""))
        payload = gateway_remote_snapshot_read(
            read_handle=read_handle,
            agent_id=agent,
            project_id=str(body.get("project_id", "") or ""),
            max_sensitivity=str(body.get("max_sensitivity", "medium") or "medium"),
            max_chars=_int_value(body.get("max_chars"), 2000),
            compact=_bool_value(body.get("compact"), True),
        )
        return "remote_snapshot_read", payload, {"read_handle": read_handle}
    return None


def _mark_gateway_safe(
    payload: dict[str, Any],
    agent: str,
    *,
    raw_content: bool | None,
    bounded_preview: bool,
) -> None:
    payload["agent_id"] = agent
    payload.setdefault("safety", {})
    payload["safety"].update(
        {
            "gateway_adapter": True,
            "writes_active_knowledge": False,
            "returns_embedding_values": False,
        }
    )
    if raw_content is not None:
        payload["safety"]["returns_raw_memory_content"] = raw_content
    if bounded_preview:
        payload["safety"]["bounded_preview"] = True


def _agent_id(value: Any) -> str:
    return str(value or "").strip().lower()


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
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _error(code: str, message: str, *, status: str = "error") -> dict[str, Any]:
    payload = {"status": status, "error": code, "message": message}
    if code == "agent_id_required":
        payload["next_action"] = "Pass a stable agent_id so Gateway can apply read policy."
    return payload
