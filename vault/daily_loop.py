"""Daily memory loop orchestration.

This module composes the existing safe automation, sync, and daily-report
surfaces into one scheduled workflow. Defaults stay report-first and
candidate-first; mutation only happens through existing policy-gated helpers.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .automation import (
    automation_brief,
    automation_cycle,
    automation_inbox,
    automation_learning_health,
    automation_review_summary,
)
from .central_vector_index import (
    central_vector_index_plan,
    central_vector_index_status,
    write_vector_index_report,
)
from .central_sync import run_central_memory_sync
from .daily_report import build_daily_report, normalize_report_language, render_daily_report_text
from .memory_pipeline import run_memory_pipeline
from .remote_status import build_remote_status
from .reflection import run_reflection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _relative_to_project(project: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project))
    except ValueError:
        return str(path.expanduser().resolve().relative_to(project.expanduser().resolve()))


def _latest_report_path(project: Path) -> Path:
    return project / "reports" / "daily-loop" / "daily-loop-latest.json"


def build_daily_loop_status(
    project_dir: str | Path,
    *,
    agent_id: str = "",
    max_sync_age_minutes: int = 24 * 60,
) -> dict[str, Any]:
    """Return read-only daily-loop freshness and sync status."""
    project = Path(project_dir).expanduser().resolve()
    latest_path = _latest_report_path(project)
    latest = _read_json(latest_path) if latest_path.exists() else {}
    sync_status = build_remote_status(
        project,
        agent_id=agent_id,
        max_sync_age_minutes=max_sync_age_minutes,
    )
    return {
        "ok": bool(sync_status.get("local", {}).get("db_exists", False)),
        "action": "daily-loop-status",
        "generated_at": _now(),
        "project_dir": str(project),
        "agent_id": agent_id,
        "latest_report": {
            "path": _relative_to_project(project, latest_path) if latest_path.exists() else "",
            "exists": latest_path.exists(),
            "status": latest.get("status", "missing") if latest else "missing",
            "generated_at": latest.get("generated_at", "") if latest else "",
            "summary": latest.get("summary", {}) if latest else {},
        },
        "sync": {
            "ok": bool(sync_status.get("ok", False)),
            "warnings": sync_status.get("warnings", []),
            "last_report": (sync_status.get("sync") or {}).get("last_report", {}),
        },
        "safety": _daily_loop_safety(apply=False, writes_candidates=False),
        "next_action": (
            "Run `vault daily-loop report --refresh --write-report` to refresh the latest report without ingestion."
            if not latest_path.exists()
            else "Review the latest daily-loop report and keep the schedule running."
        ),
    }


def run_daily_loop(
    project_dir: str | Path,
    *,
    agent_id: str = "",
    mode: str = "balanced",
    apply: bool = False,
    limit: int = 5,
    min_events: int = 5,
    language: str = "en",
    include_transcripts: bool = False,
    transcript_limit: int = 5,
    central_backend: str = "supabase",
    max_sync_age_minutes: int = 24 * 60,
    write_report: bool = False,
    report_path: str | Path = "",
) -> dict[str, Any]:
    """Run one report-first daily memory loop."""
    project = Path(project_dir).expanduser().resolve()
    limit_i = max(1, min(int(limit or 5), 20))
    transcript_limit_i = max(1, min(int(transcript_limit or 5), 20))
    generated_at = _now()
    pipeline = run_memory_pipeline(
        project,
        agent_id=agent_id,
        write_candidates=True,
        run_cycle=False,
        apply=False,
        transcript_limit=transcript_limit_i,
        include_content=False,
        write_report=True,
    )
    reflection = run_reflection(
        project,
        limit=max(limit_i, 20),
        write_candidates=True,
        apply=bool(apply),
        write_report=True,
    )
    sync = run_central_memory_sync(
        project,
        agent_id=agent_id,
        max_sync_age_minutes=max_sync_age_minutes,
        push_read_copy=True,
        push_central_store=bool(apply),
        pull_candidates=True,
        central_backend=central_backend,
        candidate_limit=max(limit_i, 20),
        apply=bool(apply),
        auto_promote_low_risk=False,
        include_content=False,
        document_map=True,
        health=True,
        dry_run=not bool(apply),
        report_path=project / "reports" / "daily-loop" / "central-memory-sync-latest.json",
    )
    cycle = automation_cycle(
        project,
        mode=mode,
        apply=bool(apply),
        limit=max(limit_i, 20),
        min_events=min_events,
        write_reports=True,
        write_workspace=True,
        inbox_limit=limit_i,
        include_transcripts=include_transcripts,
        transcript_limit=transcript_limit_i,
        capture_transcripts=False,
    )
    inbox = automation_inbox(
        project,
        limit=limit_i,
        include_content=False,
        include_transcripts=include_transcripts,
        transcript_limit=transcript_limit_i,
        write_handoff=True,
    )
    brief = automation_brief(
        project,
        limit=limit_i,
        review_limit=limit_i,
        min_events=min_events,
        write_brief=True,
    )
    review = automation_review_summary(
        project,
        limit=limit_i,
        min_events=min_events,
        write_summary=True,
        precomputed_brief=brief,
    )
    learning = automation_learning_health(
        project,
        limit=limit_i,
        min_events=min_events,
        write_health=True,
    )
    daily = build_daily_report(
        project,
        limit=limit_i,
        min_events=min_events,
        language=language,
        precomputed_brief=brief,
        precomputed_review=review,
        write_report=True,
    )
    vector_index = _build_vector_index_observability(
        project,
        limit=limit_i,
        write_reports=bool(write_report),
    )
    payload = {
        "ok": _loop_ok(pipeline, reflection, sync, cycle, inbox, brief, review, learning, daily, vector_index),
        "action": "daily-loop-run",
        "generated_at": generated_at,
        "project_dir": str(project),
        "agent_id": agent_id,
        "status": _loop_status(sync, cycle, brief, review, learning, daily),
        "mode": mode,
        "apply": bool(apply),
        "central_backend": central_backend,
        "language": normalize_report_language(language),
        "summary": _loop_summary(pipeline, reflection, sync, cycle, inbox, brief, review, learning, daily, vector_index),
        "memory_ingestion": _compact_ingestion(pipeline, reflection),
        "sync": _compact_sync(sync),
        "vector_index": vector_index,
        "candidate_review": _compact_inbox(inbox),
        "lifecycle": _compact_lifecycle(cycle, brief),
        "human_review": _compact_human_review(review, daily),
        "learning": _compact_learning(learning),
        "daily_report": {
            "status": daily.get("status", ""),
            "headline": daily.get("headline", ""),
            "paths": daily.get("paths", {}),
        },
        "artifacts": _loop_artifacts(pipeline, reflection, sync, cycle, inbox, brief, review, learning, daily, vector_index),
        "safety": _daily_loop_safety(apply=bool(apply)),
        "next_actions": _next_actions(sync, cycle, inbox, review, learning, daily, vector_index, apply=bool(apply)),
        "paths": {
            "json": "",
            "markdown": "",
        },
    }
    if write_report:
        payload["paths"] = _write_daily_loop_report(project, payload, report_path=report_path)
    return payload


def refresh_daily_loop_report(
    project_dir: str | Path,
    *,
    agent_id: str = "",
    limit: int = 5,
    min_events: int = 5,
    language: str = "en",
    include_transcripts: bool = False,
    transcript_limit: int = 5,
    max_sync_age_minutes: int = 24 * 60,
    write_report: bool = False,
    report_path: str | Path = "",
) -> dict[str, Any]:
    """Rebuild the latest daily-loop report from read-only status surfaces."""
    project = Path(project_dir).expanduser().resolve()
    limit_i = max(1, min(int(limit or 5), 20))
    transcript_limit_i = max(1, min(int(transcript_limit or 5), 20))
    generated_at = _now()
    sync_status = build_remote_status(
        project,
        agent_id=agent_id,
        max_sync_age_minutes=max_sync_age_minutes,
    )
    inbox = automation_inbox(
        project,
        limit=limit_i,
        include_content=False,
        include_transcripts=include_transcripts,
        transcript_limit=transcript_limit_i,
        write_handoff=False,
    )
    brief = automation_brief(
        project,
        limit=limit_i,
        review_limit=limit_i,
        min_events=min_events,
        write_brief=False,
    )
    review = automation_review_summary(
        project,
        limit=limit_i,
        min_events=min_events,
        write_summary=False,
        precomputed_brief=brief,
    )
    learning = automation_learning_health(
        project,
        limit=limit_i,
        min_events=min_events,
        write_health=False,
    )
    daily = build_daily_report(
        project,
        limit=limit_i,
        min_events=min_events,
        language=language,
        precomputed_brief=brief,
        precomputed_review=review,
        write_report=False,
    )
    sync = _compact_remote_status(sync_status)
    vector_index = _build_vector_index_observability(
        project,
        limit=limit_i,
        write_reports=bool(write_report),
    )
    payload = {
        "ok": _loop_ok(sync_status, inbox, brief, review, learning, daily, vector_index),
        "action": "daily-loop-refresh",
        "generated_at": generated_at,
        "project_dir": str(project),
        "agent_id": agent_id,
        "status": _loop_status(sync_status, inbox, brief, review, learning, daily),
        "mode": "read-only-refresh",
        "apply": False,
        "central_backend": "status-only",
        "language": normalize_report_language(language),
        "summary": _refresh_summary(sync, inbox, brief, review, learning, daily, vector_index),
        "memory_ingestion": _read_only_ingestion(),
        "sync": sync,
        "vector_index": vector_index,
        "candidate_review": _compact_inbox(inbox),
        "lifecycle": _read_only_lifecycle(brief),
        "human_review": _compact_human_review(review, daily),
        "learning": _compact_learning(learning),
        "daily_report": {
            "status": daily.get("status", ""),
            "headline": daily.get("headline", ""),
            "paths": daily.get("paths", {}),
        },
        "artifacts": _refresh_artifacts(inbox, brief, review, learning, daily, vector_index),
        "safety": _daily_loop_safety(apply=False, writes_candidates=False),
        "next_actions": _next_actions(sync, {"status": "completed"}, inbox, review, learning, daily, vector_index, apply=False),
        "paths": {
            "json": "",
            "markdown": "",
        },
    }
    if write_report:
        payload["paths"] = _write_daily_loop_report(project, payload, report_path=report_path)
    return payload


def build_daily_loop_report(
    project_dir: str | Path,
    *,
    language: str = "en",
    write_report: bool = False,
    report_path: str | Path = "",
) -> dict[str, Any]:
    """Render the latest daily-loop run as a human report."""
    project = Path(project_dir).expanduser().resolve()
    latest_path = _latest_report_path(project)
    if not latest_path.exists():
        return {
            "ok": False,
            "action": "daily-loop-report",
            "generated_at": _now(),
            "project_dir": str(project),
            "status": "missing",
            "reason": "daily-loop report missing",
            "paths": {"json": "", "markdown": ""},
            "next_action": "Run `vault daily-loop run --write-report` before rendering the latest report.",
        }
    payload = _read_json(latest_path)
    payload["language"] = normalize_report_language(language or payload.get("language", "en"))
    paths = payload.get("paths") or {
        "json": _relative_to_project(project, latest_path),
        "markdown": _relative_to_project(project, latest_path.with_suffix(".md")),
    }
    if write_report:
        paths = _write_daily_loop_report(project, payload, report_path=report_path or latest_path)
    return {
        "ok": True,
        "action": "daily-loop-report",
        "generated_at": _now(),
        "project_dir": str(project),
        "status": payload.get("status", ""),
        "headline": (payload.get("daily_report") or {}).get("headline", ""),
        "summary": payload.get("summary", {}),
        "paths": paths,
        "text": render_daily_loop_text(payload),
        "next_action": "Review human_review.cards, then record feedback or keep the schedule running.",
    }


def render_daily_loop_text(payload: dict[str, Any]) -> str:
    daily = payload.get("daily_report") or {}
    summary = payload.get("summary") or {}
    lines = [
        "Vault Daily Loop",
        "",
        str(daily.get("headline") or payload.get("status") or ""),
        "",
        f"status: {payload.get('status', '')}",
        f"apply: {str(bool(payload.get('apply', False))).lower()}",
        f"pending candidates: {summary.get('pending_candidates', 0)}",
        f"human review cards: {summary.get('human_review_cards', 0)}",
        f"sync: {summary.get('sync_status', '')}",
        f"learning: {summary.get('learning_status', '')}",
    ]
    actions = payload.get("next_actions") or []
    if actions:
        lines += ["", "Next:"]
        for action in actions[:5]:
            lines.append(f"  - {action}")
    paths = payload.get("paths") or {}
    if paths.get("markdown"):
        lines.append(f"Markdown: {paths['markdown']}")
    if paths.get("json"):
        lines.append(f"JSON: {paths['json']}")
    return "\n".join(lines).rstrip() + "\n"


def _write_daily_loop_report(project: Path, payload: dict[str, Any], *, report_path: str | Path = "") -> dict[str, str]:
    report_dir = project / "reports" / "daily-loop"
    report_dir.mkdir(parents=True, exist_ok=True)
    if report_path:
        raw = Path(report_path)
        json_path = raw if raw.is_absolute() else project / raw
        resolved = json_path.expanduser().resolve()
        allowed = report_dir.expanduser().resolve()
        if allowed != resolved and allowed not in resolved.parents:
            raise ValueError("daily-loop report path must stay under reports/daily-loop")
        json_path = resolved
    else:
        json_path = report_dir / "daily-loop-latest.json"
    markdown_path = json_path.with_suffix(".md")
    data = dict(payload)
    data["paths"] = {
        "json": _relative_to_project(project, json_path),
        "markdown": _relative_to_project(project, markdown_path),
    }
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_daily_loop_markdown(data), encoding="utf-8")
    return data["paths"]


def _render_daily_loop_markdown(payload: dict[str, Any]) -> str:
    daily = payload.get("daily_report") or {}
    summary = payload.get("summary") or {}
    lines = [
        "# Vault Daily Loop",
        "",
        f"- generated_at: `{payload.get('generated_at', '')}`",
        f"- status: `{payload.get('status', '')}`",
        f"- apply: `{str(bool(payload.get('apply', False))).lower()}`",
        f"- headline: {daily.get('headline', '')}",
        "",
        "## Summary",
        "",
        f"- pending candidates: `{summary.get('pending_candidates', 0)}`",
        f"- human review cards: `{summary.get('human_review_cards', 0)}`",
        f"- sync status: `{summary.get('sync_status', '')}`",
        f"- vector index status: `{summary.get('vector_index_status', '')}`",
        f"- lifecycle status: `{summary.get('lifecycle_status', '')}`",
        f"- learning status: `{summary.get('learning_status', '')}`",
        "",
        "## Vector Index",
        "",
        f"- status: `{(payload.get('vector_index') or {}).get('status', '')}`",
        f"- semantic vector rows: `{(payload.get('vector_index') or {}).get('semantic_vector_rows', 0)}`",
        f"- missing default-policy rows: `{(payload.get('vector_index') or {}).get('missing_default_policy_rows', 0)}`",
        f"- stale vector rows: `{(payload.get('vector_index') or {}).get('stale_vector_rows', 0)}`",
        f"- shared remote-risk rows: `{(payload.get('vector_index') or {}).get('shared_remote_risk_vector_rows', 0)}`",
        f"- repair rows sampled: `{((payload.get('vector_index') or {}).get('plan') or {}).get('repair_rows_sampled', 0)}`",
        f"- cleanup rows sampled: `{((payload.get('vector_index') or {}).get('plan') or {}).get('cleanup_rows_sampled', 0)}`",
        f"- remote vector read: `{str(bool((payload.get('vector_index') or {}).get('shared_remote_vector_read', False))).lower()}`",
        "",
        "## Human Review",
        "",
    ]
    cards = (payload.get("human_review") or {}).get("cards") or []
    if cards:
        lines += [_md_row(["kind", "id", "title", "action", "reason"]), _md_row(["---", "---", "---", "---", "---"])]
        for card in cards[:5]:
            lines.append(
                _md_row(
                    [
                        card.get("kind", ""),
                        card.get("id", ""),
                        card.get("title", ""),
                        card.get("recommended_action", card.get("suggested_decision", "")),
                        card.get("reason", ""),
                    ]
                )
            )
    else:
        lines.append("No human-review cards.")
    lines += [
        "",
        "## Artifacts",
        "",
    ]
    for key, value in (payload.get("artifacts") or {}).items():
        if value:
            lines.append(f"- {key}: `{value}`")
    lines += [
        "",
        "## Safety",
        "",
    ]
    for key, value in (payload.get("safety") or {}).items():
        lines.append(f"- {key}: `{value}`")
    actions = payload.get("next_actions") or []
    if actions:
        lines += ["", "## Next Actions", ""]
        lines.extend([f"- {action}" for action in actions[:5]])
    return "\n".join(lines).rstrip() + "\n"


def _md_row(values: list[Any]) -> str:
    return "| " + " | ".join(_md_cell(value) for value in values) + " |"


def _md_cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ").strip()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _loop_ok(*payloads: dict[str, Any]) -> bool:
    return all(payload.get("ok", True) is not False for payload in payloads)


def _loop_status(*payloads: dict[str, Any]) -> str:
    if any(str(payload.get("status") or "") == "blocked" for payload in payloads):
        return "blocked"
    if any(payload.get("ok", True) is False or str(payload.get("status") or "") == "failed" for payload in payloads):
        return "warning"
    return "completed"


def _loop_summary(
    pipeline: dict[str, Any],
    reflection: dict[str, Any],
    sync: dict[str, Any],
    cycle: dict[str, Any],
    inbox: dict[str, Any],
    brief: dict[str, Any],
    review: dict[str, Any],
    learning: dict[str, Any],
    daily: dict[str, Any],
    vector_index: dict[str, Any],
) -> dict[str, Any]:
    inbox_summary = inbox.get("summary") or {}
    daily_summary = daily.get("summary") or {}
    review_summary = review.get("summary") or {}
    return {
        "sync_status": sync.get("status", ""),
        "lifecycle_status": cycle.get("status", ""),
        "learning_status": learning.get("status", ""),
        "pending_candidates": int(daily_summary.get("pending_candidates") or inbox_summary.get("pending_candidates") or 0),
        "needs_review": int(inbox_summary.get("needs_review") or 0),
        "human_review_cards": len(daily.get("review_cards") or []),
        "review_summary_cards": int(review_summary.get("cards") or 0),
        "requires_human_decision": bool(review_summary.get("requires_human_decision", False)),
        "learning_rules": int(daily_summary.get("learning_rules") or 0),
        "expired_active": int(daily_summary.get("expired_active") or 0),
        "open_sync_conflicts": int(daily_summary.get("open_sync_conflicts") or 0),
        "cycle_candidates_written": int((cycle.get("summary") or {}).get("candidates_written") or 0),
        "pipeline_candidates_written": int(pipeline.get("candidate_count") or 0),
        "reflection_candidates_written": int((reflection.get("consolidation") or {}).get("candidates_written") or 0)
        + int(((reflection.get("dream") or {}).get("summary") or {}).get("candidates_written") or 0),
        "daily_report_status": daily.get("status", ""),
        "brief_status": brief.get("status", ""),
        "vector_index_status": vector_index.get("status", ""),
        "vector_index_repair_rows_sampled": int((vector_index.get("plan") or {}).get("repair_rows_sampled") or 0),
        "vector_index_cleanup_rows_sampled": int((vector_index.get("plan") or {}).get("cleanup_rows_sampled") or 0),
    }


def _compact_ingestion(pipeline: dict[str, Any], reflection: dict[str, Any]) -> dict[str, Any]:
    return {
        "pipeline": {
            "status": pipeline.get("status", "completed"),
            "candidate_count": int(pipeline.get("candidate_count") or 0),
            "preview_count": int(pipeline.get("preview_count") or 0),
            "discovery": pipeline.get("discovery", {}),
            "report_path": pipeline.get("report_path", ""),
            "report_markdown_path": pipeline.get("report_markdown_path", ""),
        },
        "reflection": {
            "status": reflection.get("status", "completed"),
            "write_candidates": bool(reflection.get("write_candidates", False)),
            "dream": reflection.get("dream", {}),
            "consolidation": reflection.get("consolidation", {}),
            "safety": reflection.get("safety", {}),
        },
    }


def _compact_sync(sync: dict[str, Any]) -> dict[str, Any]:
    operations = sync.get("operations") or {}
    return {
        "ok": bool(sync.get("ok", False)),
        "status": sync.get("status", ""),
        "dry_run": bool(sync.get("dry_run", False)),
        "report_path": sync.get("report_path", ""),
        "last_synced_at": sync.get("last_synced_at", ""),
        "errors": sync.get("errors", []),
        "operations": {
            key: {
                "enabled": value.get("enabled", False),
                "status": value.get("status", ""),
                "dry_run": value.get("dry_run", False),
            }
            for key, value in operations.items()
            if isinstance(value, dict)
        },
    }


def _compact_remote_status(status: dict[str, Any]) -> dict[str, Any]:
    report = (status.get("sync") or {}).get("last_report", {})
    warning_items = status.get("warnings") or []
    return {
        "ok": bool(status.get("ok", False)),
        "status": "warning" if warning_items else "completed",
        "dry_run": False,
        "report_path": str(report.get("path") or ""),
        "last_synced_at": str(report.get("generated_at") or report.get("updated_at") or ""),
        "errors": [
            item
            for item in warning_items
            if isinstance(item, dict) and str(item.get("severity") or "") == "high"
        ],
        "warnings": warning_items,
        "operations": {},
        "source": "remote-status",
    }


def _compact_inbox(inbox: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": inbox.get("status", ""),
        "summary": inbox.get("summary", {}),
        "queue": inbox.get("review_queue", []),
        "review_digest": inbox.get("review_digest", {}),
        "handoff_path": inbox.get("inbox_handoff_path", ""),
    }


def _read_only_ingestion() -> dict[str, Any]:
    return {
        "pipeline": {
            "status": "skipped",
            "candidate_count": 0,
            "preview_count": 0,
            "discovery": {},
            "report_path": "",
            "report_markdown_path": "",
            "reason": "read-only refresh does not capture sessions or write memory candidates",
        },
        "reflection": {
            "status": "skipped",
            "write_candidates": False,
            "dream": {},
            "consolidation": {},
            "safety": {
                "read_only": True,
                "writes_candidates": False,
            },
        },
    }


def _compact_lifecycle(cycle: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
    run = cycle.get("run") or {}
    return {
        "status": cycle.get("status", ""),
        "cycle_workspace_path": cycle.get("workspace_path", ""),
        "cycle_workspace_markdown_path": cycle.get("workspace_markdown_path", ""),
        "automation_report_path": (cycle.get("summary") or {}).get("automation_report_path", ""),
        "dream": (run.get("dream") or {}).get("summary", {}),
        "forgetting_strategy": brief.get("forgetting_strategy", {}),
        "archive": run.get("archive_expired", {}),
        "cold_store": run.get("cold_store_expired", {}),
    }


def _read_only_lifecycle(brief: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "read_only",
        "cycle_workspace_path": "",
        "cycle_workspace_markdown_path": "",
        "automation_report_path": "",
        "dream": {},
        "forgetting_strategy": brief.get("forgetting_strategy", {}),
        "archive": {},
        "cold_store": {},
    }


def _compact_human_review(review: dict[str, Any], daily: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": review.get("status", ""),
        "summary": review.get("summary", {}),
        "cards": daily.get("review_cards", []),
        "review_summary_path": review.get("review_summary_path", ""),
        "review_summary_markdown_path": review.get("review_summary_markdown_path", ""),
    }


def _compact_learning(learning: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": learning.get("status", ""),
        "summary": learning.get("summary", {}),
        "cards": learning.get("cards", []),
        "top_rules": learning.get("top_rules", []),
        "health_path": learning.get("health_path", ""),
        "health_markdown_path": learning.get("health_markdown_path", ""),
    }


def _build_vector_index_observability(project: Path, *, limit: int, write_reports: bool) -> dict[str, Any]:
    db_path = project / "vault.db"
    status = central_vector_index_status(db_path)
    status["action"] = "status"
    plan = central_vector_index_plan(db_path, limit=limit)
    plan["action"] = "plan"
    status_paths = {"json": "", "markdown": ""}
    plan_paths = {"json": "", "markdown": ""}
    if write_reports:
        status_paths = write_vector_index_report(project, status, action="status")
        plan_paths = write_vector_index_report(project, plan, action="plan")
        status["paths"] = status_paths
        plan["paths"] = plan_paths
    return _compact_vector_index(status, plan, status_paths=status_paths, plan_paths=plan_paths)


def _compact_vector_index(
    status: dict[str, Any],
    plan: dict[str, Any],
    *,
    status_paths: dict[str, str],
    plan_paths: dict[str, str],
) -> dict[str, Any]:
    counts = status.get("counts") or {}
    readiness = status.get("readiness") or {}
    plan_counts = plan.get("counts") or {}
    return {
        "ok": True,
        "status": status.get("status", ""),
        "source_of_truth": status.get("source_of_truth", ""),
        "index_role": status.get("index_role", ""),
        "local_only": bool(status.get("local_only", True)),
        "remote_read_enabled": bool(status.get("remote_read_enabled", False)),
        "remote_write_enabled": bool(status.get("remote_write_enabled", False)),
        "local_vector_search": bool(readiness.get("local_vector_search", False)),
        "shared_remote_vector_read": bool(readiness.get("shared_remote_vector_read", False)),
        "semantic_vector_rows": int(counts.get("semantic_vector_rows") or 0),
        "indexed_default_policy_rows": int(counts.get("indexed_default_policy_rows") or 0),
        "missing_default_policy_rows": int(counts.get("missing_default_policy_rows") or 0),
        "stale_vector_rows": int(counts.get("stale_vector_rows") or 0),
        "orphan_vector_rows": int(counts.get("orphan_vector_rows") or 0),
        "shared_remote_risk_vector_rows": int(counts.get("shared_remote_risk_vector_rows") or 0),
        "provider_breakdown": status.get("provider_breakdown", []),
        "plan": {
            "dry_run": bool(plan.get("dry_run", True)),
            "repair_rows_sampled": int(plan_counts.get("repair_rows_sampled") or 0),
            "cleanup_rows_sampled": int(plan_counts.get("cleanup_rows_sampled") or 0),
            "missing_default_policy_rows_sampled": int(plan_counts.get("missing_default_policy_rows_sampled") or 0),
            "stale_rows_sampled": int(plan_counts.get("stale_rows_sampled") or 0),
            "shared_remote_risk_rows_sampled": int(plan_counts.get("shared_remote_risk_rows_sampled") or 0),
            "orphan_vector_rows_sampled": int(plan_counts.get("orphan_vector_rows_sampled") or 0),
            "recommended_commands": plan.get("recommended_commands", []),
        },
        "paths": {
            "status_json": status_paths.get("json", ""),
            "status_markdown": status_paths.get("markdown", ""),
            "plan_json": plan_paths.get("json", ""),
            "plan_markdown": plan_paths.get("markdown", ""),
        },
        "notes": [
            "Daily-loop includes vector-index metadata only.",
            "Remote vector read remains disabled.",
        ],
    }


def _loop_artifacts(
    pipeline: dict[str, Any],
    reflection: dict[str, Any],
    sync: dict[str, Any],
    cycle: dict[str, Any],
    inbox: dict[str, Any],
    brief: dict[str, Any],
    review: dict[str, Any],
    learning: dict[str, Any],
    daily: dict[str, Any],
    vector_index: dict[str, Any],
) -> dict[str, str]:
    vector_paths = vector_index.get("paths") or {}
    return {
        "pipeline": str(pipeline.get("report_path") or ""),
        "pipeline_markdown": str(pipeline.get("report_markdown_path") or ""),
        "reflection_dream": str(((reflection.get("dream") or {}).get("report_path")) or ""),
        "reflection_lifecycle": str(((reflection.get("lifecycle") or {}).get("report_path")) or ""),
        "sync_report": str(sync.get("report_path") or ""),
        "cycle_workspace": str(cycle.get("workspace_path") or ""),
        "cycle_workspace_markdown": str(cycle.get("workspace_markdown_path") or ""),
        "inbox_handoff": str(inbox.get("inbox_handoff_path") or ""),
        "brief": str(brief.get("brief_path") or ""),
        "brief_markdown": str(brief.get("brief_markdown_path") or ""),
        "review_summary": str(review.get("review_summary_path") or ""),
        "review_summary_markdown": str(review.get("review_summary_markdown_path") or ""),
        "learning_health": str(learning.get("health_path") or ""),
        "learning_health_markdown": str(learning.get("health_markdown_path") or ""),
        "daily_report": str((daily.get("paths") or {}).get("json") or ""),
        "daily_report_markdown": str((daily.get("paths") or {}).get("markdown") or ""),
        "vector_index_status": str(vector_paths.get("status_json") or ""),
        "vector_index_status_markdown": str(vector_paths.get("status_markdown") or ""),
        "vector_index_plan": str(vector_paths.get("plan_json") or ""),
        "vector_index_plan_markdown": str(vector_paths.get("plan_markdown") or ""),
    }


def _refresh_artifacts(
    inbox: dict[str, Any],
    brief: dict[str, Any],
    review: dict[str, Any],
    learning: dict[str, Any],
    daily: dict[str, Any],
    vector_index: dict[str, Any],
) -> dict[str, str]:
    vector_paths = vector_index.get("paths") or {}
    return {
        "pipeline": "",
        "pipeline_markdown": "",
        "reflection_dream": "",
        "reflection_lifecycle": "",
        "sync_report": "",
        "cycle_workspace": "",
        "cycle_workspace_markdown": "",
        "inbox_handoff": str(inbox.get("inbox_handoff_path") or ""),
        "brief": str(brief.get("brief_path") or ""),
        "brief_markdown": str(brief.get("brief_markdown_path") or ""),
        "review_summary": str(review.get("review_summary_path") or ""),
        "review_summary_markdown": str(review.get("review_summary_markdown_path") or ""),
        "learning_health": str(learning.get("health_path") or ""),
        "learning_health_markdown": str(learning.get("health_markdown_path") or ""),
        "daily_report": str((daily.get("paths") or {}).get("json") or ""),
        "daily_report_markdown": str((daily.get("paths") or {}).get("markdown") or ""),
        "vector_index_status": str(vector_paths.get("status_json") or ""),
        "vector_index_status_markdown": str(vector_paths.get("status_markdown") or ""),
        "vector_index_plan": str(vector_paths.get("plan_json") or ""),
        "vector_index_plan_markdown": str(vector_paths.get("plan_markdown") or ""),
    }


def _refresh_summary(
    sync: dict[str, Any],
    inbox: dict[str, Any],
    brief: dict[str, Any],
    review: dict[str, Any],
    learning: dict[str, Any],
    daily: dict[str, Any],
    vector_index: dict[str, Any],
) -> dict[str, Any]:
    inbox_summary = inbox.get("summary") or {}
    daily_summary = daily.get("summary") or {}
    review_summary = review.get("summary") or {}
    return {
        "sync_status": sync.get("status", ""),
        "lifecycle_status": "read_only",
        "learning_status": learning.get("status", ""),
        "pending_candidates": int(daily_summary.get("pending_candidates") or inbox_summary.get("pending_candidates") or 0),
        "needs_review": int(inbox_summary.get("needs_review") or 0),
        "human_review_cards": len(daily.get("review_cards") or []),
        "review_summary_cards": int(review_summary.get("cards") or 0),
        "requires_human_decision": bool(review_summary.get("requires_human_decision", False)),
        "learning_rules": int(daily_summary.get("learning_rules") or 0),
        "expired_active": int(daily_summary.get("expired_active") or 0),
        "open_sync_conflicts": int(daily_summary.get("open_sync_conflicts") or 0),
        "cycle_candidates_written": 0,
        "pipeline_candidates_written": 0,
        "reflection_candidates_written": 0,
        "daily_report_status": daily.get("status", ""),
        "brief_status": brief.get("status", ""),
        "vector_index_status": vector_index.get("status", ""),
        "vector_index_repair_rows_sampled": int((vector_index.get("plan") or {}).get("repair_rows_sampled") or 0),
        "vector_index_cleanup_rows_sampled": int((vector_index.get("plan") or {}).get("cleanup_rows_sampled") or 0),
    }


def _daily_loop_safety(*, apply: bool, writes_candidates: bool = True) -> dict[str, Any]:
    return {
        "candidate_first": True,
        "report_first": not bool(apply),
        "apply_requested": bool(apply),
        "hard_delete": False,
        "includes_raw_candidate_content": False,
        "auto_promote_requested": False,
        "writes_candidates": bool(writes_candidates),
        "active_memory_writes": "policy-gated only when --apply is set",
        "sync_writes": "dry-run unless --apply is set",
    }


def _next_actions(
    sync: dict[str, Any],
    cycle: dict[str, Any],
    inbox: dict[str, Any],
    review: dict[str, Any],
    learning: dict[str, Any],
    daily: dict[str, Any],
    vector_index: dict[str, Any],
    *,
    apply: bool,
) -> list[str]:
    actions: list[str] = []
    if sync.get("errors"):
        actions.append("Fix sync errors before enabling scheduled central writes.")
    if sync.get("dry_run") and not apply:
        actions.append("Keep sync in dry-run until trusted host credentials and policy are ready.")
    if (review.get("summary") or {}).get("requires_human_decision"):
        actions.append("Review the top daily report cards and record accept/reject/defer feedback.")
    elif (inbox.get("summary") or {}).get("pending_candidates"):
        actions.append("Let an agent review the candidate inbox; no urgent human decision is required.")
    if learning.get("status") in {"cold", "blocked"}:
        actions.append("Collect more review-summary feedback before widening automation.")
    if vector_index.get("status") == "stale" or int(vector_index.get("shared_remote_risk_vector_rows") or 0):
        actions.append("Review vector-index status before enabling hybrid or shared remote vector retrieval.")
    if cycle.get("status") == "blocked":
        actions.append(cycle.get("next_action", "Initialize the vault before running the daily loop."))
    if not actions:
        actions.append(daily.get("next_action", "Keep the daily-loop schedule running."))
    return actions[:5]
