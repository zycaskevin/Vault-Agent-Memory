from __future__ import annotations

from pathlib import Path

import pytest

from scripts import validate_subject_task_authorization_dispatch_v4 as dispatch

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _restore_repo_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)


def test_dispatch_accepts_inactive_bridge_only_at_exact_t003_terminal_prefix() -> None:
    assert dispatch.validate(ROOT) == {
        "active": False,
        "mission_id": None,
        "mission_state": "INACTIVE",
        "protocol_version": 4,
        "sequence": 6,
        "status": "PASS",
    }


def test_dispatch_cli_is_exact_and_no_abbreviation(capsys) -> None:
    assert dispatch.main(["--ledger", "--json"]) == 0
    assert dispatch.main(["--led", "--json"]) == 2
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
