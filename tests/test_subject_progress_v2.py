from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PROGRESS_PATH = REPO_ROOT / "specs/subject-distillation/implementation-progress.json"
MANIFEST_PATH = REPO_ROOT / "specs/subject-distillation/baseline-manifest.json"
TASKS_PATH = REPO_ROOT / "specs/subject-distillation/tasks.md"
PROOF_PATH = "specs/subject-distillation/task-authorizations/T-002.json"
REVIEW_PATH = "specs/subject-distillation/task-authorizations/T-002.review.json"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runner():
    return _load(
        REPO_ROOT / "scripts/run_subject_task_authorization_v2.py",
        "subject_task_v2_progress_runner_test",
    )


@pytest.fixture(scope="module")
def validator():
    return _load(
        REPO_ROOT / "scripts/validate_subject_task_authorization_v2.py",
        "subject_task_v2_progress_validator_test",
    )


@pytest.fixture(scope="module")
def updater():
    return _load(
        REPO_ROOT / "scripts/update_subject_task_progress_v2.py",
        "subject_task_v2_progress_updater_test",
    )


@pytest.fixture(autouse=True)
def _restore_repo_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(REPO_ROOT)


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode()


def _retained_trust(runner) -> dict[str, bytes]:
    paths = {
        runner.CONTRACT_PATH,
        runner.PROOF_SCHEMA_PATH,
        runner.VALIDATOR_PATH,
        runner.UPDATER_PATH,
        runner.V1_RUNNER_PATH,
        runner.PROGRESS_VALIDATOR_PATH,
        runner.v1.verifier.SCHEMA_PATH,
        runner.v1.verifier.VERIFIER_PATH,
        "scripts/run_subject_task_authorization_v2.py",
    }
    return {path: (REPO_ROOT / path).read_bytes() for path in paths}


def _synthetic_start(authorization_id: str, proof_raw: bytes) -> dict[str, object]:
    value = json.loads(PROGRESS_PATH.read_text())
    refs = [
        {"kind": "opaque", "id": f"t002-authorization:{authorization_id}"},
        {
            "kind": "repo_file",
            "path": PROOF_PATH,
            "sha256": hashlib.sha256(proof_raw).hexdigest(),
        },
    ]
    refs.sort(key=_canonical)
    value["events"].append(
        {
            "at_utc": "2026-08-12T12:00:00Z",
            "blocker": None,
            "evidence_refs": refs,
            "from": "PENDING",
            "sequence": 3,
            "task_id": "T-002",
            "to": "IN_PROGRESS",
        }
    )
    value["tasks"]["T-002"] = "IN_PROGRESS"
    value["updated_at_utc"] = "2026-08-12T12:00:00Z"
    return value


def _install_proof_fakes(
    monkeypatch: pytest.MonkeyPatch,
    runner,
    validator,
    proof_value: dict[str, object],
    proof_raw: bytes,
    review_value: dict[str, object] | None = None,
    review_raw: bytes | None = None,
) -> None:
    target_runner = validator.runner
    descriptor = json.loads(
        (REPO_ROOT / "specs/subject-distillation/task-scopes/T-002.json").read_text()
    )
    original_read = target_runner._read_repo_file
    monkeypatch.setattr(
        target_runner,
        "_load_scope_descriptor",
        lambda _root, _task: (descriptor, _canonical(descriptor)),
    )

    def read(root: Path, path: str, **kwargs):
        if path == PROOF_PATH:
            return proof_raw, (1, 1, 0o100644, 1, len(proof_raw), 1, 1)
        return original_read(root, path, **kwargs)

    monkeypatch.setattr(target_runner, "_read_repo_file", read)
    monkeypatch.setattr(
        validator,
        "_load_json",
        lambda path: (proof_value, proof_raw)
        if path.as_posix().endswith(PROOF_PATH)
        else (review_value, review_raw)
        if review_value is not None
        and review_raw is not None
        and path.as_posix().endswith(REVIEW_PATH)
        else pytest.fail(f"unexpected proof read: {path}"),
    )
    monkeypatch.setattr(
        validator,
        "validate_proof_value",
        lambda *_args, **_kwargs: {
            "authorization_id": proof_value["authorization_id"],
            "authorized_task": "T-002",
            "status": "PASS",
        },
    )


def _review_value(
    descriptor: dict[str, object],
    proof_value: dict[str, object],
    proof_raw: bytes,
    artifact_raw: dict[str, bytes],
    progress_value: dict[str, object],
) -> dict[str, object]:
    outputs = [
        {
            "mode": "100644",
            "path": path,
            "sha256": hashlib.sha256(artifact_raw[path]).hexdigest(),
        }
        for path in descriptor["completion_repo_relative_paths"]
    ]
    change_paths = sorted(
        descriptor["completion_repo_relative_paths"]
        + [PROOF_PATH]
    )
    raw_by_path = {
        **artifact_raw,
        PROOF_PATH: proof_raw,
    }
    changes = [
        {
            "action": "add",
            "mode": "100644",
            "path": path,
            "sha256": hashlib.sha256(raw_by_path[path]).hexdigest(),
        }
        for path in change_paths
    ]
    return {
        "schema_version": 2,
        "artifact_kind": "subject-task-completion-review-v2",
        "status": "PASS",
        "authorized_task": "T-002",
        "implementation_base_commit": proof_value["implementation_base_commit"],
        "baseline_id": proof_value["baseline_id"],
        "baseline_full_digest": proof_value["baseline_full_digest"],
        "scope_descriptor_sha256": hashlib.sha256(_canonical(descriptor)).hexdigest(),
        "authorization_proof_sha256": hashlib.sha256(proof_raw).hexdigest(),
        "reviewed_at_utc": "2026-08-12T12:25:00Z",
        "builder_principal": "agent:builder",
        "reviewer_principal": "agent:reviewer",
        "verification_argv": descriptor["verification_argv"],
        "verification_result": {"exit_code": 0, "status": "PASS"},
        "p0": 0,
        "p1": 0,
        "p2": 0,
        "verdict": "PASS",
        "reviewed_outputs": outputs,
        "reviewed_changes": changes,
        "reviewed_change_paths": change_paths,
        "reviewed_change_set_sha256": hashlib.sha256(
            _canonical(changes)[:-1]
        ).hexdigest(),
        "progress_before_sequence": len(progress_value["events"]),
        "progress_before_sha256": hashlib.sha256(
            _canonical(progress_value)
        ).hexdigest(),
    }
def test_v1_accepts_bypass_shape_while_v2_rejects_it(validator) -> None:
    value = json.loads(PROGRESS_PATH.read_text())
    value["events"].append(
        {
            "at_utc": "2026-08-12T12:00:00Z",
            "blocker": None,
            "evidence_refs": [],
            "from": "PENDING",
            "sequence": 3,
            "task_id": "T-002",
            "to": "IN_PROGRESS",
        }
    )
    value["tasks"]["T-002"] = "IN_PROGRESS"
    value["updated_at_utc"] = "2026-08-12T12:00:00Z"
    manifest = validator.progress_v1.baseline.validate(MANIFEST_PATH, REPO_ROOT)
    assert validator.progress_v1.validate_value(
        value,
        repo_root=REPO_ROOT,
        manifest_result=manifest,
        tasks_sha256=hashlib.sha256(TASKS_PATH.read_bytes()).hexdigest(),
    )["status"] == "PASS"
    with pytest.raises(validator.Denied):
        validator.validate_ledger_value(value, REPO_ROOT)


def test_pre_authorization_pending_to_blocked_denies(validator) -> None:
    value = json.loads(PROGRESS_PATH.read_text())
    value["events"].append(
        {
            "at_utc": "2026-08-12T12:00:00Z",
            "blocker": "UNAUTHORIZED_PRESTART",
            "evidence_refs": [],
            "from": "PENDING",
            "sequence": 3,
            "task_id": "T-002",
            "to": "BLOCKED",
        }
    )
    value["tasks"]["T-002"] = "BLOCKED"
    value["updated_at_utc"] = "2026-08-12T12:00:00Z"
    with pytest.raises(validator.Denied):
        validator.validate_ledger_value(value, REPO_ROOT)


def test_t002_only_validator_rejects_t003_proof_review_and_start(validator) -> None:
    with pytest.raises(validator.Denied):
        validator._require_supported_task(REPO_ROOT, "T-003")
    with pytest.raises(validator.Denied):
        validator.validate_completion_review_value({}, b"{}\n", REPO_ROOT, "T-003")
    value = json.loads(PROGRESS_PATH.read_text())
    value["events"].append(
        {
            "at_utc": "2026-08-12T12:00:00Z",
            "blocker": None,
            "evidence_refs": [],
            "from": "PENDING",
            "sequence": 3,
            "task_id": "T-003",
            "to": "IN_PROGRESS",
        }
    )
    value["tasks"]["T-003"] = "IN_PROGRESS"
    value["updated_at_utc"] = "2026-08-12T12:00:00Z"
    with pytest.raises(validator.Denied):
        validator.validate_ledger_value(value, REPO_ROOT)


@pytest.mark.parametrize("post_failure", [False, True])
def test_start_wrapper_publishes_only_inside_v2_validated_atomic_callbacks(
    updater,
    monkeypatch: pytest.MonkeyPatch,
    post_failure: bool,
) -> None:
    authorization_id = "7" * 64
    proof_value = {
        "authorization_id": authorization_id,
        "authorized_task": "T-002",
        "proof_repo_relative_path": PROOF_PATH,
        "progress_sequence": 2,
        "progress_sha256": hashlib.sha256(PROGRESS_PATH.read_bytes()).hexdigest(),
    }
    proof_raw = _canonical(proof_value)
    current = json.loads(PROGRESS_PATH.read_text())
    state = {"ledger": copy.deepcopy(current)}
    audit_calls = 0

    class Guard:
        def audit(self) -> None:
            nonlocal audit_calls
            audit_calls += 1

        def close(self) -> None:
            return None

        def snapshot(self) -> dict[str, bytes]:
            return {PROOF_PATH: proof_raw}

    @contextlib.contextmanager
    def lock(*_args, **_kwargs):
        yield None

    monkeypatch.setattr(updater.runner.v1, "_authorization_lock", lock)
    monkeypatch.setattr(
        updater.runner,
        "_open_bridge_guard",
        lambda *_args, **_kwargs: Guard(),
    )
    monkeypatch.setattr(
        updater.validator, "_load_json", lambda _path: (proof_value, proof_raw)
    )
    monkeypatch.setattr(
        updater.validator,
        "validate_proof_value",
        lambda *_args, **_kwargs: {
            "authorization_id": authorization_id,
            "authorized_task": "T-002",
            "status": "PASS",
        },
    )
    monkeypatch.setattr(
        updater.validator,
        "validate_start_refs",
        lambda *_args, **_kwargs: None,
    )
    expected_refs = [
        {"kind": "opaque", "id": f"t002-authorization:{authorization_id}"},
        {
            "kind": "repo_file",
            "path": PROOF_PATH,
            "sha256": hashlib.sha256(proof_raw).hexdigest(),
        },
    ]
    expected_refs.sort(key=_canonical)
    monkeypatch.setattr(
        updater.writer_v1,
        "_parse_refs",
        lambda *_args, **_kwargs: copy.deepcopy(expected_refs),
    )

    def validate_overlay(value, _root, *, retained=None):
        assert retained == {PROOF_PATH: proof_raw}
        return {
            "proofs": 1,
            "sequence": len(value["events"]),
            "status": "PASS",
        }

    monkeypatch.setattr(
        updater.validator,
        "validate_ledger_value",
        validate_overlay,
    )
    monkeypatch.setattr(
        updater.validator,
        "validate_ledger",
        lambda _root: (_ for _ in ()).throw(updater.Denied)
        if post_failure
        else {"proofs": 1, "sequence": 3, "status": "PASS"},
    )
    monkeypatch.setattr(
        updater.writer_v1,
        "_inputs",
        lambda _paths: ({"baseline_id": "0dc10cfc4a429662"}, "unused"),
    )
    monkeypatch.setattr(
        updater.writer_v1, "_existing", lambda _paths: copy.deepcopy(state["ledger"])
    )

    def publish(_paths, candidate, *, pre_publish, post_publish, **_kwargs):
        old = copy.deepcopy(state["ledger"])
        pre_publish((1, 2, 3, 4, 5))
        state["ledger"] = copy.deepcopy(candidate)
        try:
            post_publish()
        except Exception:
            state["ledger"] = old
            raise
        return False

    monkeypatch.setattr(updater.writer_v1, "_publish", publish)
    runtime = updater.writer_v1.Runtime(
        now=lambda: updater.writer_v1.datetime(
            2026, 8, 12, 12, 0, tzinfo=updater.writer_v1.timezone.utc
        )
    )
    if post_failure:
        with pytest.raises(updater.Denied):
            updater.start(REPO_ROOT / PROOF_PATH, runtime=runtime, lock_runtime=object())
        assert state["ledger"] == current
    else:
        assert updater.start(
            REPO_ROOT / PROOF_PATH, runtime=runtime, lock_runtime=object()
        ) == {"sequence": 3, "status": "PASS", "task_id": "T-002"}
        assert state["ledger"]["tasks"]["T-002"] == "IN_PROGRESS"
    assert audit_calls >= 3


@pytest.mark.parametrize("case", ["success", "post_failure", "future_review"])
def test_completion_wrapper_publishes_review_and_ledger_under_atomic_guards(
    updater,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
) -> None:
    post_failure = case == "post_failure"
    descriptor = json.loads(
        (REPO_ROOT / "specs/subject-distillation/task-scopes/T-002.json").read_text()
    )
    authorization_id = "a" * 64
    review_id = "b" * 64
    review_packet = tmp_path / "review.json"
    refs = [
        {"kind": "opaque", "id": f"t002-authorization:{authorization_id}"},
        {"kind": "opaque", "id": f"t002-review:{review_id}"},
    ]
    refs.sort(key=_canonical)
    current = _synthetic_start(authorization_id, b"proof\n")
    reviewed_paths = sorted(
        descriptor["completion_repo_relative_paths"] + [PROOF_PATH]
    )
    reviewed_changes = [
        {
            "action": "add",
            "mode": "100644",
            "path": path,
            "sha256": "1" * 64,
        }
        for path in reviewed_paths
    ]
    review_value = {
        "implementation_base_commit": "git:" + "1" * 40,
        "reviewed_change_paths": reviewed_paths,
        "reviewed_changes": reviewed_changes,
        "progress_before_sequence": len(current["events"]),
        "progress_before_sha256": hashlib.sha256(_canonical(current)).hexdigest(),
        "synthetic": True,
    }
    review_raw = _canonical(review_value)
    state = {"ledger": copy.deepcopy(current)}
    published_reviews: list[bytes] = []
    audits = 0

    class Guard:
        def __init__(self, snapshot: dict[str, bytes]) -> None:
            self._snapshot = snapshot

        def audit(self) -> None:
            nonlocal audits
            audits += 1

        def close(self) -> None:
            return None

        def snapshot(self) -> dict[str, bytes]:
            return dict(self._snapshot)

    external = Guard({os.fspath(review_packet): review_raw})
    source_snapshot = {
        PROOF_PATH: b"proof\n",
        "specs/subject-distillation/implementation-progress.json": _canonical(current),
        "specs/subject-distillation/task-scopes/T-002.json": _canonical(descriptor),
        **{
            path: _canonical({"path": path})
            for path in descriptor["completion_repo_relative_paths"]
        },
    }
    source = Guard(source_snapshot)
    review_guard = Guard({REVIEW_PATH: review_raw})

    @contextlib.contextmanager
    def lock(*_args, **_kwargs):
        yield None

    monkeypatch.setattr(updater.runner.v1, "_authorization_lock", lock)
    monkeypatch.setattr(
        updater.runner,
        "_open_external_public_packet",
        lambda *_args, **_kwargs: (external, review_raw),
    )
    monkeypatch.setattr(
        updater.runner,
        "_open_bridge_guard",
        lambda *_args, **kwargs: review_guard
        if REVIEW_PATH in kwargs.get("extra_paths", ())
        else source,
    )
    monkeypatch.setattr(
        updater.runner,
        "_directory_names",
        lambda *_args: ["README.md", "T-002.json"],
    )
    monkeypatch.setattr(
        updater.runner,
        "_load_scope_descriptor",
        lambda *_args: (descriptor, _canonical(descriptor)),
    )
    monkeypatch.setattr(
        updater.runner.v1.verifier,
        "_parse",
        lambda raw: copy.deepcopy(descriptor)
        if raw == _canonical(descriptor)
        else copy.deepcopy(current)
        if raw == _canonical(current)
        else copy.deepcopy(review_value),
    )
    monkeypatch.setattr(updater.runner, "_scan_v2", lambda _value: None)
    monkeypatch.setattr(
        updater.runner,
        "_repository_changes",
        lambda _root, _base, paths, _retained: copy.deepcopy(reviewed_changes)
        + [
            {
                "action": "modify",
                "mode": "100644",
                "path": "specs/subject-distillation/implementation-progress.json",
                "sha256": hashlib.sha256(_canonical(current)).hexdigest(),
            }
        ]
        + (
            [
                {
                    "action": "add",
                    "mode": "100644",
                    "path": REVIEW_PATH,
                    "sha256": hashlib.sha256(review_raw).hexdigest(),
                }
            ]
            if REVIEW_PATH in paths
            else []
        ),
    )
    monkeypatch.setattr(
        updater.runner,
        "_publish_proof",
        lambda _root, path, raw, **_kwargs: published_reviews.append(raw)
        if path == REVIEW_PATH
        else pytest.fail(path),
    )
    review_result = {
        "authorization_id": authorization_id,
        "review_id": review_id,
        "review_path": REVIEW_PATH,
        "reviewed_at_utc": "2026-08-12T12:25:00Z",
        "status": "PASS",
    }
    monkeypatch.setattr(
        updater.validator,
        "validate_completion_review_value",
        lambda *_args, **_kwargs: copy.deepcopy(review_result),
    )
    monkeypatch.setattr(
        updater.validator,
        "_expected_completion_refs",
        lambda *_args, **_kwargs: (copy.deepcopy(refs), copy.deepcopy(review_result)),
    )
    monkeypatch.setattr(
        updater.validator,
        "validate_ledger_value",
        lambda value, _root, **_kwargs: {
            "proofs": 1,
            "sequence": len(value["events"]),
            "status": "PASS",
        },
    )
    monkeypatch.setattr(
        updater.validator,
        "validate_ledger",
        lambda _root: (_ for _ in ()).throw(updater.Denied)
        if post_failure
        else {"proofs": 1, "sequence": 4, "status": "PASS"},
    )
    monkeypatch.setattr(
        updater.writer_v1,
        "_inputs",
        lambda _paths: ({"baseline_id": "0dc10cfc4a429662"}, "unused"),
    )
    monkeypatch.setattr(
        updater.writer_v1, "_existing", lambda _paths: copy.deepcopy(state["ledger"])
    )

    def publish(_paths, candidate, *, pre_publish, post_publish, **_kwargs):
        old = copy.deepcopy(state["ledger"])
        pre_publish((1, 2, 3, 4, 5))
        state["ledger"] = copy.deepcopy(candidate)
        try:
            post_publish()
        except Exception:
            state["ledger"] = old
            raise
        return False

    monkeypatch.setattr(updater.writer_v1, "_publish", publish)
    runtime = updater.writer_v1.Runtime(
        now=lambda: updater.writer_v1.datetime(
            2026,
            8,
            12,
            12,
            20 if case == "future_review" else 30,
            tzinfo=updater.writer_v1.timezone.utc,
        )
    )
    if case in {"post_failure", "future_review"}:
        with pytest.raises(updater.Denied):
            updater.complete(review_packet, runtime=runtime, lock_runtime=object())
        assert state["ledger"] == current
    else:
        assert updater.complete(
            review_packet, runtime=runtime, lock_runtime=object()
        ) == {"sequence": 4, "status": "PASS", "task_id": "T-002"}
        assert state["ledger"]["tasks"]["T-002"] == "COMPLETED"
    assert published_reviews == ([] if case == "future_review" else [review_raw])
    assert audits >= (4 if case == "future_review" else 5)


def test_exact_proof_bound_t002_start_passes_overlay(
    runner, validator, monkeypatch: pytest.MonkeyPatch
) -> None:
    authorization_id = "a" * 64
    proof_value: dict[str, object] = {
        "authorization_id": authorization_id,
        "progress_sequence": 2,
        "progress_sha256": hashlib.sha256(PROGRESS_PATH.read_bytes()).hexdigest(),
    }
    proof_raw = _canonical(proof_value)
    _install_proof_fakes(monkeypatch, runner, validator, proof_value, proof_raw)
    value = _synthetic_start(authorization_id, proof_raw)
    assert validator.validate_ledger_value(value, REPO_ROOT) == {
        "proofs": 1,
        "sequence": 3,
        "status": "PASS",
    }


def test_offline_overlay_uses_one_retained_proof_snapshot(
    runner, validator, monkeypatch: pytest.MonkeyPatch
) -> None:
    authorization_id = "6" * 64
    proof_value = {
        "authorization_id": authorization_id,
        "progress_sequence": 2,
        "progress_sha256": hashlib.sha256(PROGRESS_PATH.read_bytes()).hexdigest(),
    }
    proof_raw = _canonical(proof_value)
    _install_proof_fakes(monkeypatch, runner, validator, proof_value, proof_raw)
    monkeypatch.setattr(
        validator,
        "_load_json",
        lambda _path: pytest.fail("retained proof must not be reopened"),
    )
    descriptor_raw = (
        REPO_ROOT / "specs/subject-distillation/task-scopes/T-002.json"
    ).read_bytes()
    retained = {
        **_retained_trust(runner),
        PROOF_PATH: proof_raw,
        "specs/subject-distillation/task-scopes/T-002.json": descriptor_raw,
    }
    assert validator.validate_ledger_value(
        _synthetic_start(authorization_id, proof_raw),
        REPO_ROOT,
        retained=retained,
    ) == {"proofs": 1, "sequence": 3, "status": "PASS"}


def test_blocked_task_resume_reuses_the_original_exact_proof_refs(
    runner, validator, monkeypatch: pytest.MonkeyPatch
) -> None:
    authorization_id = "9" * 64
    proof_value: dict[str, object] = {
        "authorization_id": authorization_id,
        "progress_sequence": 2,
        "progress_sha256": hashlib.sha256(PROGRESS_PATH.read_bytes()).hexdigest(),
    }
    proof_raw = _canonical(proof_value)
    _install_proof_fakes(monkeypatch, runner, validator, proof_value, proof_raw)
    value = _synthetic_start(authorization_id, proof_raw)
    value["events"].append(
        {
            "at_utc": "2026-08-12T12:15:00Z",
            "blocker": "WAITING_FOR_REVIEW",
            "evidence_refs": [],
            "from": "IN_PROGRESS",
            "sequence": 4,
            "task_id": "T-002",
            "to": "BLOCKED",
        }
    )
    value["events"].append(
        {
            "at_utc": "2026-08-12T12:20:00Z",
            "blocker": None,
            "evidence_refs": copy.deepcopy(value["events"][2]["evidence_refs"]),
            "from": "BLOCKED",
            "sequence": 5,
            "task_id": "T-002",
            "to": "IN_PROGRESS",
        }
    )
    value["tasks"]["T-002"] = "IN_PROGRESS"
    value["updated_at_utc"] = "2026-08-12T12:20:00Z"
    assert validator.validate_ledger_value(value, REPO_ROOT) == {
        "proofs": 1,
        "sequence": 5,
        "status": "PASS",
    }
    value["events"][4]["evidence_refs"][0] = {
        "kind": "opaque",
        "id": "t002-authorization:" + "8" * 64,
    }
    value["events"][4]["evidence_refs"].sort(key=_canonical)
    with pytest.raises(validator.Denied):
        validator.validate_ledger_value(value, REPO_ROOT)


@pytest.mark.parametrize("mutation", ["opaque", "repo-hash", "extra-ref", "prefix"])
def test_t002_start_ref_mutations_deny(
    runner,
    validator,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    authorization_id = "b" * 64
    proof_value: dict[str, object] = {
        "authorization_id": authorization_id,
        "progress_sequence": 2,
        "progress_sha256": hashlib.sha256(PROGRESS_PATH.read_bytes()).hexdigest(),
    }
    proof_raw = _canonical(proof_value)
    _install_proof_fakes(monkeypatch, runner, validator, proof_value, proof_raw)
    value = _synthetic_start(authorization_id, proof_raw)
    refs = value["events"][2]["evidence_refs"]
    if mutation == "opaque":
        next(item for item in refs if item["kind"] == "opaque")["id"] = (
            "t002-authorization:" + "c" * 64
        )
    elif mutation == "repo-hash":
        next(item for item in refs if item["kind"] == "repo_file")["sha256"] = "c" * 64
    elif mutation == "extra-ref":
        refs.append({"kind": "opaque", "id": "unreviewed-extra"})
        refs.sort(key=_canonical)
    else:
        proof_value["progress_sha256"] = "c" * 64
    with pytest.raises(validator.Denied):
        validator.validate_ledger_value(value, REPO_ROOT)


def test_cross_task_proof_result_denies(
    runner, validator, monkeypatch: pytest.MonkeyPatch
) -> None:
    authorization_id = "d" * 64
    proof_value: dict[str, object] = {
        "authorization_id": authorization_id,
        "progress_sequence": 2,
        "progress_sha256": hashlib.sha256(PROGRESS_PATH.read_bytes()).hexdigest(),
    }
    proof_raw = _canonical(proof_value)
    _install_proof_fakes(monkeypatch, runner, validator, proof_value, proof_raw)
    monkeypatch.setattr(
        validator,
        "validate_proof_value",
        lambda *_args, **_kwargs: {
            "authorization_id": authorization_id,
            "authorized_task": "T-003",
            "status": "PASS",
        },
    )
    with pytest.raises(validator.Denied):
        validator.validate_ledger_value(
            _synthetic_start(authorization_id, proof_raw), REPO_ROOT
        )


@pytest.mark.parametrize(
    "mutation",
    [None, "missing-output", "arbitrary-review", "failed-review", "same-principal"],
)
def test_t002_completion_requires_exact_outputs_proof_and_review(
    runner,
    validator,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str | None,
) -> None:
    authorization_id = "e" * 64
    proof_value: dict[str, object] = {
        "authorization_id": authorization_id,
        "progress_sequence": 2,
        "progress_sha256": hashlib.sha256(PROGRESS_PATH.read_bytes()).hexdigest(),
        "implementation_base_commit": "git:" + "1" * 40,
        "baseline_id": "0dc10cfc4a429662",
        "baseline_full_digest": "0dc10cfc4a429662" + "0" * 48,
        "recorded_at_utc": "2026-08-12T12:00:00Z",
    }
    proof_raw = _canonical(proof_value)
    target_runner = validator.runner
    current_read = target_runner._read_repo_file
    descriptor = json.loads(
        (REPO_ROOT / "specs/subject-distillation/task-scopes/T-002.json").read_text()
    )
    artifact_raw = {
        path: _canonical({"path": path, "synthetic": True})
        for path in descriptor["completion_repo_relative_paths"]
    }
    value = _synthetic_start(authorization_id, proof_raw)
    progress_raw = _canonical(value)
    review_value = _review_value(
        descriptor, proof_value, proof_raw, artifact_raw, value
    )
    if mutation == "failed-review":
        review_value["p1"] = 1
    elif mutation == "same-principal":
        review_value["reviewer_principal"] = review_value["builder_principal"]
    review_raw = _canonical(review_value)
    _install_proof_fakes(
        monkeypatch,
        runner,
        validator,
        proof_value,
        proof_raw,
        review_value,
        review_raw,
    )

    def read(root: Path, path: str, **kwargs):
        if path == PROOF_PATH:
            return proof_raw, (1, 1, 0o100644, 1, len(proof_raw), 1, 1)
        if path in artifact_raw:
            raw = artifact_raw[path]
            return raw, (1, 2, 0o100644, 1, len(raw), 1, 1)
        if path == REVIEW_PATH:
            return review_raw, (1, 3, 0o100644, 1, len(review_raw), 1, 1)
        return current_read(root, path, **kwargs)

    monkeypatch.setattr(target_runner, "_read_repo_file", read)
    retained = {
        **_retained_trust(target_runner),
        **artifact_raw,
        PROOF_PATH: proof_raw,
        REVIEW_PATH: review_raw,
        "specs/subject-distillation/implementation-progress.json": progress_raw,
        "specs/subject-distillation/task-scopes/T-002.json": _canonical(descriptor),
    }
    if mutation in {"failed-review", "same-principal"}:
        with pytest.raises(validator.Denied):
            validator._expected_completion_refs(
                REPO_ROOT,
                "T-002",
                descriptor,
                authorization_id,
                review_value=review_value,
                review_raw=review_raw,
                retained=retained,
            )
        return
    refs, _review_result = validator._expected_completion_refs(
        REPO_ROOT,
        "T-002",
        descriptor,
        authorization_id,
        review_value=review_value,
        review_raw=review_raw,
        retained=retained,
    )
    if mutation == "missing-output":
        refs = refs[1:]
    elif mutation == "arbitrary-review":
        next(
            item
            for item in refs
            if item["kind"] == "opaque" and item["id"].startswith("t002-review:")
        )["id"] = "t002-review:" + "f" * 64
        refs.sort(key=_canonical)
    value["events"].append(
        {
            "at_utc": "2026-08-12T12:30:00Z",
            "blocker": None,
            "evidence_refs": refs,
            "from": "IN_PROGRESS",
            "sequence": 4,
            "task_id": "T-002",
            "to": "COMPLETED",
        }
    )
    value["tasks"]["T-002"] = "COMPLETED"
    value["updated_at_utc"] = "2026-08-12T12:30:00Z"
    if mutation is None:
        assert validator.validate_ledger_value(value, REPO_ROOT)["proofs"] == 1
    else:
        with pytest.raises(validator.Denied):
            validator.validate_ledger_value(value, REPO_ROOT)


def test_prefix_reconstruction_is_byte_exact(validator) -> None:
    original = json.loads(PROGRESS_PATH.read_text())
    started = copy.deepcopy(original)
    started["events"].append(
        {
            "at_utc": "2026-08-12T12:00:00Z",
            "blocker": None,
            "evidence_refs": [],
            "from": "PENDING",
            "sequence": 3,
            "task_id": "T-002",
            "to": "IN_PROGRESS",
        }
    )
    assert validator._prefix_value(started, 2) == original
    assert _canonical(validator._prefix_value(started, 2)) == PROGRESS_PATH.read_bytes()


def test_review_time_cannot_precede_latest_resume(validator) -> None:
    value = _synthetic_start("a" * 64, b"proof\n")
    value["events"].extend(
        [
            {
                "at_utc": "2026-08-12T12:10:00Z",
                "blocker": "WAITING_FOR_REVIEW",
                "evidence_refs": [],
                "from": "IN_PROGRESS",
                "sequence": 4,
                "task_id": "T-002",
                "to": "BLOCKED",
            },
            {
                "at_utc": "2026-08-12T12:20:00Z",
                "blocker": None,
                "evidence_refs": copy.deepcopy(value["events"][2]["evidence_refs"]),
                "from": "BLOCKED",
                "sequence": 5,
                "task_id": "T-002",
                "to": "IN_PROGRESS",
            },
        ]
    )
    value["tasks"]["T-002"] = "IN_PROGRESS"
    value["updated_at_utc"] = "2026-08-12T12:20:00Z"
    with pytest.raises(validator.Denied):
        validator._review_progress_context(
            value, "T-002", "2026-08-12T12:19:59Z"
        )
    prefix, raw = validator._review_progress_context(
        value, "T-002", "2026-08-12T12:20:00Z"
    )
    assert prefix == value
    assert raw == _canonical(value)


def test_review_time_cannot_postdate_completion(validator) -> None:
    value = _synthetic_start("a" * 64, b"proof\n")
    value["events"].append(
        {
            "at_utc": "2026-08-12T12:29:00Z",
            "blocker": None,
            "evidence_refs": [{"kind": "opaque", "id": "t002-review:synthetic"}],
            "from": "IN_PROGRESS",
            "sequence": 4,
            "task_id": "T-002",
            "to": "COMPLETED",
        }
    )
    value["tasks"]["T-002"] = "COMPLETED"
    value["updated_at_utc"] = "2026-08-12T12:29:00Z"
    with pytest.raises(validator.Denied):
        validator._review_progress_context(
            value, "T-002", "2026-08-12T12:29:01Z"
        )
    prefix, raw = validator._review_progress_context(
        value, "T-002", "2026-08-12T12:29:00Z"
    )
    assert prefix["tasks"]["T-002"] == "IN_PROGRESS"
    assert raw == _canonical(prefix)


def test_retained_snapshot_merge_denies_duplicate_drift(validator) -> None:
    assert validator._merge_retained_snapshots(
        {"contract": b"same"}, {"contract": b"same", "progress": b"ledger"}
    ) == {"contract": b"same", "progress": b"ledger"}
    with pytest.raises(validator.Denied):
        validator._merge_retained_snapshots(
            {"contract": b"first"}, {"contract": b"replacement"}
        )


def test_real_git_completion_reconstructs_progress_prefix_and_passes_final_overlay(
    runner,
    validator,
    updater,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    subprocess.run(
        ["git", "clone", "-q", "--no-hardlinks", os.fspath(REPO_ROOT), os.fspath(repo)],
        check=True,
    )
    delivery_paths = [
        ".github/workflows/ci.yml",
        "docs/decision_records/2026-08-12-subject-task-authorization-v2-bridge.md",
        "scripts/run_subject_task_authorization_v2.py",
        "scripts/update_subject_task_progress_v2.py",
        "scripts/validate_subject_task_authorization_v2.py",
        "specs/subject-distillation/task-authorization-v2.contract.json",
        "specs/subject-distillation/task-authorization-v2.schema.json",
        "specs/subject-distillation/task-authorizations/README.md",
        "specs/subject-distillation/task-scopes/T-002.json",
        "tests/test_subject_progress_v2.py",
        "tests/test_subject_task_authorization_v2.py",
    ]
    for relative in delivery_paths:
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative, target)
    subprocess.run(["git", "add", "--", *delivery_paths], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "bridge"],
        cwd=repo,
        check=True,
    )
    bridge_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    private_root = tmp_path / "private"
    private_root.mkdir()
    monkeypatch.chdir(repo)
    state = runner.v1.RepositoryState(os.fspath(repo), bridge_head, True)
    issued = runner.datetime(2026, 8, 12, 12, 0, tzinfo=runner.timezone.utc)
    runtime = runner.Runtime(
        now=lambda: issued,
        repository_state=lambda: state,
        temp_root=os.fspath(private_root),
    )
    proposal_raw = runner._propose(
        {
            "--implementation-base-commit": bridge_head,
            "--expected-task": "T-002",
        },
        runtime,
    )
    proposal = json.loads(proposal_raw)
    runtime.run_child = lambda *_args: runner.v1.ChildResult(
        0,
        _canonical(
            {
                "authorization_id": proposal["authorization_id"],
                "authorized_task": "T-002",
                "baseline_id": proposal["baseline_id"],
                "status": "PASS",
            }
        ),
        b"",
    )
    runner._verify_confirmed(
        {
            "--implementation-base-commit": bridge_head,
            "--expected-task": "T-002",
            "--expected-proposal-id": proposal["proposal_id"],
            "--expected-receipt-sha256": proposal["receipt_sha256"],
            "--proposal-json": proposal_raw.decode(),
            "--owner-confirmation-ref": "owner-message:integration-test",
        },
        runtime,
    )
    proof_path = repo / PROOF_PATH
    lock_runtime = runner.v1.Runtime(temp_root=os.fspath(private_root))
    start_runtime = updater.writer_v1.Runtime(
        now=lambda: updater.writer_v1.datetime(
            2026, 8, 12, 12, 10, tzinfo=updater.writer_v1.timezone.utc
        )
    )
    assert updater.start(
        proof_path, runtime=start_runtime, lock_runtime=lock_runtime
    )["status"] == "PASS"
    descriptor = json.loads((repo / "specs/subject-distillation/task-scopes/T-002.json").read_text())
    for relative in descriptor["completion_repo_relative_paths"]:
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_canonical({"artifact_kind": "synthetic-t002-output", "path": relative}))
        target.chmod(0o644)
    proof_raw = proof_path.read_bytes()
    proof_value = json.loads(proof_raw)
    progress_before = json.loads((repo / runner.PROGRESS_PATH).read_text())
    progress_before_raw = _canonical(progress_before)
    immutable_paths = sorted(
        descriptor["completion_repo_relative_paths"] + [PROOF_PATH]
    )
    expected_pre_paths = immutable_paths + [runner.PROGRESS_PATH]
    retained = {path: (repo / path).read_bytes() for path in expected_pre_paths}
    pre_changes = runner._repository_changes(
        repo, "git:" + bridge_head, expected_pre_paths, retained
    )
    immutable_changes = [
        item for item in pre_changes if item["path"] != runner.PROGRESS_PATH
    ]
    review_value = {
        "schema_version": 2,
        "artifact_kind": "subject-task-completion-review-v2",
        "status": "PASS",
        "authorized_task": "T-002",
        "implementation_base_commit": "git:" + bridge_head,
        "baseline_id": proof_value["baseline_id"],
        "baseline_full_digest": proof_value["baseline_full_digest"],
        "scope_descriptor_sha256": hashlib.sha256(
            (repo / "specs/subject-distillation/task-scopes/T-002.json").read_bytes()
        ).hexdigest(),
        "authorization_proof_sha256": hashlib.sha256(proof_raw).hexdigest(),
        "reviewed_at_utc": "2026-08-12T12:20:00Z",
        "builder_principal": "agent:builder",
        "reviewer_principal": "agent:reviewer",
        "verification_argv": descriptor["verification_argv"],
        "verification_result": {"exit_code": 0, "status": "PASS"},
        "p0": 0,
        "p1": 0,
        "p2": 0,
        "verdict": "PASS",
        "reviewed_outputs": [
            {
                "mode": "100644",
                "path": path,
                "sha256": hashlib.sha256((repo / path).read_bytes()).hexdigest(),
            }
            for path in descriptor["completion_repo_relative_paths"]
        ],
        "reviewed_changes": immutable_changes,
        "reviewed_change_paths": immutable_paths,
        "reviewed_change_set_sha256": hashlib.sha256(
            runner._canonical(immutable_changes, newline=False)
        ).hexdigest(),
        "progress_before_sequence": len(progress_before["events"]),
        "progress_before_sha256": hashlib.sha256(progress_before_raw).hexdigest(),
    }
    review_packet = tmp_path / "review.json"
    review_packet.write_bytes(_canonical(review_value))
    review_packet.chmod(0o644)
    complete_runtime = updater.writer_v1.Runtime(
        now=lambda: updater.writer_v1.datetime(
            2026, 8, 12, 12, 30, tzinfo=updater.writer_v1.timezone.utc
        )
    )
    assert updater.complete(
        review_packet, runtime=complete_runtime, lock_runtime=lock_runtime
    ) == {"sequence": 4, "status": "PASS", "task_id": "T-002"}
    assert validator.validate_ledger(repo) == {
        "proofs": 1,
        "sequence": 4,
        "status": "PASS",
    }
    completed_raw = (repo / runner.PROGRESS_PATH).read_bytes()
    assert updater.complete(
        review_packet, runtime=complete_runtime, lock_runtime=lock_runtime
    ) == {"sequence": 4, "status": "RECOVERED_COMMITTED", "task_id": "T-002"}
    assert (repo / runner.PROGRESS_PATH).read_bytes() == completed_raw
