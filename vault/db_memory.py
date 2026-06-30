"""Memory candidate and feedback helpers for VaultDB."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import sqlite3
from typing import Any

from .governance import normalize_governance_metadata
from .db_runtime import sqlite_write_with_retry


def add_memory_candidate(conn: sqlite3.Connection, candidate: dict) -> str:
    """Insert a memory candidate and return its id."""
    now = datetime.now(timezone.utc).isoformat()
    values = dict(candidate)
    values.setdefault("created_at", now)
    values.setdefault("updated_at", now)
    values.setdefault("promoted_knowledge_id", None)
    governance = normalize_governance_metadata(
        scope=values.get("scope", "project"),
        sensitivity=values.get("sensitivity", "low"),
        owner_agent=values.get("owner_agent", ""),
        allowed_agents=values.get("allowed_agents"),
        memory_type=values.get("memory_type", "knowledge"),
        expires_at=values.get("expires_at", ""),
        valid_from=values.get("valid_from", ""),
        valid_until=values.get("valid_until", ""),
        supersedes_id=values.get("supersedes_id"),
    )
    values.update(governance)
    def write() -> None:
        conn.execute(
            """INSERT INTO memory_candidates
               (id, created_at, updated_at, title, content, layer, category,
                tags, trust, source, source_ref, reason, status,
                privacy_status, duplicate_status, quality_status, gate_payload_json,
                promoted_knowledge_id,
                scope, sensitivity, owner_agent, allowed_agents, memory_type, expires_at,
                valid_from, valid_until, supersedes_id)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                values["id"],
                values["created_at"],
                values["updated_at"],
                values["title"],
                values["content"],
                values["layer"],
                values["category"],
                values["tags"],
                values["trust"],
                values["source"],
                values["source_ref"],
                values["reason"],
                values["status"],
                values["privacy_status"],
                values["duplicate_status"],
                values.get("quality_status", "pass"),
                values["gate_payload_json"],
                values.get("promoted_knowledge_id"),
                values["scope"],
                values["sensitivity"],
                values["owner_agent"],
                values["allowed_agents"],
                values["memory_type"],
                values["expires_at"],
                values["valid_from"],
                values["valid_until"],
                values["supersedes_id"],
            ),
        )
        conn.commit()

    sqlite_write_with_retry(write, rollback=conn.rollback)
    return str(values["id"])


def get_memory_candidate(conn: sqlite3.Connection, candidate_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM memory_candidates WHERE id=?", (candidate_id,)).fetchone()
    return dict(row) if row else None


def update_memory_candidate(
    conn: sqlite3.Connection,
    candidate_id: str,
    update_columns: set[str] | frozenset[str],
    **fields: Any,
) -> bool:
    if not fields:
        return False
    invalid = set(fields) - set(update_columns)
    if invalid:
        raise ValueError(f"invalid memory candidate update field(s): {sorted(invalid)}")
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    sets = ", ".join(f"{key}=?" for key in fields)
    values = list(fields.values()) + [candidate_id]
    cur = conn.execute(f"UPDATE memory_candidates SET {sets} WHERE id=?", values)
    conn.commit()
    return cur.rowcount > 0


def list_memory_candidates(
    conn: sqlite3.Connection,
    status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    query = "SELECT * FROM memory_candidates"
    params: list[Any] = []
    if status:
        query += " WHERE status=?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def record_memory_feedback(conn: sqlite3.Connection, event: dict) -> int:
    """Record a candidate outcome event for automation evaluation."""
    now = datetime.now(timezone.utc).isoformat()
    values = dict(event)
    values.setdefault("created_at", now)
    values.setdefault("event_type", "candidate_outcome")
    values.setdefault("candidate_id", "")
    values.setdefault("knowledge_id", None)
    values.setdefault("source", "")
    values.setdefault("source_ref", "")
    values.setdefault("memory_type", "")
    values.setdefault("category", "")
    values.setdefault("outcome", "")
    values.setdefault("score", 0.0)
    values.setdefault("reason", "")
    payload = values.get("payload_json", "{}")
    if isinstance(payload, (dict, list)):
        payload = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    values["payload_json"] = str(payload or "{}")
    def write() -> int:
        cur = conn.execute(
            """INSERT INTO memory_feedback_events
               (created_at, event_type, candidate_id, knowledge_id, source, source_ref,
                memory_type, category, outcome, score, reason, payload_json)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                values["created_at"],
                values["event_type"],
                values["candidate_id"],
                values.get("knowledge_id"),
                values["source"],
                values["source_ref"],
                values["memory_type"],
                values["category"],
                values["outcome"],
                float(values.get("score") or 0.0),
                values["reason"],
                values["payload_json"],
            ),
        )
        conn.commit()
        return int(cur.lastrowid)

    return sqlite_write_with_retry(write, rollback=conn.rollback)


def list_memory_feedback(
    conn: sqlite3.Connection,
    *,
    limit: int = 100,
    source: str = "",
    memory_type: str = "",
    outcome: str = "",
) -> list[dict]:
    query = "SELECT * FROM memory_feedback_events"
    clauses = []
    params: list[Any] = []
    if source:
        clauses.append("source = ?")
        params.append(source)
    if memory_type:
        clauses.append("memory_type = ?")
        params.append(memory_type)
    if outcome:
        clauses.append("outcome = ?")
        params.append(outcome)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC, id DESC LIMIT ?"
    params.append(max(1, min(int(limit or 100), 1000)))
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def memory_feedback_summary(conn: sqlite3.Connection, *, limit: int = 1000) -> dict:
    """Return JSON-safe feedback aggregates for automation evaluation."""
    limit_i = max(1, min(int(limit or 1000), 10000))
    rows = conn.execute(
        """SELECT * FROM memory_feedback_events
           ORDER BY created_at DESC, id DESC
           LIMIT ?""",
        (limit_i,),
    ).fetchall()
    events = [dict(row) for row in rows]
    outcome_counts: dict[str, int] = {}
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in events:
        outcome = str(row.get("outcome") or "unknown")
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        key = (
            str(row.get("source") or ""),
            str(row.get("memory_type") or ""),
            str(row.get("category") or ""),
        )
        group = groups.setdefault(
            key,
            {
                "source": key[0],
                "memory_type": key[1],
                "category": key[2],
                "total": 0,
                "accepted": 0,
                "promoted": 0,
                "rejected": 0,
                "blocked": 0,
                "deferred": 0,
                "score_sum": 0.0,
            },
        )
        group["total"] += 1
        group["score_sum"] += float(row.get("score") or 0.0)
        if outcome in {"accepted", "promoted", "rejected", "blocked", "deferred"}:
            group[outcome] += 1

    grouped = []
    for group in groups.values():
        total = int(group["total"] or 0)
        accepted = int(group["accepted"] or 0)
        promoted = int(group["promoted"] or 0)
        score_sum = float(group.pop("score_sum", 0.0))
        group["positive_outcomes"] = accepted + promoted
        group["acceptance_rate"] = (accepted + promoted) / total if total else 0.0
        group["average_score"] = score_sum / total if total else 0.0
        grouped.append(group)
    grouped.sort(key=lambda item: (item["acceptance_rate"], item["total"]), reverse=True)
    return {
        "event_count": len(events),
        "outcome_counts": outcome_counts,
        "groups": grouped,
        "recent_events": events[: min(20, limit_i)],
    }
