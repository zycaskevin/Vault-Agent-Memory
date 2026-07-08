"""Reusable Gateway error suggestions."""

from __future__ import annotations

from typing import Any


GATEWAY_ERROR_SUGGESTIONS: dict[str, dict[str, Any]] = {
    "db_not_found": {
        "try": ["Run `vault init --project-dir <project>` before starting the Gateway.", "Pass the intended project with `--project-dir <project>`."],
        "next_action": "Initialize the vault, then retry the Gateway request.",
    },
    "auth_failed": {
        "try": ["Send `Authorization: Bearer $VAULT_GATEWAY_TOKEN` or `X-Vault-Gateway-Token`.", "If locked out, wait for the lockout window or restart the local Gateway."],
        "next_action": "Retry with the configured Gateway token.",
    },
    "auth_locked": {
        "try": ["Send `Authorization: Bearer $VAULT_GATEWAY_TOKEN` or `X-Vault-Gateway-Token`.", "If locked out, wait for the lockout window or restart the local Gateway."],
        "next_action": "Retry with the configured Gateway token.",
    },
    "rate_limited": {"try": ["Reduce request rate or raise `--rate-limit-per-minute` for trusted local clients."], "next_action": "Wait and retry the request."},
    "agent_id_required": {"try": ["Include `agent_id` in the JSON body, for example `codex` or `claude-code`."], "next_action": "Retry with an explicit agent_id."},
    "not_found": {"try": ["Use `/health`, `/openapi.json`, `/search`, `/read-range`, or `/submit-candidate`."], "next_action": "Check `/openapi.json` for the supported Gateway contract."},
}


def gateway_error_suggestions(code: str) -> dict[str, Any]:
    return GATEWAY_ERROR_SUGGESTIONS.get(code, {})
