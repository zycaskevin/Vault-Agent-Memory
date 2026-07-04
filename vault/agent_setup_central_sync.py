"""Central Memory Station schedule template helpers for agent setup."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .agent_setup_templates import _normalize_sync_targets, render_launchagent_plist, shell_join


DEFAULT_CENTRAL_MEMORY_SYNC_INTERVAL_MINUTES = 60


def render_central_memory_cron_template(*, command: list[str], interval_minutes: int = 60) -> str:
    interval = max(30, min(int(interval_minutes or 60), 60))
    schedule = "0 * * * *" if interval >= 60 else f"*/{interval} * * * *"
    return "\n".join(
        [
            "# Vault Agent Memory Central Memory Station sync",
            "# Runs on a trusted sync host. Keep service-role credentials out of hosted readers.",
            f"{schedule} {shell_join(command)} >> $HOME/.vault-for-llm/central-memory-sync.log 2>&1",
            "",
        ]
    )


def render_n8n_central_memory_sync_workflow(
    *,
    command: list[str],
    interval_minutes: int = 60,
) -> str:
    workflow = {
        "name": "Vault Central Memory Station Sync",
        "nodes": [
            {
                "parameters": {
                    "rule": {
                        "interval": [
                            {
                                "field": "minutes",
                                "minutesInterval": max(
                                    30,
                                    min(int(interval_minutes or 60), 60),
                                ),
                            }
                        ]
                    }
                },
                "id": "schedule",
                "name": "Every 30-60 minutes",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 0],
            },
            {
                "parameters": {"command": shell_join(command)},
                "id": "vault-central-memory-sync",
                "name": "Vault Central Memory Sync",
                "type": "n8n-nodes-base.executeCommand",
                "typeVersion": 1,
                "position": [280, 0],
            },
        ],
        "connections": {
            "Every 30-60 minutes": {
                "main": [[{"node": "Vault Central Memory Sync", "type": "main", "index": 0}]]
            }
        },
        "active": False,
        "settings": {"executionOrder": "v1"},
    }
    return json.dumps(workflow, ensure_ascii=False, indent=2) + "\n"


def central_memory_sync_command(
    *,
    project_dir: str | Path,
    python_executable: str | Path | None = None,
    push_read_copy: bool = True,
    push_central_store: bool = True,
    pull_candidates: bool = True,
    apply: bool = True,
    require_hmac: bool = True,
    document_map: bool = True,
    health: bool = True,
    include_content: bool = False,
) -> list[str]:
    command = [
        str(python_executable or sys.executable),
        "-m",
        "scripts.central_memory_sync",
        "--db",
        str(Path(project_dir).expanduser() / "vault.db"),
    ]
    if push_read_copy:
        command.append("--push-read-copy")
    if push_central_store:
        command.append("--push-central-store")
    if pull_candidates:
        command.append("--pull-candidates")
    if apply:
        command.append("--apply")
    if require_hmac:
        command.append("--require-hmac")
    if include_content:
        command.append("--include-content")
    command.append("--document-map" if document_map else "--no-document-map")
    command.append("--health" if health else "--no-health")
    return command


def write_central_memory_sync_templates(
    *,
    output_dir: str | Path,
    project_dir: str | Path,
    targets: str | list[str] = "all",
    interval_minutes: int = DEFAULT_CENTRAL_MEMORY_SYNC_INTERVAL_MINUTES,
    python_executable: str | Path | None = None,
) -> dict[str, str]:
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    selected = _normalize_sync_targets(targets)
    interval = max(30, min(int(interval_minutes or DEFAULT_CENTRAL_MEMORY_SYNC_INTERVAL_MINUTES), 60))
    command = central_memory_sync_command(
        project_dir=project_dir,
        python_executable=python_executable,
    )

    written: dict[str, str] = {}
    if "cron" in selected:
        path = out / "central-memory-sync.cron"
        path.write_text(
            render_central_memory_cron_template(command=command, interval_minutes=interval),
            encoding="utf-8",
        )
        written["cron"] = str(path)
    if "launchagent" in selected:
        path = out / "com.zycaskevin.vault-for-llm.central-memory-sync.plist"
        path.write_text(
            render_launchagent_plist(
                command=command,
                label="com.zycaskevin.vault-for-llm.central-memory-sync",
                interval_minutes=interval,
                log_basename="central-memory-sync",
            ),
            encoding="utf-8",
        )
        written["launchagent"] = str(path)
    if "n8n" in selected:
        path = out / "n8n-central-memory-sync.workflow.json"
        path.write_text(
            render_n8n_central_memory_sync_workflow(command=command, interval_minutes=interval),
            encoding="utf-8",
        )
        written["n8n"] = str(path)

    readme = out / "README-central-memory-sync.md"
    readme.write_text(
        "\n".join(
            [
                "# Vault Agent Memory Central Memory Station Sync",
                "",
                "Generated command:",
                "",
                f"```bash\n{shell_join(command)}\n```",
                "",
                "Run this only on a trusted sync host.",
                "It pushes the reviewed local read copy, pulls central candidate memory into local review, and writes `reports/central-memory-sync-latest.json`.",
                "Remote writes remain candidate-first. Active memory is not multi-master.",
                "Start with a manual dry run before enabling the schedule:",
                "",
                f"```bash\n{shell_join(command + ['--dry-run'])}\n```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    written["readme"] = str(readme)
    return written


def configure_central_memory_sync_templates(
    result: dict[str, Any],
    *,
    output_dir: str | Path,
    project_dir: str | Path,
    targets: list[str],
    sync_interval_minutes: int,
) -> None:
    interval = min(
        DEFAULT_CENTRAL_MEMORY_SYNC_INTERVAL_MINUTES,
        max(30, int(sync_interval_minutes or DEFAULT_CENTRAL_MEMORY_SYNC_INTERVAL_MINUTES)),
    )
    result["central_memory_sync_templates"] = write_central_memory_sync_templates(
        output_dir=output_dir,
        project_dir=project_dir,
        targets=targets,
        interval_minutes=interval,
    )
    readme = result["central_memory_sync_templates"]["readme"]
    result["next_steps"].append(f"Review Central Memory Station sync schedule: {readme}")
