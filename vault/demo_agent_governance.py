"""Agent memory governance demo helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import tempfile
from pathlib import Path
from typing import Any

from .db import VaultDB
from .db_backup import backup_database
from .mcp_read import _vault_read_range_payload
from .memory import promote_candidate, propose_memory
from .search import VaultSearch


DEFAULT_DEMO_AGENTS = ["codex", "claude-code", "hermes"]


def run_agent_governance_demo(
    *,
    project_dir: str | Path | None = None,
    agent_set: str | list[str] | tuple[str, ...] = DEFAULT_DEMO_AGENTS,
    keep_project: bool = False,
) -> dict[str, Any]:
    """Run a local, candidate-first multi-agent memory governance demo."""
    project, created_temp = _resolve_demo_project(project_dir)
    agents = _normalize_agents(agent_set)
    codex, claude_code, hermes = agents[:3]
    _ensure_demo_project(project)

    db_path = project / "vault.db"
    with VaultDB(db_path) as db:
        candidate = propose_memory(
            db,
            title="Agent governance demo lesson",
            content=_demo_memory_content(),
            reason="Show that shared agent memory should be reviewed before it becomes active knowledge.",
            source="demo",
            source_ref="demo://agent-governance/codex-session",
            layer="L3",
            category="workflow",
            tags="demo,agent-governance,shared-memory",
            trust=0.8,
            scope="shared",
            sensitivity="low",
            owner_agent=codex,
            allowed_agents=json.dumps([codex, claude_code, hermes]),
            memory_type="project_lesson",
        )
        candidate_id = str(candidate["candidate_id"])

        promoted = promote_candidate(
            db,
            candidate_id,
            confirm=True,
            project_dir=project,
            compile=False,
            build_map=True,
        )
        knowledge_id = int(promoted["knowledge_id"])

        backup = backup_database(db_path, verify=True)

        search_rows = VaultSearch(db, embed_provider=None, embed_provider_name="none").search(
            "agent memory governance rollback audit",
            mode="keyword",
            limit=5,
            compact=True,
            include_snippet=True,
            fields=["id", "title", "category", "layer", "trust", "_score", "_snippet", "source"],
            agent_id=hermes,
            max_sensitivity="low",
        )
        search_hit = next((row for row in search_rows if int(row.get("id", 0)) == knowledge_id), None)
        audit_events = db.list_memory_feedback(limit=20)

    read_range = _vault_read_range_payload(
        knowledge_id,
        line_start=1,
        line_end=8,
        max_lines=20,
        agent_id=hermes,
        max_sensitivity="low",
        db_path=str(db_path),
    )

    demo_scenarios = _build_demo_scenarios(project, agents)
    artifacts = _write_demo_artifacts(
        project=project,
        agents=agents,
        candidate_id=candidate_id,
        knowledge_id=knowledge_id,
        search_hit=search_hit,
        read_range=read_range,
        audit_events=audit_events,
        backup=backup,
        created_temp=created_temp,
        keep_project=keep_project,
        demo_scenarios=demo_scenarios,
    )

    return {
        "ok": True,
        "status": "ok",
        "scenario": "agent_memory_governance",
        "message": "Vault governs what agents remember, trust, cite, and can roll back.",
        "project_dir": str(project),
        "temporary_project": created_temp,
        "keep_project": bool(keep_project),
        "agents": [
            {"id": codex, "role": "proposer", "action": "proposed a reusable project lesson"},
            {"id": claude_code, "role": "reviewer", "action": "promoted the candidate after gates passed"},
            {"id": hermes, "role": "recaller", "action": "searched and bounded-read the promoted memory"},
        ],
        "lifecycle": [
            "propose",
            "review",
            "promote",
            "search",
            "bounded_read",
            "rollback_available",
            "audit",
        ],
        "candidate_id": candidate_id,
        "promoted_knowledge_id": knowledge_id,
        "search_hit": search_hit or {},
        "read_range_citation": read_range.get("citation", ""),
        "audit_events": _compact_audit_events(audit_events),
        "rollback_available": bool(backup.get("ok")),
        "rollback": {
            "backup_path": backup.get("backup_path", ""),
            "sha256": backup.get("sha256", ""),
            "verified": bool(backup.get("verified")),
        },
        "demo_scenarios": demo_scenarios,
        "artifacts": artifacts,
        "next_action": [
            "Open start-here.md first, then demo-report.md and evidence-summary.md.",
            "Copy the runtime snippets into Codex, Claude Code, and Hermes startup configs when running the real demo.",
            "Use the same lifecycle in public demos: propose -> review -> promote -> bounded read -> rollback/audit.",
        ],
    }


def _resolve_demo_project(project_dir: str | Path | None) -> tuple[Path, bool]:
    if project_dir:
        return Path(project_dir).expanduser().resolve(), False
    return Path(tempfile.mkdtemp(prefix="vault-agent-governance-demo-")).resolve(), True


def _ensure_demo_project(project: Path) -> None:
    for name in ["raw", "compiled", "reports/demo", "agent-config-snippets"]:
        (project / name).mkdir(parents=True, exist_ok=True)
    with VaultDB(project / "vault.db") as db:
        db.set_config("demo.agent_governance.created_at", datetime.now(timezone.utc).isoformat())


def _normalize_agents(agent_set: str | list[str] | tuple[str, ...]) -> list[str]:
    if isinstance(agent_set, str):
        agents = [item.strip() for item in agent_set.split(",") if item.strip()]
    else:
        agents = [str(item).strip() for item in agent_set if str(item).strip()]
    for default in DEFAULT_DEMO_AGENTS:
        if len(agents) >= 3:
            break
        agents.append(default)
    return agents[:3]


def _demo_memory_content() -> str:
    return "\n".join(
        [
            "# Agent Memory Governance Demo",
            "",
            "Decision: shared agent memory must enter Vault as a candidate before it becomes active knowledge.",
            "",
            "Why it matters:",
            "- Codex can propose a reusable lesson without silently polluting shared memory.",
            "- Claude Code can review and promote only if privacy, duplicate, metadata, and quality gates pass.",
            "- Hermes can later recall the reviewed memory with a bounded source citation.",
            "- Operators can audit who proposed the memory and keep a verified backup for rollback.",
        ]
    )


def _write_demo_artifacts(
    *,
    project: Path,
    agents: list[str],
    candidate_id: str,
    knowledge_id: int,
    search_hit: dict[str, Any] | None,
    read_range: dict[str, Any],
    audit_events: list[dict[str, Any]],
    backup: dict[str, Any],
    created_temp: bool,
    keep_project: bool,
    demo_scenarios: list[dict[str, Any]],
) -> dict[str, str]:
    reports = project / "reports" / "demo"
    snippets = project / "agent-config-snippets"
    reports.mkdir(parents=True, exist_ok=True)
    snippets.mkdir(parents=True, exist_ok=True)

    payload = {
        "ok": True,
        "scenario": "agent_memory_governance",
        "project_dir": str(project),
        "temporary_project": created_temp,
        "keep_project": keep_project,
        "agents": agents,
        "candidate_id": candidate_id,
        "promoted_knowledge_id": knowledge_id,
        "search_hit": search_hit or {},
        "read_range": {
            "citation": read_range.get("citation", ""),
            "range": read_range.get("range", ""),
            "content_hash": read_range.get("content_hash", ""),
        },
        "audit_events": _compact_audit_events(audit_events),
        "rollback": {
            "backup_path": backup.get("backup_path", ""),
            "sha256": backup.get("sha256", ""),
            "verified": bool(backup.get("verified")),
        },
    }
    payload["demo_scenarios"] = demo_scenarios

    json_path = reports / "demo-report.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = reports / "demo-report.md"
    md_path.write_text(_render_demo_markdown(payload), encoding="utf-8")

    script_path = reports / "public-demo-script.md"
    script_path.write_text(_render_public_demo_script(project, agents), encoding="utf-8")

    script_zh_hant_path = reports / "public-demo-script.zh-Hant.md"
    script_zh_hant_path.write_text(_render_public_demo_script_zh_hant(project, agents), encoding="utf-8")

    script_zh_cn_path = reports / "public-demo-script.zh-CN.md"
    script_zh_cn_path.write_text(_render_public_demo_script_zh_cn(project, agents), encoding="utf-8")

    checklist_path = reports / "acceptance-checklist.md"
    checklist_path.write_text(_render_acceptance_checklist(), encoding="utf-8")

    evidence = _build_evidence_summary(payload)
    evidence_json_path = reports / "evidence-summary.json"
    evidence_json_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    evidence_md_path = reports / "evidence-summary.md"
    evidence_md_path.write_text(_render_evidence_summary_markdown(evidence), encoding="utf-8")

    scenario_paths = _write_demo_scenario_guides(reports, demo_scenarios)

    snippet_paths = _write_agent_snippets(snippets, project, agents)

    start_here_path = reports / "start-here.md"
    start_here_path.write_text(
        _render_start_here(
            project=project,
            report=md_path,
            script=script_path,
            script_zh_hant=script_zh_hant_path,
            script_zh_cn=script_zh_cn_path,
            evidence=evidence_md_path,
            checklist=checklist_path,
            snippets=snippets,
            scenario_paths=scenario_paths,
        ),
        encoding="utf-8",
    )

    return {
        "start_here": str(start_here_path),
        "report_md": str(md_path),
        "report_json": str(json_path),
        "public_demo_script": str(script_path),
        "public_demo_script_zh_hant": str(script_zh_hant_path),
        "public_demo_script_zh_cn": str(script_zh_cn_path),
        "acceptance_checklist": str(checklist_path),
        "evidence_summary_md": str(evidence_md_path),
        "evidence_summary_json": str(evidence_json_path),
        "snippet_dir": str(snippets),
        **scenario_paths,
        **snippet_paths,
    }


def _render_demo_markdown(payload: dict[str, Any]) -> str:
    agents = payload["agents"]
    rollback = payload["rollback"]
    return "\n".join(
        [
            "# Agents Need Memory Governance, Not Just RAG",
            "",
            "This demo proves Vault-for-LLM is a governed memory layer for agents.",
            "It does not just retrieve notes. It controls how shared agent memory is proposed, reviewed, promoted, cited, backed up, and audited.",
            "",
            "## Lifecycle",
            "",
            "1. **Propose** - `{}` submitted a reusable lesson as a memory candidate.".format(agents[0]),
            "2. **Review** - `{}` promoted it only after gates passed.".format(agents[1]),
            "3. **Recall** - `{}` searched the shared vault and used bounded read before citing.".format(agents[2]),
            "4. **Rollback** - Vault created a verified backup before publishing the evidence.",
            "5. **Audit** - Candidate feedback events preserve who changed memory and why.",
            "",
            "## Evidence",
            "",
            f"- Candidate ID: `{payload['candidate_id']}`",
            f"- Promoted knowledge ID: `{payload['promoted_knowledge_id']}`",
            f"- Citation: `{payload['read_range']['citation']}`",
            f"- Backup verified: `{rollback['verified']}`",
            f"- Backup SHA256: `{rollback['sha256']}`",
            "",
            "## Why This Is Not Just RAG",
            "",
            "RAG can retrieve text. This demo shows a memory lifecycle:",
            "",
            "`propose -> review -> promote -> search -> bounded read -> rollback -> audit`",
            "",
            "That lifecycle is the difference between a memory database and an agent memory governance layer.",
            "",
        ]
    )


def _render_start_here(
    *,
    project: Path,
    report: Path,
    script: Path,
    script_zh_hant: Path,
    script_zh_cn: Path,
    evidence: Path,
    checklist: Path,
    snippets: Path,
    scenario_paths: dict[str, str],
) -> str:
    return "\n".join(
        [
            "# Start Here: Three-Agent Governed Memory Demo",
            "",
            "Open this file first after running `vault demo agent-governance`.",
            "",
            "This demo is not trying to prove that Vault can search text. It proves that",
            "multiple agents can share one memory layer without turning long-term memory",
            "into an unreviewed note dump.",
            "",
            "## 30-Second Story",
            "",
            "1. Codex proposes a reusable project lesson as a candidate.",
            "2. Claude Code reviews and promotes it only after gates pass.",
            "3. Hermes recalls the promoted memory with a bounded citation.",
            "4. Vault leaves a backup and audit trail so the memory can be rolled back.",
            "",
            "## Open These In Order",
            "",
            f"1. Lifecycle proof: `{report}`",
            f"2. Evidence summary: `{evidence}`",
            f"3. English talk track: `{script}`",
            f"4. Traditional Chinese talk track: `{script_zh_hant}`",
            f"5. Simplified Chinese talk track: `{script_zh_cn}`",
            f"6. Acceptance checklist: `{checklist}`",
            f"7. Agent startup snippets: `{snippets}`",
            f"8. Consumer mode scenario: `{scenario_paths['consumer_mode_demo']}`",
            f"9. Automation mode scenario: `{scenario_paths['automation_mode_demo']}`",
            f"10. Multi-host sync scenario: `{scenario_paths['multi_host_sync_demo']}`",
            "",
            "## One-Sentence Close",
            "",
            "Vault-for-LLM governs what agents remember, trust, share, forget, and roll back.",
            "",
            "## Project",
            "",
            f"`{project}`",
            "",
        ]
    )


def _build_demo_scenarios(project: Path, agents: list[str]) -> list[dict[str, Any]]:
    codex, claude_code, hermes = agents
    return [
        {
            "id": "consumer_mode",
            "title": "Consumer Mode Demo",
            "artifact": "consumer-mode-demo.md",
            "audience": "agent-assisted builders trying Vault for the first time",
            "story": [
                "Start from the smallest useful path instead of exposing setup-agent's full option surface.",
                "Use the guided quickstart to create a governed local vault.",
                "Open the daily report as the first human review surface.",
            ],
            "commands": [
                f"vault quickstart --project {project} --non-interactive",
                f"vault --project-dir {project} daily-report --pretty",
                f"vault --project-dir {project} search \"agent memory governance\"",
            ],
            "proof_points": [
                "The first run has one guided path.",
                "Memory starts reviewed or candidate-first, not silently trusted.",
                "A non-expert user sees the next action from daily report output.",
            ],
            "next_action": "Use this when the demo audience asks how a new user starts in five minutes.",
        },
        {
            "id": "automation_mode",
            "title": "Automation Mode Demo",
            "artifact": "automation-mode-demo.md",
            "audience": "operators who want routine memory maintenance without silent writes",
            "story": [
                "Show that automation starts with read-only health and review surfaces.",
                "Run the automation brief and inbox before any apply step.",
                "Explain that low-risk automation remains policy-gated and observable.",
            ],
            "commands": [
                f"vault --project-dir {project} automation doctor --pretty",
                f"vault --project-dir {project} automation brief --pretty",
                f"vault --project-dir {project} automation inbox --limit 5 --pretty",
            ],
            "proof_points": [
                "Automation has a doctor/readiness check.",
                "The review inbox is the human approval surface.",
                "Reports are generated under reports/automation for handoff and audit.",
            ],
            "next_action": "Use this after the governance lifecycle proof, when the audience asks what happens every day.",
        },
        {
            "id": "multi_host_sync",
            "title": "Multi-Host Sync Demo",
            "artifact": "multi-host-sync-demo.md",
            "audience": "teams using more than one machine or runtime surface",
            "story": [
                f"{codex} submits a remote candidate from one host.",
                f"{claude_code} reviews pulled candidates on the owner vault.",
                f"{hermes} checks remote health before trusting cross-host memory.",
            ],
            "commands": [
                f"vault --project-dir {project} remote status --pretty",
                f"vault --project-dir {project} remote hmac-keys --json",
                f"vault --project-dir {project} remote pull-candidates --require-hmac --json",
            ],
            "proof_points": [
                "Cross-host writes arrive as candidates, not active knowledge.",
                "HMAC status is visible without printing secrets.",
                "Remote health can be checked before enabling review/apply workflows.",
            ],
            "next_action": "Use this for remote deployment discussions; keep it framed as remote candidate sync, not broad bidirectional sync.",
        },
    ]


def _write_demo_scenario_guides(reports: Path, scenarios: list[dict[str, Any]]) -> dict[str, str]:
    index_path = reports / "demo-scenarios.json"
    index_path.write_text(json.dumps(scenarios, ensure_ascii=False, indent=2), encoding="utf-8")

    written: dict[str, str] = {"demo_scenarios_json": str(index_path)}
    for scenario in scenarios:
        artifact = str(scenario["artifact"])
        path = reports / artifact
        path.write_text(_render_demo_scenario_markdown(scenario), encoding="utf-8")
        written[f"{scenario['id']}_demo"] = str(path)
    return written


def _render_demo_scenario_markdown(scenario: dict[str, Any]) -> str:
    lines = [
        f"# {scenario['title']}",
        "",
        f"Audience: {scenario['audience']}",
        "",
        "## Story",
        "",
    ]
    lines.extend(f"- {item}" for item in scenario["story"])
    lines.extend(["", "## Commands", "", "```bash"])
    lines.extend(scenario["commands"])
    lines.extend(["```", "", "## Proof Points", ""])
    lines.extend(f"- {item}" for item in scenario["proof_points"])
    lines.extend(["", "## Next Action", "", scenario["next_action"], ""])
    return "\n".join(lines)


def _render_public_demo_script(project: Path, agents: list[str]) -> str:
    codex, claude_code, hermes = agents
    return "\n".join(
        [
            "# Public Demo Script: Governed Shared Memory",
            "",
            "Use this script when recording or presenting the demo. The goal is to show",
            "memory governance, not only search quality.",
            "",
            "## Setup",
            "",
            "```bash",
            f"vault demo agent-governance --project-dir {project} --json",
            "```",
            "",
            "Open:",
            "",
            f"- `{project / 'reports' / 'demo' / 'demo-report.md'}`",
            f"- `{project / 'agent-config-snippets'}`",
            "",
            "## Talk Track",
            "",
            "1. Introduce the problem: three agents can work on the same repo, but shared",
            "   memory becomes dangerous if every agent writes directly into active context.",
            f"2. `{codex}` proposes a lesson as a candidate. It exists, but it is not active",
            "   shared memory yet.",
            f"3. `{claude_code}` reviews and promotes the candidate only after gates pass.",
            f"4. `{hermes}` searches the shared vault, then uses bounded read before citing.",
            "5. Show the verified backup and audit events. The memory can be rolled back or",
            "   deprecated instead of silently lingering forever.",
            "",
            "## One-Sentence Close",
            "",
            "Vault is not another place for agents to dump notes. It is the governance",
            "layer that controls what agents remember, trust, share, forget, and roll back.",
            "",
        ]
    )


def _render_public_demo_script_zh_hant(project: Path, agents: list[str]) -> str:
    codex, claude_code, hermes = agents
    return "\n".join(
        [
            "# 公開 Demo 講稿：受治理的共享記憶",
            "",
            "這份講稿用來錄影或對外展示。重點不是搜尋比較準，而是記憶可以被治理。",
            "",
            "## 設定",
            "",
            "```bash",
            f"vault demo agent-governance --project-dir {project} --json",
            "```",
            "",
            "打開：",
            "",
            f"- `{project / 'reports' / 'demo' / 'demo-report.md'}`",
            f"- `{project / 'reports' / 'demo' / 'evidence-summary.md'}`",
            f"- `{project / 'agent-config-snippets'}`",
            "",
            "## 講解順序",
            "",
            "1. 先說問題：多個 Agent 可以一起工作，但如果每個 Agent 都能直接寫長期記憶，共享記憶很快會被污染。",
            f"2. `{codex}` 先把經驗提出為候選記憶。它存在，但還不是正式共享記憶。",
            f"3. `{claude_code}` 審核並 promote。重點是記憶進正式庫前有邊界。",
            f"4. `{hermes}` 搜尋共享 Vault，然後用 bounded read 取得可引用來源。",
            "5. 最後展示 backup 與 audit。錯誤或過期記憶可以回滾或淘汰，不會永遠留在上下文裡。",
            "",
            "## 收尾句",
            "",
            "Vault 不是讓 Agent 亂丟筆記的地方。它是治理層，負責控制 Agent 記住什麼、相信什麼、分享什麼、忘記什麼，以及如何回滾。",
            "",
        ]
    )


def _render_public_demo_script_zh_cn(project: Path, agents: list[str]) -> str:
    codex, claude_code, hermes = agents
    return "\n".join(
        [
            "# 公开 Demo 讲稿：受治理的共享记忆",
            "",
            "这份讲稿用来录屏或对外展示。重点不是搜索比较准，而是记忆可以被治理。",
            "",
            "## 设置",
            "",
            "```bash",
            f"vault demo agent-governance --project-dir {project} --json",
            "```",
            "",
            "打开：",
            "",
            f"- `{project / 'reports' / 'demo' / 'demo-report.md'}`",
            f"- `{project / 'reports' / 'demo' / 'evidence-summary.md'}`",
            f"- `{project / 'agent-config-snippets'}`",
            "",
            "## 讲解顺序",
            "",
            "1. 先说问题：多个 Agent 可以一起工作，但如果每个 Agent 都能直接写长期记忆，共享记忆很快会被污染。",
            f"2. `{codex}` 先把经验提出为候选记忆。它存在，但还不是正式共享记忆。",
            f"3. `{claude_code}` 审核并 promote。重点是记忆进正式库前有边界。",
            f"4. `{hermes}` 搜索共享 Vault，然后用 bounded read 取得可引用来源。",
            "5. 最后展示 backup 与 audit。错误或过期记忆可以回滚或淘汰，不会永远留在上下文里。",
            "",
            "## 收尾句",
            "",
            "Vault 不是让 Agent 乱丢笔记的地方。它是治理层，负责控制 Agent 记住什么、相信什么、分享什么、忘记什么，以及如何回滚。",
            "",
        ]
    )


def _render_acceptance_checklist() -> str:
    return "\n".join(
        [
            "# Acceptance Checklist",
            "",
            "A public demo is successful when it proves these points:",
            "",
            "- [ ] A memory starts as a candidate, not active shared knowledge.",
            "- [ ] Gate and review steps are visible before promotion.",
            "- [ ] A different agent can search the promoted memory.",
            "- [ ] The answer path uses bounded read with a citation.",
            "- [ ] A verified backup or rollback path exists.",
            "- [ ] Audit events show the lifecycle, not just the final text.",
            "- [ ] The demo does not require private data, cloud services, or hidden state.",
            "- [ ] The talk track says \"memory governance\", not \"better RAG\".",
            "",
            "If any item fails, fix the demo before using it as an external proof.",
            "",
        ]
    )


def _build_evidence_summary(payload: dict[str, Any]) -> dict[str, Any]:
    checks = [
        {
            "id": "candidate_created",
            "ok": bool(str(payload.get("candidate_id", "")).startswith("mem_")),
            "evidence": f"candidate_id={payload.get('candidate_id', '')}",
        },
        {
            "id": "promoted_memory_created",
            "ok": int(payload.get("promoted_knowledge_id") or 0) > 0,
            "evidence": f"knowledge_id={payload.get('promoted_knowledge_id', '')}",
        },
        {
            "id": "search_found_promoted_memory",
            "ok": bool((payload.get("search_hit") or {}).get("id") == payload.get("promoted_knowledge_id")),
            "evidence": f"search_hit_id={(payload.get('search_hit') or {}).get('id', '')}",
        },
        {
            "id": "bounded_read_citation",
            "ok": bool((payload.get("read_range") or {}).get("citation")),
            "evidence": str((payload.get("read_range") or {}).get("citation", "")),
        },
        {
            "id": "rollback_verified",
            "ok": bool((payload.get("rollback") or {}).get("verified")),
            "evidence": str((payload.get("rollback") or {}).get("backup_path", "")),
        },
        {
            "id": "audit_event_recorded",
            "ok": any(event.get("outcome") == "promoted" for event in payload.get("audit_events", [])),
            "evidence": f"events={len(payload.get('audit_events', []))}",
        },
    ]
    return {
        "ok": all(item["ok"] for item in checks),
        "scenario": payload.get("scenario", "agent_memory_governance"),
        "project_dir": payload.get("project_dir", ""),
        "checks": checks,
        "summary": "Agent governance demo evidence is complete."
        if all(item["ok"] for item in checks)
        else "Agent governance demo evidence is incomplete.",
    }


def _render_evidence_summary_markdown(evidence: dict[str, Any]) -> str:
    lines = [
        "# Agent Governance Evidence Summary",
        "",
        f"Status: `{'PASS' if evidence.get('ok') else 'FAIL'}`",
        "",
        "This file is generated by `vault demo agent-governance`. It records whether",
        "the demo produced concrete evidence for the governed memory lifecycle.",
        "",
        "| Check | Result | Evidence |",
        "|---|---:|---|",
    ]
    for check in evidence.get("checks", []):
        result = "PASS" if check.get("ok") else "FAIL"
        lines.append(f"| `{check.get('id', '')}` | {result} | `{check.get('evidence', '')}` |")
    lines.extend(
        [
            "",
            "A publishable demo should pass every check. If this file shows `FAIL`, fix",
            "the demo flow before using it as evidence for Agent Memory Governance.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_agent_snippets(snippets: Path, project: Path, agents: list[str]) -> dict[str, str]:
    codex, claude_code, hermes = agents
    common = f"vault-mcp --project-dir {project} --tool-profile core"
    data = {
        "codex_startup": (
            "codex-startup.md",
            f"# Codex Startup\n\nUse shared Vault memory through MCP:\n\n```bash\n{common}\n```\n\n"
            f"Agent id: `{codex}`\n\nFlow: search first, bounded-read before citing, propose durable lessons as candidates.\n",
        ),
        "claude_code_startup": (
            "claude-code-startup.md",
            f"# Claude Code Startup\n\nUse shared Vault memory through MCP:\n\n```bash\n{common}\n```\n\n"
            f"Agent id: `{claude_code}`\n\nFlow: review candidate memory before promotion; keep active memory clean.\n",
        ),
        "hermes_startup": (
            "hermes-startup.md",
            f"# Hermes Startup\n\nUse shared Vault memory through MCP:\n\n```bash\n{common}\n```\n\n"
            f"Agent id: `{hermes}`\n\nFlow: recall reviewed memory with bounded citations; private identity memory stays outside shared Vault.\n",
        ),
    }
    written: dict[str, str] = {}
    for key, (filename, content) in data.items():
        path = snippets / filename
        path.write_text(content, encoding="utf-8")
        written[key] = str(path)
    return written


def _compact_audit_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact = []
    for row in events:
        compact.append(
            {
                "id": row.get("id"),
                "created_at": row.get("created_at"),
                "event_type": row.get("event_type"),
                "candidate_id": row.get("candidate_id"),
                "outcome": row.get("outcome"),
                "source": row.get("source"),
                "memory_type": row.get("memory_type"),
                "knowledge_id": row.get("knowledge_id"),
            }
        )
    return compact
