from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
MANIFEST = REPO_ROOT / "specs/subject-distillation/baseline-manifest.json"
TASKS = REPO_ROOT / "specs/subject-distillation/tasks.md"
SCHEMA = REPO_ROOT / "specs/subject-distillation/implementation-progress.schema.json"
PROGRESS = REPO_ROOT / "specs/subject-distillation/implementation-progress.json"
VALIDATOR = REPO_ROOT / "scripts/validate_subject_progress.py"
WRITER = REPO_ROOT / "scripts/update_subject_progress.py"


def _run(*args: str) -> subprocess.CompletedProcess[bytes]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [PYTHON, *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        check=False,
        timeout=20,
    )


def _validator_args(progress: Path, schema: Path = SCHEMA) -> tuple[str, ...]:
    return (
        str(VALIDATOR),
        "--manifest",
        str(MANIFEST),
        "--schema",
        str(schema),
        "--tasks",
        str(TASKS),
        "--progress",
        str(progress),
    )


def _load_writer():
    spec = importlib.util.spec_from_file_location("subject_progress_writer", WRITER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_progress_validator():
    spec = importlib.util.spec_from_file_location("subject_progress_validator", VALIDATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _test_paths(writer, tmp_path: Path):
    progress_path = tmp_path / "implementation-progress.json"
    return writer.Paths(
        REPO_ROOT,
        MANIFEST,
        SCHEMA,
        TASKS,
        progress_path,
        tmp_path / ".implementation-progress.pending",
    )


def _runtime(writer):
    return writer.Runtime(
        now=lambda: datetime(2026, 8, 11, 8, 0, 0, tzinfo=timezone.utc)
    )


def test_progress_artifacts_exist_with_expected_modes() -> None:
    assert VALIDATOR.is_file() and VALIDATOR.stat().st_mode & 0o777 == 0o755
    assert WRITER.is_file() and WRITER.stat().st_mode & 0o777 == 0o755
    assert SCHEMA.is_file() and SCHEMA.stat().st_mode & 0o777 == 0o644
    assert PROGRESS.is_file() and PROGRESS.stat().st_mode & 0o777 == 0o644


def test_seed_ledger_is_strict_and_in_progress() -> None:
    result = _run(*_validator_args(PROGRESS))
    assert result.returncode == 0
    assert result.stderr == b""
    payload = json.loads(result.stdout)
    assert payload == {
        "baseline_id": "5dd83dd8b3d3696a",
        "sequence": 1,
        "status": "PASS",
    }
    ledger = json.loads(PROGRESS.read_text(encoding="utf-8"))
    assert ledger["tasks"]["T-001"] == "IN_PROGRESS"
    assert set(ledger["tasks"].values()) == {"PENDING", "IN_PROGRESS"}
    assert ledger["events"][0]["from"] == "PENDING"
    assert ledger["events"][0]["to"] == "IN_PROGRESS"


def test_seed_time_is_not_before_fresh_authorization() -> None:
    validator = _load_progress_validator()
    value = json.loads(PROGRESS.read_text(encoding="utf-8"))
    environment = json.loads(
        (
            REPO_ROOT
            / "specs/subject-distillation/evidence/5dd83dd8b3d3696a/environment.json"
        ).read_text(encoding="utf-8")
    )
    recorded = datetime.strptime(
        environment["implementation_authorization"]["recorded_at_utc"],
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc)
    manifest, tasks_sha256 = _validation_inputs(validator)

    equal = deepcopy(value)
    equal_time = recorded.strftime("%Y-%m-%dT%H:%M:%SZ")
    equal["events"][0]["at_utc"] = equal_time
    equal["updated_at_utc"] = equal_time
    assert validator.validate_value(
        equal,
        repo_root=REPO_ROOT,
        manifest_result=manifest,
        tasks_sha256=tasks_sha256,
    )["status"] == "PASS"

    before = deepcopy(equal)
    before_time = (recorded - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    before["events"][0]["at_utc"] = before_time
    before["updated_at_utc"] = before_time
    with pytest.raises(validator.Denied):
        validator.validate_value(
            before,
            repo_root=REPO_ROOT,
            manifest_result=manifest,
            tasks_sha256=tasks_sha256,
        )


def test_writer_init_creates_exact_seed_and_recovers_exact_reinit(tmp_path: Path) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path)
    result = writer.init(paths, _runtime(writer))
    assert result == {
        "sequence": 1,
        "status": "PASS",
        "task_id": "T-001",
    }
    assert paths.progress.stat().st_mode & 0o777 == 0o644
    assert writer._existing(paths)["tasks"]["T-001"] == "IN_PROGRESS"
    assert writer.init(paths, _runtime(writer)) == {
        "sequence": 1,
        "status": "RECOVERED_COMMITTED",
        "task_id": "T-001",
    }


def test_writer_rejects_stale_expected_state_without_changing_bytes(tmp_path: Path) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path)
    writer.init(paths, _runtime(writer))
    before = paths.progress.read_bytes()
    with pytest.raises(writer.Denied):
        writer.transition(
            paths,
            _runtime(writer),
            task="T-001",
            expected="PENDING",
            target="BLOCKED",
            repo_refs=[],
            opaque_refs=[],
            blocker="TEST_BLOCKER",
            source_review_packet=None,
        )
    assert paths.progress.read_bytes() == before


def test_progress_parser_rejects_duplicate_keys_and_secret_markers(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_bytes(b'{"schema_version":1,"schema_version":1}\n')
    assert _run(*_validator_args(duplicate)).returncode == 2

    value = json.loads(PROGRESS.read_text(encoding="utf-8"))
    value["events"][0]["evidence_refs"] = [
        {"kind": "opaque", "id": "prefix-sk_test_example"}
    ]
    unsafe = tmp_path / "unsafe.json"
    unsafe.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    result = _run(*_validator_args(unsafe))
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == b"SUBJECT_PROGRESS_DENY\n"


def test_progress_parser_exact_depth_node_and_container_boundaries() -> None:
    validator = _load_progress_validator()
    parser = validator.authorization._parse
    canonical = validator.evidence._canonical

    depth_value: object = 0
    for _ in range(31):
        depth_value = [depth_value]
    parser(canonical(depth_value))
    with pytest.raises(validator.authorization.Denied):
        parser(canonical([depth_value]))

    parser(canonical([0] * 4_096))
    with pytest.raises(validator.authorization.Denied):
        parser(canonical([0] * 4_097))

    exact_nodes = [[0] * 4_095 for _ in range(7)] + [[0] * 4_094]
    parser(canonical(exact_nodes))
    exact_nodes[-1].append(0)
    with pytest.raises(validator.authorization.Denied):
        parser(canonical(exact_nodes))


def test_progress_owner_covers_complete_shared_digest_and_key_scanner() -> None:
    validator = _load_progress_validator()
    scanner = validator.authorization
    assert len(scanner.DIGEST_KEYS) == 22
    for key in scanner.DIGEST_KEYS:
        scanner._scan({key: "a" * 64})
        for invalid in ("A" * 64, "a" * 63, "a" * 65):
            with pytest.raises(scanner.Denied):
                scanner._scan({key: invalid})
    for key in scanner.FORBIDDEN_KEYS:
        variants = {
            key,
            key.upper(),
            key.replace("_", "."),
            key.replace("_", "-"),
            key.replace("_", "__"),
        }
        for variant in variants:
            with pytest.raises(scanner.Denied):
                scanner._scan({variant: "public"})
    scanner._scan({scanner.DOMAIN_KEY: scanner.DOMAIN_HEX})
    for key in (
        scanner.DOMAIN_KEY.upper(),
        scanner.DOMAIN_KEY.replace("_", "."),
        scanner.DOMAIN_KEY.replace("_", "-"),
        scanner.DOMAIN_KEY.replace("_", "__"),
    ):
        with pytest.raises(scanner.Denied):
            scanner._scan({key: scanner.DOMAIN_HEX})
    for value in (
        scanner.DOMAIN_HEX.upper(),
        "0" + scanner.DOMAIN_HEX,
        scanner.DOMAIN_HEX + "0",
        scanner.DOMAIN_HEX[:-1],
        scanner.DOMAIN_HEX[:-1] + ("0" if scanner.DOMAIN_HEX[-1] != "0" else "1"),
    ):
        with pytest.raises(scanner.Denied):
            scanner._scan({scanner.DOMAIN_KEY: value})
    private_ref = "private-shadow-pass:" + "a" * 64
    scanner._scan({"id": private_ref})
    for invalid in (private_ref.upper(), private_ref + "x", "x" + private_ref):
        with pytest.raises(scanner.Denied):
            scanner._scan({"id": invalid})
    scanner._scan({"ordinary": "four.part.public.identifier"})
    for length in (32, 64, 128):
        with pytest.raises(scanner.Denied):
            scanner._scan({"ordinary": "a" * length})


@pytest.mark.parametrize(
    "value",
    [
        "gho_example",
        "prefix gho_example",
        "sk_test_example",
        "prefix sk_test_example",
        "rk_test_example",
        "prefix rk_test_example",
        "whsec_example",
        "prefix whsec_example",
        "Bearer:value",
        "prefix Bearer:value",
        "abc.def.ghi",
        "prefix abc.def.ghi",
        "client_secret=value",
        "prefix --client-secret=value",
        "-----BEGIN PRIVATE KEY-----",
        "prefix -----BEGIN PRIVATE KEY----- suffix",
    ],
)
def test_progress_owner_covers_embedded_scanner_families(value: str) -> None:
    validator = _load_progress_validator()
    with pytest.raises(validator.authorization.Denied):
        validator.authorization._scan({"ordinary": value})


def test_repo_file_ref_rejects_symlink_target(tmp_path: Path) -> None:
    target = REPO_ROOT / "specs/subject-distillation/tasks.md"
    alias = tmp_path / "alias"
    alias.symlink_to(target)
    value = json.loads(PROGRESS.read_text(encoding="utf-8"))
    value["events"][0]["evidence_refs"] = [
        {"kind": "repo_file", "path": str(alias), "sha256": "0" * 64}
    ]
    candidate = tmp_path / "symlink-ref.json"
    candidate.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    assert _run(*_validator_args(candidate)).returncode == 2


def test_progress_schema_is_exact_and_closed() -> None:
    validator = _load_progress_validator()
    raw = SCHEMA.read_bytes()
    expected = validator._expected_schema()
    assert raw == validator.evidence._canonical(expected)
    assert expected["additionalProperties"] is False
    assert expected["properties"]["tasks"]["additionalProperties"] is False
    assert expected["properties"]["events"]["items"]["additionalProperties"] is False
    assert expected["properties"]["events"]["maxItems"] == 4096
    assert expected["properties"]["events"]["items"]["properties"]["sequence"][
        "maximum"
    ] == 4096


def test_progress_cli_binds_fixed_path_and_rejects_duplicate_scalar(
    tmp_path: Path,
) -> None:
    copied = tmp_path / "implementation-progress.json"
    copied.write_bytes(PROGRESS.read_bytes())
    copied.chmod(0o644)
    result = _run(*_validator_args(copied))
    assert (result.returncode, result.stdout, result.stderr) == (
        2,
        b"",
        b"SUBJECT_PROGRESS_DENY\n",
    )
    duplicate = _run(*_validator_args(PROGRESS), "--progress", str(PROGRESS))
    assert (duplicate.returncode, duplicate.stdout, duplicate.stderr) == (
        2,
        b"",
        b"SUBJECT_PROGRESS_DENY\n",
    )


def _validation_inputs(validator):
    manifest = validator.baseline.validate(MANIFEST, REPO_ROOT)
    tasks_sha256 = hashlib.sha256(TASKS.read_bytes()).hexdigest()
    return manifest, tasks_sha256


@pytest.mark.parametrize(
    "mutation",
    [
        "boolean-sequence",
        "sequence-gap",
        "tasks-mismatch",
        "backward-time",
        "completed-without-evidence",
        "dependency-bypass",
        "two-in-progress",
        "noncanonical-refs",
    ],
)
def test_progress_replay_and_dependency_mutations_deny(mutation: str) -> None:
    validator = _load_progress_validator()
    value = json.loads(PROGRESS.read_text(encoding="utf-8"))
    event = value["events"][0]
    if mutation == "boolean-sequence":
        event["sequence"] = True
    elif mutation == "sequence-gap":
        event["sequence"] = 2
    elif mutation == "tasks-mismatch":
        value["tasks"]["T-002"] = "COMPLETED"
    elif mutation == "backward-time":
        value["updated_at_utc"] = "2026-01-01T00:00:00Z"
    elif mutation == "completed-without-evidence":
        event["to"] = "COMPLETED"
        value["tasks"]["T-001"] = "COMPLETED"
    elif mutation == "dependency-bypass":
        second = deepcopy(event)
        second.update(
            {
                "sequence": 2,
                "task_id": "T-002",
                "from": "PENDING",
                "to": "IN_PROGRESS",
                "at_utc": event["at_utc"],
            }
        )
        value["events"].append(second)
        value["tasks"]["T-002"] = "IN_PROGRESS"
    elif mutation == "two-in-progress":
        second = deepcopy(event)
        second.update(
            {
                "sequence": 2,
                "task_id": "T-003",
                "from": "PENDING",
                "to": "IN_PROGRESS",
                "at_utc": event["at_utc"],
            }
        )
        value["events"].append(second)
        value["tasks"]["T-003"] = "IN_PROGRESS"
    else:
        event["evidence_refs"] = [
            {"kind": "opaque", "id": "z"},
            {"kind": "opaque", "id": "a"},
        ]
    manifest, tasks_sha256 = _validation_inputs(validator)
    with pytest.raises(validator.Denied):
        validator.validate_value(
            value,
            repo_root=REPO_ROOT,
            manifest_result=manifest,
            tasks_sha256=tasks_sha256,
        )


def test_regular_repo_file_ref_allows_exact_hash() -> None:
    validator = _load_progress_validator()
    value = json.loads(PROGRESS.read_text(encoding="utf-8"))
    digest = hashlib.sha256(TASKS.read_bytes()).hexdigest()
    value["events"][0]["evidence_refs"] = [
        {
            "kind": "repo_file",
            "path": "specs/subject-distillation/tasks.md",
            "sha256": digest,
        }
    ]
    manifest, tasks_sha256 = _validation_inputs(validator)
    assert validator.validate_value(
        value,
        repo_root=REPO_ROOT,
        manifest_result=manifest,
        tasks_sha256=tasks_sha256,
    )["status"] == "PASS"


def test_t033_completed_replay_automatically_invokes_final_gate(monkeypatch) -> None:
    validator = _load_progress_validator()
    seed = json.loads(PROGRESS.read_text(encoding="utf-8"))
    value = {
        "schema_version": seed["schema_version"],
        "baseline_id": seed["baseline_id"],
        "baseline_full_digest": seed["baseline_full_digest"],
        "tasks_sha256": seed["tasks_sha256"],
        "updated_at_utc": "2026-08-11T08:00:00Z",
        "tasks": {task: "PENDING" for task in validator.TASK_IDS},
        "events": [],
    }

    def append(task: str, before: str, after: str, refs, blocker=None) -> None:
        value["events"].append(
            {
                "sequence": len(value["events"]) + 1,
                "task_id": task,
                "from": before,
                "to": after,
                "at_utc": "2026-08-11T08:00:00Z",
                "evidence_refs": refs,
                "blocker": blocker,
            }
        )
        value["tasks"][task] = after

    for task in validator.TASK_IDS[:31]:
        append(task, "PENDING", "IN_PROGRESS", [])
        append(
            task,
            "IN_PROGRESS",
            "COMPLETED",
            [{"kind": "opaque", "id": f"evidence:{task}"}],
        )
    append("T-032", "PENDING", "BLOCKED", [], "PRIVATE_GATE_NOT_RUN")
    append("T-033", "PENDING", "IN_PROGRESS", [])
    append(
        "T-033",
        "IN_PROGRESS",
        "COMPLETED",
        [{"kind": "opaque", "id": "attestation:synthetic"}],
    )
    called = []

    def final_gate(candidate, *, repo_root, manifest_result, private_inputs):
        called.append((candidate, repo_root, manifest_result, private_inputs))

    monkeypatch.setattr(validator, "_final_gate", final_gate)
    manifest, tasks_sha256 = _validation_inputs(validator)
    assert validator.validate_value(
        value,
        repo_root=REPO_ROOT,
        manifest_result=manifest,
        tasks_sha256=tasks_sha256,
    )["status"] == "PASS"
    assert len(called) == 1
    assert called[0][3] == (None, None, None, None)


def test_private_gate_inputs_must_be_external_and_identity_stable(
    tmp_path: Path,
) -> None:
    validator = _load_progress_validator()
    repo_file = REPO_ROOT / "specs/subject-distillation/tasks.md"
    with pytest.raises(validator.Denied):
        validator._open_private_inputs(
            REPO_ROOT,
            tuple(os.fspath(repo_file) for _ in range(4)),
        )

    private_files = []
    for index in range(4):
        private_file = tmp_path / f"private-{index}"
        private_file.write_bytes(b"public-safe-synthetic")
        private_file.chmod(0o700 if index == 0 else 0o600)
        private_files.append(private_file)
    handles, _raws, owned = validator._open_private_inputs(
        REPO_ROOT,
        tuple(os.fspath(item) for item in private_files),
    )
    try:
        private_files[1].unlink()
        private_files[1].write_bytes(b"replacement")
        private_files[1].chmod(0o600)
        with pytest.raises(validator.Denied):
            validator._audit_private_inputs(handles)
    finally:
        for fd in reversed(owned):
            os.close(fd)


PRIVATE_KEY_HEX = "ab" * 32
PRIVATE_DOMAIN = b"vault-subject-private-shadow-release-v1\x00"


def _canonical_core(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _private_config(*, count: int = 1) -> dict[str, object]:
    return {
        "schema_version": 1,
        "artifact_kind": "subject-distillation-private-shadow-verifier-config",
        "keys": [
            {
                "key_id": f"operator-key-{index:02d}",
                "hmac_sha256_key_hex": PRIVATE_KEY_HEX,
            }
            for index in range(count)
        ],
    }


def _private_receipt(*, key_id: str = "operator-key-00") -> dict[str, object]:
    receipt = {
        "schema_version": 1,
        "artifact_kind": "private-shadow-release",
        "verdict": "PASS",
        "gate_version": "gate-v1",
        "scorecard_sha256": "1" * 64,
        "manifest_sha256": "2" * 64,
        "subject_controller_signoff_id": "controller-signoff",
        "fresh_reviewer_signoff_id": "reviewer-signoff",
        "created_at_utc": "2026-08-10T00:00:00Z",
        "key_id": key_id,
    }
    receipt["receipt_hmac_sha256"] = hmac.new(
        bytes.fromhex(PRIVATE_KEY_HEX),
        PRIVATE_DOMAIN + _canonical_core(receipt),
        hashlib.sha256,
    ).hexdigest()
    return receipt


def _exercise_private_gate(validator, tmp_path: Path, monkeypatch, receipt) -> None:
    private_paths = [tmp_path / name for name in ("verifier", "gate", "config", "receipt")]
    receipt_raw = validator.evidence._canonical(receipt)
    config_raw = _canonical_core(_private_config())
    digest = hashlib.sha256(receipt_raw).hexdigest()
    for index, private_path in enumerate(private_paths):
        private_path.write_bytes(
            receipt_raw
            if index == 3
            else config_raw
            if index == 2
            else b"synthetic-private-input"
        )
        private_path.chmod(0o700 if index == 0 else 0o600)

    completed = validator._PrivateChildResult(
        returncode=0,
        stdout=f"private-shadow-pass:{digest}\n".encode("ascii"),
        stderr=b"",
    )
    monkeypatch.setattr(validator, "_run_private_child", lambda *_args, **_kwargs: completed)
    value = {
        "tasks": {"T-032": "COMPLETED"},
        "events": [
            {
                "task_id": "T-032",
                "to": "COMPLETED",
                "evidence_refs": [
                    {"kind": "opaque", "id": f"private-shadow-pass:{digest}"}
                ],
            }
        ],
    }
    attestation = {
        "release_label": "stable",
        "private_shadow_receipt_sha256": digest,
    }
    validator._private_gate(
        value,
        attestation,
        tuple(os.fspath(item) for item in private_paths),
        REPO_ROOT,
    )


def test_private_gate_accepts_exact_closed_receipt_without_public_scanner(
    tmp_path: Path, monkeypatch
) -> None:
    validator = _load_progress_validator()
    _exercise_private_gate(validator, tmp_path, monkeypatch, _private_receipt())


@pytest.mark.parametrize("count", [1, 64])
def test_private_config_accepts_exact_sorted_bounds(count: int) -> None:
    validator = _load_progress_validator()
    value = _private_config(count=count)
    keys = validator._private_config_keys(_canonical_core(value))
    assert len(keys) == count
    assert keys["operator-key-00"] == bytes.fromhex(PRIVATE_KEY_HEX)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(keys=[]),
        lambda value: value.update(keys=_private_config(count=65)["keys"]),
        lambda value: value["keys"].reverse(),
        lambda value: value["keys"].append(dict(value["keys"][0])),
        lambda value: value.update(extra=True),
        lambda value: value["keys"][0].update(hmac_sha256_key_hex="AB" * 32),
        lambda value: value["keys"][0].update(hmac_sha256_key_hex="ab" * 31),
    ],
)
def test_private_config_rejects_closed_shape_and_key_mutations(mutation) -> None:
    validator = _load_progress_validator()
    value = _private_config(count=2)
    mutation(value)
    with pytest.raises(validator.Denied):
        validator._private_config_keys(_canonical_core(value))


@pytest.mark.parametrize(
    "raw",
    [
        _canonical_core(_private_config()) + b"\n",
        (
            b'{"artifact_kind":"subject-distillation-private-shadow-verifier-config",'
            b'"keys":[],"schema_version":1,"schema_version":1}'
        ),
    ],
)
def test_private_config_rejects_lf_and_duplicate_keys(raw: bytes) -> None:
    validator = _load_progress_validator()
    with pytest.raises(validator.Denied):
        validator._private_config_keys(raw)


@pytest.mark.parametrize("mutation", ["wrong-mac", "plain-sha", "unknown-key"])
def test_private_gate_independently_rejects_invalid_hmac_after_child_pass(
    tmp_path: Path, monkeypatch, mutation: str
) -> None:
    validator = _load_progress_validator()
    receipt = _private_receipt()
    if mutation == "wrong-mac":
        receipt["receipt_hmac_sha256"] = "0" * 64
    elif mutation == "plain-sha":
        without = dict(receipt)
        without.pop("receipt_hmac_sha256")
        receipt["receipt_hmac_sha256"] = hashlib.sha256(
            PRIVATE_DOMAIN + _canonical_core(without)
        ).hexdigest()
    else:
        receipt = _private_receipt(key_id="missing-key")
    with pytest.raises(validator.Denied):
        _exercise_private_gate(validator, tmp_path, monkeypatch, receipt)


def test_private_child_reader_enforces_exact_caps_and_deadline() -> None:
    validator = _load_progress_validator()
    valid = validator._run_private_child(
        [sys.executable, "-c", "import os;os.write(1,b'x'*85)"],
        timeout_seconds=2.0,
        terminate_grace_seconds=0.1,
    )
    assert valid.stdout == b"x" * 85 and valid.stderr == b""
    stderr_boundary = validator._run_private_child(
        [sys.executable, "-c", "import os;os.write(2,b'x'*96)"],
        timeout_seconds=2.0,
        terminate_grace_seconds=0.1,
    )
    assert stderr_boundary.stdout == b""
    assert stderr_boundary.stderr == b"x" * 96
    for fd, size in ((1, 86), (2, 97)):
        script = f"import os;os.write({fd},b'x'*{size})"
        with pytest.raises(validator.Denied):
            validator._run_private_child(
                [sys.executable, "-c", script],
                timeout_seconds=2.0,
                terminate_grace_seconds=0.1,
            )
    with pytest.raises(validator.Denied):
        validator._run_private_child(
            [sys.executable, "-c", "import time;time.sleep(2)"],
            timeout_seconds=0.05,
            terminate_grace_seconds=0.05,
        )


def test_private_child_cleanup_fault_still_closes_local_resources(
    monkeypatch,
) -> None:
    validator = _load_progress_validator()
    selectors_seen = []
    children = []
    original_selector = validator.selectors.DefaultSelector
    original_popen = validator.subprocess.Popen

    class TrackingSelector:
        def __init__(self):
            self.inner = original_selector()
            self.closed = False
            self.buffers = []

        def register(self, fileobj, events, data=None):
            self.buffers.append(data[0])
            return self.inner.register(fileobj, events, data)

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def close(self):
            self.closed = True
            self.inner.close()

    def selector_factory():
        selector = TrackingSelector()
        selectors_seen.append(selector)
        return selector

    def tracked_popen(*args, **kwargs):
        child = original_popen(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(validator.selectors, "DefaultSelector", selector_factory)
    monkeypatch.setattr(validator.subprocess, "Popen", tracked_popen)
    monkeypatch.setattr(
        validator,
        "_terminate_private_child",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(validator.Denied()),
    )
    try:
        with pytest.raises(validator.Denied):
            validator._run_private_child(
                [sys.executable, "-c", "import time;time.sleep(10)"],
                timeout_seconds=0.05,
                terminate_grace_seconds=0.05,
            )
        assert selectors_seen and selectors_seen[0].closed
        assert all(not buffer for buffer in selectors_seen[0].buffers)
        assert children[0].stdout is not None and children[0].stdout.closed
        assert children[0].stderr is not None and children[0].stderr.closed
    finally:
        if children and children[0].poll() is None:
            os.killpg(children[0].pid, signal.SIGKILL)
            children[0].wait(timeout=2)


def test_private_child_timeout_does_not_echo_or_mutate_repo(
    capsys,
) -> None:
    validator = _load_progress_validator()
    before = PROGRESS.read_bytes()
    marker = "synthetic-private-marker"
    with pytest.raises(validator.Denied):
        validator._run_private_child(
            [
                sys.executable,
                "-c",
                f"import os,time;os.write(1,{marker!r}.encode());time.sleep(10)",
            ],
            timeout_seconds=0.05,
            terminate_grace_seconds=0.05,
        )
    captured = capsys.readouterr()
    assert marker not in captured.out + captured.err
    assert captured == ("", "")
    assert PROGRESS.read_bytes() == before


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@pytest.mark.parametrize("close_pipes", [False, True])
def test_private_child_cleanup_kills_leader_first_descendant_group(
    tmp_path: Path, close_pipes: bool
) -> None:
    validator = _load_progress_validator()
    pid_file = tmp_path / "descendant.pid"
    script = (
        "import os,signal,time,sys;"
        "pid=os.fork();"
        "(os.close(1),os.close(2)) if pid==0 and sys.argv[2]=='close' else None;"
        "signal.signal(signal.SIGTERM,signal.SIG_IGN) if pid==0 else None;"
        "open(sys.argv[1],'w').write(str(os.getpid())) if pid==0 else None;"
        "time.sleep(10) if pid==0 else None;"
        "os._exit(0 if pid==0 else 7)"
    )
    with pytest.raises(validator.Denied):
        validator._run_private_child(
            [
                sys.executable,
                "-c",
                script,
                os.fspath(pid_file),
                "close" if close_pipes else "hold",
            ],
            timeout_seconds=0.15,
            terminate_grace_seconds=0.05,
        )
    deadline = time.monotonic() + 1.0
    while not pid_file.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert pid_file.exists()
    pid = int(pid_file.read_text())
    while _pid_exists(pid) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not _pid_exists(pid)


def test_private_child_cross_pipe_stall_is_bounded_and_kills_group(
    tmp_path: Path,
) -> None:
    validator = _load_progress_validator()
    pid_file = tmp_path / "cross-pipe-descendant.pid"
    script = (
        "import os,signal,time,sys;"
        "pid=os.fork();"
        "os.close(1) if pid==0 else os.write(1,b'x'*85);"
        "signal.signal(signal.SIGTERM,signal.SIG_IGN) if pid==0 else None;"
        "open(sys.argv[1],'w').write(str(os.getpid())) if pid==0 else None;"
        "time.sleep(10) if pid==0 else None;"
        "os._exit(0)"
    )
    with pytest.raises(validator.Denied):
        validator._run_private_child(
            [sys.executable, "-c", script, os.fspath(pid_file)],
            timeout_seconds=0.15,
            terminate_grace_seconds=0.05,
        )
    deadline = time.monotonic() + 1.0
    while not pid_file.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert pid_file.exists()
    pid = int(pid_file.read_text())
    while _pid_exists(pid) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not _pid_exists(pid)


def test_private_gate_executes_retained_verifier_not_swapped_path(
    tmp_path: Path, monkeypatch
) -> None:
    validator = _load_progress_validator()
    receipt = _private_receipt()
    receipt_raw = validator.evidence._canonical(receipt)
    digest = hashlib.sha256(receipt_raw).hexdigest()
    config_raw = _canonical_core(_private_config())
    marker = tmp_path / "replacement-executed"
    verifier = tmp_path / "verifier"
    gate = tmp_path / "gate"
    config = tmp_path / "config"
    receipt_path = tmp_path / "receipt"
    verifier.write_text(
        "#!/bin/sh\nprintf 'private-shadow-pass:%s\\n' '" + digest + "'\n"
    )
    verifier.chmod(0o700)
    gate.write_bytes(b"synthetic-gate")
    gate.chmod(0o600)
    config.write_bytes(config_raw)
    config.chmod(0o600)
    receipt_path.write_bytes(receipt_raw)
    receipt_path.chmod(0o600)
    original_run = validator._run_private_child

    def swap_then_run(argv, **kwargs):
        held = verifier.with_name("verifier-held")
        verifier.rename(held)
        verifier.write_text(
            "#!/bin/sh\n"
            f"touch '{marker}'\n"
            "printf 'private-shadow-pass:%s\\n' '" + digest + "'\n"
        )
        verifier.chmod(0o700)
        try:
            return original_run(argv, **kwargs)
        finally:
            verifier.unlink()
            held.rename(verifier)

    monkeypatch.setattr(validator, "_run_private_child", swap_then_run)
    value = {
        "tasks": {"T-032": "COMPLETED"},
        "events": [
            {
                "task_id": "T-032",
                "to": "COMPLETED",
                "evidence_refs": [
                    {"kind": "opaque", "id": f"private-shadow-pass:{digest}"}
                ],
            }
        ],
    }
    attestation = {
        "release_label": "stable",
        "private_shadow_receipt_sha256": digest,
    }
    with pytest.raises(validator.Denied):
        validator._private_gate(
            value,
            attestation,
            tuple(os.fspath(item) for item in (verifier, gate, config, receipt_path)),
            REPO_ROOT,
        )
    assert not marker.exists()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update({"api_key": "rk_test_synthetic"}),
        lambda value: value.update({"scorecard_sha256": "A" * 64}),
        lambda value: value.update(
            {"fresh_reviewer_signoff_id": value["subject_controller_signoff_id"]}
        ),
    ],
)
def test_private_gate_rejects_extra_secret_carrier_and_malformed_receipt(
    tmp_path: Path, monkeypatch, mutation
) -> None:
    validator = _load_progress_validator()
    receipt = _private_receipt()
    mutation(receipt)
    with pytest.raises(validator.Denied):
        _exercise_private_gate(validator, tmp_path, monkeypatch, receipt)


def test_private_gate_rejects_child_path_swap_restore_even_with_mtime_restore(
    tmp_path: Path, monkeypatch
) -> None:
    validator = _load_progress_validator()
    receipt = _private_receipt()
    receipt_raw = validator.evidence._canonical(receipt)
    config_raw = _canonical_core(_private_config())
    digest = hashlib.sha256(receipt_raw).hexdigest()
    private_paths = [tmp_path / name for name in ("verifier", "gate", "config", "receipt")]
    for index, private_path in enumerate(private_paths):
        private_path.write_bytes(
            receipt_raw
            if index == 3
            else config_raw
            if index == 2
            else b"synthetic-private-input"
        )
        private_path.chmod(0o700 if index == 0 else 0o600)
    completed = validator._PrivateChildResult(
        returncode=0,
        stdout=f"private-shadow-pass:{digest}\n".encode("ascii"),
        stderr=b"",
    )

    def swap_restore(*_args, **_kwargs):
        target = private_paths[2]
        before = target.stat()
        held = target.with_name("config-held")
        target.rename(held)
        target.write_bytes(b"replacement-private-input")
        target.chmod(0o600)
        target.unlink()
        held.rename(target)
        os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
        return completed

    monkeypatch.setattr(validator, "_run_private_child", swap_restore)
    value = {
        "tasks": {"T-032": "COMPLETED"},
        "events": [
            {
                "task_id": "T-032",
                "to": "COMPLETED",
                "evidence_refs": [
                    {"kind": "opaque", "id": f"private-shadow-pass:{digest}"}
                ],
            }
        ],
    }
    attestation = {
        "release_label": "stable",
        "private_shadow_receipt_sha256": digest,
    }
    with pytest.raises(validator.Denied):
        validator._private_gate(
            value,
            attestation,
            tuple(os.fspath(item) for item in private_paths),
            REPO_ROOT,
        )


def test_atomic_writer_routes_attester_private_context_to_final_validator(
    tmp_path: Path, monkeypatch
) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path)
    candidate = writer._seed(paths, _runtime(writer))
    expected = ("verifier", "gate", "config", "receipt")
    seen = []

    def validate_value(value, **kwargs):
        seen.append(kwargs["private_inputs"])
        return {"baseline_id": value["baseline_id"], "status": "PASS"}

    monkeypatch.setattr(writer.progress, "validate_value", validate_value)
    writer._validate_candidate(paths, candidate, private_inputs=expected)
    assert seen == [expected]


def test_t033_completion_has_no_public_cli_or_forgeable_capability(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path)
    kwargs = {
        "task": "T-033",
        "expected": "IN_PROGRESS",
        "target": "COMPLETED",
        "repo_refs": [],
        "opaque_refs": ["attestation:synthetic"],
        "blocker": None,
    }
    with pytest.raises(writer.Denied):
        writer.transition(
            paths,
            _runtime(writer),
            source_review_packet=None,
            **kwargs,
        )
    assert not hasattr(writer, "_ATTESTER_CAPABILITY")
    assert writer.main(
        [
            "transition",
            "--task",
            "T-033",
            "--expected",
            "IN_PROGRESS",
            "--to",
            "COMPLETED",
            "--opaque-ref",
            "attestation:synthetic",
            "--json",
        ]
    ) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == writer.DENY_TEXT

    seen = []

    def transition_impl(*args, **inner_kwargs):
        seen.append((args, inner_kwargs))
        return {"sequence": 64, "status": "PASS", "task_id": "T-033"}

    monkeypatch.setattr(writer, "_transition_impl", transition_impl)
    result = writer._finalize_attested_t033(
        paths,
        _runtime(writer),
        private_inputs=writer.PRIVATE_NONE,
        **kwargs,
    )
    assert result == {"sequence": 64, "status": "PASS", "task_id": "T-033"}
    assert seen[0][1]["source_review_packet"] is None
    assert seen[0][1]["private_inputs"] == writer.PRIVATE_NONE
    stable_inputs = ("verifier", "gate", "config", "receipt")
    writer._finalize_attested_t033(
        paths,
        _runtime(writer),
        private_inputs=stable_inputs,
        **kwargs,
    )
    assert seen[1][1]["private_inputs"] == stable_inputs


def test_repo_file_ref_rejects_symlink_and_hash_drift_directly(tmp_path: Path) -> None:
    validator = _load_progress_validator()
    target = tmp_path / "target"
    target.write_bytes(b"public")
    alias = tmp_path / "alias"
    alias.symlink_to(target)
    with pytest.raises(validator.Denied):
        validator._validate_repo_path(tmp_path, "alias", hashlib.sha256(b"public").hexdigest())
    with pytest.raises(validator.Denied):
        validator._validate_repo_path(tmp_path, "target", "0" * 64)


def test_repo_file_ref_rejects_parent_symlink_escape_and_nonregular(
    tmp_path: Path,
) -> None:
    validator = _load_progress_validator()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "file").write_bytes(b"public")
    (tmp_path / "alias").symlink_to(outside, target_is_directory=True)
    digest = hashlib.sha256(b"public").hexdigest()
    for path in ("alias/file", "../outside/file", "/absolute", "outside"):
        with pytest.raises(validator.Denied):
            validator._validate_repo_path(tmp_path, path, digest)


def test_repo_file_ref_exact_sixteen_mebibyte_boundary(tmp_path: Path) -> None:
    validator = _load_progress_validator()
    target = tmp_path / "large-evidence.txt"
    raw = b"x" * 16_777_216
    target.write_bytes(raw)
    validator._validate_repo_path(
        tmp_path, target.name, hashlib.sha256(raw).hexdigest()
    )
    with target.open("ab") as stream:
        stream.write(b"x")
    with pytest.raises(validator.Denied):
        validator._validate_repo_path(tmp_path, target.name, "0" * 64)


def test_writer_short_write_and_replace_failure_preserve_old_bytes(tmp_path: Path) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path)
    bad_write = writer.Runtime(
        now=lambda: datetime(2026, 8, 11, 8, 0, 0, tzinfo=timezone.utc),
        write=lambda _fd, _raw: 0,
    )
    with pytest.raises(RuntimeError):
        writer.init(paths, bad_write)
    assert not paths.progress.exists()
    assert not paths.pending.exists()

    writer.init(paths, _runtime(writer))
    before = paths.progress.read_bytes()

    def fail_replace(*_args, **_kwargs):
        raise OSError

    replace_failure = writer.Runtime(
        now=lambda: datetime(2026, 8, 11, 8, 0, 1, tzinfo=timezone.utc),
        replace=fail_replace,
    )
    with pytest.raises(OSError):
        writer.transition(
            paths,
            replace_failure,
            task="T-001",
            expected="IN_PROGRESS",
            target="BLOCKED",
            repo_refs=[],
            opaque_refs=[],
            blocker="TEST_BLOCKER",
            source_review_packet=None,
        )
    assert paths.progress.read_bytes() == before
    assert not paths.pending.exists()


def test_writer_file_fsync_and_candidate_validation_faults_leave_no_partial(
    tmp_path: Path, monkeypatch
) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path / "fsync")
    paths.progress.parent.mkdir()
    fsync_failure = writer.Runtime(
        now=lambda: datetime(2026, 8, 11, 8, 0, 0, tzinfo=timezone.utc),
        fsync=lambda _fd: (_ for _ in ()).throw(OSError()),
    )
    with pytest.raises(RuntimeError):
        writer.init(paths, fsync_failure)
    assert not paths.progress.exists()
    assert not paths.pending.exists()

    original = writer._validate_candidate
    calls = 0

    def fail_second(candidate_paths, value, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise writer.Denied
        return original(candidate_paths, value, **kwargs)

    monkeypatch.setattr(writer, "_validate_candidate", fail_second)
    with pytest.raises(writer.Denied):
        writer.init(paths, _runtime(writer))
    assert not paths.progress.exists()
    assert not paths.pending.exists()


def test_writer_rejects_symlinked_publication_parent(tmp_path: Path) -> None:
    writer = _load_writer()
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    paths = writer.Paths(
        REPO_ROOT,
        MANIFEST,
        SCHEMA,
        TASKS,
        alias / "implementation-progress.json",
        alias / ".implementation-progress.pending",
    )
    with pytest.raises(writer.Denied):
        writer.init(paths, _runtime(writer))
    assert not (real / "implementation-progress.json").exists()


def test_writer_denies_second_cooperative_process_lease(tmp_path: Path) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path)
    with writer.authorization_runner._authorization_lock(
        os.fspath(REPO_ROOT),
        "subject-progress",
        "5dd83dd8b3d3696a",
        writer.authorization_runner.Runtime(),
    ), pytest.raises(writer.authorization_runner.Denied):
        writer.init(paths, _runtime(writer))
    assert not paths.progress.exists()


def test_writer_directory_fsync_failure_leaves_complete_valid_state(tmp_path: Path) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path)
    calls = 0

    def fsync(fd: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError
        os.fsync(fd)

    runtime = writer.Runtime(
        now=lambda: datetime(2026, 8, 11, 8, 0, 0, tzinfo=timezone.utc),
        fsync=fsync,
    )
    with pytest.raises(OSError):
        writer.init(paths, runtime)
    assert paths.progress.is_file()
    assert not paths.pending.exists()
    assert writer._existing(paths)["tasks"]["T-001"] == "IN_PROGRESS"
    assert writer.init(paths, _runtime(writer)) == {
        "sequence": 1,
        "status": "RECOVERED_COMMITTED",
        "task_id": "T-001",
    }


def test_writer_resumes_matching_retained_init_pending(tmp_path: Path) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path)
    candidate = writer._seed(paths, _runtime(writer))
    paths.pending.write_bytes(writer.evidence._canonical(candidate))
    paths.pending.chmod(0o600)
    assert writer.init(paths, _runtime(writer)) == {
        "sequence": 1,
        "status": "RECOVERED_COMMITTED",
        "task_id": "T-001",
    }
    assert paths.progress.read_bytes() == writer.evidence._canonical(candidate)
    assert paths.progress.stat().st_mode & 0o777 == 0o644
    assert not paths.pending.exists()


def test_writer_recovers_init_link_before_pending_unlink(tmp_path: Path) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path)
    candidate = writer._seed(paths, _runtime(writer))
    paths.pending.write_bytes(writer.evidence._canonical(candidate))
    paths.pending.chmod(0o644)
    os.link(paths.pending, paths.progress)
    assert paths.pending.stat().st_ino == paths.progress.stat().st_ino
    assert writer.init(paths, _runtime(writer)) == {
        "sequence": 1,
        "status": "RECOVERED_COMMITTED",
        "task_id": "T-001",
    }
    assert paths.progress.read_bytes() == writer.evidence._canonical(candidate)
    assert not paths.pending.exists()


def test_writer_transition_retry_recovers_committed_event(tmp_path: Path) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path)
    writer.init(paths, _runtime(writer))
    calls = 0

    def fsync(fd: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError
        os.fsync(fd)

    runtime = writer.Runtime(
        now=lambda: datetime(2026, 8, 11, 8, 0, 1, tzinfo=timezone.utc),
        fsync=fsync,
    )
    with pytest.raises(OSError):
        writer.transition(
            paths,
            runtime,
            task="T-001",
            expected="IN_PROGRESS",
            target="BLOCKED",
            repo_refs=[],
            opaque_refs=[],
            blocker="TEST_BLOCKER",
            source_review_packet=None,
        )
    before = paths.progress.read_bytes()
    assert writer.transition(
        paths,
        _runtime(writer),
        task="T-001",
        expected="IN_PROGRESS",
        target="BLOCKED",
        repo_refs=[],
        opaque_refs=[],
        blocker="TEST_BLOCKER",
        source_review_packet=None,
    ) == {"sequence": 2, "status": "RECOVERED_COMMITTED", "task_id": "T-001"}
    assert paths.progress.read_bytes() == before


def test_writer_resumes_matching_retained_transition_pending(tmp_path: Path) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path)
    writer.init(paths, _runtime(writer))
    current = writer._existing(paths)
    candidate = deepcopy(current)
    candidate["tasks"]["T-001"] = "BLOCKED"
    candidate["events"].append(
        {
            "sequence": 2,
            "task_id": "T-001",
            "from": "IN_PROGRESS",
            "to": "BLOCKED",
            "at_utc": "2026-08-11T08:00:01Z",
            "evidence_refs": [],
            "blocker": "TEST_BLOCKER",
        }
    )
    candidate["updated_at_utc"] = "2026-08-11T08:00:01Z"
    writer._validate_candidate(paths, candidate)
    paths.pending.write_bytes(writer.evidence._canonical(candidate))
    paths.pending.chmod(0o600)
    assert writer.transition(
        paths,
        _runtime(writer),
        task="T-001",
        expected="IN_PROGRESS",
        target="BLOCKED",
        repo_refs=[],
        opaque_refs=[],
        blocker="TEST_BLOCKER",
        source_review_packet=None,
    ) == {"sequence": 2, "status": "RECOVERED_COMMITTED", "task_id": "T-001"}
    assert writer._existing(paths) == candidate
    assert not paths.pending.exists()


def test_writer_denies_hostile_pending_replacement_before_publish(
    tmp_path: Path,
) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path)
    writer.init(paths, _runtime(writer))
    current = writer._existing(paths)
    before = paths.progress.read_bytes()
    candidate = deepcopy(current)
    candidate["tasks"]["T-001"] = "BLOCKED"
    candidate["events"].append(
        {
            "sequence": 2,
            "task_id": "T-001",
            "from": "IN_PROGRESS",
            "to": "BLOCKED",
            "at_utc": "2026-08-11T08:00:01Z",
            "evidence_refs": [],
            "blocker": "TEST_BLOCKER",
        }
    )
    candidate["updated_at_utc"] = "2026-08-11T08:00:01Z"

    def replace_pending(_identity) -> None:
        paths.pending.unlink()
        paths.pending.write_bytes(writer.evidence._canonical(candidate))
        paths.pending.chmod(0o644)

    with pytest.raises(writer.Denied):
        writer._publish(
            paths,
            candidate,
            initialize=False,
            runtime=_runtime(writer),
            pre_publish=replace_pending,
        )
    assert paths.progress.read_bytes() == before
    assert paths.pending.exists()


def test_writer_rejects_mismatching_retained_pending_without_deleting_it(
    tmp_path: Path,
) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path)
    paths.pending.write_bytes(b"{}\n")
    paths.pending.chmod(0o600)
    before = paths.pending.read_bytes()
    with pytest.raises(writer.Denied):
        writer.init(paths, _runtime(writer))
    assert paths.pending.read_bytes() == before


def test_writer_post_publish_guard_failure_restores_previous_ledger(
    tmp_path: Path,
) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path)
    writer.init(paths, _runtime(writer))
    before = paths.progress.read_bytes()
    candidate = json.loads(before)
    candidate["tasks"]["T-001"] = "BLOCKED"
    candidate["events"].append(
        {
            "sequence": 2,
            "task_id": "T-001",
            "from": "IN_PROGRESS",
            "to": "BLOCKED",
            "at_utc": "2026-08-11T08:00:01Z",
            "evidence_refs": [],
            "blocker": "POST_PUBLISH_GUARD",
        }
    )
    candidate["updated_at_utc"] = "2026-08-11T08:00:01Z"

    def deny_after_publish() -> None:
        raise writer.Denied

    with pytest.raises(writer.Denied):
        writer._publish(
            paths,
            candidate,
            initialize=False,
            runtime=_runtime(writer),
            post_publish=deny_after_publish,
        )
    assert paths.progress.read_bytes() == before
    assert not paths.pending.exists()


def test_writer_rejects_hostile_progress_path_replacement_and_restores_old(
    tmp_path: Path,
) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path)
    writer.init(paths, _runtime(writer))
    before = paths.progress.read_bytes()
    candidate = json.loads(before)
    candidate["tasks"]["T-001"] = "BLOCKED"
    candidate["events"].append(
        {
            "sequence": 2,
            "task_id": "T-001",
            "from": "IN_PROGRESS",
            "to": "BLOCKED",
            "at_utc": "2026-08-11T08:00:01Z",
            "evidence_refs": [],
            "blocker": "HOSTILE_PROGRESS_REPLACEMENT",
        }
    )
    candidate["updated_at_utc"] = "2026-08-11T08:00:01Z"

    def replace_progress() -> None:
        replacement = paths.progress.with_name("hostile-progress")
        replacement.write_bytes(writer.evidence._canonical(candidate))
        replacement.chmod(0o644)
        os.replace(replacement, paths.progress)

    with pytest.raises(writer.Denied):
        writer._publish(
            paths,
            candidate,
            initialize=False,
            runtime=_runtime(writer),
            post_publish=replace_progress,
        )
    assert paths.progress.read_bytes() == before
    assert paths.progress.stat().st_mode & 0o777 == 0o644
    assert not paths.pending.exists()


def test_writer_cli_rejects_path_override_without_echo(tmp_path: Path) -> None:
    marker = tmp_path / "private-marker"
    result = _run(str(WRITER), "init", "--progress", str(marker), "--json")
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == b"SUBJECT_PROGRESS_DENY\n"
    assert str(marker).encode() not in result.stderr


def _source_review_value(writer, paths):
    environment_path = (
        "specs/subject-distillation/evidence/5dd83dd8b3d3696a/environment.json"
    )
    environment_raw = (REPO_ROOT / environment_path).read_bytes()
    environment = json.loads(environment_raw)
    proof = environment["implementation_authorization"]
    return {
        "schema_version": 1,
        "artifact_kind": "subject-distillation-t001-source-review",
        "implementation_base_commit": "git:24e1a126a1022a53480b7126f5f393dc0be85613",
        "baseline_id": "5dd83dd8b3d3696a",
        "baseline_full_digest": "5dd83dd8b3d3696ae4f33ac863af87f4baf569ac1ca5ea11014ad5919ae740e0",
        "builder_principal": "agent:main-builder",
        "reviewer_principal": "agent:independent-reviewer",
        "reviewed_at_utc": "2026-08-11T08:01:00Z",
        "immutable_outputs": writer._immutable_entries(paths),
        "authorization": {
            "environment_path": environment_path,
            "environment_sha256": hashlib.sha256(environment_raw).hexdigest(),
            "authorization_id": proof["authorization_id"],
            "authorization_pass_packet_sha256": proof[
                "authorization_pass_packet_sha256"
            ],
            "status": "PASS",
        },
        "command_results": [
            {"command_id": command_id, "exit_code": 0, "status": "PASS"}
            for command_id in writer.COMMAND_IDS
        ],
        "pending_absent": True,
        "p0": 0,
        "p1": 0,
        "p2": 0,
        "verdict": "PASS",
    }


def _write_packet(writer, path: Path, value: object) -> None:
    path.write_bytes(writer.evidence._canonical(value))


def test_source_review_packet_is_closed_and_review_id_is_derived(tmp_path: Path) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path / "ledger")
    paths.progress.parent.mkdir()
    packet = tmp_path / "source-review.json"
    value = _source_review_value(writer, paths)
    _write_packet(writer, packet, value)
    review_id, proof, reviewed_at = writer._source_review(paths, packet)
    assert review_id == hashlib.sha256(packet.read_bytes()).hexdigest()
    assert proof["authorization_id"]
    assert reviewed_at == datetime(2026, 8, 11, 8, 1, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "mutation",
    [
        "same-reviewer",
        "principal-type",
        "p1",
        "command",
        "output-hash",
        "authorization",
        "reviewed-before-authorization",
    ],
)
def test_source_review_packet_binding_mutations_deny(
    tmp_path: Path, mutation: str
) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path / "ledger")
    paths.progress.parent.mkdir()
    value = _source_review_value(writer, paths)
    if mutation == "same-reviewer":
        value["reviewer_principal"] = value["builder_principal"]
    elif mutation == "principal-type":
        value["reviewer_principal"] = 1
    elif mutation == "p1":
        value["p1"] = 1
    elif mutation == "command":
        value["command_results"][0]["command_id"] = "mutated"
    elif mutation == "output-hash":
        value["immutable_outputs"][0]["sha256"] = "0" * 64
    elif mutation == "reviewed-before-authorization":
        value["reviewed_at_utc"] = "2026-08-11T07:45:59Z"
    else:
        value["authorization"]["authorization_id"] = "0" * 64
    packet = tmp_path / "source-review.json"
    _write_packet(writer, packet, value)
    with pytest.raises(writer.Denied):
        writer._source_review(paths, packet)


def test_source_review_packet_rejects_symlink_final_and_parent(tmp_path: Path) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path / "ledger")
    paths.progress.parent.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    packet = outside / "source-review.json"
    _write_packet(writer, packet, _source_review_value(writer, paths))
    alias = tmp_path / "packet-alias.json"
    alias.symlink_to(packet)
    with pytest.raises(writer.Denied):
        writer._source_review(paths, alias)
    parent_alias = tmp_path / "parent-alias"
    parent_alias.symlink_to(outside, target_is_directory=True)
    with pytest.raises(writer.Denied):
        writer._source_review(paths, parent_alias / packet.name)


@pytest.mark.parametrize(
    "mutated_relative",
    ["scripts/source.py", "scripts/verify_subject_implementation_authorization.py"],
)
def test_source_review_guard_retains_manifest_normative_trust_and_source_set(
    tmp_path: Path, monkeypatch, mutated_relative: str
) -> None:
    writer = _load_writer()
    repo = tmp_path / "repo"
    for relative in (
        "specs/subject-distillation/baseline-manifest.json",
        *writer.baseline.CANONICAL_PATHS,
        *writer.AUTHORIZATION_TRUST_PATHS,
    ):
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((REPO_ROOT / relative).read_bytes())
    source = repo / "scripts/source.py"
    source.parent.mkdir(exist_ok=True)
    source.write_bytes(b"VALUE = 1\n")
    source.chmod(0o755)
    packet = tmp_path / "source-review.json"
    packet_value = {
        "baseline_id": "5dd83dd8b3d3696a",
        "baseline_full_digest": (
            "5dd83dd8b3d3696ae4f33ac863af87f4baf569ac1ca5ea11014ad5919ae740e0"
        ),
    }
    _write_packet(writer, packet, packet_value)
    monkeypatch.setattr(writer, "T001_PATHS", ("scripts/source.py",))
    refs = [
        {
            "kind": "repo_file",
            "path": "scripts/source.py",
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }
    ]
    paths = writer.Paths(
        repo,
        repo / "specs/subject-distillation/baseline-manifest.json",
        repo / "unused-schema",
        repo / "specs/subject-distillation/tasks.md",
        repo / "unused-progress",
        repo / "unused-pending",
    )
    guard = writer._open_source_review_guard(
        paths,
        packet,
        refs,
        hashlib.sha256(packet.read_bytes()).hexdigest(),
        {
            "runner": {
                "path": writer.AUTHORIZATION_TRUST_PATHS[0],
                "sha256": hashlib.sha256(
                    (repo / writer.AUTHORIZATION_TRUST_PATHS[0]).read_bytes()
                ).hexdigest(),
            },
            "authorization_verifier_sha256": hashlib.sha256(
                (repo / writer.AUTHORIZATION_TRUST_PATHS[1]).read_bytes()
            ).hexdigest(),
            "authorization_schema_sha256": hashlib.sha256(
                (repo / writer.AUTHORIZATION_TRUST_PATHS[2]).read_bytes()
            ).hexdigest(),
        },
    )
    try:
        mutated = repo / mutated_relative
        replacement = mutated.with_name("replacement.py")
        replacement.write_bytes(b"VALUE = 2\n")
        replacement.chmod(0o755)
        os.replace(replacement, mutated)
        with pytest.raises(writer.authorization_runner.verifier.Denied):
            guard.audit()
    finally:
        guard.close()


def test_t001_completion_consumes_packet_and_exact_sixteen_refs(tmp_path: Path) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path / "ledger")
    paths.progress.parent.mkdir()
    writer.init(paths, _runtime(writer))
    value = _source_review_value(writer, paths)
    packet = tmp_path / "source-review.json"
    _write_packet(writer, packet, value)
    review_id = hashlib.sha256(packet.read_bytes()).hexdigest()
    environment = json.loads(
        (
            REPO_ROOT
            / "specs/subject-distillation/evidence/5dd83dd8b3d3696a/environment.json"
        ).read_text()
    )
    refs = writer._immutable_entries(paths)
    repo_refs = [f"{item['path']}={item['sha256']}" for item in refs]
    opaque_refs = [
        "t001-authorization:"
        + environment["implementation_authorization"]["authorization_id"],
        "t001-review:" + review_id,
    ]
    result = writer.transition(
        paths,
        writer.Runtime(
            now=lambda: datetime(2026, 8, 11, 8, 2, 0, tzinfo=timezone.utc)
        ),
        task="T-001",
        expected="IN_PROGRESS",
        target="COMPLETED",
        repo_refs=repo_refs,
        opaque_refs=opaque_refs,
        blocker=None,
        source_review_packet=str(packet),
    )
    assert result == {"sequence": 2, "status": "PASS", "task_id": "T-001"}
    ledger = json.loads(paths.progress.read_text())
    assert ledger["tasks"]["T-001"] == "COMPLETED"
    assert len(ledger["events"][-1]["evidence_refs"]) == 16


def test_t001_completion_time_is_not_before_source_review(tmp_path: Path) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path / "ledger")
    paths.progress.parent.mkdir()
    writer.init(paths, _runtime(writer))
    value = _source_review_value(writer, paths)
    packet = tmp_path / "source-review.json"
    _write_packet(writer, packet, value)
    review_id = hashlib.sha256(packet.read_bytes()).hexdigest()
    environment = json.loads(
        (
            REPO_ROOT
            / "specs/subject-distillation/evidence/5dd83dd8b3d3696a/environment.json"
        ).read_text()
    )
    repo_refs = [
        f"{item['path']}={item['sha256']}"
        for item in writer._immutable_entries(paths)
    ]
    with pytest.raises(writer.Denied):
        writer.transition(
            paths,
            _runtime(writer),
            task="T-001",
            expected="IN_PROGRESS",
            target="COMPLETED",
            repo_refs=repo_refs,
            opaque_refs=[
                "t001-authorization:"
                + environment["implementation_authorization"]["authorization_id"],
                "t001-review:" + review_id,
            ],
            blocker=None,
            source_review_packet=str(packet),
        )


def test_t001_completion_rejects_arbitrary_review_id(tmp_path: Path) -> None:
    writer = _load_writer()
    paths = _test_paths(writer, tmp_path / "ledger")
    paths.progress.parent.mkdir()
    writer.init(paths, _runtime(writer))
    value = _source_review_value(writer, paths)
    packet = tmp_path / "source-review.json"
    _write_packet(writer, packet, value)
    environment = json.loads(
        (REPO_ROOT / "specs/subject-distillation/evidence/5dd83dd8b3d3696a/environment.json").read_text()
    )
    repo_refs = [
        f"{item['path']}={item['sha256']}" for item in writer._immutable_entries(paths)
    ]
    with pytest.raises(writer.Denied):
        writer.transition(
            paths,
            _runtime(writer),
            task="T-001",
            expected="IN_PROGRESS",
            target="COMPLETED",
            repo_refs=repo_refs,
            opaque_refs=[
                "t001-authorization:"
                + environment["implementation_authorization"]["authorization_id"],
                "t001-review:" + "0" * 64,
            ],
            blocker=None,
            source_review_packet=str(packet),
        )
