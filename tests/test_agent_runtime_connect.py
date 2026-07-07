import json


def test_connect_openclaw_runtime_dry_run_does_not_write_full_config(tmp_path):
    from vault.agent_runtime_connect import connect_openclaw_runtime

    config = tmp_path / "openclaw.json"
    project = tmp_path / "shared"
    config.write_text(
        json.dumps(
            {
                "plugins": {
                    "allow": ["brave"],
                    "entries": {
                        "brave": {"enabled": True, "config": {"apiKey": "secret"}},
                        "vault-for-llm": {
                            "enabled": True,
                            "config": {
                                "wrapperPath": "/old/wrapper",
                                "autoRecall": False,
                            },
                        },
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    payload = connect_openclaw_runtime(project_dir=project, config_path=config, apply=False)

    stored = json.loads(config.read_text(encoding="utf-8"))
    assert payload["apply"] is False
    assert payload["changed"] is True
    assert payload["previous_project_dir"] == ""
    assert payload["project_dir"] == str(project.resolve())
    assert "apiKey" not in json.dumps(payload)
    assert "projectDir" not in stored["plugins"]["entries"]["vault-for-llm"]["config"]


def test_connect_openclaw_runtime_apply_writes_project_dir_and_backup(tmp_path):
    from vault.agent_runtime_connect import connect_openclaw_runtime

    config = tmp_path / "openclaw.json"
    project = tmp_path / "shared"
    old_project = tmp_path / "old"
    config.write_text(
        json.dumps(
            {
                "plugins": {
                    "allow": [],
                    "entries": {
                        "vault-for-llm": {
                            "enabled": True,
                            "config": {
                                "wrapperPath": "/old/wrapper",
                                "projectDir": str(old_project),
                            },
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    payload = connect_openclaw_runtime(project_dir=project, config_path=config, apply=True)

    stored = json.loads(config.read_text(encoding="utf-8"))
    assert payload["apply"] is True
    assert payload["changed"] is True
    assert payload["backup_path"]
    assert payload["previous_project_dir"] == str(old_project)
    assert stored["plugins"]["entries"]["vault-for-llm"]["config"]["projectDir"] == str(project.resolve())
    assert stored["plugins"]["entries"]["vault-for-llm"]["config"]["wrapperPath"] == "/old/wrapper"
    assert "vault-for-llm" in stored["plugins"]["allow"]


def test_agent_connect_runtime_cli(tmp_path, capsys):
    from vault.cli import main

    config = tmp_path / "openclaw.json"
    project = tmp_path / "shared"
    config.write_text('{"plugins":{"entries":{}}}\n', encoding="utf-8")

    main(
        [
            "agent",
            "connect-runtime",
            "--runtime",
            "openclaw",
            "--project",
            str(project),
            "--config",
            str(config),
            "--apply",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    stored = json.loads(config.read_text(encoding="utf-8"))
    assert payload["runtime"] == "openclaw"
    assert payload["project_dir"] == str(project.resolve())
    assert stored["plugins"]["entries"]["vault-for-llm"]["config"]["projectDir"] == str(project.resolve())
