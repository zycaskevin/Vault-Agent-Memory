"""Candidate queue convergence helpers for governed automation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .automation_policy import policy_float as _policy_float
from .automation_policy import policy_int as _policy_int
from .automation_policy import policy_list as _policy_list
from .db import VaultDB


def _candidate_tags(row: dict[str, Any]) -> set[str]:
    raw = row.get("tags") or ""
    if isinstance(raw, list):
        values = raw
    else:
        values = str(raw).replace(";", ",").split(",")
    return {str(value or "").strip().lower() for value in values if str(value or "").strip()}


def _dream_noise_reason(row: dict[str, Any], policy: dict[str, Any]) -> tuple[bool, str, str]:
    source = str(row.get("source") or "").strip().lower()
    memory_type = str(row.get("memory_type") or "").strip().lower()
    scope = str(row.get("scope") or "").strip().lower()
    sensitivity = str(row.get("sensitivity") or "").strip().lower()
    trust = float(row.get("trust") or 0.0)
    tags = _candidate_tags(row)
    category = str(row.get("category") or "").strip().lower()
    source_ref = str(row.get("source_ref") or "").strip().lower()
    title = str(row.get("title") or "").strip().lower()

    allowed_types = set(_policy_list(policy, "auto_close_dream_noise_memory_types"))
    allowed_scopes = set(_policy_list(policy, "auto_close_dream_noise_scopes"))
    allowed_sensitivities = set(_policy_list(policy, "auto_close_dream_noise_sensitivities"))
    allowed_tags = set(_policy_list(policy, "auto_close_dream_noise_tags"))
    max_trust = _policy_float(policy, "auto_close_dream_noise_max_trust", 0.5)

    if source != "dream":
        return False, f"source_not_dream:{source or 'empty'}", ""
    if memory_type not in allowed_types:
        return False, f"memory_type_not_allowed:{memory_type or 'empty'}", ""
    if scope not in allowed_scopes:
        return False, f"scope_not_allowed:{scope or 'empty'}", ""
    if sensitivity not in allowed_sensitivities:
        return False, f"sensitivity_not_allowed:{sensitivity or 'empty'}", ""
    if str(row.get("privacy_status") or "") != "pass":
        return False, f"privacy_gate_not_pass:{row.get('privacy_status') or 'unknown'}", ""
    if trust > max_trust:
        return False, "trust_above_auto_close_threshold", ""

    signals = tags | {category}
    if "dedup" in source_ref or "duplicate" in title or "consolidat" in title:
        signals.add("dedup")
    if "metadata" in title:
        signals.add("metadata")
    matched = sorted(signals & allowed_tags)
    if not matched:
        return False, "dream_noise_tag_not_allowed", ""
    return True, "eligible low-risk Dream queue noise", matched[0]


def auto_close_low_risk_dream_noise_candidates(
    db: VaultDB,
    *,
    project: Path,
    policy: dict[str, Any],
    apply: bool,
) -> dict[str, Any]:
    """Reject low-risk Dream review noise so governed-auto queues converge.

    This path never promotes candidates, never deletes rows, and never mutates
    active memory. It only records a review outcome for narrow Dream suggestions
    that are safe to close automatically.
    """
    enabled = bool(policy.get("auto_close_low_risk_dream_noise", False))
    max_per_run = max(0, min(_policy_int(policy, "auto_close_dream_noise_max_per_run", 100), 200))
    payload: dict[str, Any] = {
        "action": "auto_close_low_risk_dream_noise_candidates",
        "enabled": enabled,
        "apply": bool(apply),
        "status": "disabled" if not enabled else "preview",
        "eligible_count": 0,
        "closed_count": 0,
        "skipped_count": 0,
        "remaining_dream_candidate_count": 0,
        "remaining_auto_closeable_count": 0,
        "closed_tags": {},
        "items": [],
        "safety": {
            "policy_gated": True,
            "requires_apply": True,
            "hard_delete": False,
            "writes_active_memory": False,
            "promotes_candidates": False,
            "private_high_restricted_auto_close": False,
            "review_feedback_recorded": True,
        },
        "next_action": "Review automation_policy.yaml before widening Dream queue convergence.",
    }
    if not enabled or max_per_run <= 0:
        return payload

    rows = db.list_memory_candidates(status="candidate", limit=1000)
    eligible: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for row in rows:
        ok, reason, matched_tag = _dream_noise_reason(row, policy)
        item = {
            "candidate_id": row.get("id", ""),
            "title": row.get("title", ""),
            "source": row.get("source", ""),
            "source_ref": row.get("source_ref", ""),
            "memory_type": row.get("memory_type", ""),
            "scope": row.get("scope", ""),
            "sensitivity": row.get("sensitivity", ""),
            "trust": float(row.get("trust") or 0.0),
            "eligible": ok,
            "reason": reason,
            "matched_tag": matched_tag,
        }
        if ok and len(eligible) < max_per_run:
            eligible.append(item)
        else:
            if ok:
                item["eligible"] = False
                item["reason"] = "auto_close_dream_noise_max_per_run reached"
            skipped.append(item)

    payload["eligible_count"] = len(eligible)
    payload["skipped_count"] = len(skipped)
    payload["items"] = eligible + skipped[: max(0, 20 - len(eligible))]
    if not apply:
        payload["next_action"] = "Re-run with --apply to close eligible low-risk Dream queue noise."
        return payload

    from .memory import review_candidate

    closed: list[dict[str, Any]] = []
    closed_tags: dict[str, int] = {}
    reason = (
        "auto-closed low-risk Dream metadata/dedup suggestion; no active memory "
        "change and no candidate promotion"
    )
    for item in eligible:
        result = review_candidate(
            db,
            str(item.get("candidate_id") or ""),
            outcome="rejected",
            reason=reason,
            score=0.0,
        )
        tag = str(item.get("matched_tag") or "dream")
        closed_tags[tag] = closed_tags.get(tag, 0) + 1
        closed.append({**item, "review_status": result.get("status", "")})

    remaining = db.list_memory_candidates(status="candidate", limit=1000)
    remaining_dream = [row for row in remaining if str(row.get("source") or "").strip().lower() == "dream"]
    remaining_auto_closeable = [row for row in remaining if _dream_noise_reason(row, policy)[0]]
    payload["status"] = "completed"
    payload["closed_count"] = len(closed)
    payload["closed_tags"] = closed_tags
    payload["remaining_dream_candidate_count"] = len(remaining_dream)
    payload["remaining_auto_closeable_count"] = len(remaining_auto_closeable)
    payload["items"] = closed + skipped[: max(0, 20 - len(closed))]
    payload["next_action"] = (
        "No low-risk Dream queue noise remains."
        if not remaining_auto_closeable
        else "Run the next automation cycle to close remaining low-risk Dream queue noise."
    )
    return payload
