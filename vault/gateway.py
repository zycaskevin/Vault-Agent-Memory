"""Thin local/remote HTTP gateway for agent memory access."""

from __future__ import annotations

from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import secrets
import signal
import ssl
import threading
from typing import Any
from urllib.parse import parse_qs, urlparse

from .access_policy import can_write_memory, normalize_write_policy
from .central_candidate_store import central_candidate_inbox_status
from .db import VaultDB
from .gateway_central_candidates import (
    gateway_pull_central_candidates,
    gateway_submit_central_candidate,
)
from .gateway_errors import gateway_error_suggestions
from .gateway_security import GatewaySecurityPolicy, GatewaySecurityState
from .gateway_server import (
    DEFAULT_GATEWAY_MAX_WORKERS,
    DEFAULT_GATEWAY_SHUTDOWN_TIMEOUT_SECONDS,
    BoundedThreadPoolHTTPServer,
)
from .gateway_openapi import (
    DEFAULT_GATEWAY_AUDIT_BACKUPS,
    DEFAULT_GATEWAY_AUDIT_MAX_BYTES,
    DEFAULT_GATEWAY_HOST,
    DEFAULT_GATEWAY_PORT,
    GATEWAY_CONTRACT_VERSION,
    GATEWAY_ENDPOINTS,
    gateway_openapi,
)
from .gateway_memory_api import (
    gateway_memory_audit,
    gateway_memory_create,
    gateway_memory_delete_request,
    gateway_memory_get,
    gateway_memory_http_delete,
    gateway_memory_http_get,
    gateway_memory_http_patch,
    gateway_memory_http_post,
    gateway_memory_search,
    gateway_memory_timeline,
    gateway_memory_update_request,
)
from . import gateway_remote_semantic as remote_semantic
from .gateway_remote_server import mark_remote_server_payload, remote_server_metadata
from .governance_contract import governance_contract_payload
from .gui_format import compact_knowledge
from .mcp_read import _vault_read_range_payload
from .memory import create_candidate
from .search import VaultSearch
from .search_utils import normalize_search_limit, validate_search_query


LOCALHOSTS = {"127.0.0.1", "localhost", "::1"}


def gateway_health(
    project_dir: str | Path,
    *,
    remote_semantic_enabled: bool | None = None,
    token_agent_map: str | dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return a compact readiness payload for agents."""
    project = Path(project_dir).expanduser().resolve()
    db_path = project / "vault.db"
    token_agents = remote_semantic.gateway_token_agent_map(token_agent_map)
    stats: dict[str, Any] = {}
    if db_path.exists():
        try:
            with VaultDB(db_path) as db:
                stats = db.stats()
        except Exception:
            stats = {}
    payload = {
        "status": "ok" if db_path.exists() else "blocked",
        "project_dir": str(project),
        "db_exists": db_path.exists(),
        "stats": stats,
        "gateway": {
            "contract_version": GATEWAY_CONTRACT_VERSION,
            "role": "unified_agent_memory_entrypoint",
            "transport": "http_json",
            "tls_supported": True,
            "source_of_truth": "local_sqlite_vault",
            "adapter_boundary": True,
            "governance_contract": governance_contract_payload(adapter="gateway"),
            "writes_active_knowledge": False,
            "candidate_first_writes": True,
            "central_candidate_inbox": True,
            "vault_memory_api": {
                "status": "facade",
                "additive": True,
                "legacy_gateway_endpoints_preserved": True,
                "update_writes_active_knowledge": False,
                "delete_hard_deletes": False,
                "delete_submits_review_candidate": True,
            },
            "central_semantic_read": remote_semantic.remote_semantic_health_info(
                enabled=remote_semantic_enabled,
                token_agent_binding=bool(token_agents),
            ),
            "default_read_max_sensitivity": "low",
            "default_include_private": False,
            "max_workers_supported": True,
            "default_max_workers": DEFAULT_GATEWAY_MAX_WORKERS,
            "graceful_shutdown_supported": True,
            "default_shutdown_timeout_seconds": DEFAULT_GATEWAY_SHUTDOWN_TIMEOUT_SECONDS,
            "audit_rotation": {
                "supported": True,
                "default_max_bytes": DEFAULT_GATEWAY_AUDIT_MAX_BYTES,
                "default_backups": DEFAULT_GATEWAY_AUDIT_BACKUPS,
            },
            "openapi": "/openapi.json",
            "endpoints": GATEWAY_ENDPOINTS,
            "remote_ready": {
                "same_machine_agents": True,
                "cross_host_agents": "supported_when_bound_to_a_network_host_with_token_auth",
                "supabase_adapter": "optional_separate_adapter",
                "self_hosted_central_candidate_inbox": True,
                "active_multi_master_sync": False,
            },
        },
    }
    if not db_path.exists():
        payload["try"] = [
            f"vault init --project-dir {project}",
            f"vault compile --project-dir {project} --no-embed",
        ]
        payload["next_action"] = "Initialize this project vault before starting Gateway clients."
    return payload


def gateway_search(
    project_dir: str | Path,
    *,
    query: str,
    agent_id: str,
    mode: str = "keyword",
    limit: int = 10,
    include_private: bool = False,
    max_sensitivity: str = "low",
) -> dict[str, Any]:
    """Search active memory through an explicit agent read policy."""
    project = Path(project_dir)
    db_path = project / "vault.db"
    agent = _agent_id(agent_id)
    limit_i = normalize_search_limit(limit, default=10, maximum=50)
    if not db_path.exists():
        return _error("db_not_found", "vault.db missing", status="blocked")
    if not agent:
        return _error("agent_id_required", "Gateway search requires agent_id")
    query_text, query_error = validate_search_query(query)
    if query_error:
        return query_error
    if not query_text.strip() or limit_i <= 0:
        return {"status": "ok", "query": query_text, "mode": mode, "results": []}
    if mode not in {"auto", "keyword", "semantic", "hybrid", "vector"}:
        mode = "keyword"
    with VaultDB(db_path) as db:
        search = VaultSearch(db, embed_provider=None, embed_provider_name="none")
        rows = search.search(
            query_text,
            mode=mode,
            limit=limit_i,
            use_rerank=False,
            compact=False,
            include_snippet=True,
            fields=[
                "id",
                "title",
                "category",
                "layer",
                "trust",
                "summary",
                "tags",
                "source",
                "scope",
                "sensitivity",
                "owner_agent",
                "memory_type",
                "valid_from",
                "valid_until",
                "expires_at",
                "line_start",
                "line_end",
                "best_span",
                "_score",
                "_snippet",
            ],
            agent_id=agent,
            include_private=include_private,
            max_sensitivity=max_sensitivity or "low",
        )
    return {
        "status": "ok",
        "query": query_text,
        "mode": mode,
        "agent_id": agent,
        "results": [compact_knowledge(row) for row in rows],
        "safety": {
            "read_policy_active": True,
            "include_private": bool(include_private),
            "max_sensitivity": max_sensitivity or "low",
            "content_hidden_by_default": True,
        },
    }


def gateway_read_range(
    project_dir: str | Path,
    *,
    knowledge_id: int,
    agent_id: str,
    line_start: int = 1,
    line_end: int = 40,
    node_uid: str = "",
    max_lines: int = 80,
    include_private: bool = False,
    max_sensitivity: str = "low",
) -> dict[str, Any]:
    """Read bounded evidence through the same policy as MCP read_range."""
    project = Path(project_dir)
    db_path = project / "vault.db"
    agent = _agent_id(agent_id)
    if not db_path.exists():
        return _error("db_not_found", "vault.db missing", status="blocked")
    if not agent:
        return _error("agent_id_required", "Gateway read-range requires agent_id")
    payload = _vault_read_range_payload(
        knowledge_id,
        node_uid=node_uid,
        line_start=line_start,
        line_end=line_end,
        max_lines=max_lines,
        agent_id=agent,
        include_private=include_private,
        max_sensitivity=max_sensitivity or "low",
        db_path=str(db_path),
    )
    if "error" in payload and "status" not in payload:
        payload["status"] = "error"
    else:
        payload["status"] = "ok"
    payload["agent_id"] = agent
    payload["safety"] = {
        "bounded_read": True,
        "include_private": bool(include_private),
        "max_sensitivity": max_sensitivity or "low",
    }
    return payload


def gateway_submit_candidate(
    project_dir: str | Path,
    *,
    title: str,
    content: str,
    agent_id: str,
    reason: str = "",
    layer: str = "L3",
    category: str = "general",
    tags: str = "",
    trust: float = 0.5,
    scope: str = "project",
    sensitivity: str = "low",
    owner_agent: str = "",
    allowed_agents: str = "",
    memory_type: str = "knowledge",
    source_ref: str = "",
    allow_shared_candidates: bool = False,
    allow_private_candidates: bool = False,
    allow_high_sensitivity_candidates: bool = False,
    allow_restricted_candidates: bool = False,
) -> dict[str, Any]:
    """Write an agent proposal into memory_candidates, never active knowledge."""
    project = Path(project_dir)
    db_path = project / "vault.db"
    agent = _agent_id(agent_id)
    if not db_path.exists():
        return _error("db_not_found", "vault.db missing", status="blocked")
    if not agent:
        return _error("agent_id_required", "Gateway candidate submit requires agent_id")
    meta = {
        "title": str(title or "").strip(),
        "content": str(content or "").strip(),
        "layer": layer or "L3",
        "category": category or "general",
        "tags": tags or "",
        "trust": trust,
        "source": f"gateway:{agent}",
        "source_ref": source_ref or f"gateway:{agent}",
        "reason": reason or "Submitted through Vault Gateway; review before promotion.",
        "scope": scope or "project",
        "sensitivity": sensitivity or "low",
        "owner_agent": owner_agent or agent,
        "allowed_agents": allowed_agents or "",
        "memory_type": memory_type or "knowledge",
    }
    allowed, why = can_write_memory(
        meta,
        normalize_write_policy(
            agent_id=agent,
            allow_shared=allow_shared_candidates,
            allow_private=allow_private_candidates,
            allow_high_sensitivity=allow_high_sensitivity_candidates,
            allow_restricted=allow_restricted_candidates,
        ),
    )
    if not allowed:
        return _error("access_denied", why)
    with VaultDB(db_path) as db:
        result = create_candidate(db, **meta)
    return {
        "status": "ok" if result.get("status") != "rejected" else "rejected",
        "candidate": result,
        "safety": {
            "candidate_first": True,
            "writes_active_knowledge": False,
            "requires_review_before_promotion": True,
            "governance_contract": governance_contract_payload(adapter="gateway_submit_candidate"),
        },
    }


def make_gateway_handler(
    project_dir: str | Path,
    *,
    auth_token: str = "",
    security_policy: GatewaySecurityPolicy | None = None,
    tls_enabled: bool = False,
    allow_shared_candidates: bool = False,
    allow_private_candidates: bool = False,
    allow_high_sensitivity_candidates: bool = False,
    allow_restricted_candidates: bool = False,
    token_agent_map: str | dict[str, str] | None = None,
    remote_semantic_enabled: bool | None = None,
):
    """Create a small JSON HTTP handler for the Gateway."""
    project = Path(project_dir).expanduser().resolve()
    token = str(auth_token or "")
    security = GatewaySecurityState(security_policy)
    token_agents = remote_semantic.gateway_token_agent_map(token_agent_map)
    semantic_enabled = remote_semantic.remote_semantic_enabled(remote_semantic_enabled)

    class VaultGatewayHandler(BaseHTTPRequestHandler):
        server_version = "VaultGateway/0.1"

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            parsed = urlparse(self.path)
            guard = self._transport_guard(parsed)
            if guard is not None:
                self._send_json(guard[0], status=guard[1])
                return
            if not self._is_authorized(parsed):
                self._send_unauthorized(parsed)
                return
            security.record_auth_success(self._client_ip())
            if parsed.path == "/health":
                payload = gateway_health(project)
                payload["gateway"]["transport"] = "https_json" if tls_enabled else "http_json"
                payload["gateway"]["tls_enabled"] = bool(tls_enabled)
                payload["gateway"]["security"] = security.status()
                payload["gateway"]["central_semantic_read"] = remote_semantic.remote_semantic_health_info(
                    enabled=semantic_enabled,
                    token_agent_binding=bool(token_agents),
                )
                _append_audit(project, "health", _request_agent({}, parsed), payload.get("status", "ok"), **self._audit_context(parsed))
                self._send_json(payload)
                return
            if parsed.path == "/openapi.json":
                payload = gateway_openapi()
                _append_audit(project, "openapi", _request_agent({}, parsed), "ok", **self._audit_context(parsed))
                self._send_json(payload)
                return
            if parsed.path == "/central-candidates/status":
                payload = central_candidate_inbox_status(project)
                _append_audit(
                    project,
                    "central_candidates_status",
                    _request_agent({}, parsed),
                    "ok",
                    **self._audit_context(parsed),
                )
                self._send_json(payload)
                return
            memory_payload = gateway_memory_http_get(
                parsed,
                project,
                append_audit=_append_audit,
                audit_context=self._audit_context(parsed),
            )
            if memory_payload is not None:
                self._send_json(memory_payload)
                return
            self._send_json(_error("not_found", "unknown endpoint"), status=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            parsed = urlparse(self.path)
            guard = self._transport_guard(parsed)
            if guard is not None:
                self._send_json(guard[0], status=guard[1])
                return
            if not self._is_authorized(parsed):
                self._send_unauthorized(parsed)
                return
            security.record_auth_success(self._client_ip())
            body = self._read_json_body()
            agent = _request_agent(body, parsed)
            if parsed.path == "/search":
                payload = gateway_search(
                    project,
                    query=str(body.get("query", "")),
                    agent_id=agent,
                    mode=str(body.get("mode", "keyword")),
                    limit=_int_value(body.get("limit"), 10),
                    include_private=_bool_value(body.get("include_private"), False),
                    max_sensitivity=str(body.get("max_sensitivity", "low") or "low"),
                )
                _append_audit(project, "search", agent, payload.get("status", "ok"), query=str(body.get("query", "")), **self._audit_context(parsed))
                self._send_json(payload)
                return
            memory_payload = gateway_memory_http_post(
                parsed,
                project,
                body=body,
                agent_id=agent,
                append_audit=_append_audit,
                audit_context=self._audit_context(parsed),
                allow_shared_candidates=allow_shared_candidates,
                allow_private_candidates=allow_private_candidates,
                allow_high_sensitivity_candidates=allow_high_sensitivity_candidates,
                allow_restricted_candidates=allow_restricted_candidates,
            )
            if memory_payload is not None:
                self._send_json(memory_payload)
                return
            if parsed.path == "/read-range":
                payload = gateway_read_range(
                    project,
                    knowledge_id=_int_value(body.get("knowledge_id"), 0),
                    node_uid=str(body.get("node_uid", "")),
                    line_start=_int_value(body.get("line_start"), 1),
                    line_end=_int_value(body.get("line_end"), 40),
                    max_lines=_int_value(body.get("max_lines"), 80),
                    agent_id=agent,
                    include_private=_bool_value(body.get("include_private"), False),
                    max_sensitivity=str(body.get("max_sensitivity", "low") or "low"),
                )
                _append_audit(project, "read_range", agent, payload.get("status", "ok"), knowledge_id=body.get("knowledge_id", 0), **self._audit_context(parsed))
                self._send_json(payload)
                return
            if parsed.path == "/submit-candidate":
                payload = gateway_submit_candidate(
                    project,
                    title=str(body.get("title", "")),
                    content=str(body.get("content", "")),
                    agent_id=agent,
                    reason=str(body.get("reason", "")),
                    layer=str(body.get("layer", "L3") or "L3"),
                    category=str(body.get("category", "general") or "general"),
                    tags=str(body.get("tags", "") or ""),
                    trust=_float_value(body.get("trust"), 0.5),
                    scope=str(body.get("scope", "project") or "project"),
                    sensitivity=str(body.get("sensitivity", "low") or "low"),
                    owner_agent=str(body.get("owner_agent", "") or ""),
                    allowed_agents=str(body.get("allowed_agents", "") or ""),
                    memory_type=str(body.get("memory_type", "knowledge") or "knowledge"),
                    source_ref=str(body.get("source_ref", "") or ""),
                    allow_shared_candidates=allow_shared_candidates,
                    allow_private_candidates=allow_private_candidates,
                    allow_high_sensitivity_candidates=allow_high_sensitivity_candidates,
                    allow_restricted_candidates=allow_restricted_candidates,
                )
                candidate = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else {}
                _append_audit(
                    project,
                    "submit_candidate",
                    agent,
                    payload.get("status", "ok"),
                    candidate_id=candidate.get("candidate_id", ""),
                    title=str(body.get("title", "")),
                    **self._audit_context(parsed),
                )
                self._send_json(payload)
                return
            if parsed.path == "/central-candidates/submit":
                payload = gateway_submit_central_candidate(
                    project,
                    title=str(body.get("title", "")),
                    content=str(body.get("content", "")),
                    agent_id=agent,
                    reason=str(body.get("reason", "")),
                    category=str(body.get("category", "general") or "general"),
                    tags=str(body.get("tags", "") or ""),
                    trust=_float_value(body.get("trust"), 0.5),
                    scope=str(body.get("scope", "project") or "project"),
                    sensitivity=str(body.get("sensitivity", "low") or "low"),
                    owner_agent=str(body.get("owner_agent", "") or ""),
                    allowed_agents=str(body.get("allowed_agents", "") or ""),
                    memory_type=str(body.get("memory_type", "remote_candidate") or "remote_candidate"),
                    source_ref=str(body.get("source_ref", "") or ""),
                    idempotency_key=str(body.get("idempotency_key", "") or ""),
                    allow_shared_candidates=allow_shared_candidates,
                    allow_private_candidates=allow_private_candidates,
                    allow_high_sensitivity_candidates=allow_high_sensitivity_candidates,
                    allow_restricted_candidates=allow_restricted_candidates,
                )
                _append_audit(
                    project,
                    "central_candidate_submit",
                    agent,
                    payload.get("status", "ok"),
                    candidate_key=payload.get("candidate_key", ""),
                    title=str(body.get("title", "")),
                    **self._audit_context(parsed),
                )
                self._send_json(payload)
                return
            if parsed.path == "/central-candidates/pull":
                payload = gateway_pull_central_candidates(
                    project,
                    agent_id=agent,
                    limit=_int_value(body.get("limit"), 20),
                    apply=_bool_value(body.get("apply"), False),
                    require_hmac=(
                        True if _bool_value(body.get("require_hmac"), False) else None
                    ),
                )
                _append_audit(
                    project,
                    "central_candidate_pull",
                    agent,
                    "ok" if payload.get("ok") else "error",
                    count=payload.get("count", 0),
                    imported_count=payload.get("imported_count", 0),
                    apply=bool(payload.get("apply")),
                    **self._audit_context(parsed),
                )
                self._send_json(payload)
                return
            semantic_post = remote_semantic.gateway_remote_semantic_authorized_post(
                parsed.path,
                body,
                agent,
                presented_token=self._presented_token(parsed),
                token_agents=token_agents,
                enabled=semantic_enabled,
            )
            if semantic_post is not None:
                event, payload, extra, status = semantic_post
                audit_agent = str(payload.get("agent_id") or agent)
                _append_audit(project, event, audit_agent, payload.get("status", "ok"), **extra, **self._audit_context(parsed))
                self._send_json(payload, status=HTTPStatus(status))
                return
            self._send_json(_error("not_found", "unknown endpoint"), status=HTTPStatus.NOT_FOUND)

        def do_PATCH(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            parsed = urlparse(self.path)
            guard = self._transport_guard(parsed)
            if guard is not None:
                self._send_json(guard[0], status=guard[1])
                return
            if not self._is_authorized(parsed):
                self._send_unauthorized(parsed)
                return
            security.record_auth_success(self._client_ip())
            body = self._read_json_body()
            agent = _request_agent(body, parsed)
            payload = gateway_memory_http_patch(
                parsed,
                project,
                body=body,
                agent_id=agent,
                append_audit=_append_audit,
                audit_context=self._audit_context(parsed),
                allow_shared_candidates=allow_shared_candidates,
                allow_private_candidates=allow_private_candidates,
                allow_high_sensitivity_candidates=allow_high_sensitivity_candidates,
                allow_restricted_candidates=allow_restricted_candidates,
            )
            if payload is None:
                self._send_json(_error("not_found", "unknown endpoint"), status=HTTPStatus.NOT_FOUND)
                return
            self._send_json(payload)

        def do_DELETE(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            parsed = urlparse(self.path)
            guard = self._transport_guard(parsed)
            if guard is not None:
                self._send_json(guard[0], status=guard[1])
                return
            if not self._is_authorized(parsed):
                self._send_unauthorized(parsed)
                return
            security.record_auth_success(self._client_ip())
            body = self._read_json_body()
            agent = _request_agent(body, parsed)
            payload = gateway_memory_http_delete(
                parsed,
                project,
                body=body,
                agent_id=agent,
                append_audit=_append_audit,
                audit_context=self._audit_context(parsed),
                allow_shared_candidates=allow_shared_candidates,
                allow_private_candidates=allow_private_candidates,
                allow_high_sensitivity_candidates=allow_high_sensitivity_candidates,
                allow_restricted_candidates=allow_restricted_candidates,
            )
            if payload is None:
                self._send_json(_error("not_found", "unknown endpoint"), status=HTTPStatus.NOT_FOUND)
                return
            self._send_json(payload)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _is_authorized(self, parsed) -> bool:
            presented = self._presented_token(parsed)
            if presented and presented in token_agents:
                return True
            if token_agents and not token:
                return False
            if not token:
                return True
            if str(self.headers.get("X-Vault-Gateway-Token", "")) == token:
                return True
            auth = str(self.headers.get("Authorization", ""))
            if auth == f"Bearer {token}":
                return True
            query = parse_qs(parsed.query)
            return bool(query.get("token") and str(query["token"][0]) == token)

        def _transport_guard(self, parsed) -> tuple[dict[str, Any], HTTPStatus] | None:
            client_ip = self._client_ip()
            allowed, reason = security.check_ip_policy(client_ip)
            if not allowed:
                payload = _error(reason, "client IP is not allowed")
                _append_audit(project, "request_blocked", _request_agent({}, parsed), payload["status"], reason=reason, **self._audit_context(parsed))
                return payload, HTTPStatus.FORBIDDEN
            allowed, reason = security.check_auth_lockout(client_ip)
            if not allowed:
                payload = _error(reason, "too many failed authentication attempts")
                _append_audit(project, "request_blocked", _request_agent({}, parsed), payload["status"], reason=reason, **self._audit_context(parsed))
                return payload, HTTPStatus.TOO_MANY_REQUESTS
            allowed, reason = security.check_rate_limit(client_ip=client_ip, token_hint=self._presented_token(parsed))
            if not allowed:
                payload = _error(reason, "Gateway rate limit exceeded")
                _append_audit(project, "request_blocked", _request_agent({}, parsed), payload["status"], reason=reason, **self._audit_context(parsed))
                return payload, HTTPStatus.TOO_MANY_REQUESTS
            return None

        def _send_unauthorized(self, parsed) -> None:
            _ok, reason = security.record_auth_failure(self._client_ip())
            status = HTTPStatus.TOO_MANY_REQUESTS if reason == "auth_locked" else HTTPStatus.UNAUTHORIZED
            _append_audit(project, "auth_failed", _request_agent({}, parsed), "error", reason=reason, **self._audit_context(parsed))
            self._send_json(_error(reason, "valid gateway token required"), status=status)

        def _client_ip(self) -> str:
            try:
                return str(self.client_address[0] or "")
            except (AttributeError, IndexError, TypeError):
                return ""

        def _presented_token(self, parsed) -> str:
            header_token = str(self.headers.get("X-Vault-Gateway-Token", "") or "")
            if header_token:
                return header_token
            auth = str(self.headers.get("Authorization", "") or "")
            if auth.startswith("Bearer "):
                return auth.removeprefix("Bearer ").strip()
            query = parse_qs(parsed.query)
            return str((query.get("token") or [""])[0])

        def _audit_context(self, parsed) -> dict[str, Any]:
            return {
                "client_ip": self._client_ip(),
                "user_agent": str(self.headers.get("User-Agent", "") or "")[:200],
                "endpoint": parsed.path,
                "method": self.command,
            }

        def _send_json(self, payload: dict[str, Any], *, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(int(status))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            if tls_enabled:
                self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _read_json_body(self) -> dict[str, Any]:
            try:
                length = max(0, min(int(self.headers.get("Content-Length", "0")), 65_536))
            except (TypeError, ValueError):
                length = 0
            if length <= 0:
                return {}
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8")) or {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {}
            return payload if isinstance(payload, dict) else {}

    return VaultGatewayHandler


def run_gateway(
    project_dir: str | Path,
    *,
    host: str = DEFAULT_GATEWAY_HOST,
    port: int = DEFAULT_GATEWAY_PORT,
    max_workers: int = DEFAULT_GATEWAY_MAX_WORKERS,
    auth_token: str | None = None,
    no_auth: bool = False,
    security_policy: GatewaySecurityPolicy | None = None,
    tls_cert: str | Path | None = None,
    tls_key: str | Path | None = None,
    server_label: str = "Vault Gateway",
    allow_shared_candidates: bool = False,
    allow_private_candidates: bool = False,
    allow_high_sensitivity_candidates: bool = False,
    allow_restricted_candidates: bool = False,
    token_agent_map: str | dict[str, str] | None = None,
    remote_semantic_enabled: bool | None = None,
    shutdown_timeout_seconds: float | None = None,
) -> None:
    """Start the thin Gateway server and block."""
    host_text = str(host or DEFAULT_GATEWAY_HOST)
    if no_auth and host_text not in LOCALHOSTS:
        raise ValueError("--no-auth is only allowed for localhost binds")
    token = "" if no_auth else (auth_token or os.environ.get("VAULT_GATEWAY_TOKEN", "").strip() or secrets.token_urlsafe(24))
    tls_paths = _resolve_tls_paths(tls_cert, tls_key)
    handler = make_gateway_handler(
        project_dir,
        auth_token=token,
        security_policy=security_policy,
        tls_enabled=bool(tls_paths),
        allow_shared_candidates=allow_shared_candidates,
        allow_private_candidates=allow_private_candidates,
        allow_high_sensitivity_candidates=allow_high_sensitivity_candidates,
        allow_restricted_candidates=allow_restricted_candidates,
        token_agent_map=token_agent_map,
        remote_semantic_enabled=remote_semantic_enabled,
    )
    workers = _gateway_max_workers(max_workers)
    shutdown_timeout = _gateway_shutdown_timeout_seconds(shutdown_timeout_seconds)
    server = BoundedThreadPoolHTTPServer(
        (host_text, int(port)),
        handler,
        max_workers=workers,
        shutdown_timeout_seconds=shutdown_timeout,
    )
    scheme = "https" if tls_paths else "http"
    if tls_paths:
        server.socket = _wrap_gateway_tls(server.socket, certfile=tls_paths[0], keyfile=tls_paths[1])
    semantic_info = remote_semantic.remote_semantic_health_info(
        enabled=remote_semantic.remote_semantic_enabled(remote_semantic_enabled),
        token_agent_binding=bool(remote_semantic.gateway_token_agent_map(token_agent_map)),
    )
    print(f"{server_label}: {scheme}://{host_text}:{int(port)}")
    print(f"Auth: {'enabled' if token else 'disabled'}")
    print(f"TLS: {'enabled' if tls_paths else 'disabled'}")
    print(f"Max workers: {workers}")
    print(f"Shutdown drain timeout: {shutdown_timeout:g}s")
    print(f"Remote semantic read: {'enabled' if semantic_info['enabled'] else 'disabled'}")
    if semantic_info["enabled"]:
        print(
            "Remote semantic query provider: "
            f"{semantic_info['query_embedding_provider']} ({semantic_info['query_embedding_model']})"
        )
        if not semantic_info["token_agent_binding_configured"]:
            print("REMOTE SEMANTIC CHECK: configure one token-agent binding per remote agent.")
        if semantic_info.get("privacy_warning"):
            print(f"PRIVACY: {semantic_info['privacy_warning']}")
    if token:
        print("SECURITY: copy this token only into trusted local agent configuration.")
        print(f"Token: {token}")
        print("SECURITY: store long-lived remote-server tokens in environment variables or a secret manager.")
    if host_text not in LOCALHOSTS:
        print("REMOTE CHECKLIST: use TLS or a trusted reverse proxy, keep auth enabled, restrict firewall/IP access, and review reports/gateway/audit.jsonl.")
    print(f"Project: {Path(project_dir).expanduser().resolve()}")
    print("Press Ctrl+C to stop.")
    stop_signal = {"name": ""}
    previous_handlers = _install_gateway_signal_handlers(server, stop_signal)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        stop_signal["name"] = stop_signal["name"] or "KeyboardInterrupt"
    finally:
        if previous_handlers:
            _restore_gateway_signal_handlers(previous_handlers)
        reason = stop_signal["name"] or "shutdown"
        print(f"\nDraining {server_label} ({reason}): no new requests; waiting for active requests.")
        begin = getattr(server, "begin_draining", None)
        if callable(begin):
            begin()
        wait = getattr(server, "wait_for_active_requests", None)
        completed = bool(wait(timeout=shutdown_timeout)) if callable(wait) else True
        if completed:
            print(f"{server_label} drain complete.")
        else:
            active = getattr(server, "active_requests", 0)
            print(
                f"{server_label} drain timeout after {shutdown_timeout:g}s; "
                f"{active} request(s) still active."
            )
        server.server_close()


def cmd_gateway(args: Any) -> None:
    from .cli_context import _arg_value, _json_print, find_project_dir

    action = str(getattr(args, "gateway_action", "") or "")
    profile = str(getattr(args, "gateway_profile", "gateway") or "gateway")
    if action == "health":
        payload = gateway_health(
            find_project_dir(),
            remote_semantic_enabled=getattr(args, "remote_semantic", None),
            token_agent_map=getattr(args, "token_agent_map", None),
        )
        if profile == "remote_server":
            mark_remote_server_payload(payload)
        payload.setdefault("ok", payload.get("status") == "ok")
        _json_print(payload, pretty=_arg_value(args, "pretty", False) is True)
        return
    if action == "openapi":
        payload = gateway_openapi(title="Vault Remote Server" if profile == "remote_server" else "Vault Gateway")
        if profile == "remote_server":
            payload["x-vault-remote-server"] = remote_server_metadata()
        payload.setdefault("ok", True)
        _json_print(payload, pretty=_arg_value(args, "pretty", False) is True)
        return
    if action == "audit":
        from .gateway_audit import gateway_audit_report

        payload = gateway_audit_report(
            find_project_dir(),
            limit=_arg_int_or_default(args, "limit", 20),
            event=str(getattr(args, "event", "") or ""),
        )
        if getattr(args, "json", False) or getattr(args, "pretty", False):
            _json_print(payload, pretty=_arg_value(args, "pretty", False) is True)
            return
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        print(
            f"Gateway audit: {payload.get('status', 'idle')} "
            f"events={summary.get('total_events', 0)} "
            f"blocked={summary.get('blocked_or_failed_events', 0)} "
            f"unique_ips={summary.get('unique_client_ips', 0)}"
        )
        for row in payload.get("recent_events", []):
            print(
                f"  - {row.get('created_at', '')} {row.get('event', '')} "
                f"{row.get('status', '')} {row.get('client_ip', '')} {row.get('endpoint', '')} "
                f"{row.get('reason', '')}"
            )
        print(f"Next: {payload.get('next_action', '')}")
        return
    if action != "serve":
        print("用法: vault gateway {serve|health|openapi|audit} 或 vault remote-server {serve|health|openapi|audit}")
        raise SystemExit(2)
    if profile == "remote_server" and not _has_stable_gateway_token(args):
        print(
            "Vault Remote Server requires a stable token. Set VAULT_GATEWAY_TOKEN "
            "or pass --auth-token before binding a remote server."
        )
        raise SystemExit(2)
    base_policy = GatewaySecurityPolicy.from_env()
    run_gateway(
        find_project_dir(),
        host=str(getattr(args, "host", DEFAULT_GATEWAY_HOST) or DEFAULT_GATEWAY_HOST),
        port=int(getattr(args, "port", DEFAULT_GATEWAY_PORT) or DEFAULT_GATEWAY_PORT),
        max_workers=_arg_int_or_default(args, "max_workers", _gateway_max_workers(None)),
        auth_token=getattr(args, "auth_token", None),
        no_auth=bool(getattr(args, "no_auth", False)),
        security_policy=GatewaySecurityPolicy(
            rate_limit_per_minute=_arg_int_or_default(args, "rate_limit_per_minute", base_policy.rate_limit_per_minute),
            token_rate_limit_per_minute=_arg_int_or_default(args, "token_rate_limit_per_minute", base_policy.token_rate_limit_per_minute),
            auth_failure_limit=_arg_int_or_default(args, "auth_failure_limit", base_policy.auth_failure_limit),
            auth_lockout_seconds=_arg_int_or_default(args, "auth_lockout_seconds", base_policy.auth_lockout_seconds),
            ip_allowlist=str(getattr(args, "ip_allowlist", "") or base_policy.ip_allowlist),
            ip_denylist=str(getattr(args, "ip_denylist", "") or base_policy.ip_denylist),
        ),
        tls_cert=str(getattr(args, "tls_cert", "") or os.environ.get("VAULT_GATEWAY_TLS_CERT", "") or ""),
        tls_key=str(getattr(args, "tls_key", "") or os.environ.get("VAULT_GATEWAY_TLS_KEY", "") or ""),
        server_label="Vault Remote Server" if profile == "remote_server" else "Vault Gateway",
        allow_shared_candidates=bool(getattr(args, "allow_shared_candidates", False)),
        allow_private_candidates=bool(getattr(args, "allow_private_candidates", False)),
        allow_high_sensitivity_candidates=bool(getattr(args, "allow_high_sensitivity_candidates", False)),
        allow_restricted_candidates=bool(getattr(args, "allow_restricted_candidates", False)),
        token_agent_map=str(getattr(args, "token_agent_map", "") or os.environ.get("VAULT_GATEWAY_TOKEN_AGENT_MAP", "") or ""),
        remote_semantic_enabled=getattr(args, "remote_semantic", None),
        shutdown_timeout_seconds=getattr(args, "shutdown_timeout_seconds", None),
    )


def _agent_id(value: Any) -> str:
    return str(value or "").strip().lower()


def _request_agent(body: dict[str, Any], parsed) -> str:
    query = parse_qs(parsed.query)
    return _agent_id(body.get("agent_id") or (query.get("agent_id") or [""])[0])


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


def _gateway_max_workers(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        env_value = os.environ.get("VAULT_GATEWAY_MAX_WORKERS", "")
        if env_value:
            try:
                parsed = int(env_value)
            except ValueError:
                parsed = DEFAULT_GATEWAY_MAX_WORKERS
        else:
            parsed = DEFAULT_GATEWAY_MAX_WORKERS
    return max(1, min(parsed, 256))


def _gateway_shutdown_timeout_seconds(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        env_value = os.environ.get("VAULT_GATEWAY_SHUTDOWN_TIMEOUT_SECONDS", "")
        if env_value:
            try:
                parsed = float(env_value)
            except ValueError:
                parsed = DEFAULT_GATEWAY_SHUTDOWN_TIMEOUT_SECONDS
        else:
            parsed = DEFAULT_GATEWAY_SHUTDOWN_TIMEOUT_SECONDS
    return max(0.0, min(parsed, 300.0))


def _install_gateway_signal_handlers(server: Any, stop_signal: dict[str, str]) -> dict[int, Any]:
    previous: dict[int, Any] = {}

    def request_stop(signum, _frame) -> None:
        try:
            name = signal.Signals(signum).name
        except ValueError:
            name = str(signum)
        stop_signal["name"] = name
        begin = getattr(server, "begin_draining", None)
        if callable(begin):
            begin()
        shutdown = getattr(server, "shutdown", None)
        if callable(shutdown):
            threading.Thread(target=shutdown, daemon=True).start()

    for signum in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
        if signum is None:
            continue
        try:
            previous[int(signum)] = signal.getsignal(signum)
            signal.signal(signum, request_stop)
        except (ValueError, OSError):
            continue
    return previous

def _restore_gateway_signal_handlers(previous: dict[int, Any]) -> None:
    for signum, handler in previous.items():
        try:
            signal.signal(signum, handler)
        except (ValueError, OSError):
            continue

def _bool_value(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return bool(default)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)

def _arg_int_or_default(args: Any, name: str, default: int) -> int:
    value = getattr(args, name, None)
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _error(code: str, message: str, *, status: str = "error") -> dict[str, Any]:
    payload: dict[str, Any] = {"status": status, "error": code, "message": message}
    suggestions = _error_suggestions(code)
    if suggestions:
        payload.update(suggestions)
    return payload

def _error_suggestions(code: str) -> dict[str, Any]:
    return gateway_error_suggestions(code)

def _resolve_tls_paths(tls_cert: str | Path | None, tls_key: str | Path | None) -> tuple[str, str] | None:
    cert_text = str(tls_cert or "").strip()
    key_text = str(tls_key or "").strip()
    if not cert_text and not key_text:
        return None
    if not cert_text or not key_text:
        raise ValueError("TLS requires both --tls-cert and --tls-key")
    cert = Path(cert_text).expanduser().resolve()
    key = Path(key_text).expanduser().resolve()
    if not cert.is_file():
        raise FileNotFoundError(f"TLS certificate not found: {cert}")
    if not key.is_file():
        raise FileNotFoundError(f"TLS key not found: {key}")
    return str(cert), str(key)

def _wrap_gateway_tls(sock: Any, *, certfile: str, keyfile: str) -> Any:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    return context.wrap_socket(sock, server_side=True)

def _has_stable_gateway_token(args: Any) -> bool:
    if bool(getattr(args, "no_auth", False)):
        return False
    if str(getattr(args, "auth_token", "") or "").strip():
        return True
    return bool(os.environ.get("VAULT_GATEWAY_TOKEN", "").strip())


def _append_audit(project_dir: Path, event: str, agent_id: str, status: str, **extra: Any) -> None:
    path = project_dir / "reports" / "gateway" / "audit.jsonl"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _rotate_audit_if_needed(path)
        row = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "agent_id": agent_id,
            "status": status,
            **extra,
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        return


def _rotate_audit_if_needed(path: Path) -> None:
    max_bytes = _gateway_audit_max_bytes(None)
    if max_bytes <= 0 or not path.exists():
        return
    try:
        if path.stat().st_size < max_bytes:
            return
    except OSError:
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    rotated = path.with_name(f"audit-{timestamp}.jsonl")
    suffix = 1
    while rotated.exists():
        rotated = path.with_name(f"audit-{timestamp}-{suffix}.jsonl")
        suffix += 1
    try:
        path.replace(rotated)
    except OSError:
        return
    _prune_audit_backups(path.parent)


def _prune_audit_backups(directory: Path) -> None:
    keep = _gateway_audit_backup_count(None)
    if keep < 0:
        return
    backups = sorted(directory.glob("audit-*.jsonl"), key=lambda item: item.stat().st_mtime, reverse=True)
    for old in backups[keep:]:
        try:
            old.unlink()
        except OSError:
            continue


def _gateway_audit_max_bytes(value: Any) -> int:
    return _int_from_value_or_env(
        value,
        "VAULT_GATEWAY_AUDIT_MAX_BYTES",
        DEFAULT_GATEWAY_AUDIT_MAX_BYTES,
        minimum=0,
        maximum=1024 * 1024 * 1024,
    )


def _gateway_audit_backup_count(value: Any) -> int:
    return _int_from_value_or_env(
        value,
        "VAULT_GATEWAY_AUDIT_BACKUPS",
        DEFAULT_GATEWAY_AUDIT_BACKUPS,
        minimum=0,
        maximum=100,
    )


def _int_from_value_or_env(value: Any, env_name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = value
    if raw is None:
        raw = os.environ.get(env_name, "")
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        parsed = int(default)
    return max(minimum, min(parsed, maximum))
