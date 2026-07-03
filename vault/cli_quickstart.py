from __future__ import annotations

import json
import sys
from pathlib import Path

from vault.agent_setup import AgentSetupConfig, default_project_dir, interactive_setup, run_agent_setup
from vault.cli_flow import _print_consumer_setup_summary


def cmd_quickstart(args):
    """Small first-run setup path for agent-assisted users."""
    if getattr(args, "non_interactive", False):
        config = _non_interactive_config(args)
    else:
        config = _interactive_config(args)

    payload = run_agent_setup(config)
    payload.setdefault("ok", True)
    payload.setdefault("status", "ok")
    if args.pretty or args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    _print_consumer_setup_summary(payload)


def _non_interactive_config(args) -> AgentSetupConfig:
    scope = args.scope or "private"
    connections = str(args.connections or "none").strip().lower()
    wants_obsidian = connections in {"obsidian", "both", "all"}
    wants_supabase = connections in {"supabase", "both", "all"}
    if wants_obsidian and not args.obsidian_vault:
        print(
            "error: --connections obsidian/both requires --obsidian-vault in --non-interactive mode",
            file=sys.stderr,
        )
        raise SystemExit(2)

    memory_mode = args.memory_mode or "governed-auto"
    features = ["core", "mcp"]
    if wants_obsidian:
        features.append("obsidian_import")
    if wants_supabase:
        features.append("supabase")

    return AgentSetupConfig(
        project_dir=Path(args.agent_project_dir or default_project_dir(scope, agent=args.agent)),
        scope=scope,
        agent=args.agent,
        audience="consumer",
        memory_mode=memory_mode,
        memory_layout="shared" if scope == "shared" else "private",
        features=features,
        language=args.language or "en",
        tool_profile="core",
        obsidian_vault=Path(args.obsidian_vault).expanduser() if args.obsidian_vault else None,
        obsidian_write_default_rules=wants_obsidian,
        obsidian_review_inbox=wants_obsidian,
        sync_targets="cron" if wants_obsidian else "none",
        supabase_setup_mode="simple" if wants_supabase else "none",
        supabase_sync_targets="cron" if wants_supabase else "none",
        remote_reader_targets="shell" if wants_supabase else "none",
        automation_schedule_targets="cron",
        automation_mode="balanced",
        automation_command="cycle",
        automation_apply=memory_mode == "governed-auto",
        automation_write_workspace=True,
        automation_auto_promote_low_risk=memory_mode == "governed-auto",
        daily_report_time=args.daily_report_time or "09:00",
        template_dir=Path(args.template_dir).expanduser() if args.template_dir else None,
    )


def _interactive_config(args) -> AgentSetupConfig:
    setup_values = {
        "agent": args.agent,
        "audience": "consumer",
        "memory_mode": args.memory_mode,
        "scope": args.scope,
        "project_dir": args.agent_project_dir,
        "language": args.language,
        "consumer_connections": args.connections,
        "obsidian_vault": args.obsidian_vault,
        "daily_report_time": args.daily_report_time,
        "template_dir": args.template_dir,
    }
    return interactive_setup(setup_values)
