"""Learning-policy helpers for automation review feedback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LEARNING_POLICY_FILE = Path("reports") / "automation" / "learning_policy.json"

def _feedback_learning_policy(
    groups: list[dict[str, Any]],
    *,
    generated_at: str,
    event_count: int,
    min_events: int,
    readiness: str,
) -> dict[str, Any]:
    """Convert feedback aggregates into bounded, auditable curation hints."""
    rules = []
    for group in groups:
        total = int(group.get("total") or 0)
        acceptance = float(group.get("acceptance_rate") or 0.0)
        average_score = float(group.get("average_score") or 0.0)
        recommendation = str(group.get("recommendation") or "collect_more_feedback")
        enough_events = total >= min_events

        if not enough_events:
            priority_multiplier = 1.0
            confidence = round(min(0.49, total / max(1, min_events) * 0.49), 3)
            action = "observe"
            reason = "Not enough reviewed outcomes for this source/type/category group."
        elif recommendation == "prefer":
            priority_multiplier = 1.15
            confidence = _learning_confidence(total, min_events, acceptance)
            action = "prefer_candidates"
            reason = "This group has earned a high promotion rate in reviewed outcomes."
        elif recommendation == "downgrade_or_review_policy":
            priority_multiplier = 0.85
            confidence = _learning_confidence(total, min_events, 1.0 - acceptance)
            action = "downgrade_or_require_review"
            reason = "This group has a low promotion rate and should stay under review."
        else:
            priority_multiplier = 1.0
            confidence = _learning_confidence(total, min_events, 0.5)
            action = "keep_observing"
            reason = "This group has mixed outcomes; keep collecting feedback."

        rules.append(
            {
                "selector": {
                    "source": group.get("source") or "",
                    "memory_type": group.get("memory_type") or "",
                    "category": group.get("category") or "",
                },
                "total": total,
                "acceptance_rate": round(acceptance, 4),
                "average_score": round(average_score, 4),
                "recommendation": recommendation,
                "action": action,
                "priority_multiplier": priority_multiplier,
                "confidence": confidence,
                "reason": reason,
            }
        )

    rules.sort(key=lambda item: (item["confidence"], item["total"]), reverse=True)
    return {
        "version": 1,
        "generated_at": generated_at,
        "readiness": readiness,
        "event_count": int(event_count),
        "min_events": int(min_events),
        "rules": rules,
        "bounds": {
            "priority_multiplier_min": 0.85,
            "priority_multiplier_max": 1.15,
            "no_auto_promote": True,
            "no_auto_delete": True,
            "respect_privacy_and_access_policy": True,
        },
        "principle": (
            "Learning policy is a ranking and review hint for future curation; "
            "it is not an authorization policy."
        ),
    }


def _learning_confidence(total: int, min_events: int, signal_strength: float) -> float:
    sample = min(1.0, total / max(1, min_events * 3))
    signal = max(0.0, min(1.0, signal_strength))
    return round(0.35 + sample * 0.45 + signal * 0.2, 3)


def _learning_health_rule_counts(rules: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"prefer": 0, "downgrade": 0, "observe": 0}
    for rule in rules:
        action = str(rule.get("action") or "")
        if action == "prefer_candidates":
            counts["prefer"] += 1
        elif action == "downgrade_or_require_review":
            counts["downgrade"] += 1
        else:
            counts["observe"] += 1
    return counts


def _learning_health_status(
    *,
    readiness: str,
    event_count: int,
    min_events: int,
    rule_counts: dict[str, int],
) -> str:
    if readiness != "learning" or event_count < min_events:
        return "cold_start"
    if rule_counts.get("downgrade", 0) > rule_counts.get("prefer", 0):
        return "needs_review"
    if rule_counts.get("downgrade", 0):
        return "watch"
    return "healthy"


def _learning_health_cards(evaluation: dict[str, Any], rules: list[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    outcome_counts = evaluation.get("outcome_counts") or {}
    event_count = int(evaluation.get("event_count") or 0)
    if event_count == 0:
        cards.append(
            {
                "kind": "cold_start",
                "priority": 80,
                "title": "No reviewed feedback yet",
                "reason": "Automation needs accepted/rejected/deferred review outcomes before it can learn.",
                "safe_action": "Start with review-summary cards and record feedback on only the obvious decisions.",
            }
        )
    elif str(evaluation.get("readiness") or "") != "learning":
        cards.append(
            {
                "kind": "collect_more_feedback",
                "priority": 76,
                "title": "Learning is still warming up",
                "reason": f"{event_count} feedback events are available; more reviewed outcomes are needed.",
                "safe_action": "Keep decisions feedback-only until the minimum event threshold is met.",
            }
        )
    deferred = int(outcome_counts.get("deferred") or 0)
    if deferred:
        cards.append(
            {
                "kind": "deferred_review",
                "priority": 68,
                "title": "Some review cards were deferred",
                "reason": f"{deferred} decisions were deferred and should not be treated as approval.",
                "safe_action": "Keep deferred groups observable; do not convert them into auto-approval.",
            }
        )
    for rule in rules:
        selector = rule.get("selector") or {}
        action = str(rule.get("action") or "")
        if action == "downgrade_or_require_review":
            cards.append(
                {
                    "kind": "downgrade_rule",
                    "priority": 90,
                    "title": _learning_selector_title(selector),
                    "reason": rule.get("reason", ""),
                    "safe_action": "Keep this group under review and inspect examples before widening automation.",
                    "confidence": float(rule.get("confidence") or 0.0),
                    "priority_multiplier": float(rule.get("priority_multiplier") or 1.0),
                }
            )
        elif action == "prefer_candidates":
            cards.append(
                {
                    "kind": "prefer_rule",
                    "priority": 72,
                    "title": _learning_selector_title(selector),
                    "reason": rule.get("reason", ""),
                    "safe_action": "Let ranking move these review cards earlier, but keep mutations policy-gated.",
                    "confidence": float(rule.get("confidence") or 0.0),
                    "priority_multiplier": float(rule.get("priority_multiplier") or 1.0),
                }
            )
    cards.sort(key=lambda item: (-int(item.get("priority") or 0), -float(item.get("confidence") or 0.0), item.get("title", "")))
    return cards[: max(1, min(int(limit or 5), 20))]


def _learning_health_top_rules(rules: list[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
    items = []
    for rule in rules:
        selector = rule.get("selector") or {}
        items.append(
            {
                "source": selector.get("source", ""),
                "memory_type": selector.get("memory_type", ""),
                "category": selector.get("category", ""),
                "action": rule.get("action", ""),
                "total": int(rule.get("total") or 0),
                "acceptance_rate": float(rule.get("acceptance_rate") or 0.0),
                "average_score": float(rule.get("average_score") or 0.0),
                "priority_multiplier": float(rule.get("priority_multiplier") or 1.0),
                "confidence": float(rule.get("confidence") or 0.0),
                "reason": rule.get("reason", ""),
            }
        )
    items.sort(key=lambda item: (-float(item["confidence"]), -int(item["total"]), item["source"]))
    return items[: max(1, min(int(limit or 5), 20))]


def _learning_selector_title(selector: dict[str, Any]) -> str:
    source = str(selector.get("source") or "(any source)")
    memory_type = str(selector.get("memory_type") or "(any type)")
    category = str(selector.get("category") or "(any category)")
    return f"{source} / {memory_type} / {category}"


def _learning_health_next_action(status: str) -> str:
    if status == "cold_start":
        return "Collect more review feedback before trusting learned ranking hints."
    if status == "needs_review":
        return "Inspect downgrade cards before widening automation policy or promotion rules."
    if status == "watch":
        return "Keep learned ranking enabled, but review downgraded groups in the next brief."
    return "Use learning-health as a startup/dashboard signal; keep mutation policies separate."


def _write_learning_policy(project: Path, learning_policy: dict[str, Any]) -> str:
    report_dir = project / "reports" / "automation"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "learning_policy.json"
    path.write_text(json.dumps(learning_policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path.relative_to(project))



def _load_automation_learning_policy(project: Path) -> dict[str, Any]:
    path = project / LEARNING_POLICY_FILE
    if not path.exists():
        return {
            "status": "missing",
            "path": str(LEARNING_POLICY_FILE),
            "rules": [],
            "applied_rules": 0,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "status": "invalid",
            "path": str(LEARNING_POLICY_FILE),
            "rules": [],
            "applied_rules": 0,
        }
    if not isinstance(payload, dict):
        return {
            "status": "invalid",
            "path": str(LEARNING_POLICY_FILE),
            "rules": [],
            "applied_rules": 0,
        }
    payload = dict(payload)
    payload["status"] = "loaded"
    payload["path"] = str(LEARNING_POLICY_FILE)
    payload["applied_rules"] = 0
    return payload


def _apply_learning_priority(item: dict[str, Any], learning_policy: dict[str, Any]) -> None:
    rule = _matching_learning_rule(item, learning_policy)
    item["learning_multiplier"] = 1.0
    item["learning_action"] = ""
    item["learning_reason"] = ""
    item["learning_rule_confidence"] = 0.0
    if not rule:
        return
    bounds = learning_policy.get("bounds") or {}
    lower = float(bounds.get("priority_multiplier_min") or 0.85)
    upper = float(bounds.get("priority_multiplier_max") or 1.15)
    multiplier = max(lower, min(float(rule.get("priority_multiplier") or 1.0), upper))
    base = int(item.get("base_priority") or item.get("priority") or 0)
    item["priority"] = int(round(base * multiplier))
    item["learning_multiplier"] = multiplier
    item["learning_action"] = str(rule.get("action") or "")
    item["learning_reason"] = str(rule.get("reason") or "")
    item["learning_rule_confidence"] = float(rule.get("confidence") or 0.0)
    learning_policy["applied_rules"] = int(learning_policy.get("applied_rules") or 0) + 1


def _matching_learning_rule(item: dict[str, Any], learning_policy: dict[str, Any]) -> dict[str, Any] | None:
    rules = learning_policy.get("rules") or []
    if not isinstance(rules, list):
        return None
    candidates: list[tuple[int, float, int, dict[str, Any]]] = []
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        selector = rule.get("selector") or {}
        if not isinstance(selector, dict):
            continue
        specificity = 0
        matched = True
        for field in ("source", "memory_type", "category"):
            expected = str(selector.get(field) or "").strip().lower()
            if not expected:
                continue
            actual = str(item.get(field) or "").strip().lower()
            if expected != actual:
                matched = False
                break
            specificity += 1
        if not matched or specificity == 0:
            continue
        candidates.append((specificity, float(rule.get("confidence") or 0.0), -index, rule))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][3]
