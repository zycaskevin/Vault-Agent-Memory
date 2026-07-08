"""Consolidated CLI surface for the Central Memory Station workflow."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Callable


JsonPrinter = Callable[..., None]
ProjectFinder = Callable[[], Any]


def add_memory_station_parsers(sub: argparse._SubParsersAction) -> None:
    """Register the high-level Central Memory Station command groups."""
    _add_start_parser(sub)
    _add_memory_sync_parser(sub)
    _add_memory_review_parser(sub)
    _add_memory_lifecycle_parser(sub)
    _add_ops_parser(sub)


def _add_output_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="輸出 JSON")
    parser.add_argument("--pretty", action="store_true", help="縮排 JSON 輸出")


def _add_start_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("start", help="Central Memory Station 初次設定與導覽入口")
    parser.add_argument("--json", action="store_true", help="輸出 JSON")
    parser.add_argument("--pretty", action="store_true", help="縮排 JSON 輸出")


def _add_memory_sync_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("memory-sync", help="中央記憶站同步：交上去、拿回來、看狀態")
    sync_sub = parser.add_subparsers(dest="memory_sync_action")

    sp = sync_sub.add_parser("status", help="顯示 local vault、中央副本與 sync freshness 狀態")
    sp.add_argument("--agent-id", default="", help="聚焦特定 Agent/remote reader")
    sp.add_argument("--max-sync-age-minutes", type=int, default=24 * 60)
    _add_output_args(sp)

    sp = sync_sub.add_parser("doctor", help="檢查中央同步前置條件與下一步")
    sp.add_argument("--agent-id", default="", help="聚焦特定 Agent/remote reader")
    sp.add_argument("--max-sync-age-minutes", type=int, default=24 * 60)
    _add_output_args(sp)

    sp = sync_sub.add_parser("push", help="提交一筆候選記憶到中央收件箱")
    sp.add_argument("--title", required=True, help="候選記憶標題")
    sp.add_argument("--content", required=True, help="候選記憶內容")
    sp.add_argument("--reason", default="", help="為什麼值得記住")
    sp.add_argument("--from-agent", default="", help="提交此候選的 Agent ID")
    sp.add_argument("--category", default="general")
    sp.add_argument("--tags", default="")
    sp.add_argument("--trust", type=float, default=0.5)
    sp.add_argument("--scope", choices=["project", "shared", "public"], default="project")
    sp.add_argument("--sensitivity", choices=["low", "medium"], default="low")
    sp.add_argument("--owner-agent", default="")
    sp.add_argument("--allowed-agents", default="")
    sp.add_argument("--memory-type", default="remote_candidate")
    sp.add_argument("--source-ref", default="")
    sp.add_argument("--idempotency-key", default="")
    sp.add_argument(
        "--central-backend",
        choices=["supabase", "self-host"],
        default="supabase",
        help="中央候選箱 backend；預設 supabase，self-host 使用本機 vault-central.db",
    )
    sp.add_argument(
        "--central-store",
        action="store_true",
        help="Supabase backend 時直接提交到新的 Central Memory Station candidate table",
    )
    _add_output_args(sp)

    sp = sync_sub.add_parser("pull", help="從中央收件箱拉回候選記憶；預設只預覽")
    sp.add_argument("--agent-id", default="", help="執行拉取的本機/授權 Agent ID")
    sp.add_argument("--limit", "-n", type=int, default=20)
    sp.add_argument("--apply", action="store_true", help="寫入本機 memory_candidates")
    sp.add_argument("--require-hmac", action="store_true", help="要求候選同步包具備有效 HMAC")
    sp.add_argument("--auto-promote-low-risk", action="store_true", help="套用 policy 允許的低風險提升")
    sp.add_argument(
        "--central-backend",
        choices=["supabase", "self-host"],
        default="supabase",
        help="中央候選箱 backend；預設 supabase，self-host 使用本機 vault-central.db",
    )
    _add_output_args(sp)

    sp = sync_sub.add_parser("run-once", help="執行一次同步檢查，並可選擇拉回中央候選")
    sp.add_argument("--agent-id", default="", help="執行同步的 Agent ID")
    sp.add_argument("--max-sync-age-minutes", type=int, default=24 * 60)
    sp.add_argument("--limit", "-n", type=int, default=20)
    sp.add_argument("--push-read-copy", action="store_true", help="推送本機已審核記憶到中央 read copy")
    sp.add_argument("--push-central-store", action="store_true", help="推送本機已審核記憶到 Central Memory Station tables")
    sp.add_argument("--push-central-vectors", action="store_true", help="推送已審核 safe summary embeddings 到中央向量索引")
    sp.add_argument("--pull-candidates", action="store_true", help="同時執行 memory-sync pull preview")
    sp.add_argument(
        "--central-backend",
        choices=["supabase", "self-host"],
        default="supabase",
        help="搭配 --pull-candidates 選擇中央候選箱 backend",
    )
    sp.add_argument("--apply", action="store_true", help="搭配 --pull-candidates 寫入本機候選池")
    sp.add_argument("--auto-promote-low-risk", action="store_true", help="搭配 --apply 套用低風險自動提升 policy")
    sp.add_argument("--require-hmac", action="store_true", help="拉取候選時要求有效 HMAC")
    sp.add_argument("--include-content", action="store_true", help="推送 read copy 時包含全文；預設只同步 metadata/summary/hash")
    sp.add_argument("--document-map", action=argparse.BooleanOptionalAction, default=True)
    sp.add_argument("--health", action=argparse.BooleanOptionalAction, default=True)
    sp.add_argument("--dry-run", action="store_true", help="只寫同步報告，不接觸中央服務")
    sp.add_argument("--report", default="", help="同步報告路徑；預設 reports/central-memory-sync-latest.json")
    _add_output_args(sp)


def _add_memory_review_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("memory-review", help="中央整理與審核：候選、衝突、人工決策")
    review_sub = parser.add_subparsers(dest="memory_review_action")

    sp = review_sub.add_parser("run", help="跑一次保守整理預覽；--apply 才執行 policy 允許動作")
    sp.add_argument("--mode", choices=["conservative", "balanced", "autonomous"], default="conservative")
    sp.add_argument("--limit", "-n", type=int, default=20)
    sp.add_argument("--apply", action="store_true")
    sp.add_argument("--no-report", action="store_true")
    _add_output_args(sp)

    sp = review_sub.add_parser("inbox", help="顯示候選記憶與同步衝突審核隊列")
    sp.add_argument("--limit", "-n", type=int, default=20)
    sp.add_argument("--include-content", action="store_true")
    _add_output_args(sp)

    sp = review_sub.add_parser("preview", help="預覽候選或衝突")
    sp.add_argument("item_id", help="candidate id 或 conflict id")
    sp.add_argument("--context-lines", type=int, default=2)
    _add_output_args(sp)

    sp = review_sub.add_parser("resolve", help="解決衝突；候選提升仍請用 vault promote")
    sp.add_argument("item_id", help="conflict id")
    sp.add_argument(
        "--action",
        choices=["keep_active", "accept_candidate", "merge_manual", "keep_both", "fork_private", "archive_stale"],
        required=True,
    )
    sp.add_argument("--reason", default="")
    sp.add_argument("--agent-id", default="")
    sp.add_argument("--apply-memory-change", action="store_true")
    _add_output_args(sp)


def _add_memory_lifecycle_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("memory-lifecycle", help="做夢、遺忘、歸檔、冷存")
    lifecycle_sub = parser.add_subparsers(dest="memory_lifecycle_action")

    sp = lifecycle_sub.add_parser("status", help="顯示記憶使用、過期與冷存壓力")
    sp.add_argument("--limit", "-n", type=int, default=10)
    _add_output_args(sp)

    sp = lifecycle_sub.add_parser("dream", help="跑 Dream 整理；預設 report-only")
    sp.add_argument("--mode", choices=["report", "apply_safe"], default="report")
    sp.add_argument(
        "--checks",
        nargs="*",
        choices=["freshness", "dedup", "convergence", "metadata", "orphans"],
    )
    sp.add_argument("--limit", "-n", type=int, default=50)
    sp.add_argument("--write-report", action="store_true")
    sp.add_argument("--write-candidates", action="store_true")
    sp.add_argument("--no-backup", action="store_true")
    _add_output_args(sp)

    sp = lifecycle_sub.add_parser("archive", help="歸檔 expires_at 已到期且可安全移出日常搜尋的記憶")
    sp.add_argument("--limit", "-n", type=int, default=100)
    sp.add_argument("--apply", action="store_true")
    _add_output_args(sp)

    sp = lifecycle_sub.add_parser("forget", help="產生遺忘/降權/冷存建議；不硬刪")
    sp.add_argument("--limit", "-n", type=int, default=20)
    sp.add_argument("--write-candidates", action="store_true", help="將建議寫成候選記憶")
    _add_output_args(sp)

    sp = lifecycle_sub.add_parser("cold-store", help="摘要並冷存已到期但仍常被使用的記憶")
    sp.add_argument("--limit", "-n", type=int, default=100)
    sp.add_argument("--min-usage", type=int, default=1)
    sp.add_argument("--summary-max-chars", type=int, default=360)
    sp.add_argument("--apply", action="store_true")
    _add_output_args(sp)


def _add_ops_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("ops", help="維護入口：doctor、status、security、db、gateway")
    ops_sub = parser.add_subparsers(dest="ops_action")

    sp = ops_sub.add_parser("status", help="顯示本機 runtime、registry 與更新狀態")
    sp.add_argument("--agent", default="")
    sp.add_argument("--read-status", action="store_true")
    sp.add_argument("--write-status", action="store_true")
    sp.add_argument("--doctor", action="store_true")
    _add_output_args(sp)

    sp = ops_sub.add_parser("doctor", help="執行環境診斷")
    _add_output_args(sp)

    sp = ops_sub.add_parser("security", help="執行安全自檢")
    _add_output_args(sp)


def cmd_start(args: argparse.Namespace, *, json_print: JsonPrinter) -> None:
    payload = {
        "ok": True,
        "surface": "central_memory_station",
        "message": "Use these primary commands for the governed memory workflow.",
        "commands": [
            "vault start",
            "vault daily-loop run --write-report",
            "vault remember",
            "vault search",
            "vault memory-sync status",
            "vault memory-review inbox",
            "vault memory-lifecycle status",
            "vault ops doctor",
        ],
        "legacy_policy": "Existing detailed commands remain available as advanced aliases.",
    }
    if getattr(args, "json", False) or getattr(args, "pretty", False):
        json_print(payload, pretty=getattr(args, "pretty", False))
        return
    print("Central Memory Station")
    for command in payload["commands"]:
        print(f"  - {command}")
    print("Existing detailed commands remain available as advanced aliases.")


def cmd_memory_sync(
    args: argparse.Namespace,
    *,
    find_project_dir: ProjectFinder,
    json_print: JsonPrinter,
) -> None:
    action = getattr(args, "memory_sync_action", "")
    if action in {"status", "doctor"}:
        from vault.remote_status import build_remote_status

        project_dir = find_project_dir()
        status = build_remote_status(
            project_dir,
            agent_id=getattr(args, "agent_id", "") or "",
            max_sync_age_minutes=getattr(args, "max_sync_age_minutes", 24 * 60),
        )
        payload: dict[str, Any] = {
            "ok": status.get("ok", False),
            "action": action,
            "central_memory_station": True,
            "status": status,
            "next_action": _sync_next_action(status),
        }
        if action == "doctor":
            payload["ok"] = bool(status.get("local", {}).get("db_exists")) and not any(
                item.get("severity") == "high" for item in status.get("warnings", [])
            )
        _emit(payload, args, json_print)
        return

    if action == "run-once":
        from vault.central_sync import run_central_memory_sync

        payload = run_central_memory_sync(
            find_project_dir(),
            agent_id=getattr(args, "agent_id", "") or "",
            max_sync_age_minutes=getattr(args, "max_sync_age_minutes", 24 * 60),
            push_read_copy=bool(getattr(args, "push_read_copy", False)),
            push_central_store=bool(getattr(args, "push_central_store", False)),
            push_central_vectors=bool(getattr(args, "push_central_vectors", False)),
            pull_candidates=bool(getattr(args, "pull_candidates", False)),
            central_backend=getattr(args, "central_backend", "supabase") or "supabase",
            candidate_limit=getattr(args, "limit", 20),
            apply=bool(getattr(args, "apply", False)),
            auto_promote_low_risk=bool(getattr(args, "auto_promote_low_risk", False)),
            require_hmac=True if bool(getattr(args, "require_hmac", False)) else None,
            include_content=bool(getattr(args, "include_content", False)),
            document_map=bool(getattr(args, "document_map", True)),
            health=bool(getattr(args, "health", True)),
            dry_run=bool(getattr(args, "dry_run", False)),
            report_path=getattr(args, "report", "") or None,
        )
        _emit(payload, args, json_print)
        return

    if action == "push":
        backend = str(getattr(args, "central_backend", "supabase") or "supabase")
        kwargs = dict(
            title=args.title,
            content=args.content,
            reason=args.reason or "",
            from_agent=args.from_agent or "",
            category=args.category or "general",
            tags=args.tags or "",
            trust=args.trust,
            scope=args.scope or "project",
            sensitivity=args.sensitivity or "low",
            owner_agent=args.owner_agent or "",
            allowed_agents=args.allowed_agents or "",
            memory_type=args.memory_type or "remote_candidate",
            source_ref=args.source_ref or "",
            idempotency_key=args.idempotency_key or "",
        )
        if backend == "self-host":
            from vault.central_candidate_store import submit_central_candidate_local

            payload = submit_central_candidate_local(find_project_dir(), **kwargs)
        else:
            from vault.remote_candidates import (
                submit_central_candidate_request,
                submit_remote_candidate_request,
            )

            submitter = (
                submit_central_candidate_request
                if bool(getattr(args, "central_store", False))
                else submit_remote_candidate_request
            )
            payload = submitter(**kwargs)
        payload.setdefault("action", "push")
        payload.setdefault("central_memory_station", True)
        payload.setdefault("central_backend", backend)
        _emit(payload, args, json_print)
        return

    if action == "pull":
        payload = _pull_remote_candidates(args, find_project_dir())
        payload.setdefault("action", "pull")
        payload.setdefault("central_memory_station", True)
        _emit(payload, args, json_print)
        return

    print("error: memory-sync requires action: status, doctor, push, pull, or run-once", file=sys.stderr)
    raise SystemExit(2)


def cmd_memory_review(
    args: argparse.Namespace,
    *,
    find_project_dir: ProjectFinder,
    json_print: JsonPrinter,
) -> None:
    action = getattr(args, "memory_review_action", "")
    project_dir = find_project_dir()
    if action == "run":
        from vault.automation import automation_run

        payload = automation_run(
            project_dir,
            mode=args.mode,
            apply=bool(args.apply),
            limit=args.limit,
            write_reports=not bool(args.no_report),
        )
        payload["central_memory_station"] = True
        _emit(payload, args, json_print)
        return

    from vault.db import VaultDB
    from vault.multi_host import list_conflicts, preview_conflict, resolve_conflict

    try:
        with VaultDB(project_dir / "vault.db") as db:
            if action == "inbox":
                candidates = db.list_memory_candidates(status="candidate", limit=args.limit)
                if not bool(args.include_content):
                    for candidate in candidates:
                        if "content" in candidate:
                            candidate["content_preview"] = str(candidate.get("content") or "")[:160]
                            candidate.pop("content", None)
                conflicts = list_conflicts(db, status="open", limit=args.limit)
                payload = {
                    "ok": True,
                    "action": "inbox",
                    "central_memory_station": True,
                    "candidate_count": len(candidates),
                    "conflict_count": len(conflicts),
                    "candidates": candidates,
                    "conflicts": conflicts,
                }
            elif action == "preview":
                if str(args.item_id).startswith("conf_"):
                    payload = preview_conflict(db, args.item_id, context_lines=args.context_lines)
                else:
                    candidate = db.get_memory_candidate(args.item_id)
                    payload = {
                        "ok": bool(candidate),
                        "action": "preview",
                        "type": "candidate",
                        "candidate": candidate or {},
                    }
            elif action == "resolve":
                resolution = _review_resolution(args.action)
                payload = {
                    "ok": True,
                    "action": "resolve",
                    "conflict": resolve_conflict(
                        db,
                        args.item_id,
                        resolution=resolution,
                        reason=args.reason or "",
                        actor_agent=args.agent_id or "",
                        apply_memory_change=bool(args.apply_memory_change),
                        project_dir=project_dir,
                    ),
                }
            else:
                print("error: memory-review requires action: run, inbox, preview, or resolve", file=sys.stderr)
                raise SystemExit(2)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    _emit(payload, args, json_print)


def cmd_memory_lifecycle(
    args: argparse.Namespace,
    *,
    find_project_dir: ProjectFinder,
    json_print: JsonPrinter,
) -> None:
    action = getattr(args, "memory_lifecycle_action", "")
    project_dir = find_project_dir()
    if action == "dream":
        from vault.dream import run_dream

        payload = run_dream(
            project_dir,
            mode=args.mode,
            checks=args.checks,
            limit=args.limit,
            write_report=bool(args.write_report),
            write_candidates=bool(args.write_candidates),
            backup=not bool(args.no_backup),
        )
        payload["central_memory_station"] = True
        _emit(payload, args, json_print)
        return

    from vault.db import VaultDB

    try:
        with VaultDB(project_dir / "vault.db") as db:
            if action == "status":
                payload = {
                    "ok": True,
                    "action": "status",
                    "central_memory_station": True,
                    **db.usage_stats(limit=args.limit),
                }
            elif action == "archive":
                payload = db.archive_expired_knowledge(limit=args.limit, dry_run=not args.apply)
            elif action == "cold-store":
                payload = db.cold_store_expired_knowledge(
                    limit=args.limit,
                    dry_run=not args.apply,
                    min_usage=args.min_usage,
                    summary_max_chars=args.summary_max_chars,
                )
            elif action == "forget":
                from vault.automation_lifecycle import _usage_review, _write_forgetting_candidates
                from vault.automation_policy import load_policy

                policy = load_policy(project_dir)
                archive_preview = db.archive_expired_knowledge(
                    limit=args.limit,
                    dry_run=True,
                    skip_used=bool(policy.get("protect_used_expired", True)),
                    protected_scopes=_config_list(policy, "protected_scopes"),
                    protected_sensitivities=_config_list(policy, "protected_sensitivities"),
                )
                usage = db.usage_stats(limit=args.limit)
                usage_review = _usage_review(policy, usage, archive_preview)
                suggestions = _write_forgetting_candidates(db, usage_review) if bool(args.write_candidates) else []
                payload = {
                    "ok": True,
                    "action": "forget",
                    "central_memory_station": True,
                    "hard_delete": False,
                    "message": "Forgetting is policy-based decay, archive, cold-store, or review; it never hard-deletes by default.",
                    "usage_review": usage_review,
                    "candidate_suggestions": len(suggestions),
                    "suggestions": suggestions,
                    "next_action": "Review forgetting suggestions, then archive or cold-store only after policy allows it.",
                    "write_candidates": bool(args.write_candidates),
                }
            else:
                print("error: memory-lifecycle requires action: status, dream, archive, forget, or cold-store", file=sys.stderr)
                raise SystemExit(2)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    payload.setdefault("central_memory_station", True)
    _emit(payload, args, json_print)


def cmd_ops(
    args: argparse.Namespace,
    *,
    json_print: JsonPrinter,
) -> None:
    action = getattr(args, "ops_action", "")
    if action == "status":
        from vault.agent_registry import build_update_status, read_update_status, write_update_status

        if bool(args.read_status):
            payload = read_update_status(agent_id=args.agent or "")
        else:
            payload = build_update_status(check_pypi=False, agent_id=args.agent or "")
        if bool(args.write_status):
            payload["status_path"] = str(write_update_status(payload))
        if bool(args.doctor):
            payload["doctor"] = True
        _emit(payload, args, json_print)
        return
    if action == "doctor":
        from vault.cli_core import cmd_doctor

        return cmd_doctor(args)
    if action == "security":
        from vault.security import security_doctor

        _emit(security_doctor(), args, json_print)
        return
    print("error: ops requires action: status, doctor, or security", file=sys.stderr)
    raise SystemExit(2)


def _pull_remote_candidates(args: argparse.Namespace, project_dir: Any) -> dict[str, Any]:
    if getattr(args, "auto_promote_low_risk", False) and not getattr(args, "apply", False):
        return {
            "ok": False,
            "error": "apply_required",
            "message": "--auto-promote-low-risk requires --apply because it can write active knowledge.",
        }
    backend = str(getattr(args, "central_backend", "supabase") or "supabase")
    if backend == "self-host":
        from vault.central_candidate_store import pull_central_candidates_local

        payload = pull_central_candidates_local(
            project_dir,
            agent_id=getattr(args, "agent_id", "") or "",
            limit=getattr(args, "limit", 20),
            apply=bool(getattr(args, "apply", False)),
            auto_promote_low_risk=bool(getattr(args, "auto_promote_low_risk", False)),
            require_hmac=True if bool(getattr(args, "require_hmac", False)) else None,
        )
    else:
        from vault.remote_candidates import pull_remote_candidate_requests

        payload = pull_remote_candidate_requests(
            project_dir,
            agent_id=getattr(args, "agent_id", "") or "",
            limit=getattr(args, "limit", 20),
            apply=bool(getattr(args, "apply", False)),
            auto_promote_low_risk=bool(getattr(args, "auto_promote_low_risk", False)),
            require_hmac=True if bool(getattr(args, "require_hmac", False)) else None,
        )
    payload.setdefault("central_backend", backend)
    return payload


def _review_resolution(action: str) -> str:
    if action == "accept_candidate":
        return "accept_remote"
    if action in {"merge_manual", "keep_both", "fork_private", "archive_stale"}:
        return "manual"
    return "keep_local"


def _sync_next_action(status: dict[str, Any]) -> str:
    warnings = status.get("warnings") or []
    if any(item.get("code") == "sync_report_missing" for item in warnings):
        return "Run memory-sync run-once after configuring the central store, then write a sync report."
    if any(item.get("severity") == "high" for item in warnings):
        return "Fix high-severity setup warnings before enabling scheduled sync."
    return "Schedule memory-sync run-once every 30-60 minutes for local working vaults."


def _config_list(config: dict[str, Any], key: str) -> list[str]:
    value = config.get(key)
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _emit(payload: dict[str, Any], args: argparse.Namespace, json_print: JsonPrinter) -> None:
    if getattr(args, "json", False) or getattr(args, "pretty", False):
        json_print(payload, pretty=getattr(args, "pretty", False))
        return
    print(json.dumps(payload, ensure_ascii=False, indent=2))
