"""DL-8 monthly deep cleanup report-only builder."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guardrails_lite.b7_report import build_b7_report
from guardrails_lite.dashboard_aggregate import build_guardrails_dashboard_aggregate

_SAFE_PRIORITY_ACTIONS = {"review_duplicate", "review_convergence", "review_freshness", "repair_provenance", "ask_arthur"}


def build_monthly_deep_cleanup_report(
    *,
    db_path: str | Path,
    raw_dir: str | Path | None = None,
    compiled_dir: str | Path | None = None,
    month: str | None = None,
    generated_at: str | None = None,
    top_n: int = 3,
) -> dict[str, Any]:
    """Build a report-only monthly health review from safe B7 metadata."""
    month = month or datetime.now(timezone.utc).strftime("%Y-%m")
    _validate_month(month)
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    b7_report = build_b7_report(db_path=db_path, raw_dir=raw_dir, compiled_dir=compiled_dir)
    aggregate = build_guardrails_dashboard_aggregate(None, b7_report, generated_at=generated_at)
    priorities = _top_priorities(b7_report.get("items", []), top_n=top_n)
    counts = {
        "knowledge_rows": int((b7_report.get("counts") or {}).get("knowledge_rows") or 0),
        "review_items": int((b7_report.get("counts") or {}).get("items") or 0),
        "by_issue_type": dict((b7_report.get("counts") or {}).get("by_issue_type") or {}),
    }
    return {
        "schema": "guardrails.librarian.monthly.v1",
        "report_only": True,
        "auto_promote": False,
        "destructive_merge": False,
        "remote_overwrite": False,
        "private_public_sync": False,
        "month": month,
        "generated_at": generated_at,
        "counts": counts,
        "trend_metrics": {
            "mode": "baseline_current_snapshot",
            "current_review_items": counts["review_items"],
            "current_knowledge_rows": counts["knowledge_rows"],
            "note": "Historical monthly trend store is not enabled yet; this is the baseline snapshot.",
        },
        "dashboard_aggregate": aggregate,
        "top_cleanup_priorities": priorities,
        "operating_manual": [
            "Report-only: review recommendations before any write.",
            "Do not auto-merge, delete, deprecate, promote, sync, or remote overwrite from this report.",
            "Use safe source refs and knowledge ids to inspect details manually before action.",
            "Treat duplicate, freshness, convergence, and provenance findings as review queues, not commands.",
        ],
    }


def write_monthly_deep_cleanup_report(path: str | Path, report: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_monthly_deep_cleanup_markdown(path: str | Path, report: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    counts = report.get("counts") or {}
    lines = [
        "# Guardrails Librarian Monthly Deep Cleanup",
        "",
        "report_only=true; auto_promote=false; destructive_merge=false; remote_overwrite=false",
        "",
        f"Month: `{report.get('month')}`",
        f"Knowledge rows: **{counts.get('knowledge_rows', 0)}**",
        f"Review items: **{counts.get('review_items', 0)}**",
        f"By issue type: `{json.dumps(counts.get('by_issue_type', {}), ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Trend Metrics",
        "",
        f"- Mode: `{(report.get('trend_metrics') or {}).get('mode', '')}`",
        f"- Note: {(report.get('trend_metrics') or {}).get('note', '')}",
        "",
        "## Top Cleanup Priorities",
        "",
    ]
    priorities = list(report.get("top_cleanup_priorities") or [])
    if priorities:
        for item in priorities:
            lines.extend(
                [
                    f"{item.get('rank')}. `{item.get('issue_type')}` — action `{item.get('recommended_action')}`",
                    f"   - Count: `{item.get('count', 1)}`; reason: {item.get('safe_reason', '')}",
                ]
            )
    else:
        lines.append("_No cleanup priorities._")
    lines.extend(["", "## Operating Manual", ""])
    for line in report.get("operating_manual") or []:
        lines.append(f"- {line}")
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _validate_month(month: str) -> None:
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise ValueError("month must be YYYY-MM")
    datetime.strptime(month, "%Y-%m")


def _top_priorities(items: list[dict[str, Any]], *, top_n: int) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in items:
        issue_type = _safe_text(item.get("issue_type") or "unknown")
        action = _safe_text(item.get("recommended_action") or "ask_arthur")
        if action not in _SAFE_PRIORITY_ACTIONS:
            action = "ask_arthur"
        entry = grouped.setdefault(
            issue_type,
            {
                "issue_type": issue_type,
                "recommended_action": action,
                "safe_reason": _safe_text(item.get("safe_reason") or "review required"),
                "count": 0,
            },
        )
        entry["count"] += 1
    ordered = sorted(grouped.values(), key=lambda item: (-int(item["count"]), str(item["issue_type"])))
    limit = max(0, int(top_n or 0))
    result = ordered[:limit]
    for rank, item in enumerate(result, start=1):
        item["rank"] = rank
    return result


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").replace("`", "'").replace("\n", " ").replace("\r", " ").split())
