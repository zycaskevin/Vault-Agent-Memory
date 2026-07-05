"""CLI entrypoint for the scheduled daily memory loop."""

from __future__ import annotations

import argparse
from typing import Any, Callable

from .daily_loop import (
    build_daily_loop_report,
    build_daily_loop_status,
    refresh_daily_loop_report,
    render_daily_loop_text,
    run_daily_loop,
)


def add_daily_loop_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("daily-loop", help="Run the scheduled memory loop and write compact reports")
    loop_sub = parser.add_subparsers(dest="daily_loop_action")

    sp = loop_sub.add_parser("run", help="Run sync, automation, inbox, review, learning, and daily report")
    _add_common_args(sp)
    sp.add_argument("--agent-id", default="", help="Agent/runtime id for sync and status checks")
    sp.add_argument("--mode", choices=["conservative", "balanced", "autonomous"], default="balanced")
    sp.add_argument("--apply", action="store_true", help="allow existing policy-gated reversible actions")
    sp.add_argument("--min-events", type=int, default=5, help="minimum feedback events before learning is warm")
    sp.add_argument("--include-transcripts", action="store_true", help="include metadata-only transcript hints")
    sp.add_argument("--transcript-limit", type=int, default=5, help="maximum transcript discovery/capture hints")
    sp.add_argument("--central-backend", choices=["supabase", "self-host"], default="supabase")
    sp.add_argument("--max-sync-age-minutes", type=int, default=24 * 60)
    sp.add_argument("--write-report", action="store_true", help="write reports/daily-loop/daily-loop-latest.json and .md")
    sp.add_argument("--report-path", default="", help="custom reports/daily-loop/*.json path")

    sp = loop_sub.add_parser("status", help="Read daily-loop freshness and sync status")
    sp.add_argument("--agent-id", default="", help="Agent/runtime id for sync checks")
    sp.add_argument("--max-sync-age-minutes", type=int, default=24 * 60)
    _add_output_args(sp)

    sp = loop_sub.add_parser("report", help="Render the latest daily-loop run as a human report")
    sp.add_argument("--refresh", action="store_true", help="rebuild latest report from read-only status surfaces")
    sp.add_argument("--agent-id", default="", help="Agent/runtime id for refresh sync checks")
    sp.add_argument("--limit", "-n", type=int, default=5, help="maximum human-review cards when refreshing")
    sp.add_argument("--min-events", type=int, default=5, help="minimum feedback events before learning is warm")
    sp.add_argument("--include-transcripts", action="store_true", help="include metadata-only transcript hints when refreshing")
    sp.add_argument("--transcript-limit", type=int, default=5, help="maximum transcript discovery hints")
    sp.add_argument("--max-sync-age-minutes", type=int, default=24 * 60)
    sp.add_argument("--language", choices=["en", "zh-Hant", "zh-CN"], default="en")
    sp.add_argument("--write-report", action="store_true", help="rewrite reports/daily-loop/daily-loop-latest.md")
    sp.add_argument("--report-path", default="", help="custom reports/daily-loop/*.json path")
    _add_output_args(sp)


def cmd_daily_loop(
    args: Any,
    *,
    find_project_dir: Callable[[], Any],
    json_print: Callable[..., None],
) -> None:
    action = getattr(args, "daily_loop_action", "")
    project_dir = find_project_dir()
    if action == "run":
        payload = run_daily_loop(
            project_dir,
            agent_id=getattr(args, "agent_id", "") or "",
            mode=getattr(args, "mode", "balanced") or "balanced",
            apply=bool(getattr(args, "apply", False)),
            limit=getattr(args, "limit", 5),
            min_events=getattr(args, "min_events", 5),
            language=getattr(args, "language", "en"),
            include_transcripts=bool(getattr(args, "include_transcripts", False)),
            transcript_limit=getattr(args, "transcript_limit", 5),
            central_backend=getattr(args, "central_backend", "supabase") or "supabase",
            max_sync_age_minutes=getattr(args, "max_sync_age_minutes", 24 * 60),
            write_report=bool(getattr(args, "write_report", False)),
            report_path=getattr(args, "report_path", ""),
        )
    elif action == "status":
        payload = build_daily_loop_status(
            project_dir,
            agent_id=getattr(args, "agent_id", "") or "",
            max_sync_age_minutes=getattr(args, "max_sync_age_minutes", 24 * 60),
        )
    elif action == "report" and bool(getattr(args, "refresh", False)):
        payload = refresh_daily_loop_report(
            project_dir,
            agent_id=getattr(args, "agent_id", "") or "",
            limit=getattr(args, "limit", 5),
            min_events=getattr(args, "min_events", 5),
            language=getattr(args, "language", "en"),
            include_transcripts=bool(getattr(args, "include_transcripts", False)),
            transcript_limit=getattr(args, "transcript_limit", 5),
            max_sync_age_minutes=getattr(args, "max_sync_age_minutes", 24 * 60),
            write_report=bool(getattr(args, "write_report", False)),
            report_path=getattr(args, "report_path", ""),
        )
    elif action == "report":
        payload = build_daily_loop_report(
            project_dir,
            language=getattr(args, "language", "en"),
            write_report=bool(getattr(args, "write_report", False)),
            report_path=getattr(args, "report_path", ""),
        )
    else:
        raise SystemExit("error: daily-loop requires action: run, status, or report")

    if getattr(args, "json", False) or getattr(args, "pretty", False):
        json_print(payload, pretty=bool(getattr(args, "pretty", False)))
        return
    print(render_daily_loop_text(payload), end="")


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", "-n", type=int, default=5, help="maximum human-review cards")
    parser.add_argument("--language", choices=["en", "zh-Hant", "zh-CN"], default="en")
    _add_output_args(parser)


def _add_output_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="輸出 JSON")
    parser.add_argument("--pretty", action="store_true", help="縮排 JSON 輸出")
