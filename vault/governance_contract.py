"""Machine-readable Vault Governance Contract metadata."""

from __future__ import annotations

from typing import Any


GOVERNANCE_CONTRACT_VERSION = "2026-07-09"

GOVERNANCE_OPERATIONS = [
    "search_approved_memory",
    "read_approved_memory",
    "submit_candidate",
    "review_candidate",
    "promote_candidate",
    "audit_memory_event",
    "daily_loop_status",
    "daily_loop_report",
]

BACKEND_ADAPTER_REQUIREMENTS = [
    "approved_memory_storage",
    "candidate_queue_storage",
    "access_policy_metadata",
    "audit_trail",
    "read_search_operations",
    "backup_or_export_path",
    "optional_semantic_index",
    "no_remote_direct_active_memory_writes",
]


def governance_contract_payload(*, adapter: str = "") -> dict[str, Any]:
    """Return a JSON-safe contract summary shared by runtime health surfaces."""
    return {
        "name": "Vault Governance Contract",
        "version": GOVERNANCE_CONTRACT_VERSION,
        "adapter": str(adapter or ""),
        "operations": list(GOVERNANCE_OPERATIONS),
        "backend_adapter_requirements": list(BACKEND_ADAPTER_REQUIREMENTS),
        "semantics": {
            "approved_memory_is_read_surface": True,
            "remote_writes_enter_candidates": True,
            "remote_agents_can_promote_active_memory": False,
            "promotion_requires_review_or_policy_gate": True,
            "audit_required_for_memory_events": True,
            "daily_report_required_for_operator_visibility": True,
            "strategic_sensitive_conflicting_memory_requires_review": True,
        },
        "write_policy": {
            "remote_write_policy": "candidate_first_only",
            "direct_remote_active_memory_writes": False,
            "trusted_local_review_can_promote": True,
            "policy_gated_low_risk_promotion_only": True,
            "hard_delete_by_remote_agent": False,
        },
        "read_policy": {
            "approved_memory_only_for_remote_readers": True,
            "bounded_read_preferred": True,
            "access_policy_metadata_required": True,
        },
    }
