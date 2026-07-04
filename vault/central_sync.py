"""Central Memory Station sync worker."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .remote_status import build_remote_status


SyncKnowledge = Callable[..., Any]
SyncDocumentMap = Callable[..., Any]
SyncHealth = Callable[..., Any]
PullCandidates = Callable[..., dict[str, Any]]
SyncCentralStore = Callable[..., dict[str, Any]]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_central_sync_report_path(project_dir: str | Path) -> Path:
    return Path(project_dir).expanduser().resolve() / "reports" / "central-memory-sync-latest.json"


def run_central_memory_sync(
    project_dir: str | Path,
    *,
    agent_id: str = "",
    max_sync_age_minutes: int = 24 * 60,
    push_read_copy: bool = False,
    push_central_store: bool = False,
    pull_candidates: bool = False,
    central_backend: str = "supabase",
    candidate_limit: int = 20,
    apply: bool = False,
    auto_promote_low_risk: bool = False,
    require_hmac: bool | None = None,
    include_content: bool = False,
    document_map: bool = True,
    health: bool = True,
    dry_run: bool = False,
    report_path: str | Path | None = None,
    sync_knowledge: SyncKnowledge | None = None,
    sync_document_map: SyncDocumentMap | None = None,
    sync_health: SyncHealth | None = None,
    sync_central_store: SyncCentralStore | None = None,
    pull_remote_candidates: PullCandidates | None = None,
) -> dict[str, Any]:
    """Run one Central Memory Station sync pass.

    The worker is conservative by default. It can inspect local/remote status and
    write a report without contacting Supabase. Actual remote writes require
    explicit flags such as ``push_read_copy`` or ``pull_candidates``.
    """
    project = Path(project_dir).expanduser().resolve()
    db_path = project / "vault.db"
    started_at = utc_now()
    report = Path(report_path).expanduser() if report_path else default_central_sync_report_path(project)
    operations: dict[str, Any] = {}
    errors: list[dict[str, str]] = []

    status = build_remote_status(project, agent_id=agent_id, max_sync_age_minutes=max_sync_age_minutes)

    if push_read_copy:
        operations["push_read_copy"] = _push_read_copy(
            db_path,
            dry_run=dry_run,
            include_content=include_content,
            document_map=document_map,
            health=health,
            sync_knowledge=sync_knowledge,
            sync_document_map=sync_document_map,
            sync_health=sync_health,
            errors=errors,
        )
    else:
        operations["push_read_copy"] = {
            "enabled": False,
            "status": "skipped",
            "reason": "Pass --push-read-copy to push reviewed local memory to the central read copy.",
        }

    if push_central_store:
        operations["push_central_store"] = _push_central_store(
            project,
            db_path,
            agent_id=agent_id,
            dry_run=dry_run,
            include_content=include_content,
            sync_central_store=sync_central_store,
            errors=errors,
        )
    else:
        operations["push_central_store"] = {
            "enabled": False,
            "status": "skipped",
            "reason": "Pass --push-central-store to write Central Memory Station tables.",
        }

    if pull_candidates:
        operations["pull_candidates"] = _pull_candidates(
            project,
            agent_id=agent_id,
            dry_run=dry_run,
            central_backend=central_backend,
            limit=candidate_limit,
            apply=apply,
            auto_promote_low_risk=auto_promote_low_risk,
            require_hmac=require_hmac,
            pull_remote_candidates=pull_remote_candidates,
            errors=errors,
        )
    else:
        operations["pull_candidates"] = {
            "enabled": False,
            "status": "skipped",
            "reason": "Pass --pull-candidates to pull central candidate memory into the local review queue.",
        }

    completed_at = utc_now()
    payload = {
        "ok": not errors,
        "status": "ok" if not errors else "failed",
        "mode": "central_memory_station_sync",
        "central_memory_station": True,
        "central_backend": _normalize_central_backend(central_backend),
        "source_of_truth": "local_sqlite",
        "direction": "local_to_central_read_copy_and_central_candidates_to_local_review",
        "bidirectional_active_memory": False,
        "project_dir": str(project),
        "db_path": str(db_path),
        "agent_id": agent_id,
        "dry_run": bool(dry_run),
        "started_at": started_at,
        "completed_at": completed_at,
        "last_synced_at": completed_at if not errors and not dry_run else "",
        "remote_status": status,
        "operations": operations,
        "errors": errors,
        "report_path": str(report),
        "next_action": _next_action(operations, errors, dry_run=dry_run),
    }
    _write_report(report, payload)
    return payload


def _push_read_copy(
    db_path: Path,
    *,
    dry_run: bool,
    include_content: bool,
    document_map: bool,
    health: bool,
    sync_knowledge: SyncKnowledge | None,
    sync_document_map: SyncDocumentMap | None,
    sync_health: SyncHealth | None,
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    command = [
        "python",
        "-m",
        "scripts.central_memory_sync",
        "--db",
        str(db_path),
        "--push-read-copy",
    ]
    if include_content:
        command.append("--include-content")
    if document_map:
        command.append("--document-map")
    if health:
        command.append("--health")

    payload: dict[str, Any] = {
        "enabled": True,
        "dry_run": bool(dry_run),
        "include_content": bool(include_content),
        "document_map": bool(document_map),
        "health": bool(health),
        "command": command,
    }
    if dry_run:
        payload["status"] = "dry_run"
        return payload

    try:
        if sync_knowledge is None or sync_document_map is None or sync_health is None:
            from scripts import sync_to_supabase

            sync_knowledge = sync_knowledge or sync_to_supabase.sync
            sync_document_map = sync_document_map or sync_to_supabase.sync_document_map
            sync_health = sync_health or sync_to_supabase.sync_vault_health
        sync_knowledge(str(db_path), include_content=include_content)
        payload["knowledge"] = {"status": "attempted"}
        if document_map:
            payload["document_map"] = sync_document_map(str(db_path)) or {"status": "attempted"}
        if health:
            payload["health"] = sync_health(str(db_path)) or {"status": "attempted"}
        payload["status"] = "ok"
    except Exception as exc:  # pragma: no cover - exercised through injected tests
        payload["status"] = "failed"
        payload["error"] = str(exc)
        errors.append({"operation": "push_read_copy", "error": str(exc)})
    return payload


def _pull_candidates(
    project: Path,
    *,
    agent_id: str,
    dry_run: bool,
    central_backend: str,
    limit: int,
    apply: bool,
    auto_promote_low_risk: bool,
    require_hmac: bool | None,
    pull_remote_candidates: PullCandidates | None,
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "enabled": True,
        "dry_run": bool(dry_run),
        "central_backend": _normalize_central_backend(central_backend),
        "apply": bool(apply),
        "auto_promote_low_risk": bool(auto_promote_low_risk),
        "require_hmac": require_hmac,
    }
    if dry_run:
        payload["status"] = "dry_run"
        payload["effective_apply"] = False
        payload["reason"] = "Dry run does not contact the central candidate inbox."
        return payload

    try:
        if pull_remote_candidates is None:
            if _normalize_central_backend(central_backend) == "self-host":
                from .central_candidate_store import pull_central_candidates_local

                pull_remote_candidates = pull_central_candidates_local
            else:
                from .remote_candidates import pull_remote_candidate_requests

                pull_remote_candidates = pull_remote_candidate_requests
        result = pull_remote_candidates(
            project,
            agent_id=agent_id,
            limit=max(1, min(int(limit or 20), 100)),
            apply=apply,
            auto_promote_low_risk=auto_promote_low_risk,
            require_hmac=require_hmac,
        )
        payload.update(result)
        payload["status"] = "ok" if result.get("ok", False) else "failed"
        if not result.get("ok", False):
            errors.append({"operation": "pull_candidates", "error": str(result.get("error") or "failed")})
    except Exception as exc:  # pragma: no cover - exercised through injected tests
        payload["status"] = "failed"
        payload["error"] = str(exc)
        errors.append({"operation": "pull_candidates", "error": str(exc)})
    return payload


def _push_central_store(
    project: Path,
    db_path: Path,
    *,
    agent_id: str,
    dry_run: bool,
    include_content: bool,
    sync_central_store: SyncCentralStore | None,
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "enabled": True,
        "dry_run": bool(dry_run),
        "include_content": bool(include_content),
        "tables": [
            "vault_active_memory_snapshots",
            "vault_memory_revisions",
            "vault_memory_events",
            "vault_sync_cursors",
        ],
    }
    if dry_run:
        payload["status"] = "dry_run"
        payload["reason"] = "Dry run does not contact the central store tables."
        return payload
    try:
        if sync_central_store is None:
            from .central_store import sync_active_memory_snapshots

            sync_central_store = sync_active_memory_snapshots
        result = sync_central_store(
            project,
            db_path=db_path,
            agent_id=agent_id,
            include_content=include_content,
        )
        payload.update(result)
        payload["status"] = "ok" if result.get("ok", False) else "failed"
        if not result.get("ok", False):
            errors.append({"operation": "push_central_store", "error": str(result.get("error") or "failed")})
    except Exception as exc:  # pragma: no cover - exercised through injected tests
        payload["status"] = "failed"
        payload["error"] = str(exc)
        errors.append({"operation": "push_central_store", "error": str(exc)})
    return payload


def _next_action(operations: dict[str, Any], errors: list[dict[str, str]], *, dry_run: bool) -> str:
    if errors:
        return "Fix failed sync operations, then rerun memory-sync run-once."
    if dry_run:
        return "Dry run complete. Rerun without --dry-run when the central store credentials and policy are ready."
    if not any(
        operations.get(name, {}).get("enabled")
        for name in ("push_read_copy", "push_central_store", "pull_candidates")
    ):
        return "Enable --push-read-copy, --push-central-store, or --pull-candidates when you want this worker to move data."
    return "Schedule this worker every 30-60 minutes on a trusted sync host."


def _normalize_central_backend(value: str) -> str:
    backend = str(value or "supabase").strip().lower().replace("_", "-")
    return backend if backend in {"supabase", "self-host"} else "supabase"


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
