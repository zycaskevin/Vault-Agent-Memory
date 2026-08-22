"""Machine-readable OpenAPI contract for Vault Gateway adapters."""

from __future__ import annotations

from typing import Any

from . import gateway_remote_semantic as remote_semantic
from .gateway_server import DEFAULT_GATEWAY_MAX_WORKERS
from .governance_contract import governance_contract_payload
from .memory_provider import memory_provider_contract_payload
from .search_utils import MAX_SEARCH_QUERY_CHARS

DEFAULT_GATEWAY_HOST = "127.0.0.1"
DEFAULT_GATEWAY_PORT = 8789
DEFAULT_GATEWAY_AUDIT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_GATEWAY_AUDIT_BACKUPS = 5
GATEWAY_CONTRACT_VERSION = "2026-08-21"
MEMORY_API_SENSITIVITY_LEVELS = ["low", "medium", "high", "restricted"]
_MEMORY_API_BAD_REQUEST = {
    "description": "Invalid cursor, cursor policy, sensitivity ceiling, or bounded range",
    "content": {
        "application/json": {"schema": {"$ref": "#/components/schemas/MemoryAPIError"}}
    },
}
GATEWAY_ENDPOINTS = [
    "/health",
    "/openapi.json",
    "/search",
    "/read-range",
    "/submit-candidate",
    "/memory/search",
    "/memory/create",
    "/memory/changes",
    "/memory/{id}",
    "/memory/audit",
    "/memory/timeline",
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
            "/memory/search": {
                "post": {
                    "summary": "Vault Memory API facade for governed active-memory search.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/MemorySearchRequest"}
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Compact active-memory search results"},
                        "400": _MEMORY_API_BAD_REQUEST,
                    },
                }
            },
            "/memory/create": {
                "post": {
                    "summary": "Vault Memory API facade for candidate-first memory creation.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/MemoryCreateRequest"}
                            }
                        }
                    },
                    "responses": {"200": {"description": "Candidate creation or gate rejection"}},
                }
            },
            "/memory/changes": {
                "get": {
                    "summary": "List policy-filtered memory changes using an opaque cursor.",
                    "parameters": [
                        {"name": "agent_id", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "cursor", "in": "query", "schema": {"type": "string"}},
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {"type": "integer", "default": 50, "minimum": 1, "maximum": 100},
                        },
                        {"name": "include_private", "in": "query", "schema": {"type": "boolean", "default": False}},
                        {
                            "name": "max_sensitivity",
                            "in": "query",
                            "schema": {
                                "type": "string",
                                "enum": MEMORY_API_SENSITIVITY_LEVELS,
                                "default": "low",
                            },
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Readable current-memory changes without hidden-row totals",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/MemoryChangePage"}
                                }
                            },
                        },
                        "400": _MEMORY_API_BAD_REQUEST,
                    },
                }
            },
            "/memory/{id}": {
                "get": {
                    "summary": "Read a bounded active-memory range through Vault Memory API.",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string", "minLength": 1},
                            "description": "Opaque provider memory identifier; consumers must not parse it.",
                            "x-vault-opaque-memory-id": True,
                        },
                        {"name": "agent_id", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "line_start", "in": "query", "schema": {"type": "integer", "default": 1}},
                        {"name": "line_end", "in": "query", "schema": {"type": "integer", "default": 40}},
                        {
                            "name": "revision_id",
                            "in": "query",
                            "schema": {"type": "string"},
                            "description": "Fail closed unless this is the current envelope revision.",
                        },
                        {
                            "name": "max_sensitivity",
                            "in": "query",
                            "schema": {
                                "type": "string",
                                "enum": MEMORY_API_SENSITIVITY_LEVELS,
                                "default": "low",
                            },
                        },
                        {
                            "name": "result_adapter",
                            "in": "query",
                            "schema": {"type": "string", "enum": ["legacy", "provider"], "default": "legacy"},
                            "description": (
                                "Use provider only for the opt-in preview bounded-read adapter; "
                                "legacy remains the default read authority."
                            ),
                        },
                    ],
                    "responses": {
                        "200": {"description": "Bounded memory read or access denial"},
                        "400": _MEMORY_API_BAD_REQUEST,
                    },
                },
                "patch": {
                    "summary": "Submit an update request as a review candidate; does not edit active memory.",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer", "minimum": 1},
                            "description": "Positive SQLite memory row id for a candidate update request.",
                        }
                    ],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/MemoryUpdateRequest"}
                            }
                        }
                    },
                    "responses": {"200": {"description": "Update candidate creation or gate rejection"}},
                },
                "delete": {
                    "summary": "Submit a soft-delete request as a review candidate; never hard-deletes memory.",
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}},
                        {"name": "agent_id", "in": "query", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "Soft-delete candidate request"}},
                },
            },
            "/memory/audit": {
                "get": {
                    "summary": "List recent memory audit events for operator visibility.",
                    "parameters": [
                        {"name": "agent_id", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "memory_id", "in": "query", "schema": {"type": "integer"}},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 20}},
                    ],
                    "responses": {"200": {"description": "Recent memory audit events"}},
                }
            },
            "/memory/timeline": {
                "get": {
                    "summary": "List metadata-only memory timeline rows for one memory id.",
                    "parameters": [
                        {"name": "agent_id", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "memory_id", "in": "query", "required": True, "schema": {"type": "integer"}},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 20}},
                        {"name": "include_private", "in": "query", "schema": {"type": "boolean", "default": False}},
                        {
                            "name": "max_sensitivity",
                            "in": "query",
                            "schema": {
                                "type": "string",
                                "enum": MEMORY_API_SENSITIVITY_LEVELS,
                                "default": "low",
                            },
                        },
                    ],
                    "responses": {
                        "200": {"description": "Metadata-only memory timeline"},
                        "400": _MEMORY_API_BAD_REQUEST,
                    },
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
                "MemoryChangeEnvelope": {
                    "type": "object",
                    "required": [
                        "schema_version",
                        "memory_id",
                        "revision_id",
                        "change_type",
                        "content_sha256",
                        "occurred_at",
                        "recorded_at",
                        "valid_from",
                        "valid_until",
                        "audit_ref",
                        "evidence_ref",
                    ],
                    "properties": {
                        "schema_version": {"const": "vault.memory-change.v1"},
                        "memory_id": {"type": "string"},
                        "revision_id": {"type": "string", "pattern": "^rev_[a-f0-9]{64}$"},
                        "change_type": {"type": "string", "enum": ["upsert", "delete"]},
                        "title": {"type": "string"},
                        "kind": {"type": "string"},
                        "content_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                        "occurred_at": {"type": "string"},
                        "recorded_at": {"type": "string"},
                        "valid_from": {"type": "string"},
                        "valid_until": {"type": "string"},
                        "provenance": {
                            "type": "object",
                            "properties": {"source": {"type": "string"}},
                        },
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "lifecycle": {
                            "type": "object",
                            "properties": {"status": {"type": "string"}},
                        },
                        "governance": {
                            "type": "object",
                            "properties": {
                                "scope": {"type": "string"},
                                "sensitivity": {"type": "string"},
                            },
                        },
                        "audit_ref": {"type": "string"},
                        "evidence_ref": {
                            "type": "object",
                            "required": ["memory_id", "revision_id", "operation"],
                            "properties": {
                                "memory_id": {"type": "string"},
                                "revision_id": {"type": "string"},
                                "operation": {"const": "read_bounded_evidence"},
                            },
                        },
                    },
                },
                "MemoryChangePage": {
                    "type": "object",
                    "required": ["status", "changes", "count", "next_cursor", "has_more"],
                    "properties": {
                        "status": {"type": "string"},
                        "changes": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/MemoryChangeEnvelope"},
                        },
                        "count": {"type": "integer", "minimum": 0, "maximum": 100},
                        "next_cursor": {"type": "string"},
                        "has_more": {"type": "boolean"},
                    },
                },
                "MemoryAPIError": {
                    "type": "object",
                    "required": ["status", "error", "message"],
                    "properties": {
                        "status": {"const": "error"},
                        "error": {
                            "type": "string",
                            "enum": [
                                "invalid_cursor",
                                "cursor_policy_mismatch",
                                "max_sensitivity_invalid",
                                "range_too_large",
                            ],
                        },
                        "message": {"type": "string"},
                    },
                },
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
                        "result_adapter": {
                            "type": "string",
                            "enum": ["legacy", "provider"],
                            "default": "legacy",
                            "description": (
                                "Use provider only for the opt-in preview adapter; "
                                "legacy remains the default result authority."
                            ),
                        },
                    },
                },
                "MemorySearchRequest": {
                    "allOf": [
                        {"$ref": "#/components/schemas/SearchRequest"},
                        {
                            "type": "object",
                            "properties": {
                                "max_sensitivity": {
                                    "type": "string",
                                    "enum": MEMORY_API_SENSITIVITY_LEVELS,
                                    "default": "low",
                                }
                            },
                        },
                    ]
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
                "MemoryCreateRequest": {
                    "allOf": [
                        {"$ref": "#/components/schemas/SubmitCandidateRequest"},
                        {
                            "type": "object",
                            "properties": {
                                "created_by_agent": {"type": "string"},
                                "owner_user": {"type": "string"},
                                "workspace_id": {"type": "string"},
                                "source_app": {"type": "string"},
                                "source_device": {"type": "string"},
                                "permission_scope": {"type": "string"},
                            },
                        },
                    ],
                },
                "MemoryUpdateRequest": {
                    "type": "object",
                    "required": ["agent_id"],
                    "properties": {
                        "agent_id": {"type": "string"},
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "proposed_content": {"type": "string"},
                        "reason": {"type": "string"},
                        "patch": {"type": "object"},
                        "scope": {"type": "string", "default": "project"},
                        "sensitivity": {"type": "string", "default": "low"},
                        "created_by_agent": {"type": "string"},
                        "owner_user": {"type": "string"},
                        "workspace_id": {"type": "string"},
                        "source_app": {"type": "string"},
                        "source_device": {"type": "string"},
                        "permission_scope": {"type": "string"},
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
            "vault_memory_api_additive": True,
            "memory_api_update_writes_active_knowledge": False,
            "memory_api_delete_hard_deletes": False,
            "memory_api_delete_submits_review_candidate": True,
            "memory_change_pages_hide_filtered_counts": True,
            "memory_change_cursors_are_policy_bound": True,
            "memory_bounded_evidence_revision_required": True,
            "memory_provider_interface": True,
            "default_memory_provider": "sqlite",
            "remote_direct_active_memory_writes": False,
        },
        "x-vault-governance-contract": governance_contract_payload(adapter=title),
        "x-vault-memory-provider-interface": memory_provider_contract_payload(provider_id="sqlite"),
        "x-vault-memory-api": {
            "status": "facade",
            "standalone_workflow_required": True,
            "legacy_gateway_endpoints_preserved": True,
            "implemented_paths": [
                "/memory/search",
                "/memory/create",
                "/memory/changes",
                "/memory/{id}",
                "/memory/audit",
                "/memory/timeline",
            ],
            "planned_paths": [
                "/memory/promote",
                "/memory/link",
                "/memory/sync",
            ],
            "memory_change_envelope": {
                "schema_version": "vault.memory-change.v1",
                "path": "/memory/changes",
                "provider_independent": True,
                "cursor_policy_bound": True,
                "hidden_totals_exposed": False,
                "bounded_evidence_path": "/memory/{id}",
                "bounded_evidence_revision_parameter": "revision_id",
                "historical_content_guaranteed": False,
            },
            "provider_read_adoption": {
                "paths": ["/memory/search", "/memory/{id}"],
                "mode": "shadow_metadata_probe",
                "policy_authority": "legacy_gateway_policy_gate",
                "provider_read_policy_filtering": True,
                "search_probes_returned_ids_only": True,
                "returns_provider_raw_rows": False,
            },
            "provider_backed_result_adapter": {
                "paths": ["/memory/search", "/memory/{id}"],
                "opt_in_field": "result_adapter",
                "opt_in_value": "provider",
                "default_result_adapter": "legacy",
                "status": "preview",
                "search_supported_modes": ["auto", "keyword"],
                "read_policy_filtering": True,
                "returns_provider_raw_rows": False,
                "search_returns_raw_content": False,
                "read_returns_bounded_content": True,
                "read_returns_full_raw_content": False,
            },
            "provider_adapter_parity_gate": {
                "helper": "vault.memory_provider_parity.provider_adapter_parity_report",
                "status": "available_internal_report",
                "required_before_default_authority_switch": True,
                "compares": ["search_result_ids", "read_access_decisions", "bounded_read_content_hashes"],
                "returns_raw_query_text": False,
                "returns_raw_memory_content": False,
                "changes_default_authority": False,
            },
            "delete_semantics": "soft_delete_review_candidate_in_gateway_facade",
            "qdrant_boundary": "semantic_index_provider_not_source_of_truth",
        },
    }
