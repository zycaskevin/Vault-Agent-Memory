"""Security diagnostics for local agent-facing Vault surfaces."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping, Any

from .governance_contract import governance_contract_payload


LOCALHOSTS = {"127.0.0.1", "localhost", "::1"}


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "require", "required"}


def security_doctor(
    env: Mapping[str, str] | None = None,
    *,
    project_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Return a compact security posture report for CLI and setup smoke tests."""
    env_map = env or os.environ
    require_hmac = _truthy(env_map.get("VAULT_MCP_REQUIRE_AGENT_SIGNATURE", ""))
    agent_secret_keys = sorted(key for key in env_map if key.startswith("VAULT_MCP_AGENT_SECRET"))
    gui_auth_configured = bool(str(env_map.get("VAULT_GUI_TOKEN", "")).strip())
    service_role_present = bool(
        str(env_map.get("SUPABASE_SERVICE_ROLE_KEY", "")).strip()
        or str(env_map.get("SUPABASE_SERVICE_KEY", "")).strip()
    )
    trusted_sync_host = _truthy(env_map.get("VAULT_SUPABASE_TRUSTED_SYNC_HOST", "")) or _truthy(
        env_map.get("VAULT_TRUSTED_SYNC_HOST", "")
    )
    gateway_auth_configured = bool(str(env_map.get("VAULT_GATEWAY_TOKEN", "")).strip())
    semantic_binding_configured = bool(str(env_map.get("VAULT_GATEWAY_TOKEN_AGENT_MAP", "")).strip())
    remote_semantic_enabled = _truthy(env_map.get("VAULT_GATEWAY_REMOTE_SEMANTIC_ENABLED", ""))
    remote_bind = str(
        env_map.get("VAULT_REMOTE_SERVER_BIND")
        or env_map.get("VAULT_GATEWAY_HOST")
        or ""
    ).strip()
    remote_url = str(env_map.get("VAULT_REMOTE_URL", "")).strip()
    tls_configured = bool(str(env_map.get("VAULT_GATEWAY_TLS_CERT", "")).strip()) and bool(
        str(env_map.get("VAULT_GATEWAY_TLS_KEY", "")).strip()
    )
    private_network_declared = any(
        _truthy(env_map.get(name, ""))
        for name in (
            "VAULT_REMOTE_SERVER_PRIVATE_NETWORK",
            "VAULT_REMOTE_SERVER_BEHIND_VPN",
            "VAULT_REMOTE_SERVER_VPN",
            "VAULT_REMOTE_SERVER_PRIVATE_LINK",
        )
    )
    self_host_signals = any(
        [
            gateway_auth_configured,
            semantic_binding_configured,
            remote_semantic_enabled,
            bool(remote_bind),
            bool(remote_url),
            tls_configured,
            private_network_declared,
        ]
    )
    public_bind = bool(remote_bind and remote_bind not in LOCALHOSTS)
    backup = _backup_status(Path(project_dir).expanduser().resolve() if project_dir else None)

    checks = [
        {
            "id": "mcp_hmac_required",
            "ok": require_hmac,
            "severity": "warn",
            "message": (
                "MCP HMAC signatures are required."
                if require_hmac
                else "MCP HMAC signatures are optional. Set VAULT_MCP_REQUIRE_AGENT_SIGNATURE=1 for stricter agent identity checks."
            ),
        },
        {
            "id": "mcp_agent_secret_configured",
            "ok": bool(agent_secret_keys),
            "severity": "warn",
            "message": (
                f"Configured MCP agent secret env keys: {', '.join(agent_secret_keys)}."
                if agent_secret_keys
                else "No VAULT_MCP_AGENT_SECRET* key is configured; signed MCP calls cannot be verified."
            ),
        },
        {
            "id": "gui_token_default",
            "ok": True,
            "severity": "info",
            "message": (
                "VAULT_GUI_TOKEN is configured; GUI will reuse it."
                if gui_auth_configured
                else "GUI generates an ephemeral token by default; pass --no-auth only for localhost testing."
            ),
        },
        {
            "id": "mcp_read_default",
            "ok": True,
            "severity": "info",
            "message": "MCP local read tools default to max_sensitivity=medium unless a stricter/elevated value is explicitly provided.",
        },
        {
            "id": "supabase_service_role_trusted_host",
            "ok": (not service_role_present) or trusted_sync_host,
            "severity": "warn",
            "message": (
                "SUPABASE_SERVICE_ROLE_KEY is present and this runtime is marked as a trusted sync host."
                if service_role_present and trusted_sync_host
                else (
                    "SUPABASE_SERVICE_ROLE_KEY is present without VAULT_SUPABASE_TRUSTED_SYNC_HOST=1; do not run hosted agents with service-role credentials."
                    if service_role_present
                    else "No Supabase service-role key detected in this runtime."
                )
            ),
        },
        {
            "id": "remote_server_stable_token",
            "ok": (not self_host_signals) or gateway_auth_configured,
            "severity": "warn",
            "message": (
                "Self-host Remote Server/Gateway signals found and VAULT_GATEWAY_TOKEN is configured."
                if self_host_signals and gateway_auth_configured
                else (
                    "Self-host Remote Server/Gateway signals found; set VAULT_GATEWAY_TOKEN before serving remote agents."
                    if self_host_signals
                    else "No self-host Remote Server/Gateway deployment signals detected."
                )
            ),
        },
        {
            "id": "remote_server_transport_boundary",
            "ok": (not public_bind) or tls_configured or private_network_declared,
            "severity": "warn",
            "message": (
                "Remote Server public bind has TLS or a declared private-network/VPN boundary."
                if public_bind and (tls_configured or private_network_declared)
                else (
                    "Remote Server public bind detected; configure TLS/reverse proxy or set a private-network/VPN marker before exposure."
                    if public_bind
                    else "Remote Server is not configured for a public bind in this environment."
                )
            ),
        },
        {
            "id": "remote_semantic_token_agent_binding",
            "ok": (not remote_semantic_enabled) or semantic_binding_configured,
            "severity": "warn",
            "message": (
                "Remote Semantic Search is enabled and token-agent binding is configured."
                if remote_semantic_enabled and semantic_binding_configured
                else (
                    "Remote Semantic Search is enabled; set VAULT_GATEWAY_TOKEN_AGENT_MAP so each token maps to one agent_id."
                    if remote_semantic_enabled
                    else "Remote Semantic Search is disabled."
                )
            ),
        },
        {
            "id": "remote_server_backup_plan",
            "ok": (not self_host_signals) or backup["ok"],
            "severity": "warn",
            "message": (
                f"Self-host backup check passed: latest backup {backup['latest_backup']}."
                if self_host_signals and backup["ok"] and backup["latest_backup"]
                else (
                    backup["message"]
                    if self_host_signals
                    else "No self-host deployment signals detected; backup cadence not required by this check."
                )
            ),
        },
    ]
    warn_count = sum(1 for item in checks if not item["ok"] and item["severity"] == "warn")
    return {
        "ok": warn_count == 0,
        "warning_count": warn_count,
        "checks": checks,
        "self_host": {
            "signals_detected": self_host_signals,
            "public_bind": public_bind,
            "tls_configured": tls_configured,
            "private_network_declared": private_network_declared,
            "remote_semantic_enabled": remote_semantic_enabled,
            "token_agent_binding_configured": semantic_binding_configured,
            "backup": backup,
        },
        "supabase": {
            "service_role_key_present": service_role_present,
            "trusted_sync_host": trusted_sync_host,
            "service_role_policy": (
                "allowed_on_trusted_sync_host"
                if service_role_present and trusted_sync_host
                else "remote_readers_must_not_receive_service_role"
            ),
        },
        "governance_contract": governance_contract_payload(adapter="security_doctor"),
        "next_action": (
            "For shared or untrusted agent runtimes, enable HMAC, keep service-role keys on trusted sync hosts only, and harden self-host Remote Server before exposure."
            if warn_count
            else "Security defaults look ready for local agent use."
        ),
    }


def _backup_status(project_dir: Path | None) -> dict[str, Any]:
    if project_dir is None:
        return {
            "ok": True,
            "checked": False,
            "latest_backup": "",
            "message": "Backup check skipped because no project_dir was provided.",
        }
    db_path = project_dir / "vault.db"
    if not db_path.exists():
        return {
            "ok": True,
            "checked": True,
            "latest_backup": "",
            "message": "Backup check skipped because vault.db does not exist yet.",
        }
    backup_dir = project_dir / "backups"
    backups = sorted(
        [item for item in backup_dir.glob("*.db") if item.is_file()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    ) if backup_dir.exists() else []
    if backups:
        return {
            "ok": True,
            "checked": True,
            "latest_backup": str(backups[0]),
            "message": "At least one SQLite backup exists.",
        }
    return {
        "ok": False,
        "checked": True,
        "latest_backup": "",
        "message": "Self-host deployment signals found but no SQLite backup was found under project backups/; run `vault db backup --verify`.",
    }
