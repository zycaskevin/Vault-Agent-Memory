from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_subject_development_mission_v4 as mission
from scripts import validate_subject_task_authorization_dispatch_v4 as dispatch

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _restore_repo_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)


def test_dispatch_accepts_exact_current_mission_phase_at_t003_terminal_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proof_path = ROOT / mission.MISSION_PROOF_PATH
    revocation_path = ROOT / mission.REVOCATION_PATH
    reference_now = mission._now().replace(microsecond=0)
    reference_text = mission._time(reference_now)
    validate = dispatch.validator.validate
    monkeypatch.setattr(
        dispatch.validator,
        "validate",
        lambda repo_root: validate(repo_root, now_utc=reference_text),
    )
    if not proof_path.exists():
        assert not revocation_path.exists()
        expected = {
            "active": False,
            "mission_id": None,
            "mission_state": "INACTIVE",
            "protocol_version": 4,
            "sequence": 6,
            "status": "PASS",
        }
    else:
        proof_raw = proof_path.read_bytes()
        proof = mission._parse(proof_raw)
        assert proof_raw == mission.canonical(proof)
        if revocation_path.exists():
            expected_state = "REVOKED"
        elif reference_now >= mission._timestamp(proof["mission_not_after_utc"]):
            expected_state = "EXPIRED"
        else:
            expected_state = "ACTIVE"
        expected = {
            "active": expected_state == "ACTIVE",
            "mission_id": proof["mission_id"],
            "mission_state": expected_state,
            "protocol_version": 4,
            "sequence": 6,
            "status": "PASS",
        }
    assert dispatch.validate(ROOT) == expected


def test_dispatch_cli_is_exact_and_no_abbreviation(capsys) -> None:
    assert dispatch.main(["--ledger", "--json"]) == 0
    assert dispatch.main(["--led", "--json"]) == 2
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
