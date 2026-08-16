from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import subprocess
import sys
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts import run_subject_development_mission_v5 as mission
from scripts import run_subject_identity_test_isolation as identity_isolation
from scripts import update_subject_task_progress_v5 as updater
from scripts import validate_subject_development_mission_v5 as validator
from scripts import verify_subject_implementation_authorization as authorization_verifier

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
def _phase_neutral_mission_root(tmp_path_factory: pytest.TempPathFactory):
    """Replay the exact V5 control appropriate to the checked Git phase."""
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
        validator.validate_mission_proof_value(
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
    snapshot = tmp_path_factory.mktemp("mission-v5-activation") / "repo"
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


def _raw(path: str) -> bytes:
    return (ROOT / path).read_bytes()


def _json(path: str) -> dict[str, object]:
    return json.loads(_raw(path))


def _authority_snapshot() -> dict[str, bytes]:
    return {
        path: _raw(path)
        for path in sorted(
            {*mission.TRUST_ROOT_PATHS, *mission.RETAINED_AUTHORITY_PATHS}
        )
    }


def _write_activation_records(repo: Path, proof_raw: bytes) -> None:
    for relative in mission.ACTIVATION_SDG_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(proof_raw if relative == mission.MISSION_PROOF_PATH else b"record\n")


def _git_commit(repo: Path, message: str, *, allow_empty: bool = False) -> str:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    command = ["git", "commit", "-q", "-m", message]
    if allow_empty:
        command.insert(2, "--allow-empty")
    subprocess.run(command, cwd=repo, check=True)
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()


def _closed_release_fixture(tmp_path: Path, mutation: str) -> tuple[Path, str, str]:
    repo = tmp_path / mutation
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "existing.txt").write_text("base\n")
    if mutation == "wrong-action":
        (repo / "new.txt").write_text("unexpected base\n")
    anchor = _git_commit(repo, "anchor")

    subprocess.run(["git", "switch", "-q", "-c", "topic"], cwd=repo, check=True)
    if mutation == "delete":
        (repo / "existing.txt").unlink()
    else:
        (repo / "existing.txt").write_text("topic\n")
    (repo / "new.txt").write_text("topic\n")
    if mutation == "mode":
        (repo / "existing.txt").chmod(0o755)
    if mutation == "extra":
        (repo / "rogue.txt").write_text("outside closed scope\n")
    _git_commit(repo, "topic source")
    if mutation == "hidden-add-delete":
        (repo / "hidden.txt").write_text("hidden history\n")
        _git_commit(repo, "hidden add")
        (repo / "hidden.txt").unlink()
        _git_commit(repo, "hidden delete")
    topic = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()

    if mutation == "reversed-order":
        tree = subprocess.check_output(
            ["git", "rev-parse", f"{topic}^{{tree}}"], cwd=repo, text=True
        ).strip()
        release = subprocess.check_output(
            ["git", "commit-tree", tree, "-p", topic, "-p", anchor, "-m", "reversed"],
            cwd=repo,
            text=True,
        ).strip()
    elif mutation == "tree-mismatch":
        tree = subprocess.check_output(
            ["git", "rev-parse", f"{anchor}^{{tree}}"], cwd=repo, text=True
        ).strip()
        release = subprocess.check_output(
            ["git", "commit-tree", tree, "-p", anchor, "-p", topic, "-m", "bad tree"],
            cwd=repo,
            text=True,
        ).strip()
    else:
        subprocess.run(["git", "switch", "-q", "main"], cwd=repo, check=True)
        if mutation == "wrong-parent":
            _git_commit(repo, "unexpected first parent", allow_empty=True)
        subprocess.run(
            ["git", "merge", "-q", "--no-ff", "--no-edit", topic], cwd=repo, check=True
        )
        release = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True
        ).strip()
    return repo, anchor, release


def _t020_authorization_fixture() -> tuple[
    dict[str, object],
    dict[str, object],
    bytes,
    dict[str, object],
    dict[str, object],
    bytes,
]:
    contract = _json(mission.CONTRACT_PATH)
    mission_proof = mission.build_signed_test_proof(
        contract, recorded_at_utc="2026-08-13T00:00:00Z"
    )
    mission_raw = mission.canonical(mission_proof)
    registry = _json(mission.SCOPE_REGISTRY_PATH)
    descriptor = next(item for item in registry["tasks"] if item["task"] == "T-020")
    proof = {
        "schema_version": 5,
        "artifact_kind": "subject-task-authorization-v5",
        "status": "PASS",
        "mission_id": mission_proof["mission_id"],
        "mission_proof_sha256": hashlib.sha256(mission_raw).hexdigest(),
        "authorized_task": "T-020",
        "implementation_base_commit": "git:" + mission.BRIDGE_BASE,
        "scope_registry_sha256": contract["scope_registry_sha256"],
        "task_header_sha256": descriptor["task_header_sha256"],
        "descriptor_sha256": hashlib.sha256(
            mission.canonical(descriptor, newline=False)
        ).hexdigest(),
        "progress_sequence": 6,
        "progress_sha256": "7" * 64,
        "required_read_files": mission.required_read_files(ROOT, descriptor),
        "derived_at_utc": "2026-08-13T00:00:01Z",
        "proof_repo_relative_path": (
            "specs/subject-distillation/task-authorizations/T-020.json"
        ),
    }
    proof["task_authorization_id"] = hashlib.sha256(
        mission.canonical(proof, newline=False)
    ).hexdigest()
    return (
        contract,
        mission_proof,
        mission_raw,
        descriptor,
        proof,
        mission.canonical(proof),
    )


def test_contract_is_closed_and_current_mission_phase_is_exact() -> None:
    contract = _json(mission.CONTRACT_PATH)
    assert contract["schema_version"] == 5
    assert contract["artifact_kind"] == "subject-development-mission-v5-contract"
    assert contract["repository"] == "zycaskevin/Vault-Agent-Memory"
    assert contract["allowed_tasks"] == [f"T-{n:03d}" for n in range(4, 34)]
    assert contract["authority"] == {
        "authorizing_principal": "github:zycaskevin",
        "delegates_task_authority": True,
        "owner_confirmation_required_for_mission": True,
        "owner_confirmation_required_per_task": False,
        "owner_decision_id": "SD-MISSION-V5-POST-START-CI-RECOVERY",
        "owner_decision_ref": "owner-message:SD-MISSION-V5-POST-START-CI-RECOVERY",
    }
    assert contract["mission_duration_seconds"] == 7_776_000
    assert contract["activation"]["bridge_implementation_base_commit"] == (
        "git:03dcdabc873658cd7de24dfeeef8b85090cf2321"
    )
    assert contract["activation"]["progress"]["sha256"] == (
        "28478445e3eeb5b838b010fa81518d4fcbbb5c6a37422cb3aa58dabdcbf87626"
    )
    assert contract["predecessor_protocol"] == {
        "activation_commit": "git:" + mission.BRIDGE_BASE,
        "activation_progress_sequence": 6,
        "activation_progress_sha256": mission.ACTIVATION_PROGRESS_SHA256,
        "contract_path": "specs/subject-distillation/development-mission-v4.contract.json",
        "contract_sha256": mission.PREDECESSOR_IMMUTABLE_HASHES[
            "specs/subject-distillation/development-mission-v4.contract.json"
        ],
        "mission_id": mission.V4_MISSION_ID,
        "proof_path": "specs/subject-distillation/task-authorizations/MISSION-T004-T033.json",
        "proof_sha256": mission.PREDECESSOR_IMMUTABLE_HASHES[
            "specs/subject-distillation/task-authorizations/MISSION-T004-T033.json"
        ],
        "protocol_base_commit": "git:" + mission.V4_PROTOCOL_BASE,
        "protocol_version": 4,
        "supersession": "task-authority-and-ci-routing-for-t004-t033",
        "trust_root_sha256": (
            "511e24bbffb1b88566d7a3cc10deee4e8f260ae29d6a0d029b2e5d4070d457b9"
        ),
    }
    proof_path = ROOT / mission.MISSION_PROOF_PATH
    revocation_path = ROOT / mission.REVOCATION_PATH
    reference_now = mission._now().replace(microsecond=0)
    result = validator.validate(ROOT, now_utc=mission._time(reference_now))
    if not proof_path.exists():
        assert not revocation_path.exists()
        assert result == {
            "active": False,
            "authorized_tasks": 0,
            "mission_id": None,
            "mission_state": "INACTIVE",
            "sequence": 6,
            "status": "PASS",
        }
        return

    proof_raw = proof_path.read_bytes()
    proof = mission._parse(proof_raw)
    assert proof_raw == mission.canonical(proof)
    if revocation_path.exists():
        expected_state = "REVOKED"
    elif reference_now >= mission._timestamp(proof["mission_not_after_utc"]):
        expected_state = "EXPIRED"
    else:
        expected_state = "ACTIVE"
    assert result == {
        "active": expected_state == "ACTIVE",
        "authorized_tasks": 30 if expected_state == "ACTIVE" else 0,
        "mission_id": proof["mission_id"],
        "mission_state": expected_state,
        "sequence": 6,
        "status": "PASS",
    }


def test_mission_v5_phase_rejects_missing_or_unknown_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SUBJECT_MISSION_V5_PHASE", raising=False)
    with pytest.raises(AssertionError, match="invalid Mission V5 CI phase"):
        _mission_phase()
    monkeypatch.setenv("SUBJECT_MISSION_V5_PHASE", "bypass")
    with pytest.raises(AssertionError, match="invalid Mission V5 CI phase"):
        _mission_phase()


def test_mission_scope_passes_the_shared_private_authorization_verifier(
    tmp_path: Path,
) -> None:
    issued = datetime(2026, 8, 13, 0, 0, tzinfo=timezone.utc)
    proposal, receipt_raw, scope_raw = mission._derive_proposal(
        ROOT,
        mission.BRIDGE_BASE,
        issued,
    )
    receipt_path = tmp_path / "receipt.json"
    scope_path = tmp_path / "scope.json"
    receipt_path.write_bytes(receipt_raw)
    scope_path.write_bytes(scope_raw)

    result = authorization_verifier._verify(
        [
            "--receipt",
            os.fspath(receipt_path),
            "--expected-receipt-sha256",
            proposal["receipt_sha256"],
            "--scope",
            os.fspath(scope_path),
            "--manifest",
            authorization_verifier.MANIFEST_PATH,
            "--schema",
            authorization_verifier.SCHEMA_PATH,
            "--expected-authority",
            mission.AUTHORITY,
            "--expected-task",
            "T-004",
            "--json",
        ],
        issued,
        None,
    )

    assert result == {
        "authorization_id": proposal["authorization_id"],
        "authorized_task": "T-004",
        "baseline_id": proposal["baseline_id"],
        "status": "PASS",
    }


def test_mission_private_lifecycle_ignores_unrelated_external_sibling_churn(
    tmp_path: Path,
) -> None:
    """Directory membership churn outside the owned private slot is not drift."""
    issued = mission._now()
    proposal, receipt_raw, scope_raw = mission._derive_proposal(
        ROOT,
        mission.BRIDGE_BASE,
        issued,
    )
    external = tmp_path / "external"
    external.mkdir(mode=0o700)
    runtime = mission.legacy.v1.Runtime(temp_root=os.fspath(external))
    slot = mission.legacy.v1.LifecycleSlot()
    cleanup_ok = False
    with mission.legacy.v1._signal_boundary() as signals:
        try:
            lifecycle = mission.legacy.v1._new_lifecycle(
                os.fspath(external),
                receipt_raw,
                scope_raw,
                runtime,
                signals,
                slot,
            )
            sibling = external / "unrelated-sibling"
            sibling.write_text("unrelated\n")
            sibling.unlink()

            mission._audit_private_lifecycle_v5(lifecycle)
            expected = mission.canonical(
                {
                    "authorization_id": proposal["authorization_id"],
                    "authorized_task": "T-004",
                    "baseline_id": proposal["baseline_id"],
                    "status": "PASS",
                }
            )
            mission.legacy.v1._run_verifier(
                lifecycle,
                os.fspath(ROOT),
                proposal["receipt_sha256"],
                "T-004",
                expected,
                runtime,
            )
            mission._audit_private_lifecycle_v5(lifecycle)
        finally:
            signals.cleanup_active = True
            if slot.value is not None:
                cleanup_ok = mission.legacy.v1._cleanup(slot.value, runtime)
                mission.legacy.v1._close_lifecycle(slot.value)
                slot.value = None
    assert cleanup_ok


def test_mission_private_lifecycle_denies_private_file_replacement(
    tmp_path: Path,
) -> None:
    issued = datetime(2026, 8, 15, 15, 54, 44, tzinfo=timezone.utc)
    _proposal, receipt_raw, scope_raw = mission._derive_proposal(
        ROOT,
        mission.BRIDGE_BASE,
        issued,
    )
    external = tmp_path / "external"
    external.mkdir(mode=0o700)
    runtime = mission.legacy.v1.Runtime(temp_root=os.fspath(external))
    slot = mission.legacy.v1.LifecycleSlot()
    cleanup_ok = False
    with mission.legacy.v1._signal_boundary() as signals:
        try:
            lifecycle = mission.legacy.v1._new_lifecycle(
                os.fspath(external),
                receipt_raw,
                scope_raw,
                runtime,
                signals,
                slot,
            )
            receipt_path = external / lifecycle.dirname / "receipt.json"
            saved_path = external / lifecycle.dirname / "receipt.saved"
            receipt_path.rename(saved_path)
            receipt_path.write_bytes(receipt_raw)
            receipt_path.chmod(0o600)
            with pytest.raises(mission.Denied):
                mission._audit_private_lifecycle_v5(lifecycle)
            receipt_path.unlink()
            saved_path.rename(receipt_path)
        finally:
            signals.cleanup_active = True
            if slot.value is not None:
                cleanup_ok = mission.legacy.v1._cleanup(slot.value, runtime)
                mission.legacy.v1._close_lifecycle(slot.value)
                slot.value = None
    assert cleanup_ok


def test_mission_private_lifecycle_denies_external_directory_replacement(
    tmp_path: Path,
) -> None:
    issued = mission._now()
    _proposal, receipt_raw, scope_raw = mission._derive_proposal(
        ROOT,
        mission.BRIDGE_BASE,
        issued,
    )
    external = tmp_path / "external"
    displaced = tmp_path / "external.displaced"
    external.mkdir(mode=0o700)
    runtime = mission.legacy.v1.Runtime(temp_root=os.fspath(external))
    slot = mission.legacy.v1.LifecycleSlot()
    cleanup_ok = False
    with mission.legacy.v1._signal_boundary() as signals:
        try:
            lifecycle = mission.legacy.v1._new_lifecycle(
                os.fspath(external),
                receipt_raw,
                scope_raw,
                runtime,
                signals,
                slot,
            )
            external.rename(displaced)
            external.mkdir(mode=0o700)
            with pytest.raises(mission.Denied):
                mission._audit_private_lifecycle_v5(lifecycle)
            external.rmdir()
            displaced.rename(external)
        finally:
            signals.cleanup_active = True
            if slot.value is not None:
                cleanup_ok = mission.legacy.v1._cleanup(slot.value, runtime)
                mission.legacy.v1._close_lifecycle(slot.value)
                slot.value = None
    assert cleanup_ok


def test_v4_predecessor_roots_are_exact_and_drift_denies() -> None:
    snapshot = _authority_snapshot()
    contract, _raw_contract = mission.load_contract(ROOT, retained=snapshot)
    assert contract["predecessor_protocol"]["mission_id"] == mission.V4_MISSION_ID
    predecessor_path = (
        "specs/subject-distillation/task-authorizations/MISSION-T004-T033.json"
    )
    mutated = dict(snapshot)
    mutated[predecessor_path] = snapshot[predecessor_path][:-2] + b"0\n"
    with pytest.raises(mission.Denied):
        mission.load_contract(ROOT, retained=mutated)


def test_scope_registry_is_exact_complete_and_safety_bounded() -> None:
    contract = _json(mission.CONTRACT_PATH)
    registry_raw = _raw(mission.SCOPE_REGISTRY_PATH)
    registry = json.loads(registry_raw)
    assert hashlib.sha256(registry_raw).hexdigest() == contract["scope_registry_sha256"]
    assert registry["tasks"] == sorted(registry["tasks"], key=lambda item: item["task"])
    assert [entry["task"] for entry in registry["tasks"]] == [f"T-{n:03d}" for n in range(4, 34)]
    for entry in registry["tasks"]:
        assert entry["phase_id"] == mission.TASK_PHASES[entry["task"]]
        paths = [policy["path"] for policy in entry["writable_path_policies"]]
        assert paths == sorted(paths)
        assert len(paths) == len(set(paths))
        assert not any("*" in path or "$" in path for path in paths)
        assert entry["completion_repo_relative_paths"] == sorted(
            entry["completion_repo_relative_paths"]
        )
        assert set(entry["completion_repo_relative_paths"]) <= set(paths)
        assert 1 <= len(entry["verification_steps"]) <= 16
    t020 = registry["tasks"][16]
    assert t020["task"] == "T-020"
    assert t020["required_read_paths"] == [
        "tests/fixtures/subject_distillation/manifest.json",
        "tests/fixtures/subject_distillation/organization/authority-boundary-cases.json",
    ]
    t029 = registry["tasks"][25]
    assert t029["task"] == "T-029"
    assert t029["completion_repo_relative_paths"] == sorted(
        [
            "scripts/capture_subject_closure.py",
            "scripts/run_subject_legacy_gate.py",
            "scripts/run_subject_sbe_fixture_gate.py",
            "specs/subject-distillation/evidence/0dc10cfc4a429662/fixture.txt",
            "specs/subject-distillation/evidence/0dc10cfc4a429662/legacy.txt",
            "specs/subject-distillation/evidence/0dc10cfc4a429662/surface.txt",
            "specs/subject-distillation/evidence/0dc10cfc4a429662/unit.txt",
            "specs/subject-distillation/sbe-traceability.json",
        ]
    )
    assert [step["step_id"] for step in t029["verification_steps"]] == [
        f"t029-verify-{number:02d}" for number in range(1, 7)
    ]
    assert t029["verification_steps"][1]["argv"][:4] == [
        "python",
        "scripts/export_subject_sbe_traceability.py",
        "--mode",
        "collected",
    ]
    t031 = registry["tasks"][27]
    assert [step["step_id"] for step in t031["verification_steps"]] == [
        f"t031-verify-{number:02d}" for number in range(1, 6)
    ]
    assert t031["required_control_api"] == (
        "scripts.validate_subject_development_mission_v5:validate_t033_action"
    )
    t032 = registry["tasks"][28]
    assert (t032["task"], t032["risk_class"], t032["terminal_policy"]) == (
        "T-032",
        "OPERATIONAL",
        "blocked_only",
    )
    assert t032["writable_path_policies"] == []
    t033 = registry["tasks"][29]
    assert (t033["task"], t033["risk_class"], t033["terminal_policy"]) == (
        "T-033",
        "L1",
        "experimental_only",
    )
    assert t033["stable_requires_operational_authority"] is True
    assert t033["required_control_api"] == t031["required_control_api"]
    assert t033["verification_steps"][-1]["argv"] == [
        "python",
        "scripts/validate_subject_task_authorization_dispatch_v5.py",
        "--ledger",
        "--json",
    ]


def test_required_ci_pins_every_nonrecursive_v5_bridge_root() -> None:
    workflow = _raw(".github/workflows/ci.yml").decode("utf-8")
    for path in mission.BRIDGE_PATHS:
        if path == ".github/workflows/ci.yml":
            continue
        line = f"{hashlib.sha256(_raw(path)).hexdigest()}  {path}"
        assert line in workflow
    assert "Replay immutable T-003 authorization checkpoint" in workflow
    assert "SUBJECT_T003_CHECKPOINT: f7aff39fecbc2fce7d612f396237afb0e094e460" in workflow
    assert "Replay immutable V4 activation checkpoint" in workflow
    assert "SUBJECT_V4_ACTIVATION_CHECKPOINT: " + mission.BRIDGE_BASE in workflow
    assert (
        "SUBJECT_V4_INACTIVE_CHECKPOINT: "
        "5ce070ddfdf2511b76e497f6c296826b6a70c050"
    ) in workflow


def test_mission_proof_is_not_self_authority() -> None:
    contract = _json(mission.CONTRACT_PATH)
    forged = mission.build_unsigned_test_proof(
        contract,
        proposal_id="1" * 64,
        receipt_sha256="2" * 64,
        recorded_at_utc="2026-08-13T00:00:00Z",
    )
    with pytest.raises(mission.Denied):
        validator.validate_mission_proof_value(
            forged,
            mission.canonical(forged),
            ROOT,
            now_utc="2026-08-13T00:00:01Z",
        )


def test_mission_duration_starts_at_activation_not_proposal_issue() -> None:
    issued = datetime(2026, 8, 13, tzinfo=timezone.utc)
    recorded = issued + timedelta(minutes=10)
    proposal, _receipt, _scope = mission._derive_proposal(ROOT, mission.BRIDGE_BASE, issued)
    proof = mission._proof_from_proposal(proposal, recorded, "test-owner-confirmation")
    assert proof["active_from_utc"] == "2026-08-13T00:10:00Z"
    assert proof["mission_not_after_utc"] == "2026-11-11T00:10:00Z"
    validator.validate_mission_proof_value(
        proof,
        mission.canonical(proof),
        ROOT,
        now_utc="2026-08-13T00:10:00Z",
    )


@pytest.mark.parametrize(
    "now_utc",
    ["2026-08-12T23:59:59Z", "2026-11-11T00:00:00Z"],
)
def test_mission_time_window_fails_closed(now_utc: str) -> None:
    proof = mission.build_signed_test_proof(
        _json(mission.CONTRACT_PATH),
        recorded_at_utc="2026-08-13T00:00:00Z",
    )
    with pytest.raises(mission.Denied):
        validator.validate_mission_proof_value(
            proof,
            mission.canonical(proof),
            ROOT,
            now_utc=now_utc,
        )


def test_revocation_is_monotonic_and_blocks_task_derivation(tmp_path: Path) -> None:
    proof = mission.build_signed_test_proof(
        _json(mission.CONTRACT_PATH),
        recorded_at_utc="2026-08-13T00:00:00Z",
    )
    revocation = {
        "schema_version": 1,
        "artifact_kind": "subject-development-mission-revocation",
        "mission_id": proof["mission_id"],
        "mission_epoch": 1,
        "previous_ledger_sequence": 6,
        "previous_ledger_sha256": mission.ACTIVATION_PROGRESS_SHA256,
        "revoked_at_utc": "2026-08-14T00:00:00Z",
        "reason_code": "OWNER_REVOKED",
        "authorizing_principal": "github:zycaskevin",
        "owner_confirmation_ref": "owner-message:mission-v5-revocation-test",
    }
    revocation["revocation_id"] = hashlib.sha256(
        mission.canonical(revocation, newline=False)
    ).hexdigest()
    validator.validate_revocation_value(revocation, mission.canonical(revocation), proof)
    validator.validate_revocation_progress(
        revocation, _json(mission.PROGRESS_PATH)
    )
    stale = copy.deepcopy(revocation)
    stale["previous_ledger_sha256"] = "9" * 64
    with pytest.raises(mission.Denied):
        validator.validate_revocation_progress(stale, _json(mission.PROGRESS_PATH))
    with pytest.raises(mission.Denied):
        mission.derive_task_authorization(
            ROOT,
            proof,
            "T-004",
            "03dcdabc873658cd7de24dfeeef8b85090cf2321",
            now_utc="2026-08-14T00:00:01Z",
            revocation=revocation,
        )


def test_only_next_pending_task_can_be_derived(monkeypatch) -> None:
    proof = mission.build_signed_test_proof(
        _json(mission.CONTRACT_PATH),
        recorded_at_utc="2026-08-13T00:00:00Z",
    )
    monkeypatch.setattr(mission, "check_task_base", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        mission,
        "validate_mission_activation_delivery",
        lambda *_args, **_kwargs: mission.BRIDGE_BASE,
    )
    grant = mission.derive_task_authorization(
        ROOT,
        proof,
        "T-004",
        "03dcdabc873658cd7de24dfeeef8b85090cf2321",
        now_utc="2026-08-13T00:00:01Z",
    )
    assert grant["authorized_task"] == "T-004"
    assert grant["mission_id"] == proof["mission_id"]
    assert grant["progress_sequence"] == 6
    with pytest.raises(mission.Denied):
        mission.derive_task_authorization(
            ROOT,
            proof,
            "T-005",
            "03dcdabc873658cd7de24dfeeef8b85090cf2321",
            now_utc="2026-08-13T00:00:01Z",
        )


def test_task_derivation_loads_the_pinned_sibling_validator(monkeypatch) -> None:
    proof = mission.build_signed_test_proof(
        _json(mission.CONTRACT_PATH),
        recorded_at_utc="2026-08-13T00:00:00Z",
    )
    loaded: list[tuple[str, str]] = []

    def load(module_name: str, filename: str):
        loaded.append((module_name, filename))
        return validator

    monkeypatch.setattr(mission, "_load_sibling_dependency", load)
    monkeypatch.setattr(mission, "check_task_base", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        mission,
        "validate_mission_activation_delivery",
        lambda *_args, **_kwargs: mission.BRIDGE_BASE,
    )
    grant = mission.derive_task_authorization(
        ROOT,
        proof,
        "T-004",
        mission.BRIDGE_BASE,
        now_utc="2026-08-13T00:00:01Z",
    )
    assert grant["authorized_task"] == "T-004"
    assert loaded == [
        (
            "scripts.validate_subject_development_mission_v5",
            "validate_subject_development_mission_v5.py",
        )
    ]


def test_next_task_base_must_equal_previous_final_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission_proof = mission.build_signed_test_proof(
        _json(mission.CONTRACT_PATH),
        recorded_at_utc="2026-08-13T00:00:00Z",
    )
    progress = copy.deepcopy(_json(mission.PROGRESS_PATH))
    progress["tasks"]["T-004"] = "COMPLETED"
    progress_raw = mission.canonical(progress)
    expected = "a" * 40
    monkeypatch.setattr(mission, "check_task_base", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(mission, "_load_progress", lambda _root: (progress, progress_raw))
    monkeypatch.setattr(
        validator,
        "validate_ledger_value",
        lambda *_args, **_kwargs: {
            "delivery_anchor": expected,
            "proofs": 1,
            "sequence": 8,
            "status": "PASS",
        },
    )
    with pytest.raises(mission.Denied):
        mission.derive_task_authorization(
            ROOT,
            mission_proof,
            "T-005",
            "b" * 40,
            now_utc="2026-08-13T00:00:01Z",
        )
    grant = mission.derive_task_authorization(
        ROOT,
        mission_proof,
        "T-005",
        expected,
        now_utc="2026-08-13T00:00:01Z",
    )
    assert grant["implementation_base_commit"] == "git:" + expected


def test_updater_denies_before_exact_mission_activation(capsys) -> None:
    assert (
        updater.main(
            [
                "start",
                "--task",
                "T-004",
                "--implementation-base-commit",
                mission.BRIDGE_BASE,
                "--json",
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == updater.DENY_TEXT


@pytest.mark.parametrize(
    ("path", "error_text"),
    [
        ("scripts/run_subject_development_mission_v5.py", mission.ERROR_TEXT),
        (
            "scripts/update_subject_task_progress_v5.py",
            updater.ERROR_TEXT,
        ),
        (
            "scripts/validate_subject_development_mission_v5.py",
            validator.ERROR_TEXT,
        ),
        (
            "scripts/validate_subject_task_authorization_dispatch_v5.py",
            "SUBJECT_TASK_AUTHORIZATION_DISPATCH_V5_ERROR\n",
        ),
    ],
)
def test_direct_cli_dependency_bootstrap_is_fixed_no_echo(
    tmp_path: Path, path: str, error_text: str
) -> None:
    copied = tmp_path / Path(path).name
    copied.write_bytes(_raw(path))
    marker = str(tmp_path).encode()
    completed = subprocess.run(
        [sys.executable, "-I", str(copied)],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert completed.returncode == 3
    assert completed.stdout == b""
    assert completed.stderr == error_text.encode()
    assert marker not in completed.stdout + completed.stderr


@pytest.mark.parametrize(
    ("path", "error_text"),
    [
        ("scripts/run_subject_development_mission_v5.py", mission.ERROR_TEXT),
        ("scripts/update_subject_task_progress_v5.py", updater.ERROR_TEXT),
        (
            "scripts/validate_subject_development_mission_v5.py",
            validator.ERROR_TEXT,
        ),
        (
            "scripts/validate_subject_task_authorization_dispatch_v5.py",
            "SUBJECT_TASK_AUTHORIZATION_DISPATCH_V5_ERROR\n",
        ),
    ],
)
def test_direct_cli_rejects_installed_dependency_shadow(
    tmp_path: Path, path: str, error_text: str
) -> None:
    copied = tmp_path / Path(path).name
    copied.write_bytes(_raw(path))
    shadow = tmp_path / "shadow"
    package = shadow / "scripts"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    payload_marker = tmp_path / "shadow-payload-executed"
    payload = f"from pathlib import Path\nPath({str(payload_marker)!r}).write_text('bad')\n"
    for name in (
        "run_subject_development_mission_v5",
        "run_subject_task_authorization_v3",
        "update_subject_progress",
        "validate_subject_development_mission_v5",
        "validate_subject_progress",
        "validate_subject_task_authorization_v3",
    ):
        (package / f"{name}.py").write_text(payload)
    command = (
        "import runpy,sys;"
        f"sys.path.insert(0,{str(shadow)!r});"
        f"runpy.run_path({str(copied)!r},run_name='__main__')"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", command],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        timeout=10,
    )
    marker = str(tmp_path).encode()
    assert completed.returncode == 3
    assert completed.stdout == b""
    assert completed.stderr == error_text.encode()
    assert marker not in completed.stdout + completed.stderr
    assert not payload_marker.exists()


@pytest.mark.parametrize(
    ("path", "dependency", "error_text"),
    [
        (
            "scripts/run_subject_development_mission_v5.py",
            "run_subject_task_authorization_v3.py",
            mission.ERROR_TEXT,
        ),
        (
            "scripts/update_subject_task_progress_v5.py",
            "run_subject_development_mission_v5.py",
            updater.ERROR_TEXT,
        ),
        (
            "scripts/validate_subject_development_mission_v5.py",
            "run_subject_development_mission_v5.py",
            validator.ERROR_TEXT,
        ),
        (
            "scripts/validate_subject_task_authorization_dispatch_v5.py",
            "run_subject_development_mission_v5.py",
            "SUBJECT_TASK_AUTHORIZATION_DISPATCH_V5_ERROR\n",
        ),
    ],
)
def test_direct_cli_rejects_symlinked_sibling_before_payload_execution(
    tmp_path: Path, path: str, dependency: str, error_text: str
) -> None:
    copied = tmp_path / Path(path).name
    copied.write_bytes(_raw(path))
    payload_marker = tmp_path / "symlink-payload-executed"
    target = tmp_path / "payload.py"
    target.write_text(
        f"from pathlib import Path\nPath({str(payload_marker)!r}).write_text('bad')\n"
    )
    (tmp_path / dependency).symlink_to(target)
    completed = subprocess.run(
        [sys.executable, "-I", str(copied)],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        timeout=10,
    )
    marker = str(tmp_path).encode()
    assert completed.returncode == 3
    assert completed.stdout == b""
    assert completed.stderr == error_text.encode()
    assert marker not in completed.stdout + completed.stderr
    assert not payload_marker.exists()


def test_repository_identity_accepts_only_canonical_github_remote_forms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    accepted = (
        "git@github.com:zycaskevin/Vault-Agent-Memory.git",
        "https://github.com/zycaskevin/Vault-Agent-Memory",
        "https://github.com/zycaskevin/Vault-Agent-Memory.git",
    )
    for remote in accepted:
        monkeypatch.setattr(
            mission, "_git", lambda *_args, value=remote: (value + "\n").encode()
        )
        mission.check_repository_identity(ROOT)
    rejected = (
        "git@github.com:zycaskevin/Vault-Agent-Memory",
        "https://github.com/other/Vault-Agent-Memory",
        "https://github.com/zycaskevin/Vault-Agent-Memory/",
        "https://github.com/zycaskevin/Vault-Agent-Memory.git?ref=main",
        "https://token@github.com/zycaskevin/Vault-Agent-Memory.git",
        "https://github.com/zycaskevin/Vault-Agent-Memory-evil",
        " https://github.com/zycaskevin/Vault-Agent-Memory",
        "https://github.com/zycaskevin/Vault-Agent-Memory ",
        "https://github.com/zycaskevin/Vault-Agent-Memory\nextra",
    )
    for remote in rejected:
        monkeypatch.setattr(
            mission, "_git", lambda *_args, value=remote: (value + "\n").encode()
        )
        with pytest.raises(mission.Denied):
            mission.check_repository_identity(ROOT)


def test_git_accepts_success_diagnostics_and_denies_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def success(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=["git", "rev-parse", "HEAD"],
            returncode=0,
            stdout=b"a" * 40 + b"\n",
            stderr=b"trace: diagnostic only\n",
        )

    monkeypatch.setattr(mission.subprocess, "run", success)
    assert mission._git(ROOT, "rev-parse", "HEAD") == b"a" * 40 + b"\n"

    def failure(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=["git", "rev-parse", "HEAD"],
            returncode=1,
            stdout=b"",
            stderr=b"fatal: failure\n",
        )

    monkeypatch.setattr(mission.subprocess, "run", failure)
    with pytest.raises(mission.Denied):
        mission._git(ROOT, "rev-parse", "HEAD")


@pytest.mark.parametrize("phase", ["pending", "linked", "final"])
def test_task_proof_publication_recovery_topologies(
    tmp_path: Path, monkeypatch, phase: str
) -> None:
    pending_path = tmp_path / mission.PENDING_PATH
    final_relative = "specs/subject-distillation/task-authorizations/T-004.json"
    final_path = tmp_path / final_relative
    pending_path.parent.mkdir(parents=True)
    final_path.parent.mkdir(parents=True)
    raw = b'{"proof":"public-safe"}\n'
    if phase in {"pending", "linked"}:
        pending_path.write_bytes(raw)
        pending_path.chmod(0o600)
    if phase == "linked":
        os.link(pending_path, final_path)
        pending_path.chmod(0o644)
    elif phase == "final":
        final_path.write_bytes(raw)
        final_path.chmod(0o644)

    present = {
        relative
        for relative in (mission.PENDING_PATH, final_relative)
        if (tmp_path / relative).exists()
    }
    monkeypatch.setattr(
        validator,
        "_entry_exists",
        lambda root, relative: (root / relative).exists(),
    )
    monkeypatch.setattr(
        updater,
        "_status",
        lambda _root: {relative: "add" for relative in present},
    )

    def read_file(root: Path, relative: str):
        path = root / relative
        info = path.stat()
        identity = (
            info.st_dev,
            info.st_ino,
            info.st_mode,
            info.st_nlink,
            info.st_size,
            info.st_mtime_ns,
            info.st_ctime_ns,
        )
        return path.read_bytes(), identity

    monkeypatch.setattr(mission.legacy, "_read_repo_file", read_file)
    seen: list[bytes] = []
    assert updater._recoverable_publication_raw(tmp_path, final_relative, seen.append) == raw
    assert seen == [raw]


def test_mission_proof_linked_recovery_is_byte_identical(tmp_path: Path, monkeypatch) -> None:
    issued = datetime(2026, 8, 13, tzinfo=timezone.utc)
    proposal, _receipt, _scope = mission._derive_proposal(ROOT, mission.BRIDGE_BASE, issued)
    raw = mission.canonical(mission._proof_from_proposal(proposal, issued, "owner-message-457"))
    pending = tmp_path / mission.PENDING_PATH
    final = tmp_path / mission.MISSION_PROOF_PATH
    pending.parent.mkdir(parents=True)
    final.parent.mkdir(parents=True)
    pending.write_bytes(raw)
    pending.chmod(0o600)
    os.link(pending, final)
    pending.chmod(0o644)
    present = {mission.PENDING_PATH, mission.MISSION_PROOF_PATH}
    monkeypatch.setattr(
        mission.legacy,
        "_repo_entry_exists",
        lambda root, relative: (root / relative).exists(),
    )
    monkeypatch.setattr(
        mission.legacy.v1,
        "_git",
        lambda _args: b"".join(b"?? " + relative.encode() + b"\0" for relative in sorted(present)),
    )

    def read_file(root: Path, relative: str):
        path = root / relative
        info = path.stat()
        return path.read_bytes(), (
            info.st_dev,
            info.st_ino,
            info.st_mode,
            info.st_nlink,
            info.st_size,
            info.st_mtime_ns,
            info.st_ctime_ns,
        )

    monkeypatch.setattr(mission.legacy, "_read_repo_file", read_file)
    assert mission._recoverable_mission_proof_raw(tmp_path, proposal, "owner-message-457") == raw


def test_protocol_release_accepts_exact_three_modifications_and_ten_additions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/zycaskevin/Vault-Agent-Memory.git"],
        cwd=repo,
        check=True,
    )
    modified = {
        ".github/workflows/ci.yml",
        "specs/subject-distillation/development-missions/README.md",
        "tests/test_repo_hygiene_tools.py",
    }
    for relative in modified:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("base\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=repo, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    monkeypatch.setattr(mission, "BRIDGE_BASE", base)
    monkeypatch.setattr(
        mission,
        "_check_predecessor_activation_commit",
        lambda _repo_root: None,
    )
    for relative in mission.BRIDGE_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("bridge\n")
        path.chmod(0o755 if relative.startswith("scripts/") else 0o644)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "bridge"], cwd=repo, check=True)
    release = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", release], cwd=repo, check=True
    )
    mission._check_v5_inactive_release_commit(repo, release)

    (repo / "extra.txt").write_text("unauthorized\n")
    subprocess.run(["git", "add", "extra.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "extra"], cwd=repo, check=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    subprocess.run(["git", "update-ref", "refs/remotes/origin/main", head], cwd=repo, check=True)
    with pytest.raises(mission.Denied):
        mission._check_v5_inactive_release_commit(repo, head)


def test_protocol_release_accepts_only_exact_post_sdg_compatibility_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "post-sdg-release"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/zycaskevin/Vault-Agent-Memory.git"],
        cwd=repo,
        check=True,
    )
    for relative in mission.POST_SDG_COMPATIBILITY_MODIFIED_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("anchor\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "reviewed SDG anchor"], cwd=repo, check=True)
    anchor = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()

    subprocess.run(["git", "switch", "-q", "-c", "compatibility"], cwd=repo, check=True)
    for relative in mission.POST_SDG_COMPATIBILITY_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("compatibility\n")
        path.chmod(0o755 if relative.startswith("scripts/") else 0o644)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "compatibility"], cwd=repo, check=True)
    topic = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(["git", "switch", "-q", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "merge", "-q", "--no-ff", "--no-edit", topic], cwd=repo, check=True
    )
    release = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", release], cwd=repo, check=True
    )

    monkeypatch.setattr(mission, "POST_SDG_BASE", anchor)
    monkeypatch.setattr(mission, "_check_post_sdg_base", lambda _repo_root: None)
    monkeypatch.setattr(
        mission,
        "_check_predecessor_activation_commit",
        lambda _repo_root: None,
    )
    mission._check_post_sdg_compatibility_release(repo, release)

    (repo / "unauthorized.txt").write_text("not in the closed hotfix\n")
    subprocess.run(["git", "add", "unauthorized.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "unauthorized"], cwd=repo, check=True)
    unauthorized = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", unauthorized],
        cwd=repo,
        check=True,
    )
    with pytest.raises(mission.Denied):
        mission._check_post_sdg_compatibility_release(repo, unauthorized)


def test_protocol_release_denies_hidden_topic_scope_and_mode_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "hostile-post-sdg-release"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/zycaskevin/Vault-Agent-Memory.git"],
        cwd=repo,
        check=True,
    )
    for relative in mission.POST_SDG_COMPATIBILITY_MODIFIED_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("anchor\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "reviewed SDG anchor"], cwd=repo, check=True)
    anchor = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    monkeypatch.setattr(mission, "POST_SDG_BASE", anchor)
    monkeypatch.setattr(mission, "_check_post_sdg_base", lambda _repo_root: None)
    monkeypatch.setattr(
        mission,
        "_check_predecessor_activation_commit",
        lambda _repo_root: None,
    )

    subprocess.run(["git", "switch", "-q", "-c", "hidden-scope"], cwd=repo, check=True)
    for relative in mission.POST_SDG_COMPATIBILITY_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("compatibility\n")
        path.chmod(0o755 if relative.startswith("scripts/") else 0o644)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "closed compatibility"], cwd=repo, check=True)
    (repo / "hidden.txt").write_text("unauthorized intermediate path\n")
    subprocess.run(["git", "add", "hidden.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add hidden path"], cwd=repo, check=True)
    (repo / "hidden.txt").unlink()
    subprocess.run(["git", "add", "-u"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "hide unauthorized path"], cwd=repo, check=True)
    hidden_topic = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(["git", "switch", "-q", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "merge", "-q", "--no-ff", "--no-edit", hidden_topic], cwd=repo, check=True
    )
    hidden_release = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", hidden_release], cwd=repo, check=True
    )
    with pytest.raises(mission.Denied):
        mission._check_post_sdg_compatibility_release(repo, hidden_release)

    subprocess.run(["git", "reset", "--hard", "-q", anchor], cwd=repo, check=True)
    subprocess.run(["git", "switch", "-q", "-c", "wrong-mode"], cwd=repo, check=True)
    for relative in mission.POST_SDG_COMPATIBILITY_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("compatibility\n")
        path.chmod(0o644)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "wrong script mode"], cwd=repo, check=True)
    mode_topic = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(["git", "switch", "-q", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "merge", "-q", "--no-ff", "--no-edit", mode_topic], cwd=repo, check=True
    )
    mode_release = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", mode_release], cwd=repo, check=True
    )
    with pytest.raises(mission.Denied):
        mission._check_post_sdg_compatibility_release(repo, mode_release)


def test_reviewed_post_sdg_anchor_binds_signed_gate_and_receipt() -> None:
    mission._check_post_sdg_base(LIVE_ROOT)


def test_sdg004_release_accepts_only_exact_linear_reviewed_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "sdg004-release"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    for relative in mission.SDG004_COMPATIBILITY_MODIFIED_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("base\n")
        if relative.startswith("scripts/"):
            path.chmod(0o755)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "anchor"], cwd=repo, check=True)
    anchor = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    monkeypatch.setattr(mission, "SDG004_BASE", anchor)
    subprocess.run(["git", "switch", "-q", "-c", "reviewed"], cwd=repo, check=True)
    for relative in mission.SDG004_COMPATIBILITY_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("reviewed\n")
        if relative.startswith("scripts/"):
            path.chmod(0o755)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "reviewed source"], cwd=repo, check=True)
    topic = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(["git", "switch", "-q", "main"], cwd=repo, check=True)
    subprocess.run(["git", "merge", "-q", "--no-ff", "--no-edit", topic], cwd=repo, check=True)
    release = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    mission._check_sdg004_compatibility_release(repo, release)

    subprocess.run(["git", "reset", "--hard", "-q", anchor], cwd=repo, check=True)
    subprocess.run(["git", "switch", "-q", "-C", "hostile"], cwd=repo, check=True)
    for relative in mission.SDG004_COMPATIBILITY_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("reviewed\n")
        if relative.startswith("scripts/"):
            path.chmod(0o755)
    (repo / "extra.txt").write_text("unauthorized\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "hostile source"], cwd=repo, check=True)
    hostile = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(["git", "switch", "-q", "main"], cwd=repo, check=True)
    subprocess.run(["git", "merge", "-q", "--no-ff", "--no-edit", hostile], cwd=repo, check=True)
    hostile_release = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    with pytest.raises(mission.Denied):
        mission._check_sdg004_compatibility_release(repo, hostile_release)


def test_sdg006_release_accepts_only_exact_linear_reviewed_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "sdg006-release"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    for relative in mission.SDG006_COMPATIBILITY_MODIFIED_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("base\n")
        if relative.startswith("scripts/"):
            path.chmod(0o755)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "sdg004 anchor"], cwd=repo, check=True)
    anchor = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    monkeypatch.setattr(mission, "SDG006_BASE", anchor)
    monkeypatch.setattr(
        mission,
        "_check_sdg004_compatibility_release",
        lambda _repo_root, candidate: None
        if candidate == anchor
        else (_ for _ in ()).throw(mission.Denied()),
    )

    subprocess.run(["git", "switch", "-q", "-c", "reviewed"], cwd=repo, check=True)
    for relative in mission.SDG006_COMPATIBILITY_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("reviewed\n")
        if relative.startswith("scripts/"):
            path.chmod(0o755)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "reviewed source"], cwd=repo, check=True)
    topic = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(["git", "switch", "-q", "main"], cwd=repo, check=True)
    subprocess.run(["git", "merge", "-q", "--no-ff", "--no-edit", topic], cwd=repo, check=True)
    release = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    mission._check_sdg006_compatibility_release(repo, release)

    subprocess.run(["git", "reset", "--hard", "-q", anchor], cwd=repo, check=True)
    subprocess.run(["git", "switch", "-q", "-C", "hostile"], cwd=repo, check=True)
    for relative in mission.SDG006_COMPATIBILITY_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("reviewed\n")
        if relative.startswith("scripts/"):
            path.chmod(0o755)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "closed source"], cwd=repo, check=True)
    (repo / "hidden.txt").write_text("unauthorized intermediate path\n")
    subprocess.run(["git", "add", "hidden.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "hidden add"], cwd=repo, check=True)
    (repo / "hidden.txt").unlink()
    subprocess.run(["git", "add", "-u"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "hidden delete"], cwd=repo, check=True)
    hostile = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(["git", "switch", "-q", "main"], cwd=repo, check=True)
    subprocess.run(["git", "merge", "-q", "--no-ff", "--no-edit", hostile], cwd=repo, check=True)
    hostile_release = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    with pytest.raises(mission.Denied):
        mission._check_sdg006_compatibility_release(repo, hostile_release)


def test_sdg007_release_accepts_only_exact_linear_reviewed_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "sdg007-release"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    for relative in mission.SDG007_COMPATIBILITY_MODIFIED_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("base\n")
        if relative.startswith("scripts/"):
            path.chmod(0o755)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "sdg006 anchor"], cwd=repo, check=True)
    anchor = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    monkeypatch.setattr(mission, "SDG007_BASE", anchor)
    monkeypatch.setattr(
        mission,
        "_check_sdg006_compatibility_release",
        lambda _repo_root, candidate: None
        if candidate == anchor
        else (_ for _ in ()).throw(mission.Denied()),
    )

    subprocess.run(["git", "switch", "-q", "-c", "reviewed"], cwd=repo, check=True)
    for relative in mission.SDG007_COMPATIBILITY_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("reviewed\n")
        if relative.startswith("scripts/"):
            path.chmod(0o755)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "reviewed source"], cwd=repo, check=True)
    topic = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(["git", "switch", "-q", "main"], cwd=repo, check=True)
    subprocess.run(["git", "merge", "-q", "--no-ff", "--no-edit", topic], cwd=repo, check=True)
    release = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    mission._check_sdg007_compatibility_release(repo, release)

    subprocess.run(["git", "reset", "--hard", "-q", anchor], cwd=repo, check=True)
    subprocess.run(["git", "switch", "-q", "-C", "hostile"], cwd=repo, check=True)
    for relative in mission.SDG007_COMPATIBILITY_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("reviewed\n")
        if relative.startswith("scripts/"):
            path.chmod(0o755)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "closed source"], cwd=repo, check=True)
    (repo / "hidden.txt").write_text("unauthorized intermediate path\n")
    subprocess.run(["git", "add", "hidden.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "hidden add"], cwd=repo, check=True)
    (repo / "hidden.txt").unlink()
    subprocess.run(["git", "add", "-u"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "hidden delete"], cwd=repo, check=True)
    hostile = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(["git", "switch", "-q", "main"], cwd=repo, check=True)
    subprocess.run(["git", "merge", "-q", "--no-ff", "--no-edit", hostile], cwd=repo, check=True)
    hostile_release = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    with pytest.raises(mission.Denied):
        mission._check_sdg007_compatibility_release(repo, hostile_release)


def test_sdg008_release_accepts_only_exact_linear_reviewed_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "sdg008-release"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    for relative in mission.SDG008_COMPATIBILITY_MODIFIED_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("base\n")
        if relative.startswith("scripts/"):
            path.chmod(0o755)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "sdg007 anchor"], cwd=repo, check=True)
    anchor = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    monkeypatch.setattr(mission, "SDG008_BASE", anchor)
    monkeypatch.setattr(
        mission,
        "_check_sdg007_compatibility_release",
        lambda _repo_root, candidate: None
        if candidate == anchor
        else (_ for _ in ()).throw(mission.Denied()),
    )

    subprocess.run(["git", "switch", "-q", "-c", "reviewed"], cwd=repo, check=True)
    for relative in mission.SDG008_COMPATIBILITY_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("reviewed\n")
        if relative.startswith("scripts/"):
            path.chmod(0o755)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "reviewed source"], cwd=repo, check=True)
    topic = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(["git", "switch", "-q", "main"], cwd=repo, check=True)
    subprocess.run(["git", "merge", "-q", "--no-ff", "--no-edit", topic], cwd=repo, check=True)
    release = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    mission._check_sdg008_compatibility_release(repo, release)

    subprocess.run(["git", "reset", "--hard", "-q", anchor], cwd=repo, check=True)
    subprocess.run(["git", "switch", "-q", "-C", "hostile"], cwd=repo, check=True)
    for relative in mission.SDG008_COMPATIBILITY_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("reviewed\n")
        if relative.startswith("scripts/"):
            path.chmod(0o755)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "closed source"], cwd=repo, check=True)
    (repo / "hidden.txt").write_text("unauthorized intermediate path\n")
    subprocess.run(["git", "add", "hidden.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "hidden add"], cwd=repo, check=True)
    (repo / "hidden.txt").unlink()
    subprocess.run(["git", "add", "-u"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "hidden delete"], cwd=repo, check=True)
    hostile = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(["git", "switch", "-q", "main"], cwd=repo, check=True)
    subprocess.run(["git", "merge", "-q", "--no-ff", "--no-edit", hostile], cwd=repo, check=True)
    hostile_release = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    with pytest.raises(mission.Denied):
        mission._check_sdg008_compatibility_release(repo, hostile_release)


def test_sdg011_anchor_is_exact_and_current_main_still_requires_sdg012() -> None:
    mission._check_sdg011_compatibility_release(LIVE_ROOT, mission.SDG011_RELEASE)
    with pytest.raises(mission.Denied):
        mission._check_sdg012_compatibility_release(LIVE_ROOT, mission.SDG011_RELEASE)


@pytest.mark.parametrize("field", ["gate", "receipt"])
def test_sdg010_anchor_denies_trusted_gate_or_receipt_drift(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    constant = "SDG010_GATE_SHA256" if field == "gate" else "SDG010_RECEIPT_SHA256"
    monkeypatch.setattr(mission, constant, "0" * 64)
    with pytest.raises(mission.Denied):
        mission._check_sdg010_compatibility_release(LIVE_ROOT)


def test_closed_sdg011_release_accepts_exact_two_parent_topic(tmp_path: Path) -> None:
    repo, anchor, release = _closed_release_fixture(tmp_path, "exact")
    assert (
        mission._check_closed_compatibility_release(
            repo,
            release,
            expected_parent=anchor,
            expected_topic=None,
            expected_tree=None,
            allowed_paths=["existing.txt", "new.txt"],
            modified_paths={"existing.txt"},
        )
        == subprocess.check_output(
            ["git", "rev-parse", f"{release}^2"], cwd=repo, text=True
        ).strip()
    )


def test_protocol_release_requires_sdg012_merge_after_sdg011_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, anchor, release = _closed_release_fixture(tmp_path, "protocol-release")
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", release], cwd=repo, check=True
    )
    monkeypatch.setattr(mission, "SDG011_RELEASE", anchor)
    monkeypatch.setattr(mission, "SDG012_COMPATIBILITY_PATHS", ["existing.txt", "new.txt"])
    monkeypatch.setattr(mission, "SDG012_COMPATIBILITY_MODIFIED_PATHS", {"existing.txt"})
    monkeypatch.setattr(mission, "check_repository_identity", lambda _repo_root: None)
    monkeypatch.setattr(mission, "_check_predecessor_activation_commit", lambda _repo: None)
    monkeypatch.setattr(mission, "_check_post_sdg_base", lambda _repo: None)
    monkeypatch.setattr(
        mission, "_check_post_sdg_compatibility_release", lambda _repo, _base: None
    )
    monkeypatch.setattr(
        mission, "_check_sdg011_compatibility_release", lambda _repo, _base: None
    )
    checked_sdg012: list[str] = []
    check_sdg012 = mission._check_sdg012_compatibility_release

    def tracked_sdg012(repo_root: Path, base: str) -> None:
        checked_sdg012.append(base)
        check_sdg012(repo_root, base)

    monkeypatch.setattr(mission, "_check_sdg012_compatibility_release", tracked_sdg012)

    mission._check_protocol_release_commit(repo, release)
    assert checked_sdg012 == [release]

    (repo / "outside-sdg012.txt").write_text("not a closed delivery\n")
    subprocess.run(["git", "add", "outside-sdg012.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "invalid later descendant"], cwd=repo, check=True)
    later = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", later], cwd=repo, check=True
    )
    with pytest.raises(mission.Denied):
        mission._check_protocol_release_commit(repo, later)
    assert checked_sdg012[-1] == later

    subprocess.run(["git", "reset", "--hard", "-q", anchor], cwd=repo, check=True)
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", anchor], cwd=repo, check=True
    )
    with pytest.raises(mission.Denied):
        mission._check_protocol_release_commit(repo, anchor)


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong-parent",
        "reversed-order",
        "tree-mismatch",
        "extra",
        "hidden-add-delete",
        "wrong-action",
        "delete",
        "mode",
    ],
)
def test_closed_sdg012_release_denies_topology_scope_action_or_mode_drift(
    tmp_path: Path, mutation: str
) -> None:
    repo, anchor, release = _closed_release_fixture(tmp_path, mutation)
    with pytest.raises(mission.Denied):
        mission._check_closed_compatibility_release(
            repo,
            release,
            expected_parent=anchor,
            expected_topic=None,
            expected_tree=None,
            allowed_paths=["existing.txt", "new.txt"],
            modified_paths={"existing.txt"},
        )


def test_post_sdg_local_green_isolates_frozen_v3_identity_suite(
    tmp_path: Path,
) -> None:
    config = json.loads((LIVE_ROOT / ".sddgov/ci-cost-guard.json").read_text())
    commands = config["local_green"]["commands"]
    full = next(command for command in commands if "--ignore=tests/test_subject_progress.py" in command)
    identity_files = [
        "tests/test_subject_authorization_bootstrap.py",
        "tests/test_subject_authorization_runner.py",
        "tests/test_subject_progress_v2.py",
        "tests/test_subject_progress_v3.py",
        "tests/test_subject_task_authorization_v2.py",
        "tests/test_subject_task_authorization_v3.py",
        "tests/test_subject_development_mission_v5.py",
        "tests/test_subject_task_authorization_dispatch_v5.py",
        "tests/test_subject_baseline_control.py",
    ]
    assert [
        "python",
        "scripts/run_subject_identity_test_isolation.py",
        "--phase",
        "candidate",
    ] in commands
    harness = (LIVE_ROOT / "scripts/run_subject_identity_test_isolation.py").read_text()
    workflow = (LIVE_ROOT / ".github/workflows/ci.yml").read_text()
    dispatcher_tests = (
        LIVE_ROOT / "tests/test_subject_task_authorization_dispatch_v5.py"
    ).read_text()
    dispatcher_tree = ast.parse(dispatcher_tests)
    identity_isolation._validate_dispatcher_source(dispatcher_tests)
    semantic_names = {
        ast.unparse(node)
        for node in ast.walk(dispatcher_tree)
        if isinstance(node, ast.Attribute)
    } | {
        ast.unparse(node.func)
        for node in ast.walk(dispatcher_tree)
        if isinstance(node, ast.Call)
    }
    harness_pin = hashlib.sha256(harness.encode()).hexdigest()
    dispatcher_pin = hashlib.sha256(dispatcher_tests.encode()).hexdigest()
    assert f"{harness_pin}  scripts/run_subject_identity_test_isolation.py" in workflow
    assert (
        f"{dispatcher_pin}  tests/test_subject_task_authorization_dispatch_v5.py"
        in workflow
    )
    for path in identity_files:
        assert path in harness
        assert f"--ignore={path}" in full
    outcome_marks = [
        (f"{path}::{node.name}", ast.unparse(decorator))
        for path in identity_files
        for node in ast.parse((LIVE_ROOT / path).read_text()).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for decorator in node.decorator_list
        if ast.unparse(decorator).startswith(
            ("pytest.mark.skip(", "pytest.mark.skipif(", "pytest.mark.xfail(")
        )
    ]
    assert outcome_marks == [
        (
            identity_isolation.DARWIN_DEFAULT_TEMP_NODE,
            (
                "pytest.mark.skipif(sys.platform != 'darwin', "
                "reason='Darwin system alias integration')"
            ),
        )
    ]
    assert "--ignore=tests/test_subject_task_authorization_dispatch_v5.py" in workflow
    assert sum(count for _path, count in identity_isolation.FILES) == 446
    assert (
        "tests/test_subject_task_authorization_dispatch_v5.py",
        2,
    ) in identity_isolation.FILES
    assert {
        "pytest.mark.skip",
        "pytest.mark.skipif",
        "pytest.mark.xfail",
        "pytest.skip",
        "pytest.xfail",
        "pytest.importorskip",
    }.isdisjoint(semantic_names)
    bypass_sources = (
        "import pytest\np = pytest\np.mark.skip\n",
        "import pytest\ngetattr(pytest.mark, 'skip')\n",
        "import pytest\npytest.mark['xfail']\n",
        "import pytest\ng = getattr\ng(pytest.mark, 'skipif')\n",
        "from pytest import importorskip as load_optional\n",
    )
    for source in bypass_sources:
        with pytest.raises(RuntimeError):
            identity_isolation._validate_dispatcher_source(source)
    passing_junit = tmp_path / "pass.xml"
    passing_junit.write_text(
        '<testsuites><testsuite tests="1" failures="0" errors="0" '
        'skipped="0"><testcase name="node"/></testsuite></testsuites>',
        encoding="utf-8",
    )
    identity_isolation._verify_single_pass_junit(passing_junit)
    for outcome in ("skipped", "failure", "error"):
        rejected_junit = tmp_path / f"{outcome}.xml"
        rejected_junit.write_text(
            '<testsuites><testsuite tests="1" failures="'
            + ("1" if outcome == "failure" else "0")
            + '" errors="'
            + ("1" if outcome == "error" else "0")
            + '" skipped="'
            + ("1" if outcome == "skipped" else "0")
            + f'"><testcase name="node"><{outcome}/></testcase>'
            + "</testsuite></testsuites>",
            encoding="utf-8",
        )
        with pytest.raises(RuntimeError):
            identity_isolation._verify_single_pass_junit(rejected_junit)
    platform_skip_junit = tmp_path / "platform-skip.xml"
    platform_skip_junit.write_text(
        '<testsuites><testsuite tests="1" failures="0" errors="0" '
        'skipped="1"><testcase name="node"><skipped type="pytest.skip" '
        'message="Darwin system alias integration"/></testcase>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    assert identity_isolation.PLATFORM_SKIP_ALLOWLIST == (
        (
            identity_isolation.DARWIN_DEFAULT_TEMP_NODE,
            "darwin",
            "Darwin system alias integration",
        ),
    )
    assert (
        identity_isolation._platform_skip_reason(
            identity_isolation.DARWIN_DEFAULT_TEMP_NODE,
            "linux",
        )
        == "Darwin system alias integration"
    )
    assert (
        identity_isolation._platform_skip_reason(
            identity_isolation.DARWIN_DEFAULT_TEMP_NODE,
            "darwin",
        )
        is None
    )
    assert (
        identity_isolation._platform_skip_reason(
            "tests/other.py::test_other",
            "linux",
        )
        is None
    )
    identity_isolation._verify_identity_junit(
        platform_skip_junit,
        node=identity_isolation.DARWIN_DEFAULT_TEMP_NODE,
        platform="linux",
    )
    for node, platform in (
        (identity_isolation.DARWIN_DEFAULT_TEMP_NODE, "darwin"),
        ("tests/other.py::test_other", "linux"),
    ):
        with pytest.raises(RuntimeError):
            identity_isolation._verify_identity_junit(
                platform_skip_junit,
                node=node,
                platform=platform,
            )
    for invalid_child in (
        '<skipped type="pytest.xfail" message="Darwin system alias integration"/>',
        '<skipped type="pytest.skip" message="wrong reason"/>',
        '<failure type="pytest.fail" message="Darwin system alias integration"/>',
        '<error type="pytest.error" message="Darwin system alias integration"/>',
    ):
        invalid_platform_skip = tmp_path / (
            "invalid-platform-skip-" + hashlib.sha256(invalid_child.encode()).hexdigest()
        )
        invalid_platform_skip.write_text(
            '<testsuites><testsuite tests="1" failures="0" errors="0" '
            'skipped="1"><testcase name="node">'
            + invalid_child
            + "</testcase></testsuite></testsuites>",
            encoding="utf-8",
        )
        with pytest.raises(RuntimeError):
            identity_isolation._verify_single_platform_skip_junit(
                invalid_platform_skip,
                expected_reason="Darwin system alias integration",
            )
    multi_case_skip = tmp_path / "multi-case-skip.xml"
    multi_case_skip.write_text(
        '<testsuites><testsuite tests="2" failures="0" errors="0" '
        'skipped="1"><testcase name="one"><skipped type="pytest.skip" '
        'message="Darwin system alias integration"/></testcase>'
        '<testcase name="two"/></testsuite></testsuites>',
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError):
        identity_isolation._verify_single_platform_skip_junit(
            multi_case_skip,
            expected_reason="Darwin system alias integration",
        )
    malformed_skip = tmp_path / "malformed-platform-skip.xml"
    malformed_skip.write_text("<testsuite>", encoding="utf-8")
    with pytest.raises(RuntimeError):
        identity_isolation._verify_identity_junit(
            malformed_skip,
            node=identity_isolation.DARWIN_DEFAULT_TEMP_NODE,
            platform="linux",
        )
    assert '"xfail_strict=true"' in harness
    assert 'f"--junitxml={junit}"' in harness
    harness_functions = {
        node.name: node
        for node in ast.parse(harness).body
        if isinstance(node, ast.FunctionDef)
    }
    identity_junit_calls = {
        ast.unparse(node)
        for node in ast.walk(harness_functions["_verify_identity_junit"])
        if isinstance(node, ast.Call)
    }
    assert "_verify_single_pass_junit(path)" in identity_junit_calls
    assert (
        "_verify_single_platform_skip_junit(path, "
        "expected_reason=platform_skip_reason)"
    ) in identity_junit_calls
    main_calls = {
        ast.unparse(node)
        for node in ast.walk(harness_functions["main"])
        if isinstance(node, ast.Call)
    }
    assert (
        "_verify_identity_junit(junit, node=node, platform=sys.platform)"
        in main_calls
    )
    assert "len(nodes) != sum(count for _path, count in FILES)" in harness
    assert ".sddgov/ci-cost-guard.json" in mission.POST_SDG_COMPATIBILITY_MODIFIED_PATHS
    assert ".sddgov/ci-cost-guard.json" in mission.SDG004_COMPATIBILITY_MODIFIED_PATHS
    assert "scripts/run_subject_development_mission_v5.py" in (
        mission.SDG006_COMPATIBILITY_MODIFIED_PATHS
    )
    assert "scripts/run_subject_identity_test_isolation.py" in (
        mission.SDG007_COMPATIBILITY_MODIFIED_PATHS
    )
    assert "tests/test_subject_baseline_control.py" not in (
        mission.SDG008_COMPATIBILITY_MODIFIED_PATHS
    )
    assert "scripts/run_subject_identity_test_isolation.py" in (
        mission.SDG008_COMPATIBILITY_MODIFIED_PATHS
    )
    assert ".sddgov/ci-cost-guard.json" in mission.SDG012_COMPATIBILITY_MODIFIED_PATHS
    assert "tests/test_subject_task_authorization_dispatch_v5.py" in (
        mission.SDG012_COMPATIBILITY_MODIFIED_PATHS
    )


def test_sdg_merge_digest_uses_full_git_object_ids(tmp_path: Path) -> None:
    config = json.loads((LIVE_ROOT / ".sddgov/ci-cost-guard.json").read_text())
    environment = config["local_green"]["environment"]
    assert environment["GIT_CONFIG_COUNT"] == "1"
    assert environment["GIT_CONFIG_KEY_0"] == "core.abbrev"
    assert environment["GIT_CONFIG_VALUE_0"] == "40"
    workflow = (LIVE_ROOT / ".github/workflows/ci.yml").read_text()
    for key, value in environment.items():
        if key.startswith("GIT_CONFIG_"):
            assert f'{key}: "{value}"' in workflow

    repo = tmp_path / "digest"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    tracked = repo / "tracked.txt"
    tracked.write_text("base\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    tracked.write_text("changed\n")
    subprocess.run(["git", "commit", "-qam", "change"], cwd=repo, check=True)
    git_environment = dict(os.environ)
    git_environment.update(environment)
    command = ["git", "diff", "--binary", f"{base}...HEAD"]
    before = subprocess.check_output(command, cwd=repo, env=git_environment)
    for number in range(128):
        subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=repo,
            env=git_environment,
            input=f"extra-object-{number}\n".encode(),
            check=True,
            stdout=subprocess.DEVNULL,
        )
    after = subprocess.check_output(command, cwd=repo, env=git_environment)
    assert after == before
    index_line = next(line for line in before.decode().splitlines() if line.startswith("index "))
    left, right = index_line.split()[1].split("..")
    assert len(left) == len(right) == 40


def test_mission_activation_requires_exact_two_parent_merge_before_active(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "activation-chain"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/zycaskevin/Vault-Agent-Memory.git"],
        cwd=repo,
        check=True,
    )
    (repo / "README.md").write_text("base\n")
    for relative in mission.ACTIVATION_SDG_MODIFIED_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("base\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "protocol"], cwd=repo, check=True)
    protocol = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    proof_raw = b'{"mission":"owner-confirmed"}\n'
    _write_activation_records(repo, proof_raw)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "activate"], cwd=repo, check=True)
    activation = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    assert mission.validate_mission_activation_topic(
        repo,
        protocol_base=protocol,
        mission_raw=proof_raw,
    ) == activation
    assert mission.validate_mission_activation_candidate(
        repo,
        protocol_base=protocol,
        mission_raw=proof_raw,
    ) == ("preliminary", activation)
    with pytest.raises(mission.Denied):
        mission.validate_mission_activation_delivery(
            repo,
            protocol_base=protocol,
            mission_raw=proof_raw,
        )

    subprocess.run(
        ["git", "switch", "-q", "-c", "delivery", protocol], cwd=repo, check=True
    )
    subprocess.run(
        ["git", "merge", "-q", "--no-ff", "--no-edit", activation],
        cwd=repo,
        check=True,
    )
    delivery = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    assert mission.validate_mission_activation_delivery(
        repo,
        protocol_base=protocol,
        mission_raw=proof_raw,
    ) == delivery
    assert mission.validate_mission_activation_candidate(
        repo,
        protocol_base=protocol,
        mission_raw=proof_raw,
    ) == ("active", delivery)
    with pytest.raises(mission.Denied):
        mission.validate_mission_activation_topic(
            repo,
            protocol_base=protocol,
            mission_raw=proof_raw,
        )

    subprocess.run(["git", "reset", "--hard", "-q", protocol], cwd=repo, check=True)
    _write_activation_records(repo, proof_raw)
    pending = repo / mission.PENDING_PATH
    pending.parent.mkdir(parents=True, exist_ok=True)
    pending.write_bytes(proof_raw)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "pending activation"], cwd=repo, check=True)
    with pytest.raises(mission.Denied):
        mission.validate_mission_activation_topic(
            repo,
            protocol_base=protocol,
            mission_raw=proof_raw,
        )

    subprocess.run(["git", "reset", "--hard", "-q", protocol], cwd=repo, check=True)
    (repo / "rogue.txt").write_text("outside mission scope\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "rogue"], cwd=repo, check=True)
    _write_activation_records(repo, proof_raw)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "late activation"], cwd=repo, check=True)
    with pytest.raises(mission.Denied):
        mission.validate_mission_activation_topic(
            repo,
            protocol_base=protocol,
            mission_raw=proof_raw,
        )
    with pytest.raises(mission.Denied):
        mission.validate_mission_activation_candidate(
            repo,
            protocol_base=protocol,
            mission_raw=proof_raw,
        )
    with pytest.raises(mission.Denied):
        mission.validate_mission_activation_delivery(
            repo,
            protocol_base=protocol,
            mission_raw=proof_raw,
        )


def test_mission_activation_accepts_only_exact_two_parent_merge_delivery(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "activation-merge"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/zycaskevin/Vault-Agent-Memory.git"],
        cwd=repo,
        check=True,
    )
    (repo / "README.md").write_text("base\n")
    for relative in mission.ACTIVATION_SDG_MODIFIED_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("base\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "protocol"], cwd=repo, check=True)
    protocol = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(["git", "switch", "-q", "-c", "activation"], cwd=repo, check=True)
    proof_raw = b'{"mission":"owner-confirmed"}\n'
    _write_activation_records(repo, proof_raw)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "activate"], cwd=repo, check=True)
    activation = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(["git", "switch", "-q", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "merge", "-q", "--no-ff", "--no-edit", activation],
        cwd=repo,
        check=True,
    )
    delivery = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    assert mission.validate_mission_activation_delivery(
        repo,
        protocol_base=protocol,
        mission_raw=proof_raw,
    ) == delivery

    (repo / "task-output.txt").write_text("governed descendant\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "task descendant"], cwd=repo, check=True)
    assert mission.validate_mission_activation_delivery(
        repo,
        protocol_base=protocol,
        mission_raw=proof_raw,
    ) == delivery
    assert mission.validate_mission_activation_candidate(
        repo,
        protocol_base=protocol,
        mission_raw=proof_raw,
    ) == ("active", delivery)

    subprocess.run(["git", "reset", "--hard", "-q", protocol], cwd=repo, check=True)
    (repo / "extra.txt").write_text("outside activation scope\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "extra"], cwd=repo, check=True)
    subprocess.run(
        ["git", "merge", "-q", "--no-ff", "--no-edit", activation],
        cwd=repo,
        check=True,
    )
    with pytest.raises(mission.Denied):
        mission.validate_mission_activation_delivery(
            repo,
            protocol_base=protocol,
            mission_raw=proof_raw,
        )
    with pytest.raises(mission.Denied):
        mission.validate_mission_activation_candidate(
            repo,
            protocol_base=protocol,
            mission_raw=proof_raw,
        )


def test_mission_activation_accepts_exact_sdg_review_records_only(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "activation-sdg-review"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/zycaskevin/Vault-Agent-Memory.git"],
        cwd=repo,
        check=True,
    )
    for relative in mission.ACTIVATION_SDG_MODIFIED_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("base\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "protocol"], cwd=repo, check=True)
    protocol = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(["git", "switch", "-q", "-c", "activation"], cwd=repo, check=True)
    proof_raw = b'{"mission":"owner-confirmed"}\n'
    _write_activation_records(repo, proof_raw)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "activate with review"], cwd=repo, check=True)
    topic = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(["git", "switch", "-q", "main"], cwd=repo, check=True)
    subprocess.run(["git", "merge", "-q", "--no-ff", "--no-edit", topic], cwd=repo, check=True)
    delivery = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    assert mission.validate_mission_activation_delivery(
        repo,
        protocol_base=protocol,
        mission_raw=proof_raw,
    ) == delivery

    subprocess.run(["git", "reset", "--hard", "-q", protocol], cwd=repo, check=True)
    subprocess.run(["git", "switch", "-q", "-C", "hostile"], cwd=repo, check=True)
    _write_activation_records(repo, proof_raw)
    (repo / "extra.txt").write_text("outside closed activation records\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "hostile activation"], cwd=repo, check=True)
    with pytest.raises(mission.Denied):
        mission.validate_mission_activation_delivery(
            repo,
            protocol_base=protocol,
            mission_raw=proof_raw,
        )


def test_mission_activation_denies_proof_without_sdg_review_records(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "activation-proof-only"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/zycaskevin/Vault-Agent-Memory.git"],
        cwd=repo,
        check=True,
    )
    for relative in mission.ACTIVATION_SDG_MODIFIED_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("base\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "protocol"], cwd=repo, check=True)
    protocol = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    proof_raw = b'{"mission":"owner-confirmed"}\n'
    proof = repo / mission.MISSION_PROOF_PATH
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_bytes(proof_raw)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "proof only"], cwd=repo, check=True)
    with pytest.raises(mission.Denied):
        mission.validate_mission_activation_delivery(
            repo,
            protocol_base=protocol,
            mission_raw=proof_raw,
        )


def test_required_read_snapshots_are_sorted_unique_mode_and_hash_bound() -> None:
    registry = _json(mission.SCOPE_REGISTRY_PATH)
    descriptor = next(item for item in registry["tasks"] if item["task"] == "T-020")
    snapshots = mission.required_read_files(ROOT, descriptor)
    assert [item["path"] for item in snapshots] == descriptor["required_read_paths"]
    assert all(item["mode"] == "100644" for item in snapshots)
    assert snapshots == sorted(snapshots, key=lambda item: item["path"])
    assert all(item["sha256"] == hashlib.sha256(_raw(item["path"])).hexdigest() for item in snapshots)

    mutated = copy.deepcopy(descriptor)
    mutated["required_read_paths"].append(mutated["required_read_paths"][0])
    with pytest.raises(mission.Denied):
        mission._validate_registry_entry(mutated, _raw(mission.TASKS_PATH))


def test_task_proof_denies_retained_required_read_drift() -> None:
    _contract, mission_proof, mission_raw, _descriptor, proof, raw = (
        _t020_authorization_fixture()
    )
    assert validator.validate_task_authorization_value(
        proof,
        raw,
        ROOT,
        mission_proof=mission_proof,
        mission_raw=mission_raw,
    )["status"] == "PASS"
    retained = {
        item["path"]: _raw(item["path"])
        for item in proof["required_read_files"]
    }
    retained[proof["required_read_files"][0]["path"]] += b"drift"
    with pytest.raises(mission.Denied):
        validator.validate_task_authorization_value(
            proof,
            raw,
            ROOT,
            mission_proof=mission_proof,
            mission_raw=mission_raw,
            retained=retained,
        )


def test_source_review_binds_retained_required_reads_outputs_and_proof() -> None:
    _contract, mission_proof, mission_raw, descriptor, proof, proof_raw = (
        _t020_authorization_fixture()
    )
    output_path = descriptor["completion_repo_relative_paths"][0]
    output_raw = b"reviewed T-020 output\n"
    retained = {
        **_authority_snapshot(),
        mission.MISSION_PROOF_PATH: mission_raw,
        proof["proof_repo_relative_path"]: proof_raw,
        output_path: output_raw,
        **{item["path"]: _raw(item["path"]) for item in proof["required_read_files"]},
    }
    reviewed_outputs = [
        {
            "mode": "100644",
            "path": output_path,
            "sha256": hashlib.sha256(output_raw).hexdigest(),
        }
    ]
    reviewed_changes = sorted(
        [
            {
                "action": "add",
                "mode": "100644",
                "path": proof["proof_repo_relative_path"],
                "sha256": hashlib.sha256(proof_raw).hexdigest(),
            },
            {"action": "add", **reviewed_outputs[0]},
        ],
        key=lambda item: item["path"],
    )
    review = {
        "schema_version": 5,
        "artifact_kind": "subject-task-source-review-v5",
        "status": "PASS",
        "authorized_task": "T-020",
        "mission_id": mission_proof["mission_id"],
        "implementation_base_commit": proof["implementation_base_commit"],
        "proof_sha256": hashlib.sha256(proof_raw).hexdigest(),
        "builder_principal": "agent:builder",
        "reviewer_principal": "agent:reviewer",
        "required_read_files": proof["required_read_files"],
        "progress_before_sequence": 7,
        "progress_before_sha256": "8" * 64,
        "reviewed_at_utc": "2026-08-13T00:00:02Z",
        "reviewed_outputs": reviewed_outputs,
        "reviewed_changes": reviewed_changes,
        "reviewed_change_set_sha256": hashlib.sha256(
            mission.canonical(reviewed_changes, newline=False)
        ).hexdigest(),
        "verification_results": [
            {
                "exit_code": 0,
                "status": "PASS",
                "step_id": descriptor["verification_steps"][0]["step_id"],
                "stderr_sha256": hashlib.sha256(b"").hexdigest(),
                "stdout_sha256": hashlib.sha256(b"passed\n").hexdigest(),
            }
        ],
        "p0": 0,
        "p1": 0,
        "p2": 0,
        "verdict": "PASS",
    }
    review["source_review_id"] = hashlib.sha256(
        mission.canonical(review, newline=False)
    ).hexdigest()
    review_raw = mission.canonical(review)
    assert validator.validate_source_review_value(
        review,
        review_raw,
        ROOT,
        "T-020",
        proof=proof,
        proof_raw=proof_raw,
        retained=retained,
    )["status"] == "PASS"

    drifted = dict(retained)
    drifted[proof["required_read_files"][0]["path"]] += b"drift"
    with pytest.raises(mission.Denied):
        validator.validate_source_review_value(
            review,
            review_raw,
            ROOT,
            "T-020",
            proof=proof,
            proof_raw=proof_raw,
            retained=drifted,
        )


def test_source_review_replays_preliminary_commit_after_later_output_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "historical-source"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    proof_path = "proof.json"
    output_path = "vault/subject_service.py"
    proof_raw = b"proof\n"
    output_raw = b"T-013 reviewed bytes\n"
    for path, raw in ((proof_path, proof_raw), (output_path, output_raw)):
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "T-013 preliminary"], cwd=repo, check=True)
    preliminary = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    (repo / output_path).write_bytes(b"T-014 later bytes\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "T-014"], cwd=repo, check=True)
    descriptor = {
        "completion_repo_relative_paths": [output_path],
        "verification_steps": [{"step_id": "verify"}],
        "writable_path_policies": [
            {"action": "modify", "final_mode": "0644", "path": output_path}
        ],
    }
    proof = {
        "derived_at_utc": "2026-08-13T00:00:01Z",
        "implementation_base_commit": "git:" + "1" * 40,
        "proof_repo_relative_path": proof_path,
        "progress_sequence": 7,
        "required_read_files": [],
    }
    monkeypatch.setattr(
        validator,
        "validate_task_authorization_value",
        lambda *_args, **_kwargs: {
            "authorization_id": "2" * 64,
            "descriptor": descriptor,
            "implementation_base_commit": proof["implementation_base_commit"],
            "mission_id": "3" * 64,
        },
    )
    changes = [
        {
            "action": "add",
            "mode": "100644",
            "path": proof_path,
            "sha256": hashlib.sha256(proof_raw).hexdigest(),
        },
        {
            "action": "modify",
            "mode": "100644",
            "path": output_path,
            "sha256": hashlib.sha256(output_raw).hexdigest(),
        },
    ]
    changes.sort(key=lambda item: item["path"])
    review = {
        "schema_version": 5,
        "artifact_kind": "subject-task-source-review-v5",
        "status": "PASS",
        "authorized_task": "T-013",
        "mission_id": "3" * 64,
        "implementation_base_commit": proof["implementation_base_commit"],
        "proof_sha256": hashlib.sha256(proof_raw).hexdigest(),
        "builder_principal": "agent:builder",
        "reviewer_principal": "agent:reviewer",
        "required_read_files": [],
        "progress_before_sequence": 8,
        "progress_before_sha256": "4" * 64,
        "reviewed_at_utc": "2026-08-13T00:00:02Z",
        "reviewed_outputs": [
            {
                "mode": "100644",
                "path": output_path,
                "sha256": hashlib.sha256(output_raw).hexdigest(),
            }
        ],
        "reviewed_changes": changes,
        "reviewed_change_set_sha256": hashlib.sha256(
            mission.canonical(changes, newline=False)
        ).hexdigest(),
        "verification_results": [
            {
                "exit_code": 0,
                "status": "PASS",
                "step_id": "verify",
                "stderr_sha256": hashlib.sha256(b"").hexdigest(),
                "stdout_sha256": hashlib.sha256(b"pass\n").hexdigest(),
            }
        ],
        "p0": 0,
        "p1": 0,
        "p2": 0,
        "verdict": "PASS",
    }
    review["source_review_id"] = hashlib.sha256(
        mission.canonical(review, newline=False)
    ).hexdigest()
    assert validator.validate_source_review_value(
        review,
        mission.canonical(review),
        repo,
        "T-013",
        proof=proof,
        proof_raw=proof_raw,
        historical_head=preliminary,
    )["status"] == "PASS"


def test_fresh_active_mission_denies_clock_rollback(monkeypatch: pytest.MonkeyPatch) -> None:
    proof = {"mission_id": "1" * 64}
    raw = mission.canonical(proof)
    monkeypatch.setattr(updater, "_mission", lambda _root, _now: (proof, raw))
    moments = iter(
        [
            datetime(2026, 8, 13, 0, 0, 2, tzinfo=timezone.utc),
            datetime(2026, 8, 13, 0, 0, 1, tzinfo=timezone.utc),
        ]
    )
    runtime = updater.writer.Runtime(now=lambda: next(moments))
    _proof, _raw_value, first = updater._fresh_active_mission(ROOT, runtime)
    with pytest.raises(mission.Denied):
        updater._fresh_active_mission(ROOT, runtime, expected_raw=raw, previous_utc=first)


def test_revoked_history_is_ci_valid_but_not_active(monkeypatch: pytest.MonkeyPatch) -> None:
    proof = {"active_from_utc": "2026-08-13T00:00:00Z", "mission_id": "1" * 64}
    proof_raw = mission.canonical(proof)
    revocation = {"revocation_id": "2" * 64}
    revocation_raw = mission.canonical(revocation)
    progress = {
        "tasks": {f"T-{number:03d}": "PENDING" for number in range(1, 34)},
        "events": [{"at_utc": "2026-08-13T00:00:00Z"}],
    }
    monkeypatch.setattr(mission, "load_contract", lambda _root: ({}, b"{}\n"))
    monkeypatch.setattr(mission, "load_registry", lambda _root, _contract: ({}, b"{}\n"))
    monkeypatch.setattr(mission, "_load_progress", lambda _root: (progress, b"progress\n"))
    monkeypatch.setattr(
        validator,
        "_entry_exists",
        lambda _root, path: path in {mission.MISSION_PROOF_PATH, mission.REVOCATION_PATH},
    )
    monkeypatch.setattr(
        mission,
        "_read",
        lambda _root, path, **_kwargs: (
            proof_raw if path == mission.MISSION_PROOF_PATH else revocation_raw
        ),
    )
    monkeypatch.setattr(
        validator,
        "validate_mission_proof_value",
        lambda *_args, **_kwargs: {
            "mission_id": proof["mission_id"],
            "protocol_base_commit": "git:" + "3" * 40,
        },
    )
    monkeypatch.setattr(mission, "check_active_protocol_ancestry", lambda *_args: None)
    activation_calls: list[tuple[str, bytes]] = []
    monkeypatch.setattr(
        mission,
        "validate_mission_activation_delivery",
        lambda _root, *, protocol_base, mission_raw: (
            activation_calls.append((protocol_base, mission_raw)) or "4" * 40
        ),
    )
    monkeypatch.setattr(validator, "validate_ledger_value", lambda *_args: {"sequence": 6})
    monkeypatch.setattr(validator, "validate_revocation_value", lambda *_args: {"status": "REVOKED"})
    monkeypatch.setattr(
        validator, "validate_revocation_progress", lambda *_args: progress
    )
    assert validator.validate(ROOT, now_utc="2026-08-14T00:00:00Z") == {
        "active": False,
        "authorized_tasks": 0,
        "mission_id": proof["mission_id"],
        "mission_state": "REVOKED",
        "sequence": 6,
        "status": "PASS",
    }
    assert activation_calls == [("3" * 40, proof_raw)]
    progress["tasks"]["T-004"] = "IN_PROGRESS"
    with pytest.raises(mission.Denied):
        validator.validate(ROOT, now_utc="2026-08-14T00:00:00Z")


def test_t033_candidate_requires_attester_owned_exact_final_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tasks = {f"T-{number:03d}": "COMPLETED" for number in range(1, 34)}
    tasks["T-032"] = "BLOCKED"
    ref = {
        "kind": "repo_file",
        "path": "specs/subject-distillation/evidence/0dc10cfc4a429662/attestation.json",
        "sha256": "4" * 64,
    }
    candidate = {
        "tasks": tasks,
        "events": [
            {"sequence": 6, "task_id": "T-003"},
            {
                "sequence": 7,
                "task_id": "T-033",
                "from": "IN_PROGRESS",
                "to": "COMPLETED",
                "evidence_refs": [ref],
            },
        ],
    }
    monkeypatch.setattr(
        validator, "validate_ledger_value", lambda *_args, **_kwargs: {"sequence": 7}
    )
    retained = {
        **_authority_snapshot(),
        mission.MISSION_PROOF_PATH: mission.canonical({"trust_root": []}),
        ref["path"]: b"attestation\n",
    }
    ref["sha256"] = hashlib.sha256(retained[ref["path"]]).hexdigest()
    retained[mission.PROGRESS_PATH] = mission.canonical(candidate)
    result = validator.validate_t033_candidate(
        ROOT,
        candidate,
        expected_attestation_ref=ref,
        retained_snapshot=retained,
    )
    assert result["status"] == "PASS"
    bad = copy.deepcopy(ref)
    bad["sha256"] = "5" * 64
    with pytest.raises(mission.Denied):
        validator.validate_t033_candidate(
            ROOT,
            candidate,
            expected_attestation_ref=bad,
            retained_snapshot=retained,
        )
    missing_attestation = dict(retained)
    missing_attestation.pop(ref["path"])
    with pytest.raises(mission.Denied):
        validator.validate_t033_candidate(
            ROOT,
            candidate,
            expected_attestation_ref=ref,
            retained_snapshot=missing_attestation,
        )


def test_retained_progress_core_never_reopens_live_repository_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _raw(mission.PROGRESS_PATH)
    progress = json.loads(raw)
    monkeypatch.setattr(
        validator.progress_writer,
        "_inputs",
        lambda *_args: pytest.fail("live progress inputs reopened"),
    )
    monkeypatch.setattr(
        validator.progress_core,
        "validate_value",
        lambda *_args, **_kwargs: pytest.fail("live progress validator called"),
    )
    monkeypatch.setattr(
        mission,
        "_read",
        lambda *_args, **_kwargs: pytest.fail("live repository path reopened"),
    )
    assert validator.validate_ledger_value(
        progress,
        ROOT,
        retained={mission.PROGRESS_PATH: raw},
    ) == {"proofs": 0, "sequence": 6, "status": "PASS"}


def test_historical_completion_review_binds_actual_ledger_prefix() -> None:
    ledger = copy.deepcopy(_json(mission.PROGRESS_PATH))
    ledger["tasks"]["T-004"] = "IN_PROGRESS"
    ledger["events"].append(
        {
            "sequence": 7,
            "task_id": "T-004",
            "from": "PENDING",
            "to": "IN_PROGRESS",
            "at_utc": "2026-08-13T00:00:01Z",
            "evidence_refs": [],
            "blocker": None,
        }
    )
    ledger["updated_at_utc"] = "2026-08-13T00:00:01Z"
    source_review = {
        "progress_before_sequence": 7,
        "progress_before_sha256": hashlib.sha256(
            mission.canonical(validator._prefix(ledger, 7))
        ).hexdigest(),
    }
    validator._validate_review_progress_prefix(source_review, ledger, 7)
    source_review["progress_before_sha256"] = "0" * 64
    with pytest.raises(mission.Denied):
        validator._validate_review_progress_prefix(source_review, ledger, 7)


def test_progress_pending_is_allowed_only_for_exact_writer_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = {
        "specs/subject-distillation/task-authorizations/T-004.json": "add"
    }
    monkeypatch.setattr(
        updater,
        "_status",
        lambda _root: {**expected, updater.PROGRESS_PENDING_PATH: "add"},
    )
    assert updater._require_status(
        ROOT,
        expected,
        progress_pending=True,
    ) is True
    monkeypatch.setattr(
        updater,
        "_status",
        lambda _root: {**expected, updater.PROGRESS_PENDING_PATH: "modify"},
    )
    with pytest.raises(mission.Denied):
        updater._require_status(ROOT, expected, progress_pending=True)
    monkeypatch.setattr(
        updater,
        "_status",
        lambda _root: {**expected, "rogue.txt": "add"},
    )
    with pytest.raises(mission.Denied):
        updater._require_status(ROOT, expected, progress_pending=None)


@pytest.mark.parametrize(
    ("state", "target", "artifact"),
    [
        ("PENDING", "IN_PROGRESS", "proof"),
        ("IN_PROGRESS", "COMPLETED", "review"),
    ],
)
def test_expiry_or_revocation_discards_only_exact_unpublished_transition(
    monkeypatch: pytest.MonkeyPatch,
    state: str,
    target: str,
    artifact: str,
) -> None:
    current = copy.deepcopy(_json(mission.PROGRESS_PATH))
    if state == "IN_PROGRESS":
        current["tasks"]["T-004"] = "IN_PROGRESS"
        current["events"].append(
            {
                "sequence": 7,
                "task_id": "T-004",
                "from": "PENDING",
                "to": "IN_PROGRESS",
                "at_utc": "2026-08-13T00:00:01Z",
                "evidence_refs": [],
                "blocker": None,
            }
        )
        current["updated_at_utc"] = "2026-08-13T00:00:01Z"
    proof = {"derived_at_utc": "2026-08-13T00:00:00Z"}
    proof_raw = mission.canonical(proof)
    review = {"review_id": "3" * 64}
    review_raw = mission.canonical(review)
    refs = [{"kind": "opaque", "id": "mission-v5:exact"}]
    pending = copy.deepcopy(current)
    pending["tasks"]["T-004"] = target
    pending["events"].append(
        {
            "sequence": len(pending["events"]) + 1,
            "task_id": "T-004",
            "from": state,
            "to": target,
            "at_utc": "2026-08-13T00:00:02Z",
            "evidence_refs": refs,
            "blocker": None,
        }
    )
    pending["updated_at_utc"] = "2026-08-13T00:00:02Z"
    monkeypatch.setattr(updater.writer, "_pending_value", lambda _paths: pending)
    monkeypatch.setattr(
        mission,
        "_read",
        lambda _root, path: review_raw if path.endswith(".review.json") else proof_raw,
    )
    monkeypatch.setattr(validator, "validate_task_authorization_value", lambda *_a, **_k: {})
    monkeypatch.setattr(validator, "validate_completion_review_value", lambda *_a, **_k: {})
    monkeypatch.setattr(validator, "_start_refs", lambda *_a: refs)
    monkeypatch.setattr(validator, "_completion_refs", lambda *_a: refs)
    discarded: list[tuple[str, bytes]] = []
    status_checks: list[tuple[dict[str, str], bool | None]] = []
    monkeypatch.setattr(
        updater,
        "_require_status",
        lambda _root, expected, *, progress_pending: status_checks.append(
            (expected, progress_pending)
        ),
    )
    monkeypatch.setattr(updater, "_audit_exact_repo_file", lambda *_a: None)
    monkeypatch.setattr(
        updater.writer,
        "_discard_matching_pending",
        lambda _paths, raw, _runtime: discarded.append(("pending", raw)),
    )
    monkeypatch.setattr(
        updater,
        "_discard_exact_repo_file",
        lambda _root, path, raw: discarded.append((path, raw)),
    )
    assert updater._discard_invalidated_active_pending(
        updater.writer._paths(ROOT),
        current,
        task="T-004",
        runtime=updater.writer.Runtime(),
    )
    assert discarded[0] == ("pending", mission.canonical(pending))
    assert discarded[1][0].endswith(
        ".review.json" if artifact == "review" else "T-004.json"
    )
    assert [pending for _expected, pending in status_checks] == [
        True,
        True,
        False,
        False,
    ]


def test_invalidated_pending_cleanup_denies_extra_dirt_without_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "cleanup-zero-mutation"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    progress = repo / mission.PROGRESS_PATH
    progress.parent.mkdir(parents=True)
    current = copy.deepcopy(_json(mission.PROGRESS_PATH))
    progress.write_bytes(mission.canonical(current))
    subprocess.run(["git", "add", mission.PROGRESS_PATH], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "progress"], cwd=repo, check=True)

    proof_path = updater._task_proof_path("T-004")
    proof_file = repo / proof_path
    proof_file.parent.mkdir(parents=True, exist_ok=True)
    proof_raw = mission.canonical({"derived_at_utc": "2026-08-13T00:00:00Z"})
    proof_file.write_bytes(proof_raw)
    proof_file.chmod(0o644)
    refs = [{"kind": "opaque", "id": "mission-v5:exact"}]
    pending = copy.deepcopy(current)
    pending["tasks"]["T-004"] = "IN_PROGRESS"
    pending["events"].append(
        {
            "sequence": len(pending["events"]) + 1,
            "task_id": "T-004",
            "from": "PENDING",
            "to": "IN_PROGRESS",
            "at_utc": "2026-08-13T00:00:02Z",
            "evidence_refs": refs,
            "blocker": None,
        }
    )
    pending["updated_at_utc"] = "2026-08-13T00:00:02Z"
    pending_file = repo / updater.PROGRESS_PENDING_PATH
    pending_file.write_bytes(mission.canonical(pending))
    pending_file.chmod(0o600)
    rogue = repo / "rogue.txt"
    rogue.write_text("must make cleanup fail before unlink\n")
    before = {
        path: (path.read_bytes(), path.stat())
        for path in (proof_file, pending_file, rogue)
    }

    monkeypatch.chdir(repo)
    monkeypatch.setattr(updater.writer, "_pending_value", lambda _paths: pending)
    monkeypatch.setattr(
        validator, "validate_task_authorization_value", lambda *_a, **_k: {}
    )
    monkeypatch.setattr(validator, "_start_refs", lambda *_a: refs)
    with pytest.raises(mission.Denied):
        updater._discard_invalidated_active_pending(
            updater.writer._paths(repo),
            current,
            task="T-004",
            runtime=updater.writer.Runtime(),
        )
    for path, (raw, identity) in before.items():
        after = path.stat()
        assert path.read_bytes() == raw
        assert (after.st_dev, after.st_ino, after.st_mode, after.st_nlink) == (
            identity.st_dev,
            identity.st_ino,
            identity.st_mode,
            identity.st_nlink,
        )


def test_orphan_cleanup_rechecks_status_after_validation_before_unlink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = copy.deepcopy(_json(mission.PROGRESS_PATH))
    proof = {
        "derived_at_utc": "2026-08-13T00:00:00Z",
        "progress_sequence": len(current["events"]),
        "progress_sha256": hashlib.sha256(mission.canonical(current)).hexdigest(),
    }
    proof_raw = mission.canonical(proof)
    proof_path = updater._task_proof_path("T-004")
    expected = {
        mission.REVOCATION_PATH: "add",
        proof_path: "add",
    }
    revocation_raw = b'{"revocation_id":"' + b"4" * 64 + b'"}\n'
    state = {"injected": False}
    monkeypatch.setattr(
        updater,
        "_status",
        lambda _root: (
            {**expected, "rogue.txt": "add"} if state["injected"] else expected
        ),
    )
    monkeypatch.setattr(mission, "_read", lambda *_a: proof_raw)
    monkeypatch.setattr(
        validator, "validate_task_authorization_value", lambda *_a, **_k: {}
    )
    guard_events: list[str] = []

    class Guard:
        def snapshot(self) -> dict[str, bytes]:
            return {mission.REVOCATION_PATH: revocation_raw}

        def audit(self) -> None:
            guard_events.append("audit")

        def close(self) -> None:
            guard_events.append("close")

    monkeypatch.setattr(mission, "open_paths_guard", lambda *_a: Guard())

    def inject_after_artifact_audit(*_args) -> None:
        state["injected"] = True

    monkeypatch.setattr(updater, "_audit_exact_repo_file", inject_after_artifact_audit)
    monkeypatch.setattr(
        updater,
        "_discard_exact_repo_file",
        lambda *_a: pytest.fail("orphan must not be unlinked after status drift"),
    )
    with pytest.raises(mission.Denied):
        updater._discard_orphaned_active_artifact(
            ROOT,
            current,
            task="T-004",
            allowed_status={mission.REVOCATION_PATH: "add"},
            expected_revocation_raw=revocation_raw,
        )
    assert guard_events == ["audit", "close"]


def test_revocation_swap_before_cleanup_guard_denies_without_discard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_raw = b'{"revocation_id":"' + b"5" * 64 + b'"}\n'
    replacement_raw = b'{"revocation_id":"' + b"6" * 64 + b'"}\n'
    closed: list[bool] = []

    class Guard:
        def snapshot(self) -> dict[str, bytes]:
            return {mission.REVOCATION_PATH: replacement_raw}

        def close(self) -> None:
            closed.append(True)

    monkeypatch.setattr(mission, "open_paths_guard", lambda *_a: Guard())
    current = copy.deepcopy(_json(mission.PROGRESS_PATH))
    proof = {
        "progress_sequence": len(current["events"]),
        "progress_sha256": hashlib.sha256(mission.canonical(current)).hexdigest(),
    }
    proof_raw = mission.canonical(proof)
    proof_path = updater._task_proof_path("T-004")
    monkeypatch.setattr(
        updater,
        "_status",
        lambda _root: {
            mission.REVOCATION_PATH: "add",
            proof_path: "add",
        },
    )
    monkeypatch.setattr(mission, "_read", lambda *_a: proof_raw)
    monkeypatch.setattr(
        validator, "validate_task_authorization_value", lambda *_a, **_k: {}
    )
    monkeypatch.setattr(
        updater,
        "_audit_exact_repo_file",
        lambda *_a: pytest.fail("artifact audit must follow exact revocation binding"),
    )
    monkeypatch.setattr(
        updater,
        "_discard_exact_repo_file",
        lambda *_a: pytest.fail("revocation swap must not discard artifact"),
    )
    with pytest.raises(mission.Denied):
        updater._discard_orphaned_active_artifact(
            ROOT,
            current,
            task="T-004",
            allowed_status={mission.REVOCATION_PATH: "add"},
            expected_revocation_raw=expected_raw,
        )
    assert closed == [True]


@pytest.mark.parametrize("delivery", ["WORKTREE", "a" * 40])
def test_t032_post_replace_retry_is_recovered_without_second_event(
    monkeypatch: pytest.MonkeyPatch, delivery: str
) -> None:
    current = copy.deepcopy(_json(mission.PROGRESS_PATH))
    current["tasks"]["T-032"] = "BLOCKED"
    current["events"].append(
        {
            "sequence": len(current["events"]) + 1,
            "task_id": "T-032",
            "from": "PENDING",
            "to": "BLOCKED",
            "at_utc": "2026-08-13T00:00:02Z",
            "evidence_refs": [],
            "blocker": "OPERATIONAL_ACTION_REQUIRED",
        }
    )
    current["updated_at_utc"] = "2026-08-13T00:00:02Z"
    anchor = "b" * 40
    monkeypatch.setattr(
        validator,
        "validate_ledger_value",
        lambda value, _root, **_kwargs: {
            "delivery_anchor": delivery if len(value["events"]) == len(current["events"]) else anchor,
            "sequence": len(value["events"]),
            "status": "PASS",
        },
    )
    monkeypatch.setattr(
        mission, "validate_progress_only_delivery", lambda *_a, **_k: delivery
    )
    expected_head = anchor if delivery == "WORKTREE" else delivery
    monkeypatch.setattr(
        mission,
        "_git",
        lambda _root, *_args: (expected_head + "\n").encode(),
    )
    statuses: list[dict[str, str]] = []
    monkeypatch.setattr(
        updater,
        "_require_status",
        lambda _root, expected, *, progress_pending: statuses.append(expected),
    )
    result = updater._recover_t032_block(ROOT, current)
    assert result == {
        "sequence": len(current["events"]),
        "status": "RECOVERED_COMMITTED",
        "task_id": "T-032",
    }
    assert statuses == [
        {mission.PROGRESS_PATH: "modify"} if delivery == "WORKTREE" else {}
    ]


def test_expiry_block_post_replace_retry_is_recovered_without_second_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = copy.deepcopy(_json(mission.PROGRESS_PATH))
    current["tasks"]["T-004"] = "IN_PROGRESS"
    current["events"].append(
        {
            "sequence": len(current["events"]) + 1,
            "task_id": "T-004",
            "from": "PENDING",
            "to": "IN_PROGRESS",
            "at_utc": "2026-08-13T00:00:01Z",
            "evidence_refs": [],
            "blocker": None,
        }
    )
    current["tasks"]["T-004"] = "BLOCKED"
    current["events"].append(
        {
            "sequence": len(current["events"]) + 1,
            "task_id": "T-004",
            "from": "IN_PROGRESS",
            "to": "BLOCKED",
            "at_utc": "2026-08-13T00:00:03Z",
            "evidence_refs": [],
            "blocker": "MISSION_EXPIRED",
        }
    )
    current["updated_at_utc"] = "2026-08-13T00:00:03Z"
    validated: list[int] = []
    monkeypatch.setattr(
        validator,
        "validate_ledger_value",
        lambda value, _root: validated.append(len(value["events"])) or {"status": "PASS"},
    )
    monkeypatch.setattr(
        updater,
        "_status",
        lambda _root: {mission.PROGRESS_PATH: "modify"},
    )
    monkeypatch.setattr(
        updater,
        "_validated_task_proof",
        lambda _root, _task: ({"authorized_task": "T-004"}, b"proof\n"),
    )
    monkeypatch.setattr(
        mission,
        "validate_authority_block_delivery",
        lambda *_a, **_k: "WORKTREE",
    )
    result = updater._recover_authority_block(
        ROOT,
        current,
        task="T-004",
        blocker="MISSION_EXPIRED",
        lower_utc="2026-08-13T00:00:02Z",
        now_utc="2026-08-13T00:00:04Z",
        allowed_status={},
        revocation=None,
        revocation_raw=None,
    )
    assert result == {
        "sequence": len(current["events"]),
        "status": "RECOVERED_COMMITTED",
        "task_id": "T-004",
    }
    assert validated == [len(current["events"]) - 1, len(current["events"])]


def test_public_block_commands_route_terminal_readback_without_republish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = copy.deepcopy(_json(mission.PROGRESS_PATH))
    t032 = copy.deepcopy(current)
    t032["tasks"]["T-032"] = "BLOCKED"
    t004 = copy.deepcopy(current)
    t004["tasks"]["T-004"] = "BLOCKED"
    marker_t032 = {
        "sequence": 7,
        "status": "RECOVERED_COMMITTED",
        "task_id": "T-032",
    }
    marker_t004 = {
        "sequence": 8,
        "status": "RECOVERED_COMMITTED",
        "task_id": "T-004",
    }
    monkeypatch.setattr(
        updater.writer,
        "_inputs",
        lambda _paths: ({"baseline_id": "0dc10cfc4a429662"}, "tasks"),
    )
    monkeypatch.setattr(
        mission.legacy.v1,
        "_authorization_lock",
        lambda *_a, **_k: nullcontext(),
    )
    monkeypatch.setattr(updater.writer, "_time", lambda _runtime: "2026-08-13T00:00:04Z")
    monkeypatch.setattr(updater, "_mission", lambda *_a: ({}, b"mission\n"))
    monkeypatch.setattr(updater, "_current", lambda _root: t032)
    monkeypatch.setattr(updater, "_recover_t032_block", lambda *_a: marker_t032)
    monkeypatch.setattr(
        updater.writer,
        "_publish",
        lambda *_a, **_k: pytest.fail("terminal retry must not publish"),
    )
    assert updater.block_t032() == marker_t032

    proof = {
        "active_from_utc": "2026-08-13T00:00:00Z",
        "mission_not_after_utc": "2026-08-13T00:00:02Z",
    }
    monkeypatch.setattr(validator, "_load_mission_proof", lambda _root: (proof, b"proof\n"))
    monkeypatch.setattr(validator, "validate_mission_proof_value", lambda *_a, **_k: {})
    monkeypatch.setattr(validator, "_entry_exists", lambda *_a: False)
    monkeypatch.setattr(updater, "_current", lambda _root: t004)
    monkeypatch.setattr(updater, "_status", lambda _root: {})
    monkeypatch.setattr(
        updater,
        "_recover_authority_block",
        lambda *_a, **_k: marker_t004,
    )
    assert updater.block_authority("T-004") == marker_t004


@pytest.mark.parametrize(
    ("current_state", "target"),
    [("PENDING", "IN_PROGRESS"), ("IN_PROGRESS", "COMPLETED")],
)
def test_start_and_completion_reuse_exact_pending_event_bytes(
    monkeypatch: pytest.MonkeyPatch,
    current_state: str,
    target: str,
) -> None:
    current = copy.deepcopy(_json(mission.PROGRESS_PATH))
    if current_state == "IN_PROGRESS":
        current["tasks"]["T-004"] = "IN_PROGRESS"
        current["events"].append(
            {
                "sequence": 7,
                "task_id": "T-004",
                "from": "PENDING",
                "to": "IN_PROGRESS",
                "at_utc": "2026-08-13T00:00:01Z",
                "evidence_refs": [],
                "blocker": None,
            }
        )
        current["updated_at_utc"] = "2026-08-13T00:00:01Z"
    refs = [{"kind": "opaque", "id": "mission-v5:test-ref"}]
    pending = copy.deepcopy(current)
    pending["tasks"]["T-004"] = target
    pending["events"].append(
        {
            "sequence": len(pending["events"]) + 1,
            "task_id": "T-004",
            "from": current_state,
            "to": target,
            "at_utc": "2026-08-13T00:00:02Z",
            "evidence_refs": refs,
            "blocker": None,
        }
    )
    pending["updated_at_utc"] = "2026-08-13T00:00:02Z"
    monkeypatch.setattr(updater.writer, "_pending_value", lambda _paths: pending)
    assert updater._pending_transition_candidate(
        updater.writer._paths(ROOT),
        current,
        task="T-004",
        target=target,
        refs=refs,
    ) is pending
    altered = copy.deepcopy(pending)
    altered["events"][-1]["evidence_refs"] = []
    monkeypatch.setattr(updater.writer, "_pending_value", lambda _paths: altered)
    with pytest.raises(mission.Denied):
        updater._pending_transition_candidate(
            updater.writer._paths(ROOT),
            current,
            task="T-004",
            target=target,
            refs=refs,
        )


def test_t033_action_requires_fresh_active_nonrevoked_mission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {"tasks": {}, "events": []}
    ref = {"kind": "repo_file", "path": "attestation", "sha256": "1" * 64}
    proof = {"mission_id": "2" * 64}
    proof_raw = mission.canonical(proof)
    retained = {mission.MISSION_PROOF_PATH: proof_raw}
    calls: list[str] = []

    def active(*_args: object, now_utc: str, **_kwargs: object) -> dict[str, str]:
        calls.append(now_utc)
        if now_utc == "2026-11-11T00:00:00Z":
            raise mission.Denied
        return {"status": "PASS"}

    monkeypatch.setattr(validator, "validate_mission_proof_value", active)
    monkeypatch.setattr(validator, "_entry_exists", lambda *_args: False)
    monkeypatch.setattr(
        validator,
        "validate_t033_candidate",
        lambda *_args, **_kwargs: {"mission_replay_sha256": "3" * 64, "status": "PASS"},
    )
    assert validator.validate_t033_action(
        ROOT,
        candidate,
        expected_attestation_ref=ref,
        retained_snapshot=retained,
        _clock=iter(
            ["2026-08-13T00:00:01Z", "2026-08-13T00:00:02Z"]
        ).__next__,
    )["status"] == "PASS"
    assert calls == ["2026-08-13T00:00:01Z", "2026-08-13T00:00:02Z"]
    monkeypatch.setattr(validator, "_entry_exists", lambda *_args: True)
    with pytest.raises(mission.Denied):
        validator.validate_t033_action(
            ROOT,
            candidate,
            expected_attestation_ref=ref,
            retained_snapshot=retained,
            _clock=lambda: "2026-08-13T00:00:01Z",
        )
    monkeypatch.setattr(validator, "_entry_exists", lambda *_args: False)
    with pytest.raises(mission.Denied):
        validator.validate_t033_action(
            ROOT,
            candidate,
            expected_attestation_ref=ref,
            retained_snapshot=retained,
            _clock=iter(
                ["2026-08-13T00:00:01Z", "2026-11-11T00:00:00Z"]
            ).__next__,
        )
    with pytest.raises(mission.Denied):
        validator.validate_t033_action(
            ROOT,
            candidate,
            expected_attestation_ref=ref,
            retained_snapshot=retained,
            _clock=lambda: "2026-11-11T00:00:00Z",
        )


def test_preliminary_delivery_binds_exact_git_head_tree_diff_and_required_ci(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "delivery"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/zycaskevin/Vault-Agent-Memory.git"],
        cwd=repo,
        check=True,
    )
    workflow = repo / ".github/workflows/ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("name: CI\n")
    progress_path = mission.PROGRESS_PATH
    base_progress = repo / progress_path
    base_progress.parent.mkdir(parents=True)
    base_progress.write_bytes(b"progress-base\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=repo, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    proof_path = "specs/subject-distillation/task-authorizations/T-004.json"
    output_path = "out/result.json"
    contents = {
        proof_path: b"proof\n",
        output_path: b"output\n",
        progress_path: b"progress-before\n",
    }
    for relative, raw in contents.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "preliminary"], cwd=repo, check=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    tree = subprocess.check_output(
        ["git", "rev-parse", f"{head}^{{tree}}"], cwd=repo, text=True
    ).strip()
    descriptor = {
        "completion_repo_relative_paths": [output_path],
        "writable_path_policies": [
            {"action": "create", "final_mode": "0644", "path": output_path}
        ],
    }
    proof = {
        "implementation_base_commit": "git:" + base,
        "mission_id": "1" * 64,
        "proof_repo_relative_path": proof_path,
    }
    proof_raw = contents[proof_path]
    reviewed_changes = [
        {
            "action": "add",
            "mode": "100644",
            "path": path,
            "sha256": hashlib.sha256(contents[path]).hexdigest(),
        }
        for path in sorted([proof_path, output_path])
    ]
    source_review = {
        "source_review_id": "2" * 64,
        "reviewed_at_utc": "2026-08-13T00:01:00Z",
        "reviewed_changes": reviewed_changes,
        "progress_before_sha256": hashlib.sha256(contents[progress_path]).hexdigest(),
    }
    source_raw = mission.canonical(source_review)
    preliminary_changes = sorted(
        [
            *reviewed_changes,
            {
                "action": "modify",
                "mode": "100644",
                "path": progress_path,
                "sha256": hashlib.sha256(contents[progress_path]).hexdigest(),
            },
        ],
        key=lambda item: item["path"],
    )
    checks = [
        {
            "completed_at_utc": "2026-08-13T00:02:00Z",
            "conclusion": "SUCCESS",
            "head_commit": "git:" + head,
            "name": name,
            "run_attempt": 1,
            "run_id": f"github-run:{index}",
        }
        for index, name in enumerate(mission.REQUIRED_HOSTED_CHECKS, 1)
    ]
    delivery = {
        "schema_version": 5,
        "artifact_kind": "subject-task-preliminary-delivery-v5",
        "status": "PASS",
        "repository": "zycaskevin/Vault-Agent-Memory",
        "authorized_task": "T-004",
        "mission_id": proof["mission_id"],
        "mission_epoch": 1,
        "authorization_proof_sha256": hashlib.sha256(proof_raw).hexdigest(),
        "source_review_sha256": hashlib.sha256(source_raw).hexdigest(),
        "source_review_id": source_review["source_review_id"],
        "implementation_base_commit": proof["implementation_base_commit"],
        "preliminary_head_commit": "git:" + head,
        "preliminary_tree_git_oid": "git:" + tree,
        "pull_request_head_ref": "agent/t004-preliminary",
        "pull_request_head_repository": "zycaskevin/Vault-Agent-Memory",
        "pull_request_number": 458,
        "preliminary_changes": preliminary_changes,
        "preliminary_change_set_sha256": hashlib.sha256(
            mission.canonical(preliminary_changes, newline=False)
        ).hexdigest(),
        "workflow": ".github/workflows/ci.yml",
        "workflow_sha256": hashlib.sha256(workflow.read_bytes()).hexdigest(),
        "required_checks": checks,
        "required_checks_sha256": hashlib.sha256(
            mission.canonical(checks, newline=False)
        ).hexdigest(),
        "readback_at_utc": "2026-08-13T00:03:00Z",
        "readback_principal": "github-actions:readback",
    }
    delivery["delivery_id"] = hashlib.sha256(
        mission.canonical(delivery, newline=False)
    ).hexdigest()
    monkeypatch.setattr(
        validator,
        "_descriptor",
        lambda _root, _task, **_kwargs: descriptor,
    )
    assert validator.validate_preliminary_delivery_value(
        delivery,
        mission.canonical(delivery),
        repo,
        "T-004",
        proof=proof,
        proof_raw=proof_raw,
        source_review=source_review,
        source_review_raw=source_raw,
    ) == {"delivery_id": delivery["delivery_id"], "status": "PASS"}

    (repo / "rogue-intermediate.txt").write_text("out of scope\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "rogue intermediate"], cwd=repo, check=True)
    (repo / "rogue-intermediate.txt").unlink()
    subprocess.run(["git", "add", "-u"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "revert rogue"], cwd=repo, check=True)
    rewritten = copy.deepcopy(delivery)
    rewritten_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    rewritten["preliminary_head_commit"] = "git:" + rewritten_head
    rewritten["preliminary_tree_git_oid"] = "git:" + subprocess.check_output(
        ["git", "rev-parse", f"{rewritten_head}^{{tree}}"], cwd=repo, text=True
    ).strip()
    for check in rewritten["required_checks"]:
        check["head_commit"] = rewritten["preliminary_head_commit"]
    rewritten["required_checks_sha256"] = hashlib.sha256(
        mission.canonical(rewritten["required_checks"], newline=False)
    ).hexdigest()
    rewritten.pop("delivery_id")
    rewritten["delivery_id"] = hashlib.sha256(
        mission.canonical(rewritten, newline=False)
    ).hexdigest()
    with pytest.raises(mission.Denied):
        validator.validate_preliminary_delivery_value(
            rewritten,
            mission.canonical(rewritten),
            repo,
            "T-004",
            proof=proof,
            proof_raw=proof_raw,
            source_review=source_review,
            source_review_raw=source_raw,
        )

    def resign(value: dict[str, object]) -> bytes:
        value.pop("delivery_id", None)
        value["required_checks_sha256"] = hashlib.sha256(
            mission.canonical(value["required_checks"], newline=False)
        ).hexdigest()
        value["delivery_id"] = hashlib.sha256(
            mission.canonical(value, newline=False)
        ).hexdigest()
        return mission.canonical(value)

    missing_check = copy.deepcopy(delivery)
    missing_check["required_checks"].pop()
    with pytest.raises(mission.Denied):
        validator.validate_preliminary_delivery_value(
            missing_check,
            resign(missing_check),
            repo,
            "T-004",
            proof=proof,
            proof_raw=proof_raw,
            source_review=source_review,
            source_review_raw=source_raw,
        )


    failed_check = copy.deepcopy(delivery)
    failed_check["required_checks"][0]["conclusion"] = "FAILURE"
    with pytest.raises(mission.Denied):
        validator.validate_preliminary_delivery_value(
            failed_check,
            resign(failed_check),
            repo,
            "T-004",
            proof=proof,
            proof_raw=proof_raw,
            source_review=source_review,
            source_review_raw=source_raw,
        )


    early_check = copy.deepcopy(delivery)
    early_check["required_checks"][0]["completed_at_utc"] = "2026-08-13T00:00:59Z"
    with pytest.raises(mission.Denied):
        validator.validate_preliminary_delivery_value(
            early_check,
            resign(early_check),
            repo,
            "T-004",
            proof=proof,
            proof_raw=proof_raw,
            source_review=source_review,
            source_review_raw=source_raw,
        )

    (repo / "extra.txt").write_text("unauthorized\n")
    subprocess.run(["git", "add", "extra.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "extra"], cwd=repo, check=True)
    bad = copy.deepcopy(delivery)
    bad_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    bad["preliminary_head_commit"] = "git:" + bad_head
    bad["preliminary_tree_git_oid"] = "git:" + subprocess.check_output(
        ["git", "rev-parse", f"{bad_head}^{{tree}}"], cwd=repo, text=True
    ).strip()
    for check in bad["required_checks"]:
        check["head_commit"] = "git:" + bad_head
    bad["required_checks_sha256"] = hashlib.sha256(
        mission.canonical(bad["required_checks"], newline=False)
    ).hexdigest()
    bad.pop("delivery_id")
    bad["delivery_id"] = hashlib.sha256(mission.canonical(bad, newline=False)).hexdigest()
    with pytest.raises(mission.Denied):
        validator.validate_preliminary_delivery_value(
            bad,
            mission.canonical(bad),
            repo,
            "T-004",
            proof=proof,
            proof_raw=proof_raw,
            source_review=source_review,
            source_review_raw=source_raw,
        )


def test_final_delivery_replays_exact_historical_review_and_progress(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "final-delivery"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/zycaskevin/Vault-Agent-Memory.git"],
        cwd=repo,
        check=True,
    )
    progress = repo / mission.PROGRESS_PATH
    progress.parent.mkdir(parents=True)
    progress.write_bytes(b"in-progress\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "preliminary"], cwd=repo, check=True)
    preliminary = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    review_path = "specs/subject-distillation/task-authorizations/T-013.review.json"
    review_raw = b"review\n"
    terminal_raw = b"completed T-013\n"
    review_file = repo / review_path
    review_file.parent.mkdir(parents=True, exist_ok=True)
    review_file.write_bytes(review_raw)
    progress.write_bytes(terminal_raw)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "complete T-013"], cwd=repo, check=True)
    final_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    unrelated = repo / "vault/subject_service.py"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("later T-014 bytes\n")
    progress.write_bytes(b"later progress\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "later task"], cwd=repo, check=True)
    assert mission.validate_final_delivery(
        repo,
        preliminary_head=preliminary,
        review_path=review_path,
        review_raw=review_raw,
        progress_raw=terminal_raw,
    ) == final_commit
    with pytest.raises(mission.Denied):
        mission.validate_final_delivery(
            repo,
            preliminary_head=preliminary,
            review_path=review_path,
            review_raw=review_raw,
            progress_raw=b"forged\n",
        )


def test_t032_progress_only_delivery_is_immediate_and_direct_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "t032-delivery"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/zycaskevin/Vault-Agent-Memory.git"],
        cwd=repo,
        check=True,
    )
    progress = repo / mission.PROGRESS_PATH
    progress.parent.mkdir(parents=True)
    progress.write_bytes(b"T-031 final\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "T-031 final"], cwd=repo, check=True)
    anchor = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    blocked = b"T-032 blocked\n"
    progress.write_bytes(blocked)
    real_read = mission._read
    monkeypatch.setattr(
        mission,
        "_read",
        lambda root, path: (
            (root / path).read_bytes() if root == repo else real_read(root, path)
        ),
    )
    assert mission.validate_progress_only_delivery(
        repo,
        parent_commit=anchor,
        progress_raw=blocked,
    ) == "WORKTREE"
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "T-032 blocked"], cwd=repo, check=True)
    block_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    assert mission.validate_progress_only_delivery(
        repo,
        parent_commit=anchor,
        progress_raw=blocked,
    ) == block_commit

    subprocess.run(["git", "reset", "--hard", "-q", anchor], cwd=repo, check=True)
    (repo / "rogue.txt").write_text("out of scope\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "rogue"], cwd=repo, check=True)
    progress.write_bytes(blocked)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "late block"], cwd=repo, check=True)
    with pytest.raises(mission.Denied):
        mission.validate_progress_only_delivery(
            repo,
            parent_commit=anchor,
            progress_raw=blocked,
        )


def test_authority_block_delivery_binds_exact_task_execution_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "authority-block-delivery"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(
        [
            "git",
            "remote",
            "add",
            "origin",
            "https://github.com/zycaskevin/Vault-Agent-Memory.git",
        ],
        cwd=repo,
        check=True,
    )
    progress = repo / mission.PROGRESS_PATH
    progress.parent.mkdir(parents=True)
    progress.write_bytes(b"base\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=repo, check=True)
    base = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    proof_path = "specs/subject-distillation/task-authorizations/T-004.json"
    output_path = "vault/subject_model.py"
    descriptor = {
        "task": "T-004",
        "completion_repo_relative_paths": [output_path],
        "writable_path_policies": [
            {"action": "create", "final_mode": "0644", "path": output_path}
        ],
    }
    monkeypatch.setattr(mission, "load_contract", lambda *_a, **_k: ({}, b"contract\n"))
    monkeypatch.setattr(
        mission,
        "load_registry",
        lambda *_a, **_k: ({"tasks": [descriptor]}, b"registry\n"),
    )
    real_read = mission._read
    monkeypatch.setattr(
        mission,
        "_read",
        lambda root, path: (
            (root / path).read_bytes() if root == repo else real_read(root, path)
        ),
    )
    proof = {
        "authorized_task": "T-004",
        "implementation_base_commit": "git:" + base,
        "proof_repo_relative_path": proof_path,
    }
    proof_raw = mission.canonical(proof)
    proof_file = repo / proof_path
    proof_file.parent.mkdir(parents=True)
    proof_file.write_bytes(proof_raw)
    progress_before = b"in progress\n"
    progress.write_bytes(progress_before)
    output = repo / output_path
    output.parent.mkdir(parents=True)
    output.write_bytes(b"synthetic output\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "preliminary"], cwd=repo, check=True)
    preliminary = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", preliminary],
        cwd=repo,
        check=True,
    )
    assert mission.validate_active_task_anchor(
        repo,
        proof=proof,
        proof_raw=proof_raw,
        progress_raw=progress_before,
        allowed_status={},
    ) == preliminary
    progress_after = b"blocked\n"
    progress.write_bytes(progress_after)
    assert mission.validate_authority_block_delivery(
        repo,
        proof=proof,
        proof_raw=proof_raw,
        progress_before_raw=progress_before,
        progress_after_raw=progress_after,
        revocation_raw=None,
    ) == "WORKTREE"
    subprocess.run(["git", "add", mission.PROGRESS_PATH], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "blocked"], cwd=repo, check=True)
    blocked = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", blocked],
        cwd=repo,
        check=True,
    )
    assert mission.validate_authority_block_delivery(
        repo,
        proof=proof,
        proof_raw=proof_raw,
        progress_before_raw=progress_before,
        progress_after_raw=progress_after,
        revocation_raw=None,
    ) == blocked

    subprocess.run(["git", "reset", "--hard", "-q", base], cwd=repo, check=True)
    (repo / "rogue.txt").write_text("outside scope\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "rogue"], cwd=repo, check=True)
    (repo / "rogue.txt").unlink()
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "revert rogue"], cwd=repo, check=True)
    proof_file.parent.mkdir(parents=True, exist_ok=True)
    proof_file.write_bytes(proof_raw)
    progress.write_bytes(progress_before)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"synthetic output\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "late preliminary"], cwd=repo, check=True)
    late = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", late],
        cwd=repo,
        check=True,
    )
    with pytest.raises(mission.Denied):
        mission.validate_active_task_anchor(
            repo,
            proof=proof,
            proof_raw=proof_raw,
            progress_raw=progress_before,
            allowed_status={},
        )


def test_revocation_publication_is_atomic_and_byte_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "revocation"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "specs/subject-distillation/development-missions").mkdir(parents=True)
    monkeypatch.chdir(repo)
    raw = b'{"public":"revoked"}\n'
    assert mission.publish_revocation_record(repo, raw) is False
    final = repo / mission.REVOCATION_PATH
    assert final.read_bytes() == raw
    assert final.stat().st_mode & 0o777 == 0o644
    assert not (repo / mission.REVOCATION_PENDING_PATH).exists()
    assert mission.publish_revocation_record(repo, raw) is True
    assert final.read_bytes() == raw
