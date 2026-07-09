"""Machine-readable OpenAPI contract for Vault Gateway adapters."""

from __future__ import annotations

from typing import Any

from . import gateway_remote_semantic as remote_semantic
from .gateway_server import DEFAULT_GATEWAY_MAX_WORKERS
from .governance_contract import governance_contract_payload
from .search_utils import MAX_SEARCH_QUERY_CHARS


DEFAULT_GATEWAY_HOST = "127.0.0.1"
DEFAULT_GATEWAY_PORT = 8789
DEFAULT_GATEWAY_AUDIT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_GATEWAY_AUDIT_BACKUPS = 5
GATEWAY_CONTRACT_VERSION = "2026-07-02"
GATEWAY_ENDPOINTS = [
    "/health",
    "/openapi.json",
    "/search",
    "/read-range",
    "/submit-candidate",
    "/central-candidates/status",
    "/central-candidates/submit",
    "/central-candidates/pull",
] + remote_semantic.REMOTE_SEMANTIC_ENDPOINTS


def gateway_openapi(*, title: str = "Vault Gateway") -> dict[str, Any]:
    """Return the stable Gateway HTTP contract for adapters and hosted tools."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": title,
            "version": GATEWAY_CONTRACT_VERSION,
            "description": (
                "A conservative HTTP adapter for governed agent memory: search, bounded read, "
                "and candidate-first memory proposals."
            ),
        },
        "servers": [{"url": f"http://{DEFAULT_GATEWAY_HOST}:{DEFAULT_GATEWAY_PORT}"}],
        "security": [{"bearerAuth": []}, {"gatewayToken": []}],
        "paths": {
            "/health": {
                "get": {
                    "summary": "Check Gateway readiness and safety defaults.",
                    "responses": {"200": {"description": "Gateway readiness payload"}},
                }
            },
            "/openapi.json": {
                "get": {
                    "summary": "Return this machine-readable Gateway contract.",
                    "responses": {"200": {"description": "OpenAPI contract"}},
                }
            },
            "/search": {
                "post": {
                    "summary": "Search readable active memory without returning raw content.",
                    "requestBody": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/SearchRequest"}}
                        }
                    },
                    "responses": {"200": {"description": "Compact search results"}},
                }
            },
            "/read-range": {
                "post": {
                    "summary": "Read a bounded source range after search/map selection.",
                    "requestBody": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/ReadRangeRequest"}}
                        }
                    },
                    "responses": {"200": {"description": "Bounded source evidence or access denial"}},
                }
            },
            "/submit-candidate": {
                "post": {
                    "summary": "Submit a memory candidate; never writes active knowledge directly.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SubmitCandidateRequest"}
                            }
                        }
                    },
                    "responses": {"200": {"description": "Candidate creation or gate rejection"}},
                }
            },
            "/central-candidates/status": {
                "get": {
                    "summary": "Inspect the self-hosted central candidate inbox.",
                    "responses": {"200": {"description": "Central candidate inbox status"}},
                }
            },
            "/central-candidates/submit": {
                "post": {
                    "summary": "Submit to the self-hosted central candidate inbox.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SubmitCandidateRequest"}
                            }
                        }
                    },
                    "responses": {"200": {"description": "Central candidate inbox write"}},
                }
            },
            "/central-candidates/pull": {
                "post": {
                    "summary": "Pull self-hosted central candidates into local review.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/PullCentralCandidatesRequest"}
                            }
                        }
                    },
                    "responses": {"200": {"description": "Local candidate import preview or apply result"}},
                }
            },
            **remote_semantic.remote_semantic_openapi_paths(),
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"},
                "gatewayToken": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-Vault-Gateway-Token",
                },
            },
            "schemas": {
                "SearchRequest": {
                    "type": "object",
                    "required": ["agent_id", "query"],
                    "properties": {
                        "agent_id": {"type": "string"},
                        "query": {"type": "string", "maxLength": MAX_SEARCH_QUERY_CHARS},
                        "mode": {
                            "type": "string",
                            "enum": ["auto", "keyword", "semantic", "hybrid", "vector"],
                            "default": "keyword",
                        },
                        "limit": {"type": "integer", "default": 10, "minimum": 0, "maximum": 50},
                        "include_private": {"type": "boolean", "default": False},
                        "max_sensitivity": {"type": "string", "default": "low"},
                    },
                },
                "ReadRangeRequest": {
                    "type": "object",
                    "required": ["agent_id", "knowledge_id"],
                    "properties": {
                        "agent_id": {"type": "string"},
                        "knowledge_id": {"type": "integer"},
                        "node_uid": {"type": "string"},
                        "line_start": {"type": "integer", "default": 1, "minimum": 1},
                        "line_end": {"type": "integer", "default": 40, "minimum": 1},
                        "max_lines": {"type": "integer", "default": 80, "minimum": 1, "maximum": 200},
                        "include_private": {"type": "boolean", "default": False},
                        "max_sensitivity": {"type": "string", "default": "low"},
                    },
                },
                "SubmitCandidateRequest": {
                    "type": "object",
                    "required": ["agent_id", "title", "content"],
                    "properties": {
                        "agent_id": {"type": "string"},
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "reason": {"type": "string"},
                        "layer": {"type": "string", "default": "L3"},
                        "category": {"type": "string", "default": "general"},
                        "tags": {"type": "string"},
                        "trust": {"type": "number", "default": 0.5, "minimum": 0, "maximum": 1},
                        "scope": {"type": "string", "default": "project"},
                        "sensitivity": {"type": "string", "default": "low"},
                        "owner_agent": {"type": "string"},
                        "allowed_agents": {"type": "string"},
                        "memory_type": {"type": "string", "default": "knowledge"},
                        "source_ref": {"type": "string"},
                    },
                },
                "PullCentralCandidatesRequest": {
                    "type": "object",
                    "required": ["agent_id"],
                    "properties": {
                        "agent_id": {"type": "string"},
                        "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
                        "apply": {"type": "boolean", "default": False},
                        "require_hmac": {"type": "boolean", "default": False},
                    },
                },
                **remote_semantic.remote_semantic_openapi_schemas(MAX_SEARCH_QUERY_CHARS),
            },
        },
        "x-vault-safety": {
            "agent_id_required_for_reads": True,
            "private_hidden_by_default": True,
            "default_max_sensitivity": "low",
            "search_returns_raw_content": False,
            "writes_active_knowledge": False,
            "candidate_first_writes": True,
            "central_candidate_inbox": True,
            **remote_semantic.remote_semantic_safety_flags(),
            "rate_limit_supported": True,
            "ip_policy_supported": True,
            "auth_lockout_supported": True,
            "tls_supported": True,
            "http_security_headers": True,
            "hsts_when_tls_enabled": True,
            "max_search_query_chars": MAX_SEARCH_QUERY_CHARS,
            "bounded_worker_pool_supported": True,
            "default_max_workers": DEFAULT_GATEWAY_MAX_WORKERS,
            "audit_rotation_supported": True,
            "default_audit_max_bytes": DEFAULT_GATEWAY_AUDIT_MAX_BYTES,
            "default_audit_backups": DEFAULT_GATEWAY_AUDIT_BACKUPS,
            "audit_path": "reports/gateway/audit.jsonl",
        },
        "x-vault-governance-contract": governance_contract_payload(adapter=title),
    }
