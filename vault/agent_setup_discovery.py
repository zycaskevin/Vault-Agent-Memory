"""Local machine discovery for agent memory setup.

The setup wizard uses these helpers to avoid accidentally creating a new
Vault project when another Agent on the same machine is already connected to
one. Discovery is deliberately read-only: it reports likely projects and
configuration hints, but never rewrites an Agent runtime config.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from vault.agent_registry import load_registry, registry_path


def _home(home: str | Path | None = None) -> Path:
    return Path(home).expanduser().resolve() if home else Path.home()


def _add_project(projects: dict[str, dict[str, Any]], path: str | Path, *, source: str, agent: str = "") -> None:
    try:
        resolved = Path(path).expanduser().resolve()
    except OSError:
        return
    if not str(resolved):
        return
    db_path = resolved / "vault.db"
    item = projects.setdefault(
        str(resolved),
        {
            "project_dir": str(resolved),
            "db_path": str(db_path),
            "db_exists": db_path.exists(),
            "sources": [],
            "agents": [],
        },
    )
    if source not in item["sources"]:
        item["sources"].append(source)
    if agent and agent not in item["agents"]:
        item["agents"].append(agent)
    item["db_exists"] = item["db_exists"] or db_path.exists()


def _candidate_project_dirs(home: Path) -> list[tuple[Path, str]]:
    candidates: list[tuple[Path, str]] = [
        (home / "Vaults" / "project-memory", "standard_shared_project"),
        (home / ".vault-for-llm" / "agent-private", "standard_private_project"),
        (home / ".openclaw" / "workspace" / "vault-project", "openclaw_default_project"),
    ]
    agents_root = home / "Vaults" / "agents"
    if agents_root.exists():
        for path in sorted(agents_root.glob("*/private-memory")):
            candidates.append((path, "vaults_agents_private_memory"))
    return candidates


def _extract_codex_vault_projects(config_path: Path) -> list[str]:
    if not config_path.exists():
        return []
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError:
        return []
    if "mcp_servers.vault" not in text and "vault-mcp" not in text:
        return []
    projects: list[str] = []
    for match in re.finditer(r'"(/[^"\n]+)"', text):
        value = match.group(1)
        if "vault" in value.lower() and (value.endswith("private-memory") or "/Vaults/" in value):
            projects.append(value)
    return projects


def _read_openclaw_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"config_path": str(config_path), "parse_error": True}
    entries = (((payload.get("plugins") or {}).get("entries") or {}))
    vault_entry = entries.get("vault-for-llm") if isinstance(entries, dict) else None
    config = vault_entry.get("config", {}) if isinstance(vault_entry, dict) else {}
    return {
        "config_path": str(config_path),
        "enabled": bool(vault_entry.get("enabled")) if isinstance(vault_entry, dict) else False,
        "wrapper_path": str(config.get("wrapperPath") or "") if isinstance(config, dict) else "",
        "configured_project_dir": str(config.get("projectDir") or "") if isinstance(config, dict) else "",
        "auto_recall": bool(config.get("autoRecall")) if isinstance(config, dict) else False,
    }


def _project_recommendation_score(item: dict[str, Any]) -> tuple[int, str]:
    sources = set(item.get("sources") or [])
    project_dir = str(item.get("project_dir") or "")
    score = 0
    if item.get("db_exists"):
        score += 2
    if "codex_config" in sources:
        score += 8
    if "agent_registry" in sources:
        score += 6
    if "vaults_agents_private_memory" in sources:
        score += 3
    if len(sources) > 1:
        score += len(sources)
    if "/.openclaw/" in project_dir:
        score -= 2
    return score, project_dir


def discover_local_agent_memory(*, home: str | Path | None = None, registry_file: str | Path | None = None) -> dict[str, Any]:
    """Return read-only evidence about local Agents and Vault projects."""
    root = _home(home)
    projects: dict[str, dict[str, Any]] = {}
    agents: dict[str, dict[str, Any]] = {}

    resolved_registry = Path(registry_file).expanduser() if registry_file else registry_path()
    registry_payload: dict[str, Any] = {}
    try:
        registry_payload = load_registry(resolved_registry)
    except (OSError, ValueError):
        registry_payload = {}
    registry_agents = registry_payload.get("agents", {}) if isinstance(registry_payload.get("agents"), dict) else {}
    for agent_id, entry in registry_agents.items():
        agent_key = str(agent_id)
        project_dir = str(entry.get("project_dir") or "")
        agents[agent_key] = {
            "agent_id": agent_key,
            "source": "agent_registry",
            "project_dir": project_dir,
            "memory_layout": str(entry.get("memory_layout") or ""),
            "tool_profile": str(entry.get("tool_profile") or ""),
            "scope": str(entry.get("scope") or ""),
            "vault_version": str(entry.get("vault_version") or ""),
        }
        if project_dir:
            _add_project(projects, project_dir, source="agent_registry", agent=agent_key)
        private_dir = str(entry.get("private_project_dir") or "")
        if private_dir:
            _add_project(projects, private_dir, source="agent_registry_private", agent=agent_key)

    for candidate, source in _candidate_project_dirs(root):
        if candidate.exists() or (candidate / "vault.db").exists():
            _add_project(projects, candidate, source=source)

    codex_config = root / ".codex" / "config.toml"
    codex_projects = _extract_codex_vault_projects(codex_config)
    if codex_config.exists():
        agents["codex"] = {
            "agent_id": "codex",
            "source": "codex_config",
            "config_path": str(codex_config),
            "project_dirs": codex_projects,
        }
        for project in codex_projects:
            _add_project(projects, project, source="codex_config", agent="codex")

    openclaw = _read_openclaw_config(root / ".openclaw" / "openclaw.json")
    if openclaw:
        configured_project = str(openclaw.get("configured_project_dir") or "").strip()
        openclaw_project = Path(configured_project).expanduser() if configured_project else root / ".openclaw" / "workspace" / "vault-project"
        openclaw["agent_id"] = "openclaw"
        openclaw["source"] = "openclaw_config"
        openclaw["project_dir"] = str(openclaw_project)
        agents["openclaw"] = openclaw
        if openclaw_project.exists() or (openclaw_project / "vault.db").exists():
            source = "openclaw_config_project" if configured_project else "openclaw_default_project"
            _add_project(projects, openclaw_project, source=source, agent="openclaw")

    sorted_projects = sorted(
        projects.values(),
        key=lambda item: (not item.get("db_exists"), item.get("project_dir", "")),
    )
    scored_projects = sorted(
        sorted_projects,
        key=lambda item: _project_recommendation_score(item),
        reverse=True,
    )
    recommended = scored_projects[0]["project_dir"] if scored_projects else ""
    return {
        "ok": True,
        "home": str(root),
        "registry_path": str(resolved_registry),
        "agent_count": len(agents),
        "agents": sorted(agents.values(), key=lambda item: item.get("agent_id", "")),
        "project_count": len(sorted_projects),
        "projects": sorted_projects,
        "recommended_shared_project_dir": recommended,
    }
