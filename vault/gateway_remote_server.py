"""Remote Server metadata helpers for the Gateway contract."""

from __future__ import annotations

from typing import Any


def remote_server_metadata() -> dict[str, Any]:
    return {
        "mode": "self_hosted_remote_memory_entrypoint",
        "uses_gateway_contract": True,
        "replaces_supabase_for": ["multi_platform_reads", "candidate_first_remote_writes"],
        "does_not_replace_yet": ["offline_multi_master_merge", "active_memory_bidirectional_sync"],
        "stable_token_required": True,
        "source_of_truth": "server_side_local_sqlite_vault",
    }


def mark_remote_server_payload(payload: dict[str, Any]) -> None:
    gateway = payload.get("gateway") if isinstance(payload.get("gateway"), dict) else {}
    remote_ready = gateway.get("remote_ready") if isinstance(gateway.get("remote_ready"), dict) else {}
    gateway["remote_server"] = remote_server_metadata()
    gateway["role"] = "self_hosted_vault_remote_server"
    remote_ready["stable_token_required"] = True
    gateway["remote_ready"] = remote_ready
    payload["gateway"] = gateway
