"""Fail-closed read guard for canonical and derived memory results.

The legacy search surfaces intentionally preserve broad historical recall.  This
module is an opt-in boundary for callers that need *currently valid* memory:
active, approved, unexpired, temporally current, and readable by the requesting
agent.  Derived indexes can use it without becoming the source of truth.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .access_policy import (
    ReadPolicy,
    SENSITIVITY_RANK,
    can_read_memory,
    normalize_read_policy,
)
from .db_lifecycle import normalize_now, parse_timestamp
from .temporal import temporal_state


APPROVED_STATES = frozenset({"approved", "promoted", "active"})
KNOWN_SCOPES = frozenset({"private", "project", "shared", "public"})


@dataclass(frozen=True)
class GovernanceReadDecision:
    """Stable, JSON-safe decision trace for one canonical memory row."""

    allowed: bool
    reason_codes: tuple[str, ...]
    temporal_state: str
    evaluated_at: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        return payload


def superseded_ids_from_snapshot(
    rows: Iterable[dict[str, Any]],
    *,
    as_of: str = "",
) -> set[int]:
    """Build effective supersession state from the full canonical snapshot.

    A future, expired, deleted, unapproved, or privacy-blocked revision must not
    hide the older current fact before the replacement itself becomes valid.
    """
    if as_of and parse_timestamp(as_of) is None:
        raise ValueError("as_of must be a valid ISO-like timestamp")
    now_dt, _now_text = normalize_now(as_of or None)
    out: set[int] = set()
    for row in rows:
        if str(row.get("approval_state") or "approved").strip().lower() not in APPROVED_STATES:
            continue
        if str(row.get("status") or "active").strip().lower() != "active":
            continue
        if str(row.get("privacy_status") or "pass").strip().lower() == "fail":
            continue
        expires_text = str(row.get("expires_at") or "").strip()
        expires_at = parse_timestamp(expires_text)
        if (expires_text and expires_at is None) or (expires_at is not None and expires_at <= now_dt):
            continue
        valid_from_text = str(row.get("valid_from") or "").strip()
        valid_until_text = str(row.get("valid_until") or "").strip()
        valid_from = parse_timestamp(valid_from_text)
        valid_until = parse_timestamp(valid_until_text)
        if (valid_from_text and valid_from is None) or (valid_until_text and valid_until is None):
            continue
        if valid_from is not None and valid_from > now_dt:
            continue
        if valid_until is not None and valid_until <= now_dt:
            continue
        value = row.get("supersedes_id")
        if value in (None, ""):
            continue
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            out.add(number)
    return out


def evaluate_governed_read(
    row: dict[str, Any],
    *,
    policy: ReadPolicy | None = None,
    agent_id: str = "",
    include_private: bool = False,
    max_sensitivity: str = "",
    as_of: str = "",
    superseded_ids: set[int] | None = None,
    require_provenance: bool = False,
) -> GovernanceReadDecision:
    """Evaluate a canonical row under Vault's strict current-memory contract.

    Access authorization is delegated to :mod:`vault.access_policy`.  This
    helper adds the lifecycle checks that legacy search keeps opt-in.
    """
    requested_sensitivity_cap = str(
        policy.max_sensitivity if policy is not None else max_sensitivity
    ).strip().lower()
    read_policy = normalize_read_policy(
        agent_id=policy.agent_id if policy is not None else agent_id,
        include_private=policy.include_private if policy is not None else include_private,
        max_sensitivity=requested_sensitivity_cap,
        allowed_statuses=("active",),
    )
    if as_of and parse_timestamp(str(as_of)) is None:
        raise ValueError("as_of must be a valid ISO-like timestamp")
    now_dt, now_text = normalize_now(as_of or None)
    reasons: list[str] = []
    if requested_sensitivity_cap and requested_sensitivity_cap not in SENSITIVITY_RANK:
        reasons.append("invalid_max_sensitivity")

    approval_state = str(row.get("approval_state") or "approved").strip().lower()
    if approval_state not in APPROVED_STATES:
        reasons.append("unapproved")

    status = str(row.get("status") or "active").strip().lower()
    if status == "deleted":
        reasons.append("deleted")
    elif status != "active":
        reasons.append("inactive")

    if str(row.get("privacy_status") or "pass").strip().lower() == "fail":
        reasons.append("privacy_blocked")

    # Status is classified above.  Evaluate ACL/sensitivity with a status-only
    # copy so a tombstone is not mislabeled as authorization failure, while the
    # strict policy remains active even when the caller omitted agent identity.
    scope = str(row.get("scope") or "project").strip().lower()
    sensitivity = str(row.get("sensitivity") or "low").strip().lower()
    if scope not in KNOWN_SCOPES:
        reasons.append("unknown_scope")
    if sensitivity not in SENSITIVITY_RANK:
        reasons.append("unknown_sensitivity")

    access_row = row if status == "active" else {**row, "status": "active"}
    if not can_read_memory(access_row, read_policy):
        sensitivity_rank = SENSITIVITY_RANK.get(sensitivity, 0)
        cap = read_policy.max_sensitivity
        if cap and sensitivity_rank > SENSITIVITY_RANK[cap]:
            reasons.append("sensitivity_capped")
        elif sensitivity == "restricted":
            reasons.append("restricted")
        elif scope == "private":
            reasons.append("private")
        else:
            reasons.append("unauthorized")
    if scope == "private":
        private_access_row = {**access_row, "sensitivity": "low"}
        if not can_read_memory(private_access_row, read_policy):
            reasons.append("private")

    expires_text = str(row.get("expires_at") or "").strip()
    expires_at = parse_timestamp(expires_text)
    if expires_text and expires_at is None:
        reasons.append("invalid_expiry")
    elif expires_at is not None and expires_at <= now_dt:
        reasons.append("expired")

    temporal_values = [str(row.get(field) or "").strip() for field in ("valid_from", "valid_until")]
    if any(value and parse_timestamp(value) is None for value in temporal_values):
        reasons.append("invalid_temporal_metadata")

    row_id = _positive_int(row.get("id")) or _positive_int(row.get("vault_knowledge_id"))
    temporal_row = row if _positive_int(row.get("id")) is not None else {**row, "id": row_id}
    state = temporal_state(
        temporal_row,
        as_of=now_text,
        superseded_ids=superseded_ids or set(),
    )
    if row_id is not None and row_id in (superseded_ids or set()):
        reasons.append("superseded")
    elif state == "past":
        reasons.append("temporal_past")
    elif state == "future":
        reasons.append("temporal_future")

    if require_provenance and not _has_provenance(row):
        reasons.append("missing_provenance")

    ordered = tuple(dict.fromkeys(reasons))
    return GovernanceReadDecision(
        allowed=not ordered,
        reason_codes=ordered,
        temporal_state=state,
        evaluated_at=now_text,
    )


def _has_provenance(row: dict[str, Any]) -> bool:
    return any(
        str(row.get(field) or "").strip()
        for field in ("source", "source_ref", "vault_knowledge_id", "memory_candidate_id")
    )


def _positive_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None
