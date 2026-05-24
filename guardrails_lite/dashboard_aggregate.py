"""DL-7 count-only Guardrails Dashboard aggregate builder."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ALLOWED_B7_ISSUE_TYPES = {
    "duplicate_title",
    "duplicate_content_hash",
    "low_convergence",
    "stale_freshness",
    "provenance_gap",
}


def build_guardrails_dashboard_aggregate(
    dream_report: dict[str, Any] | None = None,
    b7_report: dict[str, Any] | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a count-only safe aggregate for dashboards/workbench surfaces."""
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    dream_counts = _dream_counts(dream_report or {})
    b7_counts = _b7_counts(b7_report or {})
    return {
        "schema": "guardrails.dashboard.aggregate.v1",
        "count_only": True,
        "report_only": True,
        "contains_private_payload": False,
        "generated_at": generated_at,
        "dream_candidates_total": dream_counts["total"],
        "dream_candidates_ready_for_review": dream_counts["ready_for_review"],
        "dream_candidates_blocked": dream_counts["blocked"],
        "dream_candidates_need_arthur": dream_counts["need_arthur"],
        "last_dream_review_at": dream_counts["date"],
        "librarian_open_duplicates": b7_counts["duplicates"],
        "librarian_open_stale": b7_counts["stale"],
        "librarian_open_low_convergence": b7_counts["low_convergence"],
        "librarian_open_provenance_gaps": b7_counts["provenance_gaps"],
        "librarian_review_items_total": b7_counts["items"],
        "last_librarian_review_at": generated_at if b7_report else "",
    }


def write_guardrails_dashboard_aggregate(path: str | Path, aggregate: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _dream_counts(report: dict[str, Any]) -> dict[str, Any]:
    if not report:
        return {"total": 0, "ready_for_review": 0, "blocked": 0, "need_arthur": 0, "date": ""}
    if (
        report.get("report_only") is not True
        or report.get("auto_promote") is not False
        or report.get("formal_knowledge_written") is not False
        or report.get("raw_written") is not False
        or report.get("sync_invoked") is not False
    ):
        raise ValueError("unsafe Dream report: dashboard aggregate accepts report-only/local-only input")
    counts = report.get("counts") or {}
    by_status = counts.get("by_status") or {}
    by_action = counts.get("by_recommended_action") or {}
    return {
        "total": int(counts.get("candidates") or 0),
        "ready_for_review": int(by_status.get("ready_for_review") or by_status.get("pending") or 0),
        "blocked": int(by_status.get("blocked") or by_action.get("block") or 0),
        "need_arthur": int(by_action.get("ask_arthur") or 0),
        "date": str(report.get("date") or ""),
    }


def _b7_counts(report: dict[str, Any]) -> dict[str, int]:
    if not report:
        return {"duplicates": 0, "stale": 0, "low_convergence": 0, "provenance_gaps": 0, "items": 0}
    if (
        report.get("report_only") is not True
        or report.get("auto_promote") is not False
        or report.get("destructive_merge") is not False
        or report.get("private_public_sync") is not False
        or report.get("remote_overwrite") is not False
    ):
        raise ValueError("unsafe B7 report: dashboard aggregate accepts report-only/non-destructive input")
    counts = report.get("counts") or {}
    by_issue = dict(counts.get("by_issue_type") or {})
    unknown = sorted(set(by_issue) - _ALLOWED_B7_ISSUE_TYPES)
    if unknown:
        raise ValueError(f"unknown B7 issue_type for dashboard aggregate: {', '.join(unknown)}")
    return {
        "duplicates": int(by_issue.get("duplicate_title", 0)) + int(by_issue.get("duplicate_content_hash", 0)),
        "stale": int(by_issue.get("stale_freshness", 0)),
        "low_convergence": int(by_issue.get("low_convergence", 0)),
        "provenance_gaps": int(by_issue.get("provenance_gap", 0)),
        "items": int(counts.get("items") or 0),
    }
