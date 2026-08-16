from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from scripts import run_subject_development_mission_v5 as mission
from scripts import validate_subject_task_authorization_dispatch_v5 as dispatch

ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = ROOT
CANDIDATE_PHASE = "candidate"
ACTIVE_PHASE = "active"


def _mission_phase() -> str:
    phase = os.environ.get("SUBJECT_MISSION_V5_PHASE")
    if phase not in {CANDIDATE_PHASE, ACTIVE_PHASE}:
        raise AssertionError("invalid Mission V5 CI phase")
    return phase


@pytest.fixture(scope="session", autouse=True)
def _phase_neutral_dispatch_root(tmp_path_factory: pytest.TempPathFactory):
    """Replay dispatcher assertions at the authority anchor for this CI phase."""
    global ROOT
    proof_path = LIVE_ROOT / mission.MISSION_PROOF_PATH
    if not proof_path.exists():
        yield
        return
    proof_raw = proof_path.read_bytes()
    proof = mission._parse(proof_raw)
    if proof_raw != mission.canonical(proof):
        raise AssertionError("non-canonical V5 mission proof")
    protocol_base = proof["protocol_base_commit"][4:]
    if _mission_phase() == CANDIDATE_PHASE:
        dispatch.validator.validate_mission_proof_value(
            proof,
            proof_raw,
            LIVE_ROOT,
            now_utc=proof["active_from_utc"],
        )
        mission.check_active_protocol_ancestry(LIVE_ROOT, protocol_base)
        candidate_phase, candidate_commit = mission.validate_mission_activation_candidate(
            LIVE_ROOT,
            protocol_base=protocol_base,
            mission_raw=proof_raw,
        )
        if candidate_phase == "preliminary":
            replay_commit = protocol_base
        elif candidate_phase == "active":
            replay_commit = candidate_commit
        else:
            raise AssertionError("invalid Mission V5 candidate phase")
    else:
        replay_commit = mission.validate_mission_activation_delivery(
            LIVE_ROOT,
            protocol_base=protocol_base,
            mission_raw=proof_raw,
        )
    snapshot = tmp_path_factory.mktemp("mission-v5-dispatch") / "repo"
    subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--no-hardlinks",
            "--no-checkout",
            os.fspath(LIVE_ROOT),
            os.fspath(snapshot),
        ],
        check=True,
    )
    subprocess.run(
        ["git", "checkout", "--quiet", "--detach", replay_commit],
        cwd=snapshot,
        check=True,
    )
    subprocess.run(
        [
            "git",
            "remote",
            "set-url",
            "origin",
            "https://github.com/zycaskevin/Vault-Agent-Memory.git",
        ],
        cwd=snapshot,
        check=True,
    )
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", replay_commit],
        cwd=snapshot,
        check=True,
    )
    ROOT = snapshot
    try:
        yield
    finally:
        ROOT = LIVE_ROOT


@pytest.fixture(autouse=True)
def _restore_repo_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)


def test_dispatch_accepts_exact_current_mission_phase(
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
            "protocol_version": 5,
            "sequence": 6,
            "status": "PASS",
        }
    else:
        proof_raw = proof_path.read_bytes()
        proof = mission._parse(proof_raw)
        assert proof_raw == mission.canonical(proof)
        progress_raw = (ROOT / mission.PROGRESS_PATH).read_bytes()
        progress = mission._parse(progress_raw)
        assert progress_raw == mission.canonical(progress)
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
            "protocol_version": 5,
            "sequence": len(progress["events"]),
            "status": "PASS",
        }
    assert dispatch.validate(ROOT) == expected


def test_dispatch_cli_is_exact_and_no_abbreviation(capsys) -> None:
    assert dispatch.main(["--ledger", "--json"]) == 0
    assert dispatch.main(["--led", "--json"]) == 2
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
