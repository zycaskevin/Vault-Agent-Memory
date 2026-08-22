"""Memory-agent and local smoke templates for setup-agent."""

from __future__ import annotations

import shlex
from pathlib import Path

from vault.agent_setup_supabase import _normalize_setup_language


def render_memory_agents_guide(
    *,
    project_dir: str | Path,
    agent: str,
    language: str = "en",
) -> str:
    project_path = Path(project_dir).expanduser()
    safe_language = _normalize_setup_language(language)
    if safe_language == "zh-Hant":
        lines = [
            "# Vault Agent Memory 記憶維護 Agent 設定",
            "",
            "這份文件用於候選整理、生命週期報告與可逆封存建議。",
            "Vault 只管理記憶，不建立人物身份、人格、關係、人生階段或人類模型。",
            "",
            "預設政策：",
            "",
            "- Candidate curator 預設只產生候選記憶，不直接寫入 active memory。",
            "- Lifecycle reporter 預設只產生 report，不直接刪除或 promote。",
            "- Archive advisor 預設只建議 archive、expire、merge 或降權，不自動刪除。",
            "- 原始私密互動不同步到 shared vault 或 Supabase，除非使用者明確同意。",
            "- 上層應用的私人模型留在該應用；Vault 只接收經審查、具來源的記憶摘要。",
            "",
            "建議生命週期：",
            "",
            "```text",
            "capture -> candidate -> review -> active -> dream -> consolidate -> archive/expire",
            "```",
            "",
            "建議 metadata：",
            "",
            "```yaml",
            "scope: private | project | shared | public",
            "sensitivity: low | medium | high | restricted",
            f"owner_agent: {agent}",
            "allowed_agents: []",
            "status: candidate | reviewed | active | archived",
            "memory_type: bootstrap_context | rule | decision_summary | maintenance_report | archive_suggestion",
            "expires_at: null",
            "```",
            "",
            "建議執行方式：",
            "",
            f"- Project vault: `{project_path}`",
            "- Candidate curator：整理 L0/L1/L2 記憶候選，等待使用者或 trusted agent review。",
            "- Lifecycle reporter：定期產生記憶維護報告。",
            "- Archive advisor：根據維護報告產生 archive/expire 建議，不直接刪除。",
        ]
    elif safe_language == "zh-CN":
        lines = [
            "# Vault Agent Memory 记忆维护 Agent 设置",
            "",
            "这份文件用于候选整理、生命周期报告与可逆归档建议。",
            "Vault 只管理记忆，不建立人物身份、人格、关系、人生阶段或人类模型。",
            "",
            "默认政策：",
            "",
            "- Candidate curator 默认只产生候选记忆，不直接写入 active memory。",
            "- Lifecycle reporter 默认只产生 report，不直接删除或 promote。",
            "- Archive advisor 默认只建议 archive、expire、merge 或降权，不自动删除。",
            "- 原始私密互动不同步到 shared vault 或 Supabase，除非用户明确同意。",
            "- 上层应用的私人模型留在该应用；Vault 只接收经审查、具来源的记忆摘要。",
            "",
            "建议生命周期：",
            "",
            "```text",
            "capture -> candidate -> review -> active -> dream -> consolidate -> archive/expire",
            "```",
            "",
            "建议 metadata：",
            "",
            "```yaml",
            "scope: private | project | shared | public",
            "sensitivity: low | medium | high | restricted",
            f"owner_agent: {agent}",
            "allowed_agents: []",
            "status: candidate | reviewed | active | archived",
            "memory_type: bootstrap_context | rule | decision_summary | maintenance_report | archive_suggestion",
            "expires_at: null",
            "```",
            "",
            "建议执行方式：",
            "",
            f"- Project vault: `{project_path}`",
            "- Candidate curator：整理 L0/L1/L2 记忆候选，等待用户或 trusted agent review。",
            "- Lifecycle reporter：定期产生记忆维护报告。",
            "- Archive advisor：根据维护报告产生 archive/expire 建议，不直接删除。",
        ]
    else:
        lines = [
            "# Vault Agent Memory Maintenance Agents",
            "",
            "Use this guide for candidate curation, lifecycle reports, and reversible archive suggestions.",
            "Vault governs memory; it does not build person identity, personality, relationship, life-phase, or human models.",
            "",
            "Default policy:",
            "",
            "- Candidate curators produce candidate memories; they do not write active memory directly.",
            "- Lifecycle reporters produce reports; they do not delete or promote memory directly.",
            "- Archive advisors suggest archive, expiry, merge, or downgrade actions; they do not auto-delete.",
            "- Raw private conversations do not sync to shared vaults or Supabase unless the user explicitly approves.",
            "- Application-owned private models stay in that application; Vault accepts only reviewed, sourced memory summaries.",
            "",
            "Recommended lifecycle:",
            "",
            "```text",
            "capture -> candidate -> review -> active -> dream -> consolidate -> archive/expire",
            "```",
            "",
            "Recommended metadata:",
            "",
            "```yaml",
            "scope: private | project | shared | public",
            "sensitivity: low | medium | high | restricted",
            f"owner_agent: {agent}",
            "allowed_agents: []",
            "status: candidate | reviewed | active | archived",
            "memory_type: bootstrap_context | rule | decision_summary | maintenance_report | archive_suggestion",
            "expires_at: null",
            "```",
            "",
            "Recommended operation:",
            "",
            f"- Project vault: `{project_path}`",
            "- Candidate curator: propose L0/L1/L2 memory candidates for user or trusted-agent review.",
            "- Lifecycle reporter: write scheduled memory-maintenance reports.",
            "- Archive advisor: convert report findings into archive/expiry suggestions, not direct deletion.",
        ]
    return "\n".join(lines) + "\n"


def write_memory_agents_guide(
    *,
    output_dir: str | Path,
    project_dir: str | Path,
    agent: str,
    language: str = "en",
) -> dict[str, str]:
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    path = out / "README-memory-agents.md"
    path.write_text(
        render_memory_agents_guide(
            project_dir=project_dir,
            agent=agent,
            language=language,
        ),
        encoding="utf-8",
    )
    return {"guide": str(path), "mode": "report_only_candidate_only"}


def render_local_smoke_script(*, project_dir: str | Path, vault_executable: str = "vault") -> str:
    project = shlex.quote(str(Path(project_dir).expanduser()))
    return "\n".join(
        [
            "#!/usr/bin/env sh",
            "set -eu",
            f"PROJECT_DIR={project}",
            f"VAULT=${{VAULT:-{shlex.quote(vault_executable)}}}",
            "if [ -z \"${PYTHON:-}\" ]; then",
            "  VAULT_BIN=\"$(command -v \"$VAULT\" 2>/dev/null || true)\"",
            "  VAULT_SHEBANG=\"$(test -n \"$VAULT_BIN\" && test -f \"$VAULT_BIN\" && sed -n '1s/^#!//p' \"$VAULT_BIN\" || true)\"",
            "  case \"$VAULT_SHEBANG\" in *python*) PYTHON=\"$VAULT_SHEBANG\" ;; *) PYTHON=python3 ;; esac",
            "fi",
            "SMOKE_ID=\"$(date +%Y%m%d%H%M%S)-$$\"",
            "TITLE=\"Vault local smoke ${SMOKE_ID}\"",
            "CANDIDATE_TITLE=\"Vault local smoke candidate ${SMOKE_ID}\"",
            "CONTENT=\"Vault Agent Memory local smoke ${SMOKE_ID}: add/search-json/remember/candidates works.\"",
            "",
            "$VAULT add \"$TITLE\" \\",
            "  --project-dir \"$PROJECT_DIR\" \\",
            "  --content \"$CONTENT\" \\",
            "  --category setup \\",
            "  --tags smoke,setup \\",
            "  --trust 0.9 \\",
            "  --source setup-agent >/dev/null",
            "",
            "SEARCH_JSON=\"$($VAULT search \"$TITLE\" --project-dir \"$PROJECT_DIR\" --keyword-only --limit 5 --json)\"",
            "export SEARCH_JSON TITLE",
            "SMOKE_KID=\"$($PYTHON -c 'import json, os; p=json.loads(os.environ[\"SEARCH_JSON\"]); t=os.environ[\"TITLE\"]; rows=p.get(\"results\", []); matches=[r for r in rows if r.get(\"title\") == t]; assert p.get(\"count\", 0) >= 1 and matches, p; print(matches[0].get(\"id\"))')\"",
            "$VAULT --project-dir \"$PROJECT_DIR\" map build >/dev/null",
            "MAP_READ=\"$($VAULT --project-dir \"$PROJECT_DIR\" map read \"$SMOKE_KID\" --lines 1-20)\"",
            "case \"$MAP_READ\" in *\"local smoke\"*) ;; *) echo \"map read did not return smoke content\" >&2; exit 1 ;; esac",
            "",
            "$VAULT remember \"$CANDIDATE_TITLE\" \\",
            "  --project-dir \"$PROJECT_DIR\" \\",
            "  --content \"Candidate-only smoke memory created during agent setup validation.\" \\",
            "  --reason \"Verify candidate memory workflow after agent installation.\" \\",
            "  --mode candidate \\",
            "  --category setup \\",
            "  --tags smoke,setup \\",
            "  --source setup-agent \\",
            "  --source-ref \"local-smoke:${SMOKE_ID}\" >/dev/null",
            "",
            "CANDIDATES_JSON=\"$($VAULT candidates --project-dir \"$PROJECT_DIR\" --pretty)\"",
            "export CANDIDATES_JSON CANDIDATE_TITLE",
            "$PYTHON - <<'PY'",
            "import json, os",
            "payload = json.loads(os.environ['CANDIDATES_JSON'])",
            "title = os.environ['CANDIDATE_TITLE']",
            "if payload.get('count', 0) < 1:",
            "    raise SystemExit(f'candidate list is empty: {payload!r}')",
            "if not any(item.get('title') == title for item in payload.get('candidates', [])):",
            "    raise SystemExit(f'candidate list did not include smoke candidate: {payload!r}')",
            "PY",
            "",
            "export PROJECT_DIR",
            "$PYTHON - <<'PY'",
            "import json, os",
            "from vault.mcp import _set_project_dir, handle_tool_call, select_tools",
            "_set_project_dir(os.environ['PROJECT_DIR'])",
            "core = [tool['name'] for tool in select_tools('core')]",
            "required = {'vault_update_status', 'vault_automation_handoff'}",
            "missing = sorted(required - set(core))",
            "if missing:",
            "    raise SystemExit(f'MCP core profile missing startup tools: {missing}')",
            "status = json.loads(handle_tool_call('vault_update_status', {})['result'])",
            "if 'installed_version' not in status or 'startup_commands' not in status:",
            "    raise SystemExit(f'invalid update status payload: {status!r}')",
            "handoff = json.loads(handle_tool_call('vault_automation_handoff', {})['result'])",
            "if handoff.get('action') != 'handoff' or not handoff.get('safety', {}).get('read_only'):",
            "    raise SystemExit(f'invalid handoff payload: {handoff!r}')",
            "PY",
            "",
            "echo \"local_smoke=ok\"",
            "",
        ]
    )


def write_local_smoke_template(
    *,
    output_dir: str | Path,
    project_dir: str | Path,
    vault_executable: str = "vault",
) -> dict[str, str]:
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    script_path = out / "local-smoke.sh"
    script_path.write_text(
        render_local_smoke_script(project_dir=project_dir, vault_executable=vault_executable),
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    return {"script": str(script_path)}
