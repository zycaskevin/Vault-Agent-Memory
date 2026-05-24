#!/usr/bin/env python3
"""Cron-ready Guardrails Dream daily review report entrypoint.

This script is intentionally report-only/local-only.  It builds the Dream review
report artifacts for a date, updates a local latest pointer, and prints a short
no-agent-friendly Feishu message only when candidates exist.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from guardrails_lite.dream_report import (
    build_dream_review_report,
    write_dream_review_report_json,
    write_dream_review_report_markdown,
)
from guardrails_lite.dream_triage import build_local_model_triage_packet, write_local_model_triage_packet
from guardrails_lite.dashboard_aggregate import build_guardrails_dashboard_aggregate, write_guardrails_dashboard_aggregate
from guardrails_lite.report_history import append_trend_snapshot, build_trend_snapshot, validate_history_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build local-only Dream daily review artifacts for cron.")
    parser.add_argument("--project-dir", default=".", help="Guardrails project directory containing guardrails.db")
    parser.add_argument("--db-path", help="Optional explicit Guardrails DB path")
    parser.add_argument("--runtime-dir", default=_default_runtime_dir(), help="Runtime artifact directory outside raw/compiled")
    parser.add_argument("--date", default=datetime.now().date().isoformat(), help="Review date filter, YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=50, help="Maximum candidates; 0 means no limit")
    parser.add_argument("--local-model", default="qwen3.6:35b", help="Local model name for prompt-only triage packet")
    args = parser.parse_args(argv)

    try:
        project_dir = Path(args.project_dir).expanduser().resolve()
        db_path = Path(args.db_path).expanduser().resolve() if args.db_path else project_dir / "guardrails.db"
        runtime_dir = Path(args.runtime_dir).expanduser().resolve()
        _validate_runtime_dir(project_dir, runtime_dir)
        report = build_dream_review_report(db_path, date=args.date, limit=args.limit)
        paths = _write_artifacts(project_dir, runtime_dir, args.date, report, local_model=args.local_model)
        _write_latest_pointer(runtime_dir, args.date, report, paths)
        if report["counts"]["candidates"] > 0:
            sys.stdout.write(_stdout_message(report, paths))
        return 0
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - defensive cron boundary
        print(f"error: dream daily review failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


def _default_runtime_dir() -> str:
    base = os.environ.get("GUARDRAILS_RUNTIME_DIR") or os.environ.get("HERMES_HOME")
    if base:
        return str(Path(base) / "runtime" / "guardrails")
    return str(Path.home() / ".hermes" / "runtime" / "guardrails")


def _validate_runtime_dir(project_dir: Path, runtime_dir: Path) -> None:
    raw_dir = (project_dir / "raw").resolve()
    compiled_dir = (project_dir / "compiled").resolve()
    if _is_relative_to(runtime_dir, raw_dir) or _is_relative_to(runtime_dir, compiled_dir):
        raise ValueError("runtime-dir must not be under project raw/ or compiled/")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _write_artifacts(
    project_dir: Path,
    runtime_dir: Path,
    date: str,
    report: dict[str, Any],
    *,
    local_model: str,
) -> dict[str, Path]:
    report_dir = runtime_dir / "dream-review" / date
    json_path = report_dir / f"dream_review_{date}.json"
    markdown_path = report_dir / f"dream_review_{date}.md"
    triage_path = report_dir / f"dream_triage_packet_{date}.json"
    dashboard_path = report_dir / f"dashboard_aggregate_{date}.json"
    history_path = validate_history_path(project_dir, runtime_dir / "dream-review" / "history" / "dashboard_history.jsonl")
    triage_packet = build_local_model_triage_packet(report, model=local_model)
    dashboard_aggregate = build_guardrails_dashboard_aggregate(report, None)
    trend_snapshot = build_trend_snapshot(dashboard_aggregate, snapshot_date=date)
    write_dream_review_report_json(json_path, report)
    write_dream_review_report_markdown(markdown_path, report)
    write_local_model_triage_packet(triage_path, triage_packet)
    write_guardrails_dashboard_aggregate(dashboard_path, dashboard_aggregate)
    append_trend_snapshot(history_path, trend_snapshot)
    return {
        "json_path": json_path.resolve(),
        "markdown_path": markdown_path.resolve(),
        "triage_packet_path": triage_path.resolve(),
        "dashboard_aggregate_path": dashboard_path.resolve(),
        "history_path": history_path.resolve(),
    }


def _write_latest_pointer(runtime_dir: Path, date: str, report: dict[str, Any], paths: dict[str, Path]) -> None:
    latest_dir = runtime_dir / "dream-review"
    latest_dir.mkdir(parents=True, exist_ok=True)
    latest_path = latest_dir / "latest.json"
    payload = {
        "schema": "guardrails.dream.review.latest.v1",
        "date": date,
        "json_path": str(paths["json_path"]),
        "markdown_path": str(paths["markdown_path"]),
        "triage_packet_path": str(paths["triage_packet_path"]),
        "dashboard_aggregate_path": str(paths["dashboard_aggregate_path"]),
        "history_path": str(paths["history_path"]),
        "candidates": report["counts"]["candidates"],
        "report_only": True,
        "auto_promote": False,
        "formal_knowledge_written": False,
        "raw_written": False,
        "sync_invoked": False,
    }
    tmp_path = latest_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(latest_path)


def _stdout_message(report: dict[str, Any], paths: dict[str, Path]) -> str:
    counts = report["counts"]
    by_action = counts.get("by_recommended_action", {})
    conclusion = report.get("reviewer_ux", {}).get("conclusion", {})
    quick_replies = report.get("reviewer_ux", {}).get("quick_replies", [])
    lines = [
        "# Guardrails Dream Curator — Daily Review",
        "",
        f"Date: `{report.get('date') or 'all'}`",
        f"Candidates: {counts['candidates']}",
        "report_only=true; auto_promote=false; formal_knowledge_written=false; raw_written=false; sync_invoked=false",
        "",
        (
            f"建議寫入 {conclusion.get('suggest_promote', 0)}、"
            f"合併 {conclusion.get('suggest_merge', 0)}、"
            f"丟棄 {conclusion.get('suggest_discard', 0)}、"
            f"封鎖 {conclusion.get('blocked', 0)}、"
            f"需 Arthur 裁決 {conclusion.get('need_arthur', 0)}。"
        ),
        f"Actions: `{json.dumps(by_action, ensure_ascii=False, sort_keys=True)}`",
        "",
        "Feishu 快速回覆: " + (" / ".join(str(reply) for reply in quick_replies) if quick_replies else "先不用"),
        f"JSON: `{paths['json_path']}`",
        f"Markdown: `{paths['markdown_path']}`",
        f"Triage packet: `{paths['triage_packet_path']}`",
        f"Dashboard aggregate: `{paths['dashboard_aggregate_path']}`",
        f"Trend history: `{paths['history_path']}`",
        f"MEDIA:{paths['markdown_path']}",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
