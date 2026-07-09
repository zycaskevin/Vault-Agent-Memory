"""Gateway helpers for the self-hosted central candidate inbox."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .access_policy import can_write_memory, normalize_write_policy
from .central_candidate_store import pull_central_candidates_local, submit_central_candidate_local
from .governance_contract import governance_contract_payload


def gateway_submit_central_candidate(
    project_dir: str | Path,
    *,
    title: str,
    content: str,
    agent_id: str,
    reason: str = "",
    category: str = "general",
    tags: str = "",
    trust: float = 0.5,
    scope: str = "project",
    sensitivity: str = "low",
    owner_agent: str = "",
    allowed_agents: str = "",
    memory_type: str = "remote_candidate",
    source_ref: str = "",
    idempotency_key: str = "",
    allow_shared_candidates: bool = False,
    allow_private_candidates: bool = False,
    allow_high_sensitivity_candidates: bool = False,
    allow_restricted_candidates: bool = False,
) -> dict[str, Any]:
    """Submit into the self-hosted central inbox, not local active knowledge."""
    project = Path(project_dir)
    agent = _agent_id(agent_id)
    if not (project / "vault.db").exists():
        return _error("db_not_found", "vault.db missing", status="blocked")
    if not agent:
        return _error("agent_id_required", "Gateway central candidate submit requires agent_id")
    meta = {
        "title": str(title or "").strip(),
        "content": str(content or "").strip(),
        "from_agent": agent,
        "reason": reason or "Submitted through Vault Gateway central candidate inbox.",
        "category": category or "general",
        "tags": tags or "",
        "trust": trust,
        "scope": scope or "project",
        "sensitivity": sensitivity or "low",
        "owner_agent": owner_agent or agent,
        "allowed_agents": allowed_agents or "",
        "memory_type": memory_type or "remote_candidate",
        "source_ref": source_ref or "",
        "idempotency_key": idempotency_key or "",
    }
    allowed, why = can_write_memory(
        {**meta, "source": f"gateway-central:{agent}"},
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
    result = submit_central_candidate_local(project, **meta)
    result["status"] = result.get("status") or ("ok" if result.get("ok") else "error")
    result["central_memory_station"] = True
    result["safety"] = {
        "candidate_first": True,
        "writes_active_knowledge": False,
        "requires_pull_into_local_review": True,
        "self_hosted_central_inbox": True,
        "governance_contract": governance_contract_payload(adapter="gateway_central_candidate_submit"),
    }
    return result


def gateway_pull_central_candidates(
    project_dir: str | Path,
    *,
    agent_id: str,
    limit: int = 20,
    apply: bool = False,
    require_hmac: bool | None = None,
) -> dict[str, Any]:
    """Pull self-hosted central candidates into the local review queue."""
    project = Path(project_dir)
    agent = _agent_id(agent_id)
    if not (project / "vault.db").exists():
        return _error("db_not_found", "vault.db missing", status="blocked")
    if not agent:
        return _error("agent_id_required", "Gateway central candidate pull requires agent_id")
    payload = pull_central_candidates_local(
        project,
        agent_id=agent,
        limit=max(1, min(int(limit or 20), 100)),
        apply=bool(apply),
        require_hmac=require_hmac,
    )
    payload["central_memory_station"] = True
    payload["safety"] = {
        "candidate_first": True,
        "writes_active_knowledge": False,
        "apply_writes_local_candidates_only": bool(apply),
        "self_hosted_central_inbox": True,
        "governance_contract": governance_contract_payload(adapter="gateway_central_candidate_pull"),
    }
    return payload


def _agent_id(value: Any) -> str:
    return str(value or "").strip().lower()


def _error(code: str, message: str, *, status: str = "error") -> dict[str, Any]:
    return {
        "status": status,
        "error": code,
        "message": message,
        **_error_suggestions(code),
    }


def _error_suggestions(code: str) -> dict[str, Any]:
    if code == "db_not_found":
        return {
            "try": [
                "Run `vault init --project-dir <project>`.",
                "Pass `--project-dir` that contains vault.db.",
            ],
            "next_action": "Initialize the project vault, then retry.",
        }
    if code == "agent_id_required":
        return {
            "try": ["Include `agent_id` in the JSON body, for example `codex` or `claude-code`."],
            "next_action": "Retry with an explicit agent_id.",
        }
    return {}
