"""Dream/Librarian DL-2 review-report builder.

Reports are read-only and metadata-only.  They intentionally exclude candidate
summary and content_draft fields because those may contain private payloads.
"""

from __future__ import annotations

import json
import re
import shlex
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from guardrails_lite.privacy_scanner import scan_text

_REDACT_METADATA_PRIVACY_STATUSES = {"unknown", "redact_required", "private_only", "blocked"}
_SAFE_PRIVACY_KINDS = {"crm", "life_profile", "pii", "secret"}
_SAFE_PRIVACY_RULE_IDS = {
    "bearer_token",
    "credential_assignment",
    "customer_context",
    "email_address",
    "github_token",
    "openai_api_key",
    "phone_number",
    "private_key_block",
    "private_life_context",
    "pypi_token",
}

_SAFE_CANDIDATE_COLUMNS = """
    candidate_id, created_at, updated_at, source_type, source_agent,
    source_session_id, source_channel, source_refs_json, proposed_title,
    category, tags_json, classification, privacy_status, privacy_flags_json,
    dedupe_status, dedupe_candidates_json, status, recommended_action,
    decision_reason, reviewer, reviewed_at, trust_initial, freshness_initial,
    convergence_status_initial
"""


def build_dream_review_report(
    conn_or_db_path: sqlite3.Connection | str | Path,
    date: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Build a report-only Dream review queue export from safe metadata."""
    _validate_report_date(date)
    owns_conn = not isinstance(conn_or_db_path, sqlite3.Connection)
    conn = _connect_readonly(Path(conn_or_db_path)) if owns_conn else conn_or_db_path
    old_row_factory = None
    if not owns_conn:
        old_row_factory = conn.row_factory
        conn.row_factory = sqlite3.Row
    try:
        rows = _load_candidate_rows(conn, date=date, limit=limit)
    finally:
        if owns_conn:
            conn.close()
        else:
            conn.row_factory = old_row_factory

    candidates = [_safe_candidate_item(row) for row in rows]
    return {
        "schema": "guardrails.dream.review.v1",
        "report_only": True,
        "auto_promote": False,
        "formal_knowledge_written": False,
        "raw_written": False,
        "sync_invoked": False,
        "date": date,
        "counts": _counts(candidates),
        "reviewer_ux": _build_reviewer_ux(candidates),
        "candidates": candidates,
    }


def write_dream_review_report_json(path: str | Path, report: dict[str, Any]) -> None:
    """Write Dream review report JSON with stable formatting."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_dream_review_report_markdown(path: str | Path, report: dict[str, Any]) -> None:
    """Write a safe Feishu-friendly markdown summary without raw candidate payloads."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    counts = report.get("counts", {})
    lines = [
        "# Dream Review Report",
        "",
        "schema: `guardrails.dream.review.v1`",
        "report_only=true; auto_promote=false; formal_knowledge_written=false; raw_written=false; sync_invoked=false",
        "",
        f"Date: `{report.get('date') or 'all'}`",
        f"Candidates: **{counts.get('candidates', 0)}**",
        "",
    ]
    lines.extend(_reviewer_ux_markdown_lines(report.get("reviewer_ux", {})))
    lines.extend([
        "**Feishu CTA:** Review each section below and reply with the shown `dream decide` command plus a specific `--reason`.",
        "",
        "## Counts",
        "",
        f"- By privacy status: `{json.dumps(counts.get('by_privacy_status', {}), ensure_ascii=False, sort_keys=True)}`",
        f"- By dedupe status: `{json.dumps(counts.get('by_dedupe_status', {}), ensure_ascii=False, sort_keys=True)}`",
        f"- By recommended action: `{json.dumps(counts.get('by_recommended_action', {}), ensure_ascii=False, sort_keys=True)}`",
        "",
    ])
    candidates = list(report.get("candidates", []))
    for action, heading in _ACTION_SECTIONS:
        section_items = [item for item in candidates if _section_key(item.get("recommended_action")) == action]
        lines.extend([f"## {heading}", ""])
        if not section_items:
            lines.extend(["_No candidates._", ""])
            continue
        for item in section_items:
            lines.extend(_candidate_markdown_lines(item))
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"Guardrails DB not found: {db_path}")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _load_candidate_rows(
    conn: sqlite3.Connection,
    *,
    date: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    limit = int(limit or 0)
    params: list[Any] = []
    where = ""
    if date:
        where = "WHERE created_at LIKE ?"
        params.append(f"{date}%")
    query = f"""SELECT {_SAFE_CANDIDATE_COLUMNS}
                FROM knowledge_candidates
                {where}
                ORDER BY created_at DESC, candidate_id DESC"""
    if limit > 0:
        query += " LIMIT ?"
        params.append(limit)
    cursor = conn.execute(query, params)
    return [dict(row) if isinstance(row, sqlite3.Row) else _row_dict(row, cursor.description) for row in cursor.fetchall()]


def _safe_candidate_item(row: dict[str, Any]) -> dict[str, Any]:
    privacy_status = str(row.get("privacy_status", "unknown") or "unknown")
    return {
        "candidate_id": _safe_control_string(row.get("candidate_id", "")),
        "created_at": _safe_control_string(row.get("created_at", "")),
        "updated_at": _safe_control_string(row.get("updated_at", "")),
        "source_type": _safe_control_string(row.get("source_type", "")),
        "source_agent": _safe_user_metadata_string(row.get("source_agent", ""), privacy_status),
        "source_session_id": _safe_user_metadata_string(row.get("source_session_id") or "", privacy_status),
        "source_channel": _safe_user_metadata_string(row.get("source_channel") or "", privacy_status),
        "proposed_title": _safe_user_metadata_string(row.get("proposed_title", ""), privacy_status),
        "category": _safe_control_string(row.get("category", "")),
        "tags": [_safe_user_metadata_string(tag, privacy_status) for tag in _safe_json_list(row.get("tags_json"))],
        "classification": row.get("classification", ""),
        "privacy_status": privacy_status,
        "privacy_flags": _privacy_flag_summary(row.get("privacy_flags_json")),
        "dedupe_status": row.get("dedupe_status", "unknown"),
        "dedupe_candidates": _safe_dedupe_candidates(row.get("dedupe_candidates_json"), privacy_status),
        "status": row.get("status", ""),
        "recommended_action": row.get("recommended_action", ""),
        "trust_initial": row.get("trust_initial"),
        "freshness_initial": row.get("freshness_initial"),
        "convergence_status_initial": row.get("convergence_status_initial", "unknown"),
    }


def _counts(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "candidates": len(candidates),
        "by_privacy_status": _count_by(candidates, "privacy_status"),
        "by_dedupe_status": _count_by(candidates, "dedupe_status"),
        "by_status": _count_by(candidates, "status"),
        "by_recommended_action": _count_by(candidates, "recommended_action"),
    }


def _count_by(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = str(item.get(field) or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _safe_json_list(raw: Any) -> list[Any]:
    if not raw:
        return []
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def _privacy_flag_summary(raw: Any) -> dict[str, Any]:
    flags = _safe_json_list(raw)
    by_kind: dict[str, int] = {}
    by_rule: dict[str, int] = {}
    for flag in flags:
        if not isinstance(flag, dict):
            continue
        kind = _safe_privacy_kind(flag.get("kind"))
        rule = _safe_privacy_rule_id(flag.get("rule_id"))
        by_kind[kind] = by_kind.get(kind, 0) + 1
        by_rule[rule] = by_rule.get(rule, 0) + 1
    return {
        "finding_count": len([flag for flag in flags if isinstance(flag, dict)]),
        "by_kind": dict(sorted(by_kind.items())),
        "by_rule": dict(sorted(by_rule.items())),
    }


def _safe_dedupe_candidates(raw: Any, privacy_status: str) -> list[dict[str, Any]]:
    candidates = _safe_json_list(raw)
    safe: list[dict[str, Any]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        safe.append(
            {
                "knowledge_id": candidate.get("knowledge_id"),
                "title": _safe_user_metadata_string(candidate.get("title") or "", privacy_status),
                "reason": _safe_control_string(candidate.get("reason") or ""),
            }
        )
    return safe


def _validate_report_date(date: str | None) -> None:
    if date is None:
        return
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError("date must be YYYY-MM-DD")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("date must be YYYY-MM-DD") from exc


def _safe_user_metadata_string(value: Any, privacy_status: str = "unknown") -> str:
    text = str(value or "")
    if not text:
        return ""
    if privacy_status in _REDACT_METADATA_PRIVACY_STATUSES:
        return "[REDACTED_PRIVATE_CONTEXT]"
    return _sanitize_text_value(text)


def _safe_control_string(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    if any(marker in text for marker in ("\n", "\r", "`", "#")):
        return "[REDACTED_UNSAFE_METADATA]"
    return _single_line(text)


def _sanitize_text_value(text: str) -> str:
    result = scan_text(text).to_dict()
    redacted = str(result["redacted_text"])
    if result["outcome"] != "clear":
        return _single_line(redacted)
    if any(marker in text for marker in ("\n", "\r", "`", "#")):
        return "[REDACTED_UNSAFE_METADATA]"
    return _single_line(text)


def _single_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _safe_privacy_kind(value: Any) -> str:
    text = _safe_control_string(value).lower()
    return text if text in _SAFE_PRIVACY_KINDS else "other"


def _safe_privacy_rule_id(value: Any) -> str:
    text = _safe_control_string(value).lower()
    return text if text in _SAFE_PRIVACY_RULE_IDS else "unknown_rule"


def _markdown_inline(value: Any) -> str:
    return _single_line(str(value or "")).replace("`", "'")


def _build_reviewer_ux(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    action_items = _reviewer_action_items(candidates)
    numbers_by_action: dict[str, list[int]] = {}
    for item in action_items:
        numbers_by_action.setdefault(str(item["recommended_action"]), []).append(int(item["number"]))
    counts = _counts(candidates)
    action_counts = counts["by_recommended_action"]
    return {
        "conclusion": {
            "total_candidates": counts["candidates"],
            "suggest_promote": action_counts.get("promote", 0),
            "suggest_merge": action_counts.get("merge", 0),
            "suggest_discard": action_counts.get("discard", 0),
            "need_arthur": action_counts.get("ask_arthur", 0),
            "blocked": action_counts.get("block", 0),
            "general_review": action_counts.get("review", 0),
        },
        "quick_replies": _quick_replies(numbers_by_action),
        "action_items": action_items,
    }


def _reviewer_action_items(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    ordered: list[dict[str, Any]] = []
    for action, _heading in _ACTION_SECTIONS:
        ordered.extend([item for item in candidates if _section_key(item.get("recommended_action")) == action])
    for number, item in enumerate(ordered, start=1):
        action = _section_key(item.get("recommended_action"))
        decision = _single_decision_hint(action)
        candidate_id = _safe_control_string(item.get("candidate_id", ""))
        command_candidate_id = shlex.quote(candidate_id)
        title = _safe_user_metadata_string(item.get("proposed_title", ""), item.get("privacy_status", "unknown"))
        items.append(
            {
                "number": number,
                "candidate_id": candidate_id,
                "title": title,
                "recommended_action": action,
                "suggested_decision": decision,
                "privacy_status": _safe_control_string(item.get("privacy_status", "")),
                "dedupe_status": _safe_control_string(item.get("dedupe_status", "")),
                "decide_command": (
                    f"dream decide {command_candidate_id} --decision {decision} "
                    '--reason "<safe reason>" --reviewer nancy'
                ),
            }
        )
    return items


def _single_decision_hint(action: str) -> str:
    decision = _DECISION_HINTS.get(action, "ask_arthur")
    if "|" in decision:
        return "ask_arthur"
    return decision


def _quick_replies(numbers_by_action: dict[str, list[int]]) -> list[str]:
    replies = ["先不用"]
    promote = numbers_by_action.get("promote", [])
    merge = numbers_by_action.get("merge", [])
    discard = numbers_by_action.get("discard", [])
    block = numbers_by_action.get("block", [])
    ask = numbers_by_action.get("ask_arthur", [])
    if promote:
        replies.extend(["寫入全部", f"只寫 {_join_numbers(promote)}"])
    if merge:
        replies.append(f"合併 {_join_numbers(merge)}")
    if discard:
        replies.append(f"丟棄 {_join_numbers(discard)}")
    if block:
        replies.append(f"封鎖 {_join_numbers(block)}")
    if ask:
        replies.append(f"裁決 {_join_numbers(ask)}")
    return replies


def _join_numbers(numbers: list[int]) -> str:
    return ",".join(str(number) for number in numbers)


def _reviewer_ux_markdown_lines(ux: dict[str, Any]) -> list[str]:
    conclusion = ux.get("conclusion", {}) if isinstance(ux, dict) else {}
    quick_replies = ux.get("quick_replies", []) if isinstance(ux, dict) else []
    action_items = ux.get("action_items", []) if isinstance(ux, dict) else []
    lines = [
        "## 結論",
        "",
        (
            f"今天有 **{conclusion.get('total_candidates', 0)}** 條候選；"
            f"建議寫入 **{conclusion.get('suggest_promote', 0)}** 條、"
            f"合併 **{conclusion.get('suggest_merge', 0)}** 條、"
            f"丟棄 **{conclusion.get('suggest_discard', 0)}** 條、"
            f"封鎖 **{conclusion.get('blocked', 0)}** 條、"
            f"需 Arthur 裁決 **{conclusion.get('need_arthur', 0)}** 條。"
        ),
        "",
        "## Feishu 快速回覆",
        "",
    ]
    if quick_replies:
        lines.append("回覆：「" + "」「".join(_markdown_inline(reply) for reply in quick_replies) + "」")
    else:
        lines.append("_No quick replies._")
    lines.extend(["", "## 編號審核清單", ""])
    if not action_items:
        lines.extend(["_No action items._", ""])
        return lines
    for item in action_items:
        lines.extend(
            [
                (
                    f"{item.get('number')}. [{_markdown_inline(item.get('recommended_action'))}] "
                    f"`{_markdown_inline(item.get('candidate_id'))}` — {_markdown_inline(item.get('title'))}"
                ),
                (
                    f"   - Privacy: `{_markdown_inline(item.get('privacy_status'))}`; "
                    f"Dedupe: `{_markdown_inline(item.get('dedupe_status'))}`"
                ),
                f"   - Command: `{_markdown_inline(item.get('decide_command'))}`",
            ]
        )
    lines.append("")
    return lines


_ACTION_SECTIONS = [

    ("promote", "Promote / Write"),
    ("merge", "Merge"),
    ("discard", "Discard"),
    ("block", "Block"),
    ("ask_arthur", "Ask Arthur"),
    ("review", "General Review"),
]

_DECISION_HINTS = {
    "promote": "approved",
    "merge": "merge_suggested",
    "discard": "discarded",
    "block": "blocked",
    "ask_arthur": "ask_arthur",
    "review": "approved|merge_suggested|discarded|blocked|ask_arthur",
}


def _section_key(action: Any) -> str:
    action_text = str(action or "review")
    if action_text in {"promote", "merge", "discard", "block", "ask_arthur"}:
        return action_text
    return "review"


def _candidate_markdown_lines(item: dict[str, Any]) -> list[str]:
    candidate_id = _markdown_inline(item.get("candidate_id", ""))
    command_candidate_id = shlex.quote(candidate_id)
    action = _section_key(item.get("recommended_action"))
    decision_hint = _DECISION_HINTS[action]
    return [
        f"### `{candidate_id}` — {_markdown_inline(item.get('proposed_title', ''))}",
        "",
        f"- Source: `{_markdown_inline(item.get('source_type', ''))}` / `{_markdown_inline(item.get('source_agent', ''))}`",
        f"- Category: `{_markdown_inline(item.get('category', ''))}`; tags: `{_markdown_inline(', '.join(item.get('tags', [])))}`",
        f"- Status: `{_markdown_inline(item.get('status', ''))}`; recommended_action: `{_markdown_inline(item.get('recommended_action', ''))}`",
        f"- Privacy: `{_markdown_inline(item.get('privacy_status', ''))}`; Dedupe: `{_markdown_inline(item.get('dedupe_status', ''))}`",
        f"- Dedupe candidates: `{_markdown_inline(_dedupe_candidates_summary(item.get('dedupe_candidates', [])))}`",
        f"- Feishu CTA: dream decide {command_candidate_id} --decision {decision_hint} --reason \"<safe reason>\" --reviewer nancy",
        "",
    ]


def _dedupe_candidates_summary(candidates: list[dict[str, Any]]) -> str:
    parts = []
    for candidate in candidates:
        parts.append(
            f"knowledge:{candidate.get('knowledge_id')} ({candidate.get('reason')}) {candidate.get('title')}"
        )
    return "; ".join(parts)


def _row_dict(row: tuple[Any, ...], description: Any) -> dict[str, Any]:
    return {description[index][0]: row[index] for index in range(len(row))}
