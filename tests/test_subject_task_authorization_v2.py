from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts/run_subject_task_authorization_v2.py"
VALIDATOR_PATH = REPO_ROOT / "scripts/validate_subject_task_authorization_v2.py"
STARTER_PATH = REPO_ROOT / "scripts/update_subject_task_progress_v2.py"
SCHEMA_PATH = REPO_ROOT / "specs/subject-distillation/task-authorization-v2.schema.json"
SCOPE_PATH = REPO_ROOT / "specs/subject-distillation/task-scopes/T-002.json"
PROGRESS_PATH = REPO_ROOT / "specs/subject-distillation/implementation-progress.json"
BASE_COMMIT = "ec841f32c0e735ba0fe027552ed712b1ecb2a440"
EXPECTED_TASK = "T-002"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runner():
    return _load(RUNNER_PATH, "subject_task_authorization_v2_test")


@pytest.fixture(scope="module")
def validator():
    return _load(VALIDATOR_PATH, "subject_task_authorization_v2_validator_test")


@pytest.fixture(autouse=True)
def _restore_repo_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(REPO_ROOT)


@pytest.fixture
def stable_temp_root() -> Path:
    preferred = Path("/private/tmp")
    parent = preferred if preferred.is_dir() else Path(tempfile.gettempdir())
    root = Path(tempfile.mkdtemp(prefix="subject-task-v2-test-", dir=parent))
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode()


def _t002_prestart_value() -> dict[str, object]:
    """Rebuild the immutable T-001-complete prefix for phase-neutral tests."""
    current = json.loads(PROGRESS_PATH.read_text())
    t001_events = [
        event for event in current["events"] if event["task_id"] == "T-001"
    ]
    assert len(t001_events) == 2
    assert t001_events[-1]["to"] == "COMPLETED"
    current["events"] = t001_events
    current["tasks"] = {task: "PENDING" for task in current["tasks"]}
    current["tasks"]["T-001"] = "COMPLETED"
    current["updated_at_utc"] = t001_events[-1]["at_utc"]
    contract = json.loads(
        (
            REPO_ROOT
            / "specs/subject-distillation/task-authorization-v2.contract.json"
        ).read_text()
    )
    assert hashlib.sha256(_canonical(t001_events)[:-1]).hexdigest() == (
        contract["activation"]["t001_events"]["sha256"]
    )
    assert hashlib.sha256(_canonical(current)).hexdigest() == (
        contract["activation"]["progress"]["sha256"]
    )
    return current


def _t002_prestart_snapshot(runner):
    raw = _canonical(_t002_prestart_value())
    info = os.stat(PROGRESS_PATH, follow_symlinks=False)
    return runner.TaskProgressSnapshot(
        sequence=2,
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        identity=runner._strong_identity(info),
        task_state="PENDING",
        completed_predecessors=("T-001",),
    )


def test_bridge_files_are_additive_and_executable() -> None:
    expected_modes = {
        RUNNER_PATH: 0o755,
        VALIDATOR_PATH: 0o755,
        STARTER_PATH: 0o755,
        SCHEMA_PATH: 0o644,
        SCOPE_PATH: 0o644,
    }
    for path, mode in expected_modes.items():
        info = path.stat()
        assert stat.S_IMODE(info.st_mode) == mode


@pytest.mark.parametrize(
    ("path", "argv", "stderr"),
    [
        (RUNNER_PATH, ["unknown"], b"SUBJECT_TASK_AUTHORIZATION_V2_DENY\n"),
        (
            VALIDATOR_PATH,
            ["--unknown"],
            b"SUBJECT_TASK_AUTHORIZATION_V2_VALIDATOR_DENY\n",
        ),
        (STARTER_PATH, ["--unknown"], b"SUBJECT_TASK_PROGRESS_V2_DENY\n"),
    ],
)
def test_public_clis_fail_closed_without_echo(
    path: Path, argv: list[str], stderr: bytes
) -> None:
    result = subprocess.run(
        [sys.executable, os.fspath(path), *argv],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        timeout=10,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == stderr


def test_runner_missing_pinned_v1_dependency_is_fixed_startup_error(
    tmp_path: Path,
) -> None:
    marker = "private-path-must-not-echo"
    isolated = tmp_path / marker
    isolated.mkdir()
    copied = isolated / RUNNER_PATH.name
    copied.write_bytes(RUNNER_PATH.read_bytes())
    copied.chmod(0o755)
    result = subprocess.run(
        [sys.executable, os.fspath(copied), "unknown"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        timeout=10,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert result.returncode == 3
    assert result.stdout == b""
    assert result.stderr == b"SUBJECT_TASK_AUTHORIZATION_V2_ERROR\n"
    assert marker.encode() not in result.stdout + result.stderr


def test_t002_scope_descriptor_is_closed_and_exact(runner) -> None:
    descriptor, raw = runner._load_scope_descriptor(REPO_ROOT, EXPECTED_TASK)
    assert raw == _canonical(descriptor)
    assert descriptor["authorized_task"] == EXPECTED_TASK
    assert descriptor["baseline_id"] == "0dc10cfc4a429662"
    assert descriptor["proof_repo_relative_path"] == (
        "specs/subject-distillation/task-authorizations/T-002.json"
    )
    assert descriptor["allowed_repo_relative_paths"] == sorted(
        [
            "specs/subject-distillation/.implementation-progress.pending",
            "specs/subject-distillation/.task-authorization.pending",
            "specs/subject-distillation/implementation-progress.json",
            "specs/subject-distillation/task-authorizations/T-002.json",
            "specs/subject-distillation/task-authorizations/T-002.review.json",
            "tests/fixtures/subject_distillation/fragments/failure-boundary-cases.json",
            "tests/fixtures/subject_distillation/manifest.json",
            "tests/fixtures/subject_distillation/migration/migration-boundary-cases.json",
            "tests/fixtures/subject_distillation/organization/authority-boundary-cases.json",
            "tests/fixtures/subject_distillation/person/person-cases.json",
            "tests/test_subject_fixture_privacy.py",
        ]
    )


def test_protocol_contract_uses_stable_proof_bound_descriptor_policy(runner) -> None:
    contract, raw = runner._load_contract(REPO_ROOT)
    assert raw == _canonical(contract)
    assert contract["descriptor_policy"] == {
        "path_template": "specs/subject-distillation/task-scopes/{task}.json",
        "registration": "proposal-and-proof-bound",
        "task_header_binding_required": True,
    }
    assert "descriptor_manifest" not in contract


def test_public_trust_files_require_exact_mode_and_single_link(runner) -> None:
    runner._require_public_identity((1, 2, 0o100644, 1, 3, 4, 5), 0o644)
    for identity in (
        (1, 2, 0o100600, 1, 3, 4, 5),
        (1, 2, 0o100644, 2, 3, 4, 5),
        (1, 2, 0o040644, 1, 3, 4, 5),
    ):
        with pytest.raises(runner.Denied):
            runner._require_public_identity(identity, 0o644)


def test_external_completion_review_packet_is_retained_and_repo_external(
    runner, stable_temp_root: Path
) -> None:
    packet = stable_temp_root / "completion-review.json"
    raw = _canonical({"artifact_kind": "public-review-test", "status": "PASS"})
    packet.write_bytes(raw)
    packet.chmod(0o644)
    guard, captured = runner._open_external_public_packet(packet, REPO_ROOT)
    try:
        assert captured == raw
        assert guard.snapshot() == {os.fspath(packet): raw}
        guard.audit()
    finally:
        guard.close()
    with pytest.raises(runner.Denied):
        runner._open_external_public_packet(SCOPE_PATH, REPO_ROOT)
    alias = stable_temp_root / "review-alias.json"
    alias.symlink_to(packet)
    with pytest.raises(runner.Denied):
        runner._open_external_public_packet(alias, REPO_ROOT)


def test_repository_change_set_is_derived_and_extra_dirt_denies(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    progress = repo / "progress.json"
    progress.write_bytes(b"old\n")
    subprocess.run(["git", "add", "progress.json"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo).decode().strip()
    progress.write_bytes(b"new\n")
    proof = repo / "proof.json"
    proof.write_bytes(b"proof\n")
    monkeypatch.chdir(repo)
    assert runner._repository_changes(
        repo,
        f"git:{base}",
        ["progress.json", "proof.json"],
        {"progress.json": b"new\n", "proof.json": b"proof\n"},
    ) == [
        {
            "action": "modify",
            "mode": "100644",
            "path": "progress.json",
            "sha256": hashlib.sha256(b"new\n").hexdigest(),
        },
        {
            "action": "add",
            "mode": "100644",
            "path": "proof.json",
            "sha256": hashlib.sha256(b"proof\n").hexdigest(),
        },
    ]
    (repo / "scope-external.txt").write_text("unexpected")
    with pytest.raises(runner.Denied):
        runner._repository_changes(
            repo,
            f"git:{base}",
            ["progress.json", "proof.json"],
            {"progress.json": b"new\n", "proof.json": b"proof\n"},
        )
    (repo / "scope-external.txt").unlink()
    subprocess.run(["git", "add", "progress.json", "proof.json"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "delivery"], cwd=repo, check=True)
    assert [item["path"] for item in runner._repository_changes(
        repo,
        f"git:{base}",
        ["progress.json", "proof.json"],
        {"progress.json": b"new\n", "proof.json": b"proof\n"},
    )] == ["progress.json", "proof.json"]


def test_t002_prestart_fixture_is_exact_and_phase_neutral(runner) -> None:
    snapshot = _t002_prestart_snapshot(runner)
    assert snapshot.sequence == 2
    assert snapshot.task_state == "PENDING"
    assert snapshot.completed_predecessors == ("T-001",)
    assert snapshot.raw_sha256 == hashlib.sha256(
        _canonical(_t002_prestart_value())
    ).hexdigest()


@pytest.mark.parametrize(
    ("mutation", "key"),
    [
        ("task", "authorized_task"),
        ("baseline", "baseline_id"),
        ("tasks", "tasks_sha256"),
        ("path", "allowed_repo_relative_paths"),
        ("proof", "proof_repo_relative_path"),
    ],
)
def test_scope_descriptor_mutation_denies(runner, tmp_path: Path, mutation: str, key: str) -> None:
    value = json.loads(SCOPE_PATH.read_text())
    if mutation == "task":
        value[key] = "T-003"
    elif mutation == "baseline":
        value[key] = "0" * 16
    elif mutation == "tasks":
        value[key] = "0" * 64
    elif mutation == "path":
        value[key].append("vault/runtime.py")
        value[key].sort()
    else:
        value[key] = "specs/subject-distillation/task-authorizations/T-003.json"
    path = tmp_path / "scope.json"
    path.write_bytes(_canonical(value))
    with pytest.raises(runner.Denied):
        runner._validate_scope_descriptor(value, path.read_bytes(), EXPECTED_TASK)


def test_proposal_binds_scope_ledger_and_bridge_bytes(runner) -> None:
    state = runner.v1.RepositoryState(os.fspath(REPO_ROOT), BASE_COMMIT, True)
    runtime = runner.Runtime(
        repository_state=lambda: state,
        task_progress_snapshot=lambda _root, _task: _t002_prestart_snapshot(runner),
    )
    raw = runner._propose(
        {
            "--implementation-base-commit": BASE_COMMIT,
            "--expected-task": EXPECTED_TASK,
        },
        runtime,
    )
    proposal = json.loads(raw)
    assert raw == _canonical(proposal)
    assert proposal["authorized_task"] == EXPECTED_TASK
    assert proposal["implementation_base_commit"] == BASE_COMMIT
    assert proposal["progress_sequence"] == 2
    assert proposal["progress_sha256"] == hashlib.sha256(
        _canonical(_t002_prestart_value())
    ).hexdigest()
    assert proposal["scope_descriptor_sha256"] == hashlib.sha256(SCOPE_PATH.read_bytes()).hexdigest()
    assert proposal["authorization_runner_v1_sha256"] == runner.EXPECTED_V1_RUNNER_SHA256
    assert proposal["authorization_runner_v2_sha256"] == hashlib.sha256(
        RUNNER_PATH.read_bytes()
    ).hexdigest()


def test_proposal_rejects_task_header_digest_drift(
    runner, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor = json.loads(SCOPE_PATH.read_text())
    descriptor["task_header_sha256"] = "0" * 64
    monkeypatch.setattr(
        runner,
        "_load_scope_descriptor",
        lambda _root, _task: (descriptor, _canonical(descriptor)),
    )
    state = runner.v1.RepositoryState(os.fspath(REPO_ROOT), BASE_COMMIT, True)
    runtime = runner.Runtime(
        repository_state=lambda: state,
        task_progress_snapshot=lambda _root, _task: _t002_prestart_snapshot(runner),
    )
    with pytest.raises(runner.Denied):
        runner._propose(
            {
                "--implementation-base-commit": BASE_COMMIT,
                "--expected-task": EXPECTED_TASK,
            },
            runtime,
        )


def test_progress_state_or_digest_drift_denies(runner) -> None:
    valid = _t002_prestart_snapshot(runner)
    state = runner.v1.RepositoryState(os.fspath(REPO_ROOT), BASE_COMMIT, True)
    invalid = runner.TaskProgressSnapshot(
        sequence=valid.sequence,
        raw_sha256="0" * 64,
        identity=valid.identity,
        task_state="IN_PROGRESS",
        completed_predecessors=valid.completed_predecessors,
    )
    runtime = runner.Runtime(
        repository_state=lambda: state,
        task_progress_snapshot=lambda _root, _task: invalid,
    )
    with pytest.raises(runner.Denied):
        runner._propose(
            {
                "--implementation-base-commit": BASE_COMMIT,
                "--expected-task": EXPECTED_TASK,
            },
            runtime,
        )


def test_validator_accepts_isolated_ledger_without_v2_started_tasks(validator) -> None:
    result = validator.validate_ledger_value(_t002_prestart_value(), REPO_ROOT)
    assert result == {"proofs": 0, "sequence": 2, "status": "PASS"}


def test_activation_ledger_core_uses_retained_manifest_schema_tasks_and_progress(
    runner, validator, monkeypatch: pytest.MonkeyPatch
) -> None:
    guard = runner._open_bridge_guard(
        REPO_ROOT, EXPECTED_TASK, include_progress=True
    )
    try:
        retained = guard.snapshot()
        activation_raw = _canonical(_t002_prestart_value())
        retained[runner.PROGRESS_PATH] = activation_raw
        value = runner.v1.verifier._parse(activation_raw)
        monkeypatch.setattr(
            validator.progress_v1,
            "validate",
            lambda *_args, **_kwargs: pytest.fail(
                "retained progress must not use pathname validator"
            ),
        )
        monkeypatch.setattr(
            validator.progress_v1.baseline,
            "validate",
            lambda *_args, **_kwargs: pytest.fail(
                "retained baseline must not be reopened"
            ),
        )
        monkeypatch.setattr(
            validator.progress_v1,
            "_load_schema",
            lambda *_args, **_kwargs: pytest.fail(
                "retained progress schema must not be reopened"
            ),
        )
        assert validator._validate_retained_progress(
            value, REPO_ROOT, retained
        ) == {
            "baseline_id": "0dc10cfc4a429662",
            "sequence": 2,
            "status": "PASS",
        }
        guard.audit()
    finally:
        guard.close()


def test_validator_rejects_t002_start_without_exact_proof_refs(validator) -> None:
    value = _t002_prestart_value()
    value["events"].append(
        {
            "at_utc": "2026-08-12T00:00:00Z",
            "blocker": None,
            "evidence_refs": [],
            "from": "PENDING",
            "sequence": 3,
            "task_id": "T-002",
            "to": "IN_PROGRESS",
        }
    )
    value["tasks"]["T-002"] = "IN_PROGRESS"
    value["updated_at_utc"] = "2026-08-12T00:00:00Z"
    with pytest.raises(validator.Denied):
        validator.validate_ledger_value(value, REPO_ROOT)


def test_original_t001_trust_artifacts_are_byte_pinned(runner) -> None:
    expected = {
        "scripts/run_subject_implementation_authorization.py": runner.EXPECTED_V1_RUNNER_SHA256,
        "scripts/verify_subject_implementation_authorization.py": runner.EXPECTED_VERIFIER_SHA256,
        "specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json": runner.EXPECTED_V1_SCHEMA_SHA256,
        "scripts/validate_subject_progress.py": runner.EXPECTED_PROGRESS_VALIDATOR_SHA256,
    }
    for path, digest in expected.items():
        assert hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest() == digest


def _fixed_runtime(runner, now: datetime, tmp_path: Path):
    state = runner.v1.RepositoryState(os.fspath(REPO_ROOT), BASE_COMMIT, True)
    return runner.Runtime(
        now=lambda: now,
        repository_state=lambda: state,
        task_progress_snapshot=lambda _root, _task: _t002_prestart_snapshot(runner),
        temp_root=os.fspath(tmp_path),
    )


def test_verify_confirmed_reuses_v1_private_lifecycle_and_emits_durable_proof(
    runner, validator, stable_temp_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 8, 12, 1, 2, 3, tzinfo=timezone.utc)
    runtime = _fixed_runtime(runner, now, stable_temp_root)
    proposal_raw = runner._propose(
        {
            "--implementation-base-commit": BASE_COMMIT,
            "--expected-task": EXPECTED_TASK,
        },
        runtime,
    )
    proposal = json.loads(proposal_raw)
    expected_child = _canonical(
        {
            "authorization_id": proposal["authorization_id"],
            "authorized_task": EXPECTED_TASK,
            "baseline_id": proposal["baseline_id"],
            "status": "PASS",
        }
    )
    runtime.run_child = lambda *_args: runner.v1.ChildResult(0, expected_child, b"")
    published: list[bytes] = []

    def publish(_root: Path, path: str, raw: bytes, **_kwargs) -> bool:
        assert path == "specs/subject-distillation/task-authorizations/T-002.json"
        published.append(raw)
        return False

    monkeypatch.setattr(runner, "_publish_proof", publish)
    proof_raw = runner._verify_confirmed(
        {
            "--implementation-base-commit": BASE_COMMIT,
            "--expected-task": EXPECTED_TASK,
            "--expected-proposal-id": proposal["proposal_id"],
            "--expected-receipt-sha256": proposal["receipt_sha256"],
            "--proposal-json": proposal_raw.decode(),
            "--owner-confirmation-ref": "owner-message:T-002-confirmation",
        },
        runtime,
    )
    assert published == [proof_raw]
    proof = json.loads(proof_raw)
    assert proof_raw == _canonical(proof)
    assert validator.validate_proof_value(proof, REPO_ROOT) == {
        "authorization_id": proposal["authorization_id"],
        "authorized_task": EXPECTED_TASK,
        "status": "PASS",
    }
    retained_paths = {
        runner.CONTRACT_PATH,
        runner.PROOF_SCHEMA_PATH,
        runner.VALIDATOR_PATH,
        runner.UPDATER_PATH,
        runner.V1_RUNNER_PATH,
        runner.PROGRESS_VALIDATOR_PATH,
        runner.v1.verifier.SCHEMA_PATH,
        runner.v1.verifier.VERIFIER_PATH,
        "scripts/run_subject_task_authorization_v2.py",
        runner._scope_path(EXPECTED_TASK),
    }
    retained = {path: (REPO_ROOT / path).read_bytes() for path in retained_paths}
    monkeypatch.setattr(
        runner,
        "_load_contract",
        lambda *_args: pytest.fail("retained contract must not be reopened"),
    )
    monkeypatch.setattr(
        runner,
        "_load_scope_descriptor",
        lambda *_args: pytest.fail("retained descriptor must not be reopened"),
    )
    monkeypatch.setattr(
        runner,
        "_support_hashes",
        lambda *_args: pytest.fail("retained support files must not be reopened"),
    )
    assert validator.validate_proof_value(
        proof, REPO_ROOT, retained=retained
    ) == {
        "authorization_id": proposal["authorization_id"],
        "authorized_task": EXPECTED_TASK,
        "status": "PASS",
    }
    assert not [path for path in stable_temp_root.iterdir() if path.is_dir()]


def test_verify_confirmed_requires_the_owner_selected_exact_proposal_id(
    runner, tmp_path: Path
) -> None:
    now = datetime(2026, 8, 12, 1, 2, 3, tzinfo=timezone.utc)
    runtime = _fixed_runtime(runner, now, tmp_path)
    proposal_raw = runner._propose(
        {
            "--implementation-base-commit": BASE_COMMIT,
            "--expected-task": EXPECTED_TASK,
        },
        runtime,
    )
    proposal = json.loads(proposal_raw)
    with pytest.raises(runner.Denied):
        runner._verify_confirmed(
            {
                "--implementation-base-commit": BASE_COMMIT,
                "--expected-task": EXPECTED_TASK,
                "--expected-proposal-id": "0" * 64,
                "--expected-receipt-sha256": proposal["receipt_sha256"],
                "--proposal-json": proposal_raw.decode(),
                "--owner-confirmation-ref": "owner-message:T-002-confirmation",
            },
            runtime,
        )


@pytest.mark.parametrize("clock_fault", ["expiry", "rollback"])
def test_publish_freshness_rejects_expiry_and_clock_rollback(
    runner,
    tmp_path: Path,
    clock_fault: str,
) -> None:
    issued = datetime(2026, 8, 12, 1, 2, 3, tzinfo=timezone.utc)
    proposal_runtime = _fixed_runtime(runner, issued, tmp_path)
    proposal_raw = runner._propose(
        {
            "--implementation-base-commit": BASE_COMMIT,
            "--expected-task": EXPECTED_TASK,
        },
        proposal_runtime,
    )
    proposal = json.loads(proposal_raw)
    recorded = (
        issued + runner.VALIDITY
        if clock_fault == "expiry"
        else issued - runner.timedelta(seconds=1)
    )
    with pytest.raises(runner.Denied):
        runner._require_recorded_freshness(proposal, issued, recorded)


def test_verifier_deny_cleans_private_bytes_and_never_publishes(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 8, 12, 1, 2, 3, tzinfo=timezone.utc)
    runtime = _fixed_runtime(runner, now, tmp_path)
    proposal_raw = runner._propose(
        {
            "--implementation-base-commit": BASE_COMMIT,
            "--expected-task": EXPECTED_TASK,
        },
        runtime,
    )
    proposal = json.loads(proposal_raw)
    runtime.run_child = lambda *_args: runner.v1.ChildResult(
        2, b"", runner.v1.VERIFIER_DENY.encode()
    )
    monkeypatch.setattr(
        runner,
        "_publish_proof",
        lambda *_args, **_kwargs: pytest.fail("DENY must not publish a proof"),
    )
    with pytest.raises(runner.v1.Denied):
        runner._verify_confirmed(
            {
                "--implementation-base-commit": BASE_COMMIT,
                "--expected-task": EXPECTED_TASK,
                "--expected-proposal-id": proposal["proposal_id"],
                "--expected-receipt-sha256": proposal["receipt_sha256"],
                "--proposal-json": proposal_raw.decode(),
                "--owner-confirmation-ref": "owner-message:T-002-confirmation",
            },
            runtime,
        )
    assert not [path for path in tmp_path.iterdir() if path.is_dir()]


def test_mid_verification_progress_drift_denies_after_cleanup(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 8, 12, 1, 2, 3, tzinfo=timezone.utc)
    valid = _t002_prestart_snapshot(runner)
    drifted = runner.TaskProgressSnapshot(
        sequence=valid.sequence + 1,
        raw_sha256="0" * 64,
        identity=valid.identity,
        task_state="PENDING",
        completed_predecessors=valid.completed_predecessors,
    )
    changed = False

    def snapshot(_root: Path, _task: str):
        return drifted if changed else valid

    def hook(event: str, _lifecycle) -> None:
        nonlocal changed
        if event == "after_verifier":
            changed = True

    runtime = _fixed_runtime(runner, now, tmp_path)
    runtime.task_progress_snapshot = snapshot
    runtime.hook = hook
    proposal_raw = runner._propose(
        {
            "--implementation-base-commit": BASE_COMMIT,
            "--expected-task": EXPECTED_TASK,
        },
        runtime,
    )
    proposal = json.loads(proposal_raw)
    expected_child = _canonical(
        {
            "authorization_id": proposal["authorization_id"],
            "authorized_task": EXPECTED_TASK,
            "baseline_id": proposal["baseline_id"],
            "status": "PASS",
        }
    )
    runtime.run_child = lambda *_args: runner.v1.ChildResult(0, expected_child, b"")
    monkeypatch.setattr(
        runner,
        "_publish_proof",
        lambda *_args, **_kwargs: pytest.fail("drift must not publish a proof"),
    )
    with pytest.raises(runner.Denied):
        runner._verify_confirmed(
            {
                "--implementation-base-commit": BASE_COMMIT,
                "--expected-task": EXPECTED_TASK,
                "--expected-proposal-id": proposal["proposal_id"],
                "--expected-receipt-sha256": proposal["receipt_sha256"],
                "--proposal-json": proposal_raw.decode(),
                "--owner-confirmation-ref": "owner-message:T-002-confirmation",
            },
            runtime,
        )
    assert not [path for path in tmp_path.iterdir() if path.is_dir()]


def test_atomic_proof_publish_is_no_overwrite_and_byte_recoverable(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    (repo / "specs/subject-distillation/task-authorizations").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", os.fspath(repo)], check=True)
    monkeypatch.chdir(repo)
    relative = "specs/subject-distillation/task-authorizations/T-002.json"
    raw = b'{"status":"PASS"}\n'
    assert runner._publish_proof(repo, relative, raw) is False
    final = repo / relative
    assert final.read_bytes() == raw
    assert stat.S_IMODE(final.stat().st_mode) == 0o644
    assert not (repo / "specs/subject-distillation/.task-authorization.pending").exists()
    assert runner._publish_proof(repo, relative, raw) is True
    with pytest.raises(runner.Denied):
        runner._publish_proof(repo, relative, b'{"status":"FAIL"}\n')


@pytest.mark.parametrize("publication_phase", ["pending-written", "linked-not-unlinked"])
def test_atomic_proof_publish_recovers_exact_crash_states(
    runner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    publication_phase: str,
) -> None:
    repo = tmp_path / publication_phase
    subject = repo / "specs/subject-distillation"
    proof_dir = subject / "task-authorizations"
    proof_dir.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", os.fspath(repo)], check=True)
    pending = subject / ".task-authorization.pending"
    final = proof_dir / "T-002.json"
    raw = b'{"status":"PASS"}\n'
    pending.write_bytes(raw)
    pending.chmod(0o644 if publication_phase == "linked-not-unlinked" else 0o600)
    if publication_phase == "linked-not-unlinked":
        os.link(pending, final)
    monkeypatch.chdir(repo)
    assert runner._publish_proof(
        repo,
        "specs/subject-distillation/task-authorizations/T-002.json",
        raw,
    ) == (publication_phase == "linked-not-unlinked")
    assert final.read_bytes() == raw
    assert stat.S_IMODE(final.stat().st_mode) == 0o644
    assert final.stat().st_nlink == 1
    assert not pending.exists()


@pytest.mark.parametrize("fail_on_audit", [1, 2])
def test_atomic_proof_publish_rolls_back_owned_identity_on_guard_drift(
    runner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fail_on_audit: int,
) -> None:
    repo = tmp_path / f"guard-{fail_on_audit}"
    subject = repo / "specs/subject-distillation"
    proof_dir = subject / "task-authorizations"
    proof_dir.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", os.fspath(repo)], check=True)
    monkeypatch.chdir(repo)
    count = 0

    def audit() -> None:
        nonlocal count
        count += 1
        if count == fail_on_audit:
            raise runner.Denied

    with pytest.raises(runner.Denied):
        runner._publish_proof(
            repo,
            "specs/subject-distillation/task-authorizations/T-002.json",
            b'{"status":"PASS"}\n',
            audit=audit,
        )
    assert not (proof_dir / "T-002.json").exists()
    assert not (subject / ".task-authorization.pending").exists()


def test_atomic_proof_publish_denies_hostile_final_path_replacement(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "replacement"
    subject = repo / "specs/subject-distillation"
    proof_dir = subject / "task-authorizations"
    proof_dir.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", os.fspath(repo)], check=True)
    monkeypatch.chdir(repo)
    final = proof_dir / "T-002.json"
    displaced = proof_dir / "displaced.json"
    count = 0

    def replace_after_link() -> None:
        nonlocal count
        count += 1
        if count == 2:
            final.rename(displaced)
            final.write_bytes(b'{"status":"hostile"}\n')
            final.chmod(0o644)

    with pytest.raises(runner.Denied):
        runner._publish_proof(
            repo,
            "specs/subject-distillation/task-authorizations/T-002.json",
            b'{"status":"PASS"}\n',
            audit=replace_after_link,
        )
    assert final.read_bytes() == b'{"status":"hostile"}\n'
    assert displaced.read_bytes() == b'{"status":"PASS"}\n'
    assert not (subject / ".task-authorization.pending").exists()


def test_unknown_next_task_without_reviewed_descriptor_denies(runner) -> None:
    state = runner.v1.RepositoryState(os.fspath(REPO_ROOT), BASE_COMMIT, True)
    runtime = runner.Runtime(repository_state=lambda: state)
    with pytest.raises(runner.Denied):
        runner._propose(
            {
                "--implementation-base-commit": BASE_COMMIT,
                "--expected-task": "T-003",
            },
            runtime,
        )


def test_proof_schema_is_closed_and_matches_validator_contract(validator) -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == validator.PROOF_KEYS
    assert set(schema["properties"]) == validator.PROOF_KEYS
