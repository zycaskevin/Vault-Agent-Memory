from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import select
import shutil
import signal
import stat
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts/run_subject_implementation_authorization.py"
BASE_COMMIT = "c32750134e92731b77f1f33e74776ec3300ed12e"
NOW = datetime(2026, 8, 2, 15, 0, tzinfo=timezone.utc)


def _load_runner():
    assert RUNNER_PATH.is_file(), "B-001 runner is absent"
    spec = importlib.util.spec_from_file_location("subject_authorization_runner", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runner():
    return _load_runner()


@pytest.fixture(autouse=True)
def _repo_cwd(monkeypatch) -> None:
    monkeypatch.chdir(REPO_ROOT)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def _state(runner, *, head: str = BASE_COMMIT, clean: bool = True):
    return runner.RepositoryState(str(REPO_ROOT), head, clean)


def _passing_child(runner):
    def child(argv, _cwd, _env, _timeout):
        receipt_path = Path(argv[argv.index("--receipt") + 1])
        receipt = json.loads(receipt_path.read_bytes())
        output = _canonical(
            {
                "authorization_id": receipt["authorization_id"],
                "authorized_task": receipt["authorized_task"],
                "baseline_id": receipt["baseline_id"],
                "status": "PASS",
            }
        ).encode()
        return runner.ChildResult(0, output, b"")

    return child


def _runtime(
    runner,
    tmp_path: Path,
    *,
    now: datetime = NOW,
    state=None,
    progress=None,
    hook=None,
    child=None,
    write=None,
    unlink=None,
    rmdir=None,
):
    return runner.Runtime(
        now=lambda: now,
        repository_state=lambda: state if state is not None else _state(runner),
        progress_snapshot=(
            progress
            if progress is not None
            else lambda _repo: runner.ProgressSnapshot(False, "", "PENDING")
        ),
        temp_root=str(tmp_path),
        hook=hook,
        run_child=child if child is not None else _passing_child(runner),
        write=write,
        unlink=unlink,
        rmdir=rmdir,
    )


def _run(runner, args: list[str], capsys, runtime):
    code = runner.main(args, _runtime=runtime)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _propose(runner, tmp_path: Path, capsys, *, runtime=None):
    selected = runtime if runtime is not None else _runtime(runner, tmp_path)
    result = _run(
        runner,
        [
            "propose",
            "--implementation-base-commit",
            BASE_COMMIT,
            "--expected-task",
            "T-001",
            "--json",
        ],
        capsys,
        selected,
    )
    assert result[0] == 0, result
    return result[1], json.loads(result[1])


def _verify_args(proposal_raw: str, proposal: dict[str, Any]) -> list[str]:
    return [
        "verify-confirmed",
        "--proposal-json",
        proposal_raw,
        "--implementation-base-commit",
        BASE_COMMIT,
        "--expected-receipt-sha256",
        proposal["receipt_sha256"],
        "--expected-task",
        "T-001",
        "--require-cleanup",
        "--json",
    ]


def _reidentify(proposal: dict[str, Any]) -> str:
    without_id = dict(proposal)
    without_id.pop("proposal_id", None)
    proposal["proposal_id"] = hashlib.sha256(_canonical(without_id).encode()).hexdigest()
    return _canonical(proposal)


def _candidate_directories(root: Path) -> list[Path]:
    return [item for item in root.iterdir() if item.is_dir()]


@pytest.mark.parametrize(
    "fault",
    ["missing", "hash_drift", "nonregular", "symlink", "unreadable"],
)
def test_verifier_startup_fault_is_fixed_no_echo_error(
    runner, tmp_path: Path, fault: str
) -> None:
    isolated = tmp_path / "harmless-private-startup-marker"
    isolated.mkdir(mode=0o700)
    isolated_runner = isolated / RUNNER_PATH.name
    isolated_verifier = isolated / "verify_subject_implementation_authorization.py"
    shutil.copyfile(RUNNER_PATH, isolated_runner)
    isolated_runner.chmod(0o755)
    if fault == "hash_drift":
        isolated_verifier.write_bytes(
            (REPO_ROOT / "scripts/verify_subject_implementation_authorization.py").read_bytes()
            + b"\n"
        )
    elif fault == "nonregular":
        isolated_verifier.mkdir(mode=0o700)
    elif fault == "symlink":
        isolated_verifier.symlink_to(
            REPO_ROOT / "scripts/verify_subject_implementation_authorization.py"
        )
    elif fault == "unreadable":
        shutil.copyfile(
            REPO_ROOT / "scripts/verify_subject_implementation_authorization.py",
            isolated_verifier,
        )
        isolated_verifier.chmod(0)

    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            os.fspath(isolated_runner),
            "propose",
            "--implementation-base-commit",
            BASE_COMMIT,
            "--expected-task",
            "T-001",
            "--json",
        ],
        cwd=REPO_ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        timeout=10,
    )
    combined = result.stdout + result.stderr
    assert (result.returncode, result.stdout, result.stderr) == (
        3,
        b"",
        runner.ERROR.encode(),
    )
    assert os.fspath(isolated).encode() not in combined
    assert b"harmless-private-startup-marker" not in combined
    assert not list(isolated.glob("subject-authorization-*"))


def test_propose_is_canonical_complete_and_file_free(runner, tmp_path: Path, capsys) -> None:
    child_called = False

    def child(*_args, **_kwargs):
        nonlocal child_called
        child_called = True
        raise AssertionError

    raw, proposal = _propose(
        runner, tmp_path, capsys, runtime=_runtime(runner, tmp_path, child=child)
    )
    assert raw == _canonical(proposal)
    assert set(proposal) == runner.PROPOSAL_KEYS
    assert proposal["proposal_id"] == hashlib.sha256(
        _canonical({key: value for key, value in proposal.items() if key != "proposal_id"}).encode()
    ).hexdigest()
    assert proposal["implementation_base_commit"] == BASE_COMMIT
    assert proposal["authorized_task"] == "T-001"
    assert proposal["expires_at_utc"] == "2026-08-02T15:15:00Z"
    assert proposal["allowed_repo_relative_paths"] == [
        path.format(baseline_id=proposal["baseline_id"]) for path in runner.T001_PATHS
    ]
    assert proposal["prohibited_operations"] == [
        "deploy",
        "live_private_data",
        "migration",
        "non_github_remote_network",
        "product_runtime",
        "release",
        "unreviewed_git_delivery",
    ]
    assert list(tmp_path.iterdir()) == []
    assert child_called is False


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["propose"],
        ["propose", "--json"],
        ["propose", "--implementation-base-commit", BASE_COMMIT, "--expected-task", "T-002", "--json"],
        [
            "propose",
            "--implementation-base-commit",
            BASE_COMMIT,
            "--expected-task",
            "T-001",
            "--json",
            "--json",
        ],
    ],
)
def test_cli_partial_cross_task_and_duplicate_arguments_deny(
    runner, tmp_path: Path, capsys, args: list[str]
) -> None:
    assert _run(runner, args, capsys, _runtime(runner, tmp_path)) == (2, "", runner.DENY)


@pytest.mark.parametrize(
    "state",
    [
        ("0" * 40, True),
        (BASE_COMMIT, False),
    ],
)
def test_propose_rejects_head_or_cleanliness_drift(
    runner, tmp_path: Path, capsys, state: tuple[str, bool]
) -> None:
    runtime = _runtime(runner, tmp_path, state=_state(runner, head=state[0], clean=state[1]))
    args = [
        "propose",
        "--implementation-base-commit",
        BASE_COMMIT,
        "--expected-task",
        "T-001",
        "--json",
    ]
    assert _run(runner, args, capsys, runtime) == (2, "", runner.DENY)


def test_verify_confirmed_passes_then_proves_cleanup(runner, tmp_path: Path, capsys) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)
    result = _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1)),
    )
    assert result == (
        0,
        _canonical(
            {
                "authorization_id": proposal["authorization_id"],
                "authorized_task": "T-001",
                "baseline_id": proposal["baseline_id"],
                "status": "PASS",
            }
        ),
        "",
    )
    assert _candidate_directories(tmp_path) == []


def test_real_verifier_accepts_exact_normative_scope(runner, tmp_path: Path, capsys) -> None:
    current = datetime.now(timezone.utc).replace(microsecond=0)
    raw, proposal = _propose(
        runner,
        tmp_path,
        capsys,
        runtime=_runtime(runner, tmp_path, now=current),
    )
    result = _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(
            runner,
            tmp_path,
            now=current + timedelta(seconds=1),
            child=runner._default_run_child,
        ),
    )
    assert result[0] == 0
    assert _candidate_directories(tmp_path) == []


def test_byte_identical_unexpired_prestart_replay_is_side_effect_free(
    runner, tmp_path: Path, capsys
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)
    args = _verify_args(raw, proposal)
    for offset in (1, 2):
        assert _run(
            runner,
            args,
            capsys,
            _runtime(runner, tmp_path, now=NOW + timedelta(seconds=offset)),
        )[0] == 0
        assert _candidate_directories(tmp_path) == []


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(unknown="value"),
        lambda value: value.pop("scope_sha256"),
        lambda value: value.update(authorized_task="T-002"),
        lambda value: value.update(implementation_base_commit="0" * 40),
        lambda value: value.update(baseline_id="0" * 16),
        lambda value: value.update(allowed_repo_relative_paths=value["allowed_repo_relative_paths"][:-1]),
        lambda value: value.update(non_goals=["different.goal"]),
        lambda value: value.update(receipt_sha256="0" * 64),
        lambda value: value.update(authorization_schema_sha256="0" * 64),
        lambda value: value.update(authorization_verifier_sha256="0" * 64),
    ],
)
def test_confirmed_proposal_field_drift_denies_before_private_creation(
    runner, tmp_path: Path, capsys, mutation
) -> None:
    _, proposal = _propose(runner, tmp_path, capsys)
    mutation(proposal)
    raw = _reidentify(proposal)
    args = _verify_args(raw, proposal)
    assert _run(
        runner,
        args,
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1)),
    ) == (2, "", runner.DENY)
    assert _candidate_directories(tmp_path) == []


def test_proposal_id_noncanonical_duplicate_and_owner_digest_mismatch_deny(
    runner, tmp_path: Path, capsys
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)
    bad = dict(proposal)
    bad["proposal_id"] = "0" * 64
    cases = [
        _canonical(bad),
        json.dumps(proposal, indent=2, sort_keys=True) + "\n",
        raw.replace("{", '{"artifact_kind":"subject-implementation-proposal",', 1),
    ]
    for candidate in cases:
        assert _run(
            runner,
            _verify_args(candidate, proposal),
            capsys,
            _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1)),
        ) == (2, "", runner.DENY)
    args = _verify_args(raw, proposal)
    args[args.index("--expected-receipt-sha256") + 1] = "0" * 64
    assert _run(
        runner,
        args,
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1)),
    ) == (2, "", runner.DENY)


@pytest.mark.parametrize(
    "now",
    [NOW - timedelta(seconds=1), NOW + timedelta(minutes=15)],
)
def test_future_issued_and_expiry_equality_deny(
    runner, tmp_path: Path, capsys, now: datetime
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)
    assert _run(runner, _verify_args(raw, proposal), capsys, _runtime(runner, tmp_path, now=now)) == (
        2,
        "",
        runner.DENY,
    )


@pytest.mark.parametrize("state", ["IN_PROGRESS", "BLOCKED", "COMPLETED"])
def test_existing_nonpending_progress_denies_before_materialization(
    runner, tmp_path: Path, capsys, state: str
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)

    def progress(_repo):
        return runner.ProgressSnapshot(True, "a" * 64, state)

    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1), progress=progress),
    ) == (2, "", runner.DENY)
    assert list(tmp_path.iterdir()) == []


def test_existing_pending_progress_also_denies_fail_closed(
    runner, tmp_path: Path, capsys
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)

    def progress(_repo):
        return runner.ProgressSnapshot(True, "a" * 64, "PENDING")

    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1), progress=progress),
    ) == (2, "", runner.DENY)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("after", ["PENDING", "IN_PROGRESS", "INVALID"])
def test_mid_verification_progress_appearance_or_state_flip_cleans_and_denies(
    runner, tmp_path: Path, capsys, after: str
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)
    current = runner.ProgressSnapshot(False, "", "PENDING")

    def progress(_repo):
        return current

    def hook(event, _lifecycle):
        nonlocal current
        if event == "after_verifier":
            current = runner.ProgressSnapshot(True, "b" * 64, after)

    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(
            runner,
            tmp_path,
            now=NOW + timedelta(seconds=1),
            progress=progress,
            hook=hook,
        ),
    ) == (2, "", runner.DENY)
    assert _candidate_directories(tmp_path) == []


def test_nonblocking_lock_allows_only_one_concurrent_verifier(
    runner, tmp_path: Path, capsys
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)
    runtime = _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1))
    with runner._authorization_lock(str(REPO_ROOT), "T-001", BASE_COMMIT, runtime):
        assert _run(runner, _verify_args(raw, proposal), capsys, runtime) == (
            2,
            "",
            runner.DENY,
        )


@pytest.mark.parametrize(
    ("reported", "expected"),
    [
        ("/var", "/private/var"),
        ("/var/folders/example", "/private/var/folders/example"),
        ("/tmp", "/private/tmp"),
        ("/tmp/example", "/private/tmp/example"),
    ],
)
def test_default_temp_root_maps_only_exact_darwin_system_aliases(
    runner, monkeypatch, reported: str, expected: str
) -> None:
    monkeypatch.setattr(runner.sys, "platform", "darwin")
    monkeypatch.setattr(runner.tempfile, "gettempdir", lambda: reported)
    monkeypatch.setattr(
        runner.os.path,
        "realpath",
        lambda *_args, **_kwargs: pytest.fail("realpath is not an authorization input"),
    )
    assert runner._external_root(runner.Runtime(), os.fspath(REPO_ROOT)) == expected


def test_environment_selected_default_symlink_remains_denied(
    runner, tmp_path: Path, monkeypatch
) -> None:
    physical = tmp_path / "physical-temp"
    physical.mkdir()
    alias = tmp_path / "environment-temp-alias"
    alias.symlink_to(physical, target_is_directory=True)
    monkeypatch.setattr(runner.sys, "platform", "darwin")
    monkeypatch.setattr(runner.tempfile, "gettempdir", lambda: os.fspath(alias))
    root = runner._external_root(runner.Runtime(), os.fspath(REPO_ROOT))
    alias_text = os.fspath(alias)
    expected = (
        "/private" + alias_text
        if alias_text.startswith(("/var/", "/tmp/"))
        else alias_text
    )
    assert root == expected
    with pytest.raises(runner.Denied):
        runner._open_external_root(root)

    explicit = runner.Runtime(temp_root=os.fspath(alias))
    with pytest.raises(runner.Denied):
        runner._open_external_root(
            runner._external_root(explicit, os.fspath(REPO_ROOT))
        )


def test_default_temp_root_resolving_inside_repo_denies(
    runner, tmp_path: Path, monkeypatch
) -> None:
    alias = tmp_path / "unsafe-system-temp-alias"
    alias.symlink_to(REPO_ROOT, target_is_directory=True)
    monkeypatch.setattr(runner.tempfile, "gettempdir", lambda: os.fspath(alias))
    root = runner._external_root(runner.Runtime(), os.fspath(REPO_ROOT))
    assert root == os.fspath(alias)
    with pytest.raises(runner.Denied):
        runner._open_external_root(root)


@pytest.mark.skipif(sys.platform != "darwin", reason="Darwin system alias integration")
def test_verify_uses_canonicalized_default_temp_root_and_cleans(
    runner, tmp_path: Path, capsys, monkeypatch
) -> None:
    physical = tmp_path / "physical-production-temp"
    physical.mkdir()
    physical_text = os.fspath(physical)
    assert physical_text.startswith("/private/var/")
    alias = "/var/" + physical_text.removeprefix("/private/var/")
    monkeypatch.setattr(runner.tempfile, "gettempdir", lambda: alias)

    runtime = _runtime(runner, physical)
    runtime.temp_root = None
    raw, proposal = _propose(runner, physical, capsys, runtime=runtime)
    runtime.now = lambda: NOW + timedelta(seconds=1)
    assert _run(runner, _verify_args(raw, proposal), capsys, runtime)[0] == 0
    assert not [
        item
        for item in physical.iterdir()
        if item.is_dir() and item.name.startswith("subject-authorization-")
    ]


def test_nonblocking_lock_rejects_a_second_process(
    runner, tmp_path: Path
) -> None:
    child = """
import os
import sys

sys.path.insert(0, sys.argv[1])
import run_subject_implementation_authorization as runner

runtime = runner.Runtime(temp_root=sys.argv[2])
with runner._authorization_lock(sys.argv[3], "T-001", sys.argv[4], runtime):
    os.write(sys.stdout.fileno(), b"LOCKED\\n")
    os.read(sys.stdin.fileno(), 1)
"""
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            child,
            os.fspath(REPO_ROOT / "scripts"),
            os.fspath(tmp_path),
            os.fspath(REPO_ROOT),
            BASE_COMMIT,
        ],
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        assert process.stdout is not None
        ready, _, _ = select.select([process.stdout], [], [], 5)
        assert ready and process.stdout.readline() == b"LOCKED\n"
        with (
            pytest.raises(runner.Denied),
            runner._authorization_lock(
                str(REPO_ROOT),
                "T-001",
                BASE_COMMIT,
                _runtime(runner, tmp_path),
            ),
        ):
            pytest.fail("a concurrent process acquired the authorization lock")
    finally:
        if process.stdin is not None:
            try:
                process.stdin.write(b"x")
                process.stdin.flush()
            except BrokenPipeError:
                pass
        try:
            child_stdout, child_stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            child_stdout, child_stderr = process.communicate(timeout=5)
            pytest.fail("authorization lock child did not terminate")
    assert (process.returncode, child_stdout, child_stderr) == (0, b"", b"")


def test_lock_replacement_invalidates_original_verification_lease(
    runner, tmp_path: Path, capsys
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)
    replacement_lease_denied = False
    runtime = _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1))

    def hook(event, _lifecycle):
        nonlocal replacement_lease_denied
        if event != "after_materialize":
            return
        lock_path = next(tmp_path.glob("subject-authorization-*.lock"))
        lock_path.unlink()
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        with (
            pytest.raises(runner.Denied),
            runner._authorization_lock(
                str(REPO_ROOT), "T-001", BASE_COMMIT, runtime
            ),
        ):
            pytest.fail("a replacement inode acquired a second lease")
        replacement_lease_denied = True

    runtime.hook = hook
    assert _run(runner, _verify_args(raw, proposal), capsys, runtime) == (
        2,
        "",
        runner.DENY,
    )
    assert replacement_lease_denied
    assert _candidate_directories(tmp_path) == []


def test_interrupt_after_lifecycle_return_before_assignment_cleans(
    runner, tmp_path: Path, capsys, monkeypatch
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)
    original = runner._new_lifecycle

    def interrupt_after_creation(*args, **kwargs):
        lifecycle = original(*args, **kwargs)
        os.kill(os.getpid(), signal.SIGTERM)
        return lifecycle

    monkeypatch.setattr(runner, "_new_lifecycle", interrupt_after_creation)
    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1)),
    ) == (2, "", runner.DENY)
    assert _candidate_directories(tmp_path) == []


def test_materialized_modes_members_and_xtrace_sanitization(
    runner, tmp_path: Path, capsys, monkeypatch
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)
    observed = False
    child_environment: dict[str, str] = {}

    def hook(event, lifecycle):
        nonlocal observed
        if event == "after_materialize":
            observed = True
            assert stat.S_IMODE(os.fstat(lifecycle.dir_fd).st_mode) == 0o700
            assert stat.S_IMODE(os.fstat(lifecycle.receipt_fd).st_mode) == 0o600
            assert stat.S_IMODE(os.fstat(lifecycle.scope_fd).st_mode) == 0o600
            assert set(os.listdir(lifecycle.dir_fd)) == {"receipt.json", "scope.json"}

    def child(argv, cwd, env, timeout):
        child_environment.update(env)
        return _passing_child(runner)(argv, cwd, env, timeout)

    monkeypatch.setenv("BASH_XTRACEFD", "harmless-xtrace-marker")
    monkeypatch.setenv("PS4", "harmless-ps4-marker")
    result = _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(
            runner,
            tmp_path,
            now=NOW + timedelta(seconds=1),
            hook=hook,
            child=child,
        ),
    )
    assert result[0] == 0
    assert observed
    assert "BASH_XTRACEFD" not in child_environment
    assert "PS4" not in child_environment
    assert "harmless" not in result[1] + result[2]


@pytest.mark.parametrize("event", ["before_verifier", "before_cleanup"])
@pytest.mark.parametrize("target", ["receipt", "scope", "directory"])
def test_identity_replacement_is_never_pathname_deleted(
    runner, tmp_path: Path, capsys, target: str, event: str
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)
    marker = "harmless-private-replacement-marker"

    def hook(actual_event, lifecycle):
        if actual_event != event:
            return
        if target in {"receipt", "scope"}:
            name = f"{target}.json"
            replacement = f"{target}.replacement"
            fd = os.open(
                replacement,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=lifecycle.dir_fd,
            )
            os.write(fd, marker.encode())
            os.close(fd)
            os.replace(
                replacement,
                name,
                src_dir_fd=lifecycle.dir_fd,
                dst_dir_fd=lifecycle.dir_fd,
            )
        else:
            saved = lifecycle.dirname + ".saved"
            os.rename(
                lifecycle.dirname,
                saved,
                src_dir_fd=lifecycle.parent_fd,
                dst_dir_fd=lifecycle.parent_fd,
            )
            os.mkdir(lifecycle.dirname, 0o700, dir_fd=lifecycle.parent_fd)

    result = _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1), hook=hook),
    )
    assert result == (4, runner.CLEANUP_REQUIRED, "")
    assert marker not in result[1] + result[2]


def test_in_place_digest_drift_denies_and_cleans_same_owned_object(
    runner, tmp_path: Path, capsys
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)

    def hook(event, lifecycle):
        if event == "before_verifier":
            os.lseek(lifecycle.scope_fd, 0, os.SEEK_SET)
            os.write(lifecycle.scope_fd, b"X")
            os.fsync(lifecycle.scope_fd)

    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1), hook=hook),
    ) == (2, "", runner.DENY)
    assert _candidate_directories(tmp_path) == []


def test_mode_drift_denies_and_cleans_same_owned_object(runner, tmp_path: Path, capsys) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)

    def hook(event, lifecycle):
        if event == "before_verifier":
            os.fchmod(lifecycle.receipt_fd, 0o644)

    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1), hook=hook),
    ) == (2, "", runner.DENY)
    assert _candidate_directories(tmp_path) == []


def test_extra_member_and_permanent_cleanup_failure_are_bounded(
    runner, tmp_path: Path, capsys
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)

    def extra(event, lifecycle):
        if event == "before_cleanup":
            fd = os.open(
                "unexpected",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=lifecycle.dir_fd,
            )
            os.close(fd)

    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1), hook=extra),
    ) == (4, runner.CLEANUP_REQUIRED, "")

    other = tmp_path / "other"
    other.mkdir(mode=0o700)
    raw, proposal = _propose(runner, other, capsys)

    def fail_unlink(*_args, **_kwargs):
        raise OSError("harmless-unlink-fault")

    result = _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(
            runner,
            other,
            now=NOW + timedelta(seconds=1),
            unlink=fail_unlink,
        ),
    )
    assert result == (4, runner.CLEANUP_REQUIRED, "")
    assert "harmless" not in result[1] + result[2]


def test_short_write_signal_and_transient_cleanup_fault_all_clean(
    runner, tmp_path: Path, capsys
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)
    result = _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1), write=lambda *_: 0),
    )
    assert result == (3, "", runner.ERROR)
    assert _candidate_directories(tmp_path) == []

    signal_sent = False

    def signal_then_unlink(name, *, dir_fd):
        nonlocal signal_sent
        if not signal_sent:
            signal_sent = True
            os.kill(os.getpid(), signal.SIGTERM)
        os.unlink(name, dir_fd=dir_fd)

    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(
            runner,
            tmp_path,
            now=NOW + timedelta(seconds=1),
            write=lambda *_: 0,
            unlink=signal_then_unlink,
        ),
    ) == (2, "", runner.DENY)
    assert signal_sent
    assert _candidate_directories(tmp_path) == []

    def interrupt(event, _lifecycle):
        if event == "after_materialize":
            raise runner.Interrupted

    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1), hook=interrupt),
    ) == (2, "", runner.DENY)
    assert _candidate_directories(tmp_path) == []

    calls = 0

    def transient(name, *, dir_fd):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise InterruptedError
        os.unlink(name, dir_fd=dir_fd)

    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(
            runner,
            tmp_path,
            now=NOW + timedelta(seconds=1),
            unlink=transient,
        ),
    )[0] == 0
    assert _candidate_directories(tmp_path) == []


@pytest.mark.parametrize("signal_name", ["SIGHUP", "SIGINT", "SIGTERM"])
def test_real_signal_during_cleanup_is_deferred_until_private_absence(
    runner, tmp_path: Path, capsys, signal_name: str
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)

    def hook(event, _lifecycle):
        if event == "before_cleanup":
            os.kill(os.getpid(), getattr(signal, signal_name))

    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1), hook=hook),
    ) == (2, "", runner.DENY)
    assert _candidate_directories(tmp_path) == []


def test_signal_never_downgrades_cleanup_required_handoff(
    runner, tmp_path: Path, capsys
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)
    signal_sent = False

    def signal_then_fail(*_args, **_kwargs):
        nonlocal signal_sent
        if not signal_sent:
            signal_sent = True
            os.kill(os.getpid(), signal.SIGHUP)
        raise OSError("harmless-cleanup-fault")

    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(
            runner,
            tmp_path,
            now=NOW + timedelta(seconds=1),
            write=lambda *_: 0,
            unlink=signal_then_fail,
        ),
    ) == (4, runner.CLEANUP_REQUIRED, "")
    assert signal_sent
    assert len(_candidate_directories(tmp_path)) == 1


def test_early_directory_open_fault_is_cleaned_or_requires_handoff(
    runner, tmp_path: Path, capsys, monkeypatch
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)
    original_open = runner.os.open
    failed = False

    def transient_open(path, *args, **kwargs):
        nonlocal failed
        if (
            isinstance(path, str)
            and path.startswith("subject-authorization-")
            and not path.endswith(".lock")
            and not failed
        ):
            failed = True
            raise OSError("harmless-early-open-fault")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(runner.os, "open", transient_open)
    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1)),
    ) == (3, "", runner.ERROR)
    assert _candidate_directories(tmp_path) == []

    failed = False
    signal_sent = False

    def signal_then_rmdir(name, *, dir_fd):
        nonlocal signal_sent
        if not signal_sent:
            signal_sent = True
            os.kill(os.getpid(), signal.SIGINT)
        os.rmdir(name, dir_fd=dir_fd)

    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(
            runner,
            tmp_path,
            now=NOW + timedelta(seconds=1),
            rmdir=signal_then_rmdir,
        ),
    ) == (2, "", runner.DENY)
    assert signal_sent
    assert _candidate_directories(tmp_path) == []


@pytest.mark.parametrize(
    ("child", "expected"),
    [
        (
            lambda runner: lambda *_args: runner.ChildResult(2, b"", runner.VERIFIER_DENY.encode()),
            "deny",
        ),
        (
            lambda runner: lambda *_args: runner.ChildResult(3, b"", runner.VERIFIER_ERROR.encode()),
            "error",
        ),
        (
            lambda runner: lambda *_args: runner.ChildResult(0, b"malformed\n", b""),
            "error",
        ),
    ],
)
def test_verifier_deny_error_and_malformed_output_cleanup(
    runner, tmp_path: Path, capsys, child, expected: str
) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)
    result = _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(
            runner,
            tmp_path,
            now=NOW + timedelta(seconds=1),
            child=child(runner),
        ),
    )
    assert result == (
        (2, "", runner.DENY) if expected == "deny" else (3, "", runner.ERROR)
    )
    assert _candidate_directories(tmp_path) == []


def test_verifier_timeout_is_error_and_cleans(runner, tmp_path: Path, capsys) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)

    def timeout(*_args):
        raise subprocess.TimeoutExpired("verifier", 30)

    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1), child=timeout),
    ) == (3, "", runner.ERROR)
    assert _candidate_directories(tmp_path) == []


def test_unexpected_child_exception_is_error_and_cleans(runner, tmp_path: Path, capsys) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)

    def explode(*_args):
        raise ValueError("harmless-child-fault")

    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1), child=explode),
    ) == (3, "", runner.ERROR)
    assert _candidate_directories(tmp_path) == []


def test_pass_is_not_returned_until_verified_cleanup(runner, tmp_path: Path, capsys) -> None:
    raw, proposal = _propose(runner, tmp_path, capsys)
    events: list[str] = []

    def hook(event, lifecycle):
        events.append(event)
        if event == "after_cleanup":
            with pytest.raises(FileNotFoundError):
                os.stat(lifecycle.dirname, dir_fd=lifecycle.parent_fd, follow_symlinks=False)

    assert _run(
        runner,
        _verify_args(raw, proposal),
        capsys,
        _runtime(runner, tmp_path, now=NOW + timedelta(seconds=1), hook=hook),
    )[0] == 0
    assert events[-1] == "after_cleanup"
    assert events.index("after_verifier") < events.index("before_cleanup")


def test_b001_artifacts_are_tracked_with_exact_modes() -> None:
    expected = {
        "scripts/run_subject_implementation_authorization.py",
        "tests/test_subject_authorization_runner.py",
    }
    assert RUNNER_PATH.is_file()
    assert os.access(RUNNER_PATH, os.X_OK)
    assert hashlib.sha256(RUNNER_PATH.read_bytes()).hexdigest() == (
        "535938b54d1aa567572ed7ad18e9fc4c8808cb83d7db16c9896d13389a99d805"
    )
    assert Path(__file__).resolve().is_file()
    tracked = subprocess.run(
        ["git", "ls-files", "--stage", "--", *sorted(expected)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    modes = {line.split(maxsplit=3)[3]: line.split(maxsplit=1)[0] for line in tracked}
    assert modes == {
        "scripts/run_subject_implementation_authorization.py": "100755",
        "tests/test_subject_authorization_runner.py": "100644",
    }
    status = subprocess.run(
        [
            "git",
            "status",
            "--short",
            "--untracked-files=all",
            "--",
            *sorted(expected),
        ],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.splitlines()
    assert {line[3:] for line in status} <= expected
