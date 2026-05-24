"""Dream candidate dedupe helpers.

DL-2 dedupe is metadata/report oriented: it compares candidate title/hash against
formal knowledge rows and stores only safe ids/titles/reasons in candidate state.
It never emits raw candidate content or formal knowledge body text.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import unicodedata
from typing import Any

from guardrails_lite.dream_queue import _json_dumps, _json_loads, _now, _row_dict, _row_to_candidate



def normalize_title(title: str) -> str:
    """Normalize titles for case/spacing/punctuation duplicate checks."""
    normalized = unicodedata.normalize("NFKC", title or "").casefold().strip()
    normalized = re.sub(r"[^\w\s-]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def check_candidate_dedupe(conn: sqlite3.Connection, candidate: dict) -> dict[str, Any]:
    """Return safe dedupe status and candidate references for a candidate dict."""
    title = str(candidate.get("proposed_title") or candidate.get("title") or "")
    normalized = normalize_title(title)
    content = str(candidate.get("content_draft") or candidate.get("content") or "")
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16] if content else ""
    candidate_tokens = _title_tokens(normalized)

    rows = _load_knowledge_metadata(conn)
    dedupe_candidates: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()

    for row in rows:
        knowledge_id = int(row["id"])
        row_title = str(row.get("title") or "")
        row_normalized = normalize_title(row_title)
        row_hash = str(row.get("content_hash") or "")
        reasons: list[str] = []

        if title and row_title == title:
            reasons.append("exact_title")
        if normalized and row_normalized == normalized:
            reasons.append("normalized_title")
        if content_hash and row_hash and row_hash == content_hash:
            reasons.append("content_hash")
        if (
            not reasons
            and _is_title_keyword_candidate(candidate_tokens, _title_tokens(row_normalized))
        ):
            reasons.append("title_keyword")

        for reason in reasons:
            key = (knowledge_id, reason)
            if key in seen:
                continue
            seen.add(key)
            dedupe_candidates.append(
                {
                    "knowledge_id": knowledge_id,
                    "title": row_title,
                    "reason": reason,
                }
            )

    dedupe_candidates.sort(key=lambda item: (_reason_rank(item["reason"]), item["knowledge_id"], item["title"]))
    status = _dedupe_status(dedupe_candidates)
    return {
        "dedupe_status": status,
        "dedupe_candidates": dedupe_candidates,
        "content_hash": content_hash,
    }


def apply_candidate_dedupe(conn: sqlite3.Connection, candidate_id: str) -> dict[str, Any]:
    """Run dedupe for a queued candidate and safely persist metadata-only result."""
    cursor = conn.execute("SELECT * FROM knowledge_candidates WHERE candidate_id=?", (candidate_id,))
    row = cursor.fetchone()
    if row is None:
        raise KeyError(f"candidate not found: {candidate_id}")
    candidate = _row_to_candidate(_row_dict(row, cursor.description))
    result = check_candidate_dedupe(conn, candidate)
    now = _now()

    audit_log = _json_loads(candidate.get("audit_log_json"), "audit_log")
    if not isinstance(audit_log, list):
        raise ValueError("audit_log must be a list")
    audit_log.append(
        {
            "event": "dedupe_check",
            "created_at": now,
            "dedupe_status": result["dedupe_status"],
            "candidate_count": len(result["dedupe_candidates"]),
            "reasons": sorted({item["reason"] for item in result["dedupe_candidates"]}),
        }
    )

    dedupe_action = _recommended_action(result["dedupe_status"])
    recommended_action = _combine_recommended_action(
        privacy_status=str(candidate.get("privacy_status") or "unknown"),
        current_action=str(candidate.get("recommended_action") or "review"),
        dedupe_action=dedupe_action,
    )
    conn.execute(
        """UPDATE knowledge_candidates
           SET dedupe_status=?, dedupe_candidates_json=?, recommended_action=?, audit_log_json=?, updated_at=?
           WHERE candidate_id=?""",
        (
            result["dedupe_status"],
            _json_dumps(result["dedupe_candidates"]),
            recommended_action,
            _json_dumps(audit_log),
            now,
            candidate_id,
        ),
    )
    conn.commit()
    return {"dedupe_status": result["dedupe_status"], "dedupe_candidates": result["dedupe_candidates"]}


def _load_knowledge_metadata(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cursor = conn.execute("SELECT id, title, category, tags, content_hash FROM knowledge ORDER BY id")
    return [_row_dict(row, cursor.description) for row in cursor.fetchall()]


def _title_tokens(normalized_title: str) -> set[str]:
    stopwords = {"a", "an", "and", "for", "of", "the", "to", "with"}
    return {token for token in normalized_title.split() if len(token) >= 3 and token not in stopwords}


def _is_title_keyword_candidate(candidate_tokens: set[str], row_tokens: set[str]) -> bool:
    if len(candidate_tokens) < 2 or len(row_tokens) < 2:
        return False
    overlap = candidate_tokens & row_tokens
    shorter = min(len(candidate_tokens), len(row_tokens))
    return len(overlap) >= 2 and len(overlap) / shorter >= 0.75


def _reason_rank(reason: str) -> int:
    return {"exact_title": 0, "normalized_title": 1, "content_hash": 2, "title_keyword": 3}.get(reason, 99)


def _dedupe_status(candidates: list[dict[str, Any]]) -> str:
    reasons = {str(candidate.get("reason") or "") for candidate in candidates}
    if {"exact_title", "normalized_title", "content_hash"} & reasons:
        return "duplicate"
    if "title_keyword" in reasons:
        return "near_duplicate"
    return "unique"


def _combine_recommended_action(*, privacy_status: str, current_action: str, dedupe_action: str) -> str:
    if privacy_status == "blocked" or current_action == "block":
        return "block"
    if privacy_status == "private_only" or current_action == "ask_arthur":
        return "ask_arthur"
    return dedupe_action


def _recommended_action(status: str) -> str:
    if status in {"duplicate", "near_duplicate", "conflict"}:
        return "merge"
    return "review"
