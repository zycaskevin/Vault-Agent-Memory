from __future__ import annotations

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
DISPATCH_PATH = REPO_ROOT / "scripts/validate_subject_task_authorization_dispatch.py"
PROGRESS_PATH = REPO_ROOT / "specs/subject-distillation/implementation-progress.json"


def _load():
    spec = importlib.util.spec_from_file_location(
        "subject_task_authorization_dispatch_test", DISPATCH_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


@pytest.fixture()
def dispatch():
    return _load()


def test_current_ledger_dispatches_through_v3_contract() -> None:
    current = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    result = subprocess.run(
        [sys.executable, os.fspath(DISPATCH_PATH), "--ledger", "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        timeout=20,
    )
    assert result.returncode == 0
    assert result.stderr == b""
    assert json.loads(result.stdout) == {
        "protocol_version": 3,
        "sequence": len(current["events"]),
        "status": "PASS",
    }


def test_dispatch_rejects_cli_expansion_without_echo() -> None:
    result = subprocess.run(
        [sys.executable, os.fspath(DISPATCH_PATH), "--unknown"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        timeout=20,
    )
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == b"SUBJECT_TASK_AUTHORIZATION_DISPATCH_DENY\n"


@pytest.mark.parametrize(
    ("script", "argv", "expected"),
    [
        (
            "update_subject_task_progress_v3.py",
            ["start", "--proof", "unused", "--j"],
            b"SUBJECT_TASK_PROGRESS_V3_DENY\n",
        ),
        (
            "validate_subject_task_authorization_v3.py",
            ["--led", "--json"],
            b"SUBJECT_TASK_AUTHORIZATION_V3_VALIDATOR_DENY\n",
        ),
    ],
)
def test_public_clis_reject_abbreviated_flags_without_echo(
    script: str, argv: list[str], expected: bytes
) -> None:
    result = subprocess.run(
        [sys.executable, os.fspath(REPO_ROOT / "scripts" / script), *argv],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        timeout=20,
    )
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == expected


@pytest.mark.parametrize(
    ("script", "argv", "expected"),
    [
        (
            "update_subject_task_progress_v3.py",
            ["start", "--json"],
            b"SUBJECT_TASK_PROGRESS_V3_ERROR\n",
        ),
        (
            "validate_subject_task_authorization_v3.py",
            ["--ledger", "--json"],
            b"SUBJECT_TASK_AUTHORIZATION_V3_VALIDATOR_ERROR\n",
        ),
        (
            "validate_subject_task_authorization_dispatch.py",
            ["--ledger", "--json"],
            b"SUBJECT_TASK_AUTHORIZATION_DISPATCH_ERROR\n",
        ),
    ],
)
@pytest.mark.parametrize("fault", ["missing", "corrupt"])
def test_public_cli_dependency_bootstrap_faults_are_fixed_and_no_echo(
    tmp_path: Path, script: str, argv: list[str], expected: bytes, fault: str
) -> None:
    isolated = tmp_path / "private-marker-bootstrap"
    isolated.mkdir()
    shutil.copy2(REPO_ROOT / "scripts" / script, isolated / script)
    if fault == "corrupt":
        (isolated / "run_subject_task_authorization_v3.py").write_text(
            "raise RuntimeError('private-marker-bootstrap')\n", encoding="utf-8"
        )
    result = subprocess.run(
        [sys.executable, "-S", os.fspath(isolated / script), *argv],
        cwd=isolated,
        capture_output=True,
        check=False,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""},
        timeout=20,
    )
    assert result.returncode == 3
    assert result.stdout == b""
    assert result.stderr == expected
    assert b"private-marker-bootstrap" not in result.stdout + result.stderr


def test_dispatch_uses_one_v3_validated_snapshot(
    dispatch, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Path] = []
    monkeypatch.setattr(
        dispatch.validator_v3,
        "validate_ledger",
        lambda root: calls.append(root)
        or {"proofs": 1, "sequence": 6, "status": "PASS"},
    )

    assert dispatch.validate(REPO_ROOT) == {
        "protocol_version": 3,
        "sequence": 6,
        "status": "PASS",
    }
    assert calls == [REPO_ROOT]


def test_validator_denial_is_propagated_fail_closed(
    dispatch, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        dispatch.validator_v3,
        "validate_ledger",
        lambda _root: (_ for _ in ()).throw(dispatch.Denied),
    )

    with pytest.raises(dispatch.Denied):
        dispatch.validate(REPO_ROOT)


def test_dispatcher_and_ci_never_mutate_frozen_v2_bytes() -> None:
    contract = json.loads(
        (
            REPO_ROOT
            / "specs/subject-distillation/task-authorization-v3.contract.json"
        ).read_text(encoding="utf-8")
    )
    trust = {item["path"]: item["sha256"] for item in contract["trust_root"]}
    frozen = {
        "scripts/run_subject_task_authorization_v2.py",
        "scripts/update_subject_task_progress_v2.py",
        "scripts/validate_subject_task_authorization_v2.py",
        "specs/subject-distillation/task-authorization-v2.contract.json",
        "specs/subject-distillation/task-authorization-v2.schema.json",
    }
    assert frozen <= set(trust)
    for path in frozen:
        assert hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest() == trust[path]
    workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "python scripts/validate_subject_task_authorization_dispatch.py" in workflow
    assert "python scripts/validate_subject_task_authorization_v2.py" not in workflow
