"""Dream candidate queue helpers for Guardrails Dream/Librarian.

DL-1 deliberately writes only to the local candidate queue. It does not create
formal knowledge rows, write raw/ files, or invoke sync.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

SOURCE_TYPES = {"session", "feishu", "cron", "subagent", "manual", "mcp"}
CATEGORIES = {"error", "technique", "decision", "workflow", "observation", "general"}
CLASSIFICATIONS = {"shared_knowledge", "private_draft", "no_write"}
PRIVACY_STATUSES = {"unknown", "clear", "redact_required", "private_only", "blocked"}
DEDUPE_STATUSES = {"unknown", "unique", "duplicate", "near_duplicate", "conflict"}
CANDIDATE_STATUSES = {
    "pending",
    "ready_for_review",
    "approved",
    "promoted",
    "merge_suggested",
    "discarded",
    "blocked",
}
RECOMMENDED_ACTIONS = {"review", "promote", "merge", "discard", "block", "ask_arthur"}
REVIEW_DECISIONS = {"approved", "merge_suggested", "discarded", "blocked", "ask_arthur"}
_TERMINAL_STATUSES = {"blocked", "discarded", "promoted"}
_APPROVAL_BLOCKING_DEDUPE_STATUSES = {"duplicate", "near_duplicate", "conflict"}
_DECISION_STATUS = {
    "approved": "approved",
    "merge_suggested": "merge_suggested",
    "discarded": "discarded",
    "blocked": "blocked",
    "ask_arthur": "ready_for_review",
}

_JSON_FIELDS = {
    "source_refs": "source_refs_json",
    "tags": "tags_json",
    "privacy_flags": "privacy_flags_json",
    "dedupe_candidates": "dedupe_candidates_json",
    "audit_log": "audit_log_json",
}

_REQUIRED_TEXT_FIELDS = (
    "source_type",
    "source_agent",
    "proposed_title",
    "summary",
    "content_draft",
    "category",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_candidate_id(now: str | None = None) -> str:
    date_part = (now or _now())[:10].replace("-", "")
    return f"dream_{date_part}_{uuid.uuid4().hex[:8]}"


def _validate_enum(field: str, value: str, allowed: set[str]) -> str:
    if value not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        raise ValueError(f"{field} must be one of: {allowed_list}")
    return value


def _ensure_text(candidate: dict[str, Any], field: str) -> str:
    value = candidate.get(field, "")
    if value is None or str(value) == "":
        raise ValueError(f"{field} is required")
    return str(value)


def _json_value(candidate: dict[str, Any], field: str, json_field: str) -> list[Any] | dict[str, Any]:
    if field in candidate:
        value = candidate[field]
    elif json_field in candidate:
        value = candidate[json_field]
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive branch
                raise ValueError(f"{field} must be valid JSON") from exc
    else:
        value = []

    if not isinstance(value, (list, dict)):
        raise ValueError(f"{field} must be a list or dict")
    return value


def _json_dumps(value: list[Any] | dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _json_loads(raw: str | None, field: str) -> list[Any] | dict[str, Any]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - invalid legacy DB state
        raise ValueError(f"{field} contains invalid JSON") from exc
    if not isinstance(value, (list, dict)):
        raise ValueError(f"{field} must contain a list or dict")
    return value


def _row_dict(row: sqlite3.Row | tuple[Any, ...], description: Any) -> dict[str, Any]:
    if isinstance(row, sqlite3.Row):
        return dict(row)
    return {description[index][0]: row[index] for index in range(len(row))}


def _row_to_candidate(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    for field, json_field in _JSON_FIELDS.items():
        item[field] = _json_loads(item.get(json_field), field)
    return item


def _load_audit_log(conn: sqlite3.Connection, candidate_id: str) -> list[Any]:
    cursor = conn.execute(
        "SELECT audit_log_json FROM knowledge_candidates WHERE candidate_id=?",
        (candidate_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise KeyError(f"candidate not found: {candidate_id}")
    row_dict = _row_dict(row, cursor.description)
    audit_log = _json_loads(row_dict["audit_log_json"], "audit_log")
    if not isinstance(audit_log, list):
        raise ValueError("audit_log must be a list")
    return audit_log


def _load_candidate_decision_metadata(conn: sqlite3.Connection, candidate_id: str) -> dict[str, Any]:
    cursor = conn.execute(
        """SELECT status, privacy_status, classification, dedupe_status
           FROM knowledge_candidates
           WHERE candidate_id=?""",
        (candidate_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise KeyError(f"candidate not found: {candidate_id}")
    return _row_dict(row, cursor.description)


def create_candidate(conn: sqlite3.Connection, candidate: dict) -> str:
    """Create a dream candidate row and return its candidate_id."""
    now = _now()
    candidate_id = str(candidate.get("candidate_id") or _new_candidate_id(now))

    values: dict[str, Any] = {
        "candidate_id": candidate_id,
        "created_at": str(candidate.get("created_at") or now),
        "updated_at": str(candidate.get("updated_at") or now),
        "source_session_id": candidate.get("source_session_id"),
        "source_channel": candidate.get("source_channel"),
        "decision_reason": str(candidate.get("decision_reason") or ""),
        "reviewer": str(candidate.get("reviewer") or ""),
        "reviewed_at": candidate.get("reviewed_at"),
        "trust_initial": float(candidate.get("trust_initial", 0.4)),
        "freshness_initial": float(candidate.get("freshness_initial", 1.0)),
        "convergence_status_initial": str(
            candidate.get("convergence_status_initial") or "unknown"
        ),
    }
    for field in _REQUIRED_TEXT_FIELDS:
        values[field] = _ensure_text(candidate, field)

    values["source_type"] = _validate_enum("source_type", values["source_type"], SOURCE_TYPES)
    values["category"] = _validate_enum("category", values["category"], CATEGORIES)
    values["classification"] = _validate_enum(
        "classification",
        str(candidate.get("classification") or "shared_knowledge"),
        CLASSIFICATIONS,
    )
    values["privacy_status"] = _validate_enum(
        "privacy_status",
        str(candidate.get("privacy_status") or "unknown"),
        PRIVACY_STATUSES,
    )
    values["dedupe_status"] = _validate_enum(
        "dedupe_status",
        str(candidate.get("dedupe_status") or "unknown"),
        DEDUPE_STATUSES,
    )
    values["status"] = _validate_enum(
        "status",
        str(candidate.get("status") or "pending"),
        CANDIDATE_STATUSES,
    )
    values["recommended_action"] = _validate_enum(
        "recommended_action",
        str(candidate.get("recommended_action") or "review"),
        RECOMMENDED_ACTIONS,
    )

    for field, json_field in _JSON_FIELDS.items():
        values[json_field] = _json_dumps(_json_value(candidate, field, json_field))

    columns = [
        "candidate_id",
        "created_at",
        "updated_at",
        "source_type",
        "source_agent",
        "source_session_id",
        "source_channel",
        "source_refs_json",
        "proposed_title",
        "summary",
        "content_draft",
        "category",
        "tags_json",
        "classification",
        "privacy_status",
        "privacy_flags_json",
        "dedupe_status",
        "dedupe_candidates_json",
        "status",
        "recommended_action",
        "decision_reason",
        "reviewer",
        "reviewed_at",
        "trust_initial",
        "freshness_initial",
        "convergence_status_initial",
        "audit_log_json",
    ]
    placeholders = ", ".join("?" for _ in columns)
    conn.execute(
        f"INSERT INTO knowledge_candidates ({', '.join(columns)}) VALUES ({placeholders})",
        [values[column] for column in columns],
    )
    conn.commit()
    return candidate_id


def list_candidates(
    conn: sqlite3.Connection,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """List dream candidates, newest first, with JSON fields decoded."""
    if status is not None:
        _validate_enum("status", status, CANDIDATE_STATUSES)
    limit = max(1, int(limit))
    if status is None:
        cursor = conn.execute(
            "SELECT * FROM knowledge_candidates ORDER BY created_at DESC, candidate_id DESC LIMIT ?",
            (limit,),
        )
    else:
        cursor = conn.execute(
            """SELECT * FROM knowledge_candidates
               WHERE status=?
               ORDER BY created_at DESC, candidate_id DESC
               LIMIT ?""",
            (status, limit),
        )
    return [_row_to_candidate(_row_dict(row, cursor.description)) for row in cursor.fetchall()]


def update_candidate_status(
    conn: sqlite3.Connection,
    candidate_id: str,
    status: str,
    reason: str,
    reviewer: str = "",
) -> None:
    """Update candidate status and append a status audit event."""
    _validate_enum("status", status, CANDIDATE_STATUSES)
    now = _now()
    audit_log = _load_audit_log(conn, candidate_id)
    audit_log.append(
        {
            "event": "status_updated",
            "status": status,
            "reason": reason,
            "reviewer": reviewer,
            "created_at": now,
        }
    )
    cursor = conn.execute(
        """UPDATE knowledge_candidates
           SET status=?, decision_reason=?, reviewer=?, reviewed_at=?, updated_at=?, audit_log_json=?
           WHERE candidate_id=?""",
        (status, reason, reviewer, now, now, _json_dumps(audit_log), candidate_id),
    )
    if cursor.rowcount == 0:  # pragma: no cover - _load_audit_log catches this first
        raise KeyError(f"candidate not found: {candidate_id}")
    conn.commit()


def decide_candidate(
    conn: sqlite3.Connection,
    candidate_id: str,
    *,
    decision: str,
    reason: str,
    reviewer: str,
) -> dict[str, Any]:
    """Persist a review decision without promoting, writing raw files, or syncing."""
    _validate_enum("decision", decision, REVIEW_DECISIONS)
    clean_reason = str(reason or "").strip()
    clean_reviewer = str(reviewer or "").strip()
    if not clean_reason:
        raise ValueError("reason is required")
    if not clean_reviewer:
        raise ValueError("reviewer is required")

    status = _DECISION_STATUS[decision]
    metadata = _load_candidate_decision_metadata(conn, candidate_id)
    _validate_decision_safety(
        decision=decision,
        next_status=status,
        current_status=str(metadata.get("status") or "pending"),
        privacy_status=str(metadata.get("privacy_status") or "unknown"),
        classification=str(metadata.get("classification") or "shared_knowledge"),
        dedupe_status=str(metadata.get("dedupe_status") or "unknown"),
    )
    now = _now()
    audit_log = _load_audit_log(conn, candidate_id)
    audit_log.append(
        {
            "event": "review_decision",
            "decision": decision,
            "status": status,
            "reason": clean_reason,
            "reviewer": clean_reviewer,
            "created_at": now,
            "formal_knowledge_written": False,
            "raw_written": False,
            "sync_invoked": False,
        }
    )
    if decision == "ask_arthur":
        cursor = conn.execute(
            """UPDATE knowledge_candidates
               SET status=?, recommended_action=?, decision_reason=?, reviewer=?,
                   reviewed_at=?, updated_at=?, audit_log_json=?
               WHERE candidate_id=?""",
            (
                status,
                "ask_arthur",
                clean_reason,
                clean_reviewer,
                now,
                now,
                _json_dumps(audit_log),
                candidate_id,
            ),
        )
    else:
        cursor = conn.execute(
            """UPDATE knowledge_candidates
               SET status=?, decision_reason=?, reviewer=?, reviewed_at=?, updated_at=?, audit_log_json=?
               WHERE candidate_id=?""",
            (status, clean_reason, clean_reviewer, now, now, _json_dumps(audit_log), candidate_id),
        )
    if cursor.rowcount == 0:  # pragma: no cover - _load_audit_log catches this first
        raise KeyError(f"candidate not found: {candidate_id}")
    conn.commit()
    return {
        "success": True,
        "candidate_id": candidate_id,
        "decision": decision,
        "status": status,
        "reason": clean_reason,
        "reviewer": clean_reviewer,
        "reviewed_at": now,
        "formal_knowledge_written": False,
        "raw_written": False,
        "sync_invoked": False,
    }


def _validate_decision_safety(
    *,
    decision: str,
    next_status: str,
    current_status: str,
    privacy_status: str,
    classification: str,
    dedupe_status: str,
) -> None:
    """Enforce DL-2.5 safety gates before persisting review decisions."""
    if current_status in _TERMINAL_STATUSES and current_status != next_status:
        raise ValueError(f"cannot change terminal status {current_status} to {decision}")

    if decision == "approved":
        if privacy_status != "clear":
            raise ValueError(f"approved requires privacy_status=clear (got {privacy_status})")
        if classification != "shared_knowledge":
            raise ValueError(
                f"approved requires classification=shared_knowledge (got {classification})"
            )
        if dedupe_status in _APPROVAL_BLOCKING_DEDUPE_STATUSES:
            raise ValueError(f"approved is blocked by dedupe_status={dedupe_status}")

    if decision == "merge_suggested":
        if privacy_status in {"blocked", "private_only"}:
            raise ValueError(f"privacy_status {privacy_status} cannot be merge_suggested")
        if classification == "no_write":
            raise ValueError("classification no_write cannot be merge_suggested")


def run_candidate_privacy_preflight(conn: sqlite3.Connection, candidate_id: str) -> dict[str, Any]:
    """Scan a candidate recursively and persist safe privacy metadata only."""
    from guardrails_lite.privacy_scanner import scan_entry

    cursor = conn.execute("SELECT * FROM knowledge_candidates WHERE candidate_id=?", (candidate_id,))
    row = cursor.fetchone()
    if row is None:
        raise KeyError(f"candidate not found: {candidate_id}")
    candidate = _row_to_candidate(_row_dict(row, cursor.description))
    scan_candidate = {
        "source_type": candidate.get("source_type"),
        "source_agent": candidate.get("source_agent"),
        "source_session_id": candidate.get("source_session_id"),
        "source_channel": candidate.get("source_channel"),
        "source_refs": candidate.get("source_refs"),
        "proposed_title": candidate.get("proposed_title"),
        "summary": candidate.get("summary"),
        "content_draft": candidate.get("content_draft"),
        "category": candidate.get("category"),
        "tags": candidate.get("tags"),
        "audit_log": candidate.get("audit_log"),
    }
    result = scan_entry(
        scan_candidate,
        context={
            "entry_point": "dream",
            "intended_visibility": "shared",
            "source_channel": candidate.get("source_channel") or "unknown",
            "actor": candidate.get("source_agent") or "unknown",
        },
    )
    result_dict = result.to_dict()
    privacy_status = result.outcome
    recommended_action = _privacy_recommended_action(privacy_status)
    status = "blocked" if privacy_status == "blocked" else str(candidate.get("status") or "pending")
    now = _now()

    audit_log = _load_audit_log(conn, candidate_id)
    audit_log.append(
        {
            "event": "privacy_preflight",
            "created_at": now,
            "privacy_status": privacy_status,
            "finding_count": len(result.findings),
            "by_kind": result.audit_summary.get("by_kind", {}),
            "by_rule": result.audit_summary.get("by_rule", {}),
            "max_severity": result.audit_summary.get("max_severity", "none"),
        }
    )
    cursor = conn.execute(
        """UPDATE knowledge_candidates
           SET privacy_status=?, privacy_flags_json=?, recommended_action=?, status=?, audit_log_json=?, updated_at=?
           WHERE candidate_id=?""",
        (
            privacy_status,
            _json_dumps(result_dict["findings"]),
            recommended_action,
            status,
            _json_dumps(audit_log),
            now,
            candidate_id,
        ),
    )
    if cursor.rowcount == 0:  # pragma: no cover - row lookup catches this first
        raise KeyError(f"candidate not found: {candidate_id}")
    conn.commit()
    return {
        "candidate_id": candidate_id,
        "privacy_status": privacy_status,
        "privacy_flags": result_dict["findings"],
        "recommended_action": recommended_action,
        "audit_summary": result_dict["audit_summary"],
    }


def _privacy_recommended_action(privacy_status: str) -> str:
    if privacy_status == "blocked":
        return "block"
    if privacy_status == "private_only":
        return "ask_arthur"
    return "review"


def append_candidate_audit(
    conn: sqlite3.Connection,
    candidate_id: str,
    event: dict,
) -> None:
    """Append an arbitrary dict audit event to a candidate."""
    if not isinstance(event, dict):
        raise ValueError("event must be a dict")
    now = _now()
    audit_log = _load_audit_log(conn, candidate_id)
    stored_event = dict(event)
    stored_event.setdefault("created_at", now)
    audit_log.append(stored_event)
    cursor = conn.execute(
        """UPDATE knowledge_candidates
           SET audit_log_json=?, updated_at=?
           WHERE candidate_id=?""",
        (_json_dumps(audit_log), now, candidate_id),
    )
    if cursor.rowcount == 0:  # pragma: no cover - _load_audit_log catches this first
        raise KeyError(f"candidate not found: {candidate_id}")
    conn.commit()
