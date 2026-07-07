import json
from pathlib import Path


def test_discover_local_agent_memory_finds_registry_codex_and_openclaw(tmp_path):
    from vault.agent_registry import register_agent
    from vault.agent_setup_discovery import discover_local_agent_memory

    home = tmp_path / "home"
    registry_dir = tmp_path / "registry"
    shared = home / "Vaults" / "agents" / "codex" / "private-memory"
    openclaw_project = home / ".openclaw" / "workspace" / "vault-project"
    shared.mkdir(parents=True)
    openclaw_project.mkdir(parents=True)
    (shared / "vault.db").write_bytes(b"SQLite format 3\x00")
    (openclaw_project / "vault.db").write_bytes(b"SQLite format 3\x00")

    register_agent(
        agent="codex",
        project_dir=shared,
        scope="shared",
        features=["core", "mcp"],
        path=registry_dir / "agent-registry.json",
    )

    codex_config = home / ".codex" / "config.toml"
    codex_config.parent.mkdir(parents=True)
    codex_config.write_text(
        '\n'.join(
            [
                "[mcp_servers.vault]",
                'command = "/Users/example/.local/bin/vault-mcp"',
                'args = ["--project-dir", "' + str(shared) + '", "--tool-profile", "remote"]',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    openclaw_config = home / ".openclaw" / "openclaw.json"
    openclaw_config.parent.mkdir(parents=True, exist_ok=True)
    openclaw_config.write_text(
        json.dumps(
            {
                "plugins": {
                    "entries": {
                        "vault-for-llm": {
                            "enabled": True,
                            "config": {"wrapperPath": str(home / "wrapper")},
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    payload = discover_local_agent_memory(home=home, registry_file=registry_dir / "agent-registry.json")

    assert payload["agent_count"] == 2
    projects = {item["project_dir"]: item for item in payload["projects"]}
    assert str(shared.resolve()) in projects
    assert str(openclaw_project.resolve()) in projects
    assert "agent_registry" in projects[str(shared.resolve())]["sources"]
    assert "codex_config" in projects[str(shared.resolve())]["sources"]
    assert "openclaw_default_project" in projects[str(openclaw_project.resolve())]["sources"]
    assert payload["recommended_shared_project_dir"] == str(shared.resolve())


def test_interactive_setup_prompts_to_use_existing_discovered_project(tmp_path, monkeypatch):
    from vault.agent_setup import interactive_setup

    existing = tmp_path / "existing-shared"
    existing.mkdir()
    (existing / "vault.db").write_bytes(b"SQLite format 3\x00")
    monkeypatch.setattr(
        "vault.agent_setup.discover_local_agent_memory",
        lambda: {
            "ok": True,
            "projects": [
                {
                    "project_dir": str(existing),
                    "db_path": str(existing / "vault.db"),
                    "db_exists": True,
                    "sources": ["agent_registry"],
                    "agents": ["codex"],
                }
            ],
            "recommended_shared_project_dir": str(existing),
        },
    )
    answers = iter(
        [
            "openclaw",
            "shared",
            "hybrid",
            "yes",
            "",
            str(tmp_path / "openclaw-private"),
            "en",
            "yes",
            "no",
            "no",
            "no",
            "no",
            "no",
            "",
            "no",
            "none",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    config = interactive_setup({})

    assert config.project_dir == existing
    assert config.agent == "openclaw"
    assert config.scope == "shared"
    assert config.memory_layout == "hybrid"


def test_agent_discover_cli_reports_machine_projects(tmp_path, monkeypatch, capsys):
    from vault.agent_registry import register_agent
    from vault.cli import main

    home = tmp_path / "home"
    registry_dir = tmp_path / "registry"
    project = home / "Vaults" / "agents" / "codex" / "private-memory"
    project.mkdir(parents=True)
    (project / "vault.db").write_bytes(b"SQLite format 3\x00")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("VAULT_AGENT_REGISTRY_DIR", str(registry_dir))
    register_agent(agent="codex", project_dir=project, scope="shared", features=["core", "mcp"])

    main(["agent", "discover", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["agent_count"] == 1
    assert payload["recommended_shared_project_dir"] == str(project.resolve())
    assert payload["projects"][0]["project_dir"] == str(project.resolve())
