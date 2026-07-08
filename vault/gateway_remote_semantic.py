"""Gateway helpers for the central semantic remote read chain."""

from __future__ import annotations

import os
from typing import Any

from .mcp_remote_semantic import (
    _vault_remote_semantic_search_payload,
    _vault_remote_snapshot_read_payload,
)
from .search_utils import validate_search_query


REMOTE_SEMANTIC_ENDPOINTS = ["/remote-semantic-search", "/remote-snapshot-read"]
REMOTE_SEMANTIC_DEFAULT_MAX_SENSITIVITY = "low"


def remote_semantic_enabled(value: Any = None) -> bool:
    if value is None:
        value = os.environ.get("VAULT_GATEWAY_REMOTE_SEMANTIC_ENABLED", "")
    return _bool_value(value, False)


def gateway_token_agent_map(value: str | dict[str, str] | None) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(token): _agent_id(agent) for token, agent in value.items() if str(token) and _agent_id(agent)}
    text = str(value or os.environ.get("VAULT_GATEWAY_TOKEN_AGENT_MAP", "") or "").strip()
    if not text:
        return {}
    if text.startswith("{"):
        try:
            import json

            raw = json.loads(text)
        except json.JSONDecodeError:
            return {}
        if isinstance(raw, dict):
            return {str(token): _agent_id(agent) for token, agent in raw.items() if str(token) and _agent_id(agent)}
        return {}
    pairs: dict[str, str] = {}
    for item in text.split(","):
        if "=" in item:
            token_text, agent = item.split("=", 1)
        elif ":" in item:
            token_text, agent = item.split(":", 1)
        else:
            continue
        token_text = token_text.strip()
        agent_id = _agent_id(agent)
        if token_text and agent_id:
            pairs[token_text] = agent_id
    return pairs


def remote_semantic_health_info(*, enabled: bool | None = None, token_agent_binding: bool = False) -> dict[str, Any]:
    enabled_flag = remote_semantic_enabled() if enabled is None else bool(enabled)
    return {
        "supported": True,
        "enabled": enabled_flag,
        "ready": enabled_flag and bool(token_agent_binding),
        "semantic_search_endpoint": "/remote-semantic-search",
        "snapshot_read_endpoint": "/remote-snapshot-read",
        "source_of_truth": "trusted_sync_host_reviewed_snapshots",
        "writes_active_knowledge": False,
        "candidate_first_writes": True,
        "returns_embedding_values": False,
        "query_embedding_provider_required": True,
        "token_agent_binding_required": True,
        "token_agent_binding_configured": bool(token_agent_binding),
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
                "responses": {
                    "200": {"description": "Safe semantic preview rows with read handles"},
                    "403": {"description": "Disabled or missing per-agent token binding"},
                },
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
                "responses": {
                    "200": {"description": "Bounded approved snapshot preview"},
                    "403": {"description": "Disabled or missing per-agent token binding"},
                },
            }
        },
    }


def remote_semantic_openapi_schemas(max_query_chars: int) -> dict[str, Any]:
    return {
        "RemoteSemanticSearchRequest": {
            "type": "object",
            "required": ["agent_id", "query", "project_id"],
            "properties": {
                "agent_id": {"type": "string"},
                "query": {"type": "string", "maxLength": max_query_chars},
                "project_id": {"type": "string"},
                "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                "max_sensitivity": {"type": "string", "default": REMOTE_SEMANTIC_DEFAULT_MAX_SENSITIVITY},
                "min_similarity": {"type": "number", "default": 0.0, "minimum": 0.0, "maximum": 1.0},
                "allow_global_public": {"type": "boolean", "default": False},
                "compact": {"type": "boolean", "default": True},
            },
        },
        "RemoteSnapshotReadRequest": {
            "type": "object",
            "required": ["agent_id", "read_handle", "project_id"],
            "properties": {
                "agent_id": {"type": "string"},
                "read_handle": {"type": "string"},
                "project_id": {"type": "string"},
                "max_sensitivity": {"type": "string", "default": REMOTE_SEMANTIC_DEFAULT_MAX_SENSITIVITY},
                "max_chars": {"type": "integer", "default": 2000, "minimum": 1, "maximum": 8000},
                "allow_global_public": {"type": "boolean", "default": False},
                "compact": {"type": "boolean", "default": True},
            },
        },
    }


def remote_semantic_safety_flags() -> dict[str, Any]:
    return {
        "central_semantic_read": True,
        "remote_semantic_supported": True,
        "remote_semantic_enabled_by_default": False,
        "remote_semantic_requires_token_agent_binding": True,
        "remote_semantic_query_sent_to_embedding_provider": True,
        "remote_semantic_search_returns_raw_content": False,
        "remote_semantic_search_returns_embedding_values": False,
        "remote_snapshot_read_bounded": True,
    }


def gateway_remote_semantic_search(
    *,
    query: str,
    agent_id: str,
    project_id: str = "",
    max_sensitivity: str = REMOTE_SEMANTIC_DEFAULT_MAX_SENSITIVITY,
    limit: int = 10,
    min_similarity: float = 0.0,
    allow_global_public: bool = False,
    compact: bool = True,
) -> dict[str, Any]:
    """Search the central semantic read layer through Gateway's HTTP contract."""
    agent = _agent_id(agent_id)
    if not agent:
        return _error("agent_id_required", "Gateway remote semantic search requires agent_id")
    query_text, query_error = validate_search_query(query)
    if query_error:
        return query_error
    project_id = str(project_id or "").strip()
    if not project_id and not allow_global_public:
        return _error(
            "remote_semantic_project_id_required",
            "project_id is required for Gateway remote semantic search unless allow_global_public=true.",
        )
    payload = _vault_remote_semantic_search_payload(
        query_text,
        agent_id=agent,
        project_id=project_id,
        max_sensitivity=max_sensitivity or REMOTE_SEMANTIC_DEFAULT_MAX_SENSITIVITY,
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
    max_sensitivity: str = REMOTE_SEMANTIC_DEFAULT_MAX_SENSITIVITY,
    max_chars: int = 2000,
    allow_global_public: bool = False,
    compact: bool = True,
) -> dict[str, Any]:
    """Read a bounded central snapshot preview through Gateway's HTTP contract."""
    agent = _agent_id(agent_id)
    if not agent:
        return _error("agent_id_required", "Gateway remote snapshot read requires agent_id")
    project_id = str(project_id or "").strip()
    if not project_id and not allow_global_public:
        return _error(
            "remote_semantic_project_id_required",
            "project_id is required for Gateway remote snapshot reads unless allow_global_public=true.",
        )
    payload = _vault_remote_snapshot_read_payload(
        read_handle,
        agent_id=agent,
        project_id=project_id,
        max_sensitivity=max_sensitivity or REMOTE_SEMANTIC_DEFAULT_MAX_SENSITIVITY,
        max_chars=max_chars,
        compact=compact,
    )
    _mark_gateway_safe(payload, agent, raw_content=None, bounded_preview=True)
    return payload


def gateway_remote_semantic_post(path: str, body: dict[str, Any], agent: str, *, enabled: bool) -> tuple[str, dict, dict] | None:
    if path in REMOTE_SEMANTIC_ENDPOINTS and not enabled:
        return "remote_semantic_disabled", _error(
            "remote_semantic_disabled",
            "Gateway remote semantic read is disabled. Set VAULT_GATEWAY_REMOTE_SEMANTIC_ENABLED=1 on a trusted Gateway host.",
            status="blocked",
        ), {}
    if path == "/remote-semantic-search":
        query = str(body.get("query", ""))
        payload = gateway_remote_semantic_search(
            query=query,
            agent_id=agent,
            project_id=str(body.get("project_id", "") or ""),
            limit=_int_value(body.get("limit"), 10),
            max_sensitivity=str(body.get("max_sensitivity", REMOTE_SEMANTIC_DEFAULT_MAX_SENSITIVITY) or REMOTE_SEMANTIC_DEFAULT_MAX_SENSITIVITY),
            min_similarity=_float_value(body.get("min_similarity"), 0.0),
            allow_global_public=_bool_value(body.get("allow_global_public"), False),
            compact=_bool_value(body.get("compact"), True),
        )
        return "remote_semantic_search", payload, {
            "query_chars": len(query),
            "count": payload.get("count", 0),
        }
    if path == "/remote-snapshot-read":
        read_handle = str(body.get("read_handle", ""))
        payload = gateway_remote_snapshot_read(
            read_handle=read_handle,
            agent_id=agent,
            project_id=str(body.get("project_id", "") or ""),
            max_sensitivity=str(body.get("max_sensitivity", REMOTE_SEMANTIC_DEFAULT_MAX_SENSITIVITY) or REMOTE_SEMANTIC_DEFAULT_MAX_SENSITIVITY),
            max_chars=_int_value(body.get("max_chars"), 2000),
            allow_global_public=_bool_value(body.get("allow_global_public"), False),
            compact=_bool_value(body.get("compact"), True),
        )
        return "remote_snapshot_read", payload, {"read_handle": read_handle}
    return None


def gateway_remote_semantic_authorized_post(
    path: str,
    body: dict[str, Any],
    requested_agent: str,
    *,
    presented_token: str,
    token_agents: dict[str, str],
    enabled: bool,
) -> tuple[str, dict, dict, int] | None:
    if path not in REMOTE_SEMANTIC_ENDPOINTS:
        return None
    if not enabled:
        event_payload = gateway_remote_semantic_post(path, body, requested_agent, enabled=False)
        if event_payload is None:
            return None
        event, payload, extra = event_payload
        return event, payload, extra, 403
    bound_agent = _agent_id(token_agents.get(str(presented_token or ""), ""))
    if not bound_agent:
        return "remote_semantic_blocked", _error(
            "agent_token_binding_required",
            "Gateway remote semantic read requires a per-agent token binding.",
            status="blocked",
        ), {"reason": "agent_token_binding_required"}, 403
    requested_agent = _agent_id(requested_agent)
    if requested_agent and requested_agent != bound_agent:
        return "remote_semantic_blocked", _error(
            "agent_token_mismatch",
            "The request agent_id does not match the Gateway token binding.",
            status="blocked",
        ), {"reason": "agent_token_mismatch"}, 403
    event_payload = gateway_remote_semantic_post(path, body, bound_agent, enabled=True)
    if event_payload is None:
        return None
    event, payload, extra = event_payload
    return event, payload, extra, 200


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
            "query_sent_to_embedding_provider": raw_content is False,
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
    if code == "remote_semantic_project_id_required":
        payload["next_action"] = "Pass project_id for the current Vault project, or explicitly set allow_global_public=true for public-only global search."
    if code == "remote_semantic_disabled":
        payload["next_action"] = "Enable remote semantic read only after configuring per-agent Gateway token binding."
    if code == "agent_token_binding_required":
        payload["next_action"] = "Set VAULT_GATEWAY_TOKEN_AGENT_MAP or pass --token-agent-map with per-agent tokens."
    if code == "agent_token_mismatch":
        payload["next_action"] = "Use the token's bound agent_id or omit agent_id and let Gateway derive it from the token."
    return payload
