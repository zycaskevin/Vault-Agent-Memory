import json

import pytest


def test_upgrade_check_reports_pip_command_without_mutating(monkeypatch, capsys):
    from vault import __version__
    from vault.cli import main

    monkeypatch.setattr("vault.cli_upgrade.fetch_latest_pypi_version", lambda: "9.9.9")
    monkeypatch.setattr(
        "vault.cli_upgrade.detect_installation",
        lambda: {"method": "pip", "python_executable": "/venv/bin/python", "editable_source": ""},
    )

    main(["upgrade", "--check", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert payload["installed_version"] == __version__
    assert payload["latest_version"] == "9.9.9"
    assert payload["status"] == "update_available"
    assert payload["automatic_upgrade"] is False
    assert payload["changes_made"] is False
    assert payload["upgrade_command"] == [
        "/venv/bin/python",
        "-m",
        "pip",
        "install",
        "--upgrade",
        "vault-for-llm==9.9.9",
    ]


def test_upgrade_without_check_remains_check_only(monkeypatch, capsys):
    from vault import __version__
    from vault.cli import main

    main(["upgrade", "--latest-version", __version__])
    output = capsys.readouterr().out

    assert "status: current" in output
    assert "changes made: no" in output
    assert "No upgrade is needed" in output


@pytest.mark.parametrize(
    ("executable", "expected"),
    [
        ("/home/user/.local/pipx/venvs/vault-for-llm/bin/python", "pipx"),
        ("/home/user/.local/share/uv/tools/vault-for-llm/bin/python", "uv-tool"),
        ("/opt/venv/bin/python", "pip"),
    ],
)
def test_detect_installation_from_python_path(executable, expected):
    from vault.cli_upgrade import detect_installation

    result = detect_installation(executable=executable, direct_url={})

    assert result["method"] == expected


def test_detect_editable_installation_from_direct_url():
    from vault.cli_upgrade import detect_installation

    result = detect_installation(
        executable="/repo/.venv/bin/python",
        direct_url={"url": "file:///work/Vault-Agent-Memory", "dir_info": {"editable": True}},
    )

    assert result["method"] == "editable"
    assert result["editable_source"] == "/work/Vault-Agent-Memory"


def test_upgrade_check_network_failure_is_machine_visible(monkeypatch, capsys):
    from vault.cli import main

    def fail():
        raise RuntimeError("unable to fetch latest version from PyPI")

    monkeypatch.setattr("vault.cli_upgrade.fetch_latest_pypi_version", fail)

    with pytest.raises(SystemExit) as exc_info:
        main(["upgrade", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exc_info.value.code == 1
    assert payload["ok"] is False
    assert payload["status"] == "check_failed"
    assert payload["changes_made"] is False
    assert "--latest-version" in payload["next_action"]
