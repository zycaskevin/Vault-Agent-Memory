"""Domain-neutral Vault v1 Memory Object contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


MEMORY_LAYER_CONTRACT_VERSION = "1.0"
MEMORY_OBJECT_KINDS = (
    "event",
    "experience",
    "decision",
    "knowledge",
    "interaction",
)
MEMORY_LAYER_CAPABILITIES = (
    "storage",
    "retrieval",
    "provenance",
    "confidence",
    "lifecycle",
    "governance",
)
MEMORY_LAYER_NON_RESPONSIBILITIES = (
    "personality",
    "identity",
    "relationship",
    "life_phase",
    "human_modeling",
)


def validate_memory_kind(value: Any) -> str:
    """Return a canonical public kind or reject an explicit invalid value."""
    normalized = str(value or "").strip().lower().replace("-", "_")
    if normalized not in MEMORY_OBJECT_KINDS:
        allowed = ", ".join(MEMORY_OBJECT_KINDS)
        raise ValueError(f"unsupported_memory_kind:{normalized or 'empty'} (expected {allowed})")
    return normalized


def memory_kind_from_record(value: Any) -> str:
    """Map an opaque stored type to a canonical kind without interpreting it."""
    normalized = str(value or "knowledge").strip().lower().replace("-", "_")
    return normalized if normalized in MEMORY_OBJECT_KINDS else "knowledge"


def legacy_memory_type_metadata(value: Any) -> dict[str, str]:
    """Preserve an unknown legacy type as opaque application metadata."""
    stored_type = str(value or "knowledge").strip() or "knowledge"
    normalized = stored_type.lower().replace("-", "_")
    if normalized in MEMORY_OBJECT_KINDS:
        return {}
    return {"legacy_memory_type": stored_type}


@dataclass(frozen=True)
class MemoryObject:
    """Stable application-facing view over a Vault memory or candidate row."""

    id: str
    kind: str
    title: str
    content: str
    provenance: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    lifecycle: dict[str, Any] = field(default_factory=dict)
    governance: dict[str, Any] = field(default_factory=dict)
    application_metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = MEMORY_LAYER_CONTRACT_VERSION

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "MemoryObject":
        """Adapt current storage rows without changing or reinterpreting them."""
        stored_type = str(record.get("memory_type") or "knowledge").strip() or "knowledge"
        requested_kind = record.get("memory_kind") or stored_type
        application_metadata: dict[str, Any] = {
            key: record.get(key)
            for key in ("layer", "category", "tags")
            if record.get(key) not in (None, "")
        }
        application_metadata.update(legacy_memory_type_metadata(stored_type))
        return cls(
            id=str(record.get("id") or record.get("candidate_id") or ""),
            kind=memory_kind_from_record(requested_kind),
            title=str(record.get("title") or ""),
            content=str(record.get("content") or record.get("content_raw") or ""),
            provenance={
                key: record.get(key)
                for key in ("source", "source_ref", "created_at", "updated_at")
                if record.get(key) not in (None, "")
            },
            confidence=_normalize_confidence(record.get("confidence", record.get("trust", 0.5))),
            lifecycle={
                key: record.get(key)
                for key in ("status", "valid_from", "valid_until", "expires_at", "supersedes_id")
                if record.get(key) not in (None, "")
            },
            governance={
                key: record.get(key)
                for key in ("scope", "sensitivity", "owner_agent", "allowed_agents")
                if record.get(key) not in (None, "")
            },
            application_metadata=application_metadata,
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe envelope with a stable top-level shape."""
        return asdict(self)


def memory_layer_contract_payload() -> dict[str, Any]:
    """Return the authoritative machine-readable Vault Memory Layer boundary."""
    return {
        "name": "Vault Memory Layer Contract",
        "version": MEMORY_LAYER_CONTRACT_VERSION,
        "mission": "Governed Memory Infrastructure for AI Agents",
        "memory_object": {
            "envelope": "MemoryObject",
            "schema_version": MEMORY_LAYER_CONTRACT_VERSION,
            "kinds": list(MEMORY_OBJECT_KINDS),
            "legacy_memory_type_preserved": True,
            "unknown_legacy_types_are_application_metadata": True,
        },
        "capabilities": list(MEMORY_LAYER_CAPABILITIES),
        "non_responsibilities": list(MEMORY_LAYER_NON_RESPONSIBILITIES),
        "integration_boundary": {
            "vault_role": "memory_provider",
            "application_runtimes_are_external_consumers": True,
            "application_semantics_are_opaque": True,
            "domain_modeling_is_external": True,
        },
        "compatibility": {
            "existing_storage_schema_preserved": True,
            "legacy_cli_mcp_gateway_preserved": True,
            "memory_kind_alias_is_additive": True,
            "confidence_aliases_legacy_trust": True,
        },
    }


def _normalize_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = 0.5
    return max(0.0, min(confidence, 1.0))
