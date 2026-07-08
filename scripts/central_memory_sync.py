#!/usr/bin/env python3
"""Run one Central Memory Station sync pass."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts._utils import find_db_path, load_dotenv_cascade  # noqa: E402
from vault.central_sync import run_central_memory_sync  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one Central Memory Station sync pass.")
    parser.add_argument("--db", default="", help="vault.db path; defaults to Vault discovery")
    parser.add_argument("--project-dir", default="", help="project directory; defaults to db parent")
    parser.add_argument("--agent-id", default="", help="trusted sync host / agent id")
    parser.add_argument("--max-sync-age-minutes", type=int, default=24 * 60)
    parser.add_argument("--push-read-copy", action="store_true", help="push reviewed local memory to the central read copy")
    parser.add_argument("--push-central-store", action="store_true", help="push reviewed local memory into Central Memory Station tables")
    parser.add_argument("--push-central-vectors", action="store_true", help="push reviewed safe-summary embeddings into the central vector index")
    parser.add_argument("--pull-candidates", action="store_true", help="pull central candidate memory into local review")
    parser.add_argument(
        "--central-backend",
        choices=["supabase", "self-host"],
        default="supabase",
        help="candidate inbox backend for --pull-candidates",
    )
    parser.add_argument("--limit", "-n", type=int, default=20)
    parser.add_argument("--apply", action="store_true", help="apply pull-candidates writes to local memory_candidates")
    parser.add_argument("--auto-promote-low-risk", action="store_true")
    parser.add_argument("--require-hmac", action="store_true")
    parser.add_argument("--include-content", action="store_true")
    parser.add_argument("--document-map", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--health", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", default="", help="report path; defaults to reports/central-memory-sync-latest.json")
    parser.add_argument("--json", action="store_true", help="print JSON payload")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    db_path = Path(args.db or find_db_path()).expanduser().resolve()
    project_dir = Path(args.project_dir).expanduser().resolve() if args.project_dir else db_path.parent
    load_dotenv_cascade(str(project_dir / ".env"))
    if not db_path.exists():
        print(f"vault.db not found: {db_path}", file=sys.stderr)
        return 2

    payload = run_central_memory_sync(
        project_dir,
        agent_id=args.agent_id,
        max_sync_age_minutes=args.max_sync_age_minutes,
        push_read_copy=bool(args.push_read_copy),
        push_central_store=bool(args.push_central_store),
        push_central_vectors=bool(args.push_central_vectors),
        pull_candidates=bool(args.pull_candidates),
        central_backend=args.central_backend,
        candidate_limit=args.limit,
        apply=bool(args.apply),
        auto_promote_low_risk=bool(args.auto_promote_low_risk),
        require_hmac=True if bool(args.require_hmac) else None,
        include_content=bool(args.include_content),
        document_map=bool(args.document_map),
        health=bool(args.health),
        dry_run=bool(args.dry_run),
        report_path=args.report or None,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"Central sync {payload['status']}: {payload['report_path']}")
    return 0 if payload.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
