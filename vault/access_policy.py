"""Governance filters for multi-agent Vault access."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

SENSITIVITY_RANK = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "restricted": 3,
}


def _normalize_agent(value: Any) -> str:
    return str(value or "").strip().lower()


def _parse_allowed_agents(value: Any) -> set[str]:
    if value is None or value == "":
        return set()
    if isinstance(value, (list, tuple, set)):
        return {_normalize_agent(item) for item in value if _normalize_agent(item)}
    text = str(value).strip()
    if not text:
        return set()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return {_normalize_agent(item) for item in parsed if _normalize_agent(item)}
    return {_normalize_agent(part) for part in text.split(",") if _normalize_agent(part)}


@dataclass(frozen=True)
class ReadPolicy:
    agent_id: str = ""
    include_private: bool = False
    max_sensitivity: str = ""
    allowed_statuses: tuple[str, ...] = ()

    @property
    def active(self) -> bool:
        return bool(self.agent_id or self.max_sensitivity or self.include_private or self.allowed_statuses)


def normalize_read_policy(
    *,
    agent_id: Any = "",
    include_private: Any = False,
    max_sensitivity: Any = "",
    allowed_statuses: Any = None,
) -> ReadPolicy:
    sensitivity = str(max_sensitivity or "").strip().lower()
    if sensitivity and sensitivity not in SENSITIVITY_RANK:
        sensitivity = ""
    statuses = _normalize_statuses(allowed_statuses)
    return ReadPolicy(
        agent_id=_normalize_agent(agent_id),
        include_private=bool(include_private),
        max_sensitivity=sensitivity,
        allowed_statuses=statuses,
    )


def _normalize_statuses(statuses: Any) -> tuple[str, ...]:
    """Parse allowed_statuses into a tuple of lowercase status strings.

    Returns empty tuple if no status filter is set (backward-compatible default).
    When non-empty, only rows with matching status pass the read policy filter.

    Example usage for knowledge tables:
        allowed_statuses=("active",)
    Example usage for candidates:
        allowed_statuses=("candidate", "reviewed")
    """
    if statuses is None:
        return ()
    if isinstance(statuses, str):
        if not statuses.strip():
            return ()
        parts = [s.strip().lower() for s in statuses.split(",") if s.strip()]
        return tuple(parts)
    if isinstance(statuses, (list, tuple, set)):
        parts = [str(s).strip().lower() for s in statuses if str(s).strip()]
        return tuple(parts)
    return ()


def can_read_memory(row: dict[str, Any], policy: ReadPolicy) -> bool:
    """Return whether a knowledge row is visible under a local read policy.

    The policy is opt-in. Without `agent_id`, `max_sensitivity`, or `include_private`,
    legacy local behavior is preserved and all rows remain visible.
    """
    if not policy.active:
        return True

    # Status filter (optional - only applied when explicitly set)
    if policy.allowed_statuses:
        status = str(row.get("status") or "active").strip().lower()
        if status not in policy.allowed_statuses:
            return False

    sensitivity = str(row.get("sensitivity") or "low").strip().lower()
    sensitivity_rank = SENSITIVITY_RANK.get(sensitivity, 0)
    if policy.max_sensitivity:
        max_rank = SENSITIVITY_RANK[policy.max_sensitivity]
        if sensitivity_rank > max_rank:
            return False

    scope = str(row.get("scope") or "project").strip().lower()
    owner_agent = _normalize_agent(row.get("owner_agent"))
    allowed_agents = _parse_allowed_agents(row.get("allowed_agents"))
    agent = policy.agent_id

    if sensitivity == "restricted":
        return bool(agent and (agent == owner_agent or agent in allowed_agents))

    if scope == "private":
        return bool(
            policy.include_private
            and agent
            and (agent == owner_agent or agent in allowed_agents)
        )

    return True


def filter_readable_memories(rows: list[dict[str, Any]], policy: ReadPolicy) -> list[dict[str, Any]]:
    if not policy.active:
        return rows
    return [row for row in rows if can_read_memory(row, policy)]


@dataclass(frozen=True)
class WritePolicy:
    agent_id: str = ""
    allow_shared: bool = False
    allow_private: bool = False
    allow_high_sensitivity: bool = False
    allow_restricted: bool = False


def normalize_write_policy(
    *,
    agent_id: Any = "",
    allow_shared: Any = False,
    allow_private: Any = False,
    allow_high_sensitivity: Any = False,
    allow_restricted: Any = False,
) -> WritePolicy:
    return WritePolicy(
        agent_id=_normalize_agent(agent_id),
        allow_shared=bool(allow_shared),
        allow_private=bool(allow_private),
        allow_high_sensitivity=bool(allow_high_sensitivity),
        allow_restricted=bool(allow_restricted),
    )


def can_write_memory(metadata: dict[str, Any], policy: WritePolicy) -> tuple[bool, str]:
    """Return whether an agent can write/promote memory with this metadata.

    Local CLI paths remain trusted. MCP callers that do not provide an agent_id
    can still create low-sensitivity project memories for backwards
    compatibility, but broader scopes and sensitive memories require explicit
    identity and capability flags.
    """
    scope = str(metadata.get("scope") or "project").strip().lower()
    sensitivity = str(metadata.get("sensitivity") or "low").strip().lower()
    owner_agent = _normalize_agent(metadata.get("owner_agent"))
    allowed_agents = _parse_allowed_agents(metadata.get("allowed_agents"))
    agent = policy.agent_id

    if sensitivity == "restricted":
        if not agent:
            return False, "restricted writes require agent_id"
        if not policy.allow_restricted:
            return False, "restricted writes require allow_restricted=true"
        if owner_agent and agent != owner_agent and agent not in allowed_agents:
            return False, "restricted writes require owner or allowed agent"

    if sensitivity == "high":
        if not agent:
            return False, "high-sensitivity writes require agent_id"
        if not policy.allow_high_sensitivity:
            return False, "high-sensitivity writes require allow_high_sensitivity=true"

    if scope == "private":
        if not agent:
            return False, "private writes require agent_id"
        if not policy.allow_private:
            return False, "private writes require allow_private=true"
        if owner_agent and agent != owner_agent and agent not in allowed_agents:
            return False, "private writes require owner or allowed agent"

    if scope in {"shared", "public"} and not policy.allow_shared:
        return False, "shared/public writes require allow_shared=true"

    return True, ""
