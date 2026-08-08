#!/usr/bin/env python3
"""Stateless, owner-confirmed Subject implementation authorization runner."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import secrets
import signal
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - the descriptor contract is Unix-only
    fcntl = None  # type: ignore[assignment]


EXPECTED_VERIFIER_SHA256 = "9016d843c28142903728fab83860bb58f22f162d9f327f045c36d6ec1540b241"
DENY = "SUBJECT_IMPLEMENTATION_AUTHORIZATION_RUNNER_DENY\n"
ERROR = "SUBJECT_IMPLEMENTATION_AUTHORIZATION_RUNNER_ERROR\n"
CLEANUP_REQUIRED = '{"status":"private_cleanup_required"}\n'
VERIFIER_DENY = "SUBJECT_IMPLEMENTATION_AUTHORIZATION_DENY\n"
VERIFIER_ERROR = "SUBJECT_IMPLEMENTATION_AUTHORIZATION_ERROR\n"


def _load_verifier():
    path = Path(__file__).with_name("verify_subject_implementation_authorization.py")
    flags = os.O_RDONLY
    for name in ("O_NOFOLLOW", "O_CLOEXEC"):
        if not hasattr(os, name):
            raise RuntimeError
        flags |= int(getattr(os, name))
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 1_048_576:
            raise RuntimeError
        raw = b""
        while len(raw) <= 1_048_576:
            part = os.read(fd, min(65_536, 1_048_577 - len(raw)))
            if not part:
                break
            raw += part
        after = os.fstat(fd)
        if (
            len(raw) > 1_048_576
            or hashlib.sha256(raw).hexdigest() != EXPECTED_VERIFIER_SHA256
            or (
                after.st_dev,
                after.st_ino,
                after.st_mode,
                after.st_size,
                after.st_mtime_ns,
            )
            != (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns)
        ):
            raise RuntimeError
    finally:
        os.close(fd)
    spec = importlib.util.spec_from_file_location("subject_authorization_verifier", path)
    if spec is None:
        raise RuntimeError
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)  # noqa: S102 - fixed reviewed bytes
    return module, raw


try:
    verifier, VERIFIER_SOURCE = _load_verifier()
except Exception:  # noqa: BLE001 - startup failure is fixed-output and no-echo
    verifier = None
    VERIFIER_SOURCE = b""

AUTHORITY = "github:zycaskevin"
PROPOSAL_KIND = "subject-implementation-proposal"
SCOPE_KIND = "subject-distillation-implementation-scope"
PROGRESS_PATH = "specs/subject-distillation/implementation-progress.json"
VALIDITY = timedelta(minutes=15)
CHILD_TIMEOUT_SECONDS = 30
HEX64 = re.compile(r"[0-9a-f]{64}")
COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")

T001_PATHS = (
    "scripts/read_subject_baseline_id.py",
    "scripts/update_subject_progress.py",
    "scripts/validate_subject_evidence.py",
    "scripts/validate_subject_progress.py",
    "specs/subject-distillation/evidence-schemas/attestation.schema.json",
    "specs/subject-distillation/evidence-schemas/backup-restore.schema.json",
    "specs/subject-distillation/evidence-schemas/environment.schema.json",
    "specs/subject-distillation/evidence-schemas/fresh-review.schema.json",
    "specs/subject-distillation/evidence-schemas/migration.schema.json",
    "specs/subject-distillation/evidence-schemas/review-result.schema.json",
    "specs/subject-distillation/evidence/{baseline_id}/environment.json",
    "specs/subject-distillation/implementation-progress.json",
    "specs/subject-distillation/implementation-progress.schema.json",
    "tests/test_subject_baseline_control.py",
    "tests/test_subject_progress.py",
)
T001_NON_GOALS = (
    "no.live.private.data",
    "no.t002.plus.artifact",
    "no_product_runtime",
    "no_production_migration",
)
T001_PROHIBITED = (
    "commit",
    "deploy",
    "github",
    "live_private_data",
    "migration",
    "pr",
    "product_runtime",
    "push",
    "release",
    "remote_network",
    "stage",
)
PROPOSAL_KEYS = {
    "schema_version",
    "artifact_kind",
    "authorized_task",
    "implementation_base_commit",
    "baseline_id",
    "baseline_full_digest",
    "authorizing_principal",
    "allowed_repo_relative_paths",
    "non_goals",
    "prohibited_operations",
    "issued_at_utc",
    "expires_at_utc",
    "scope_sha256",
    "receipt_sha256",
    "authorization_verifier_sha256",
    "authorization_schema_sha256",
    "authorization_id",
    "proposal_id",
}


class Denied(Exception):
    pass


class InternalFailure(Exception):
    pass


class PrivateCleanupRequired(Exception):
    pass


class Interrupted(Denied):
    pass


VERIFIER_DENIED = verifier.Denied if verifier is not None else Denied


@dataclass(frozen=True)
class RepositoryState:
    repo_root: str
    head: str
    clean: bool


@dataclass(frozen=True)
class ProgressSnapshot:
    exists: bool
    fingerprint: str
    task_state: str


@dataclass(frozen=True)
class ChildResult:
    returncode: int
    stdout: bytes
    stderr: bytes


@dataclass
class SignalState:
    cleanup_active: bool = False
    interrupted: bool = False


@dataclass
class Runtime:
    now: Callable[[], datetime] = field(default_factory=lambda: lambda: datetime.now(timezone.utc))
    repository_state: Callable[[], RepositoryState] | None = None
    progress_snapshot: Callable[[str], ProgressSnapshot] | None = None
    temp_root: str | None = None
    hook: Callable[[str, Lifecycle], None] | None = None
    run_child: Callable[[list[str], str, dict[str, str], int], ChildResult] | None = None
    write: Callable[[int, bytes], int] | None = None
    unlink: Callable[..., None] | None = None
    rmdir: Callable[..., None] | None = None


Identity = tuple[int, int, int, int, int]


@dataclass
class Lifecycle:
    parent_handle: Any
    parent_fd: int
    dirname: str
    dir_fd: int
    dir_identity: Identity
    receipt_fd: int | None
    receipt_identity: Identity | None
    scope_fd: int | None
    scope_identity: Identity | None
    owned_fds: list[int]
    receipt_raw: bytes
    scope_raw: bytes


@dataclass
class LifecycleSlot:
    value: Lifecycle | None = None


@dataclass(frozen=True)
class RepoInputs:
    baseline_id: str
    full_digest: str
    schema_raw: bytes
    verifier_raw: bytes


def _canonical(value: Any, *, newline: bool = True) -> bytes:
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise Denied from None
    return encoded + (b"\n" if newline else b"")


def _identity(info: os.stat_result) -> Identity:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns)


def _same_object(left: Identity, right: Identity) -> bool:
    return left[:2] == right[:2]


def _exact_line(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeError:
        raise Denied from None
    if not text.endswith("\n") or "\n" in text[:-1]:
        raise Denied
    return text[:-1]


def _git(args: list[str]) -> bytes:
    try:
        result = subprocess.run(
            ["git", *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        raise Denied from None
    if result.returncode != 0:
        raise Denied
    return result.stdout


def _default_repository_state() -> RepositoryState:
    root = _exact_line(_git(["rev-parse", "--show-toplevel"]))
    head = _exact_line(_git(["rev-parse", "HEAD"]))
    status = _git(["status", "--porcelain=v1", "--untracked-files=all"])
    if not os.path.isabs(root) or os.path.normpath(root) != root or root != os.getcwd():
        raise Denied
    return RepositoryState(root, head, not status)


def _repository_state(runtime: Runtime) -> RepositoryState:
    state = (
        runtime.repository_state()
        if runtime.repository_state is not None
        else _default_repository_state()
    )
    if (
        type(state) is not RepositoryState
        or type(state.repo_root) is not str
        or not os.path.isabs(state.repo_root)
        or os.path.normpath(state.repo_root) != state.repo_root
        or state.repo_root != os.getcwd()
        or type(state.head) is not str
        or COMMIT.fullmatch(state.head) is None
        or type(state.clean) is not bool
    ):
        raise Denied
    return state


def _parse_arguments(argv: Sequence[str]) -> tuple[str, dict[str, str]]:
    if not argv or argv[0] not in {"propose", "verify-confirmed"}:
        raise Denied
    mode = argv[0]
    value_flags = (
        {"--implementation-base-commit", "--expected-task"}
        if mode == "propose"
        else {
            "--proposal-json",
            "--implementation-base-commit",
            "--expected-receipt-sha256",
            "--expected-task",
        }
    )
    boolean_flags = {"--json"} | ({"--require-cleanup"} if mode == "verify-confirmed" else set())
    values: dict[str, str] = {}
    seen: set[str] = set()
    index = 1
    while index < len(argv):
        flag = argv[index]
        if flag in seen:
            raise Denied
        seen.add(flag)
        if flag in boolean_flags:
            index += 1
            continue
        if flag not in value_flags or index + 1 >= len(argv):
            raise Denied
        value = argv[index + 1]
        if value.startswith("--"):
            raise Denied
        values[flag] = value
        index += 2
    if seen != value_flags | boolean_flags or set(values) != value_flags:
        raise Denied
    return mode, values


def _repo_inputs(repo_root: str) -> RepoInputs:
    owned: list[int] = []
    handles: list[Any] = []
    try:
        root_fd = os.open("/", verifier._flags(directory=True))
        owned.append(root_fd)
        discovered, repo = verifier._repo_root(root_fd, owned)
        if discovered != repo_root:
            raise Denied
        handles.append(repo)
        manifest_handle = verifier._open_chain(
            repo.fd, verifier.MANIFEST_PATH.split("/"), owned
        )
        schema_handle = verifier._open_chain(repo.fd, verifier.SCHEMA_PATH.split("/"), owned)
        verifier_handle = verifier._open_chain(
            repo.fd, verifier.VERIFIER_PATH.split("/"), owned
        )
        handles.extend([manifest_handle, schema_handle, verifier_handle])
        manifest_raw = verifier._read(manifest_handle)
        schema_raw = verifier._read(schema_handle)
        verifier_raw = verifier._read(verifier_handle)
        if verifier_raw != VERIFIER_SOURCE:
            raise Denied
        manifest = verifier._parse(manifest_raw)
        schema = verifier._parse(schema_raw)
        verifier._scan(manifest)
        verifier._scan(schema)
        baseline_id, full_digest = verifier._manifest(manifest)
        verifier._bind_manifest_files(manifest, repo, owned, handles)
        verifier._schema_shape(schema)
        verifier._audit(handles)
        return RepoInputs(baseline_id, full_digest, schema_raw, verifier_raw)
    except verifier.Denied:
        raise Denied from None
    except Denied:
        raise
    except Exception:  # noqa: BLE001 - fail closed around verifier internals
        raise InternalFailure from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _format_time(value: datetime) -> str:
    if value.tzinfo != timezone.utc or value.microsecond:
        raise Denied
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _scope(inputs: RepoInputs, task: str) -> tuple[dict[str, Any], bytes]:
    if task != "T-001":
        raise Denied
    paths = [path.format(baseline_id=inputs.baseline_id) for path in T001_PATHS]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise InternalFailure
    value = {
        "schema_version": 1,
        "artifact_kind": SCOPE_KIND,
        "baseline_id": inputs.baseline_id,
        "baseline_full_digest": inputs.full_digest,
        "authorized_task": task,
        "allowed_repo_relative_paths": paths,
        "non_goals": list(T001_NON_GOALS),
        "prohibited_operations": list(T001_PROHIBITED),
    }
    return value, _canonical(value)


def _derive(
    inputs: RepoInputs,
    base_commit: str,
    task: str,
    issued: datetime,
) -> tuple[dict[str, Any], bytes, bytes]:
    scope, scope_raw = _scope(inputs, task)
    issued_text = _format_time(issued)
    expires_text = _format_time(issued + VALIDITY)
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "subject-distillation-implementation-authorization",
        "baseline_id": inputs.baseline_id,
        "baseline_full_digest": inputs.full_digest,
        "authorizing_principal": AUTHORITY,
        "authorized_task": task,
        "scope_sha256": hashlib.sha256(scope_raw).hexdigest(),
        "authorization_verifier_sha256": hashlib.sha256(inputs.verifier_raw).hexdigest(),
        "authorization_schema_sha256": hashlib.sha256(inputs.schema_raw).hexdigest(),
        "issued_at_utc": issued_text,
        "expires_at_utc": expires_text,
    }
    receipt["authorization_id"] = hashlib.sha256(
        _canonical(receipt, newline=False)
    ).hexdigest()
    receipt_raw = _canonical(receipt)
    proposal: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": PROPOSAL_KIND,
        "authorized_task": task,
        "implementation_base_commit": base_commit,
        "baseline_id": inputs.baseline_id,
        "baseline_full_digest": inputs.full_digest,
        "authorizing_principal": AUTHORITY,
        "allowed_repo_relative_paths": scope["allowed_repo_relative_paths"],
        "non_goals": scope["non_goals"],
        "prohibited_operations": scope["prohibited_operations"],
        "issued_at_utc": issued_text,
        "expires_at_utc": expires_text,
        "scope_sha256": receipt["scope_sha256"],
        "receipt_sha256": hashlib.sha256(receipt_raw).hexdigest(),
        "authorization_verifier_sha256": receipt["authorization_verifier_sha256"],
        "authorization_schema_sha256": receipt["authorization_schema_sha256"],
        "authorization_id": receipt["authorization_id"],
    }
    proposal["proposal_id"] = hashlib.sha256(_canonical(proposal)).hexdigest()
    return proposal, receipt_raw, scope_raw


def _clock(runtime: Runtime) -> datetime:
    value = runtime.now()
    if type(value) is not datetime or value.tzinfo != timezone.utc:
        raise Denied
    return value


def _proposal(raw_text: str, now: datetime) -> tuple[dict[str, Any], datetime]:
    if type(raw_text) is not str:
        raise Denied
    raw = raw_text.encode("utf-8")
    if len(raw) > verifier.MAX_BYTES:
        raise Denied
    try:
        value = verifier._parse(raw)
    except verifier.Denied:
        raise Denied from None
    if type(value) is not dict or set(value) != PROPOSAL_KEYS:
        raise Denied
    if raw != _canonical(value):
        raise Denied
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise Denied
    fixed_strings = {
        "artifact_kind": PROPOSAL_KIND,
        "authorizing_principal": AUTHORITY,
        "authorized_task": "T-001",
    }
    if any(type(value[key]) is not str or value[key] != expected for key, expected in fixed_strings.items()):
        raise Denied
    if COMMIT.fullmatch(value["implementation_base_commit"]) is None:
        raise Denied
    if verifier.HEX16.fullmatch(value["baseline_id"]) is None:
        raise Denied
    for key in (
        "baseline_full_digest",
        "scope_sha256",
        "receipt_sha256",
        "authorization_verifier_sha256",
        "authorization_schema_sha256",
        "authorization_id",
        "proposal_id",
    ):
        if type(value[key]) is not str or HEX64.fullmatch(value[key]) is None:
            raise Denied
    for key in ("allowed_repo_relative_paths", "non_goals", "prohibited_operations"):
        items = value[key]
        if (
            type(items) is not list
            or any(type(item) is not str or not item.isascii() for item in items)
            or items != sorted(items)
            or len(items) != len(set(items))
        ):
            raise Denied
    issued = verifier._timestamp(value["issued_at_utc"])
    expires = verifier._timestamp(value["expires_at_utc"])
    if issued.microsecond or expires - issued != VALIDITY or issued > now or now >= expires:
        raise Denied
    without_id = dict(value)
    without_id.pop("proposal_id")
    if value["proposal_id"] != hashlib.sha256(_canonical(without_id)).hexdigest():
        raise Denied
    return value, issued


def _default_progress_snapshot(repo_root: str) -> ProgressSnapshot:
    path = os.path.join(repo_root, PROGRESS_PATH)
    try:
        info = os.stat(path, follow_symlinks=False)
    except FileNotFoundError:
        return ProgressSnapshot(False, "", "PENDING")
    except OSError:
        raise Denied from None
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_size > verifier.MAX_BYTES:
        raise Denied
    try:
        fd = os.open(path, verifier._flags(directory=False))
        raw = b""
        try:
            before = os.fstat(fd)
            while len(raw) <= verifier.MAX_BYTES:
                part = os.read(fd, min(65_536, verifier.MAX_BYTES + 1 - len(raw)))
                if not part:
                    break
                raw += part
            after = os.fstat(fd)
        finally:
            os.close(fd)
    except OSError:
        raise Denied from None
    if len(raw) > verifier.MAX_BYTES or _identity(before) != _identity(after):
        raise Denied
    try:
        value = verifier._parse(raw)
    except verifier.Denied:
        raise Denied from None
    if type(value) is not dict or type(value.get("tasks")) is not dict:
        raise Denied
    state = value["tasks"].get("T-001")
    if state not in {"PENDING", "IN_PROGRESS", "BLOCKED", "COMPLETED"}:
        raise Denied
    fingerprint = hashlib.sha256(raw).hexdigest() + ":" + ":".join(map(str, _identity(after)))
    return ProgressSnapshot(True, fingerprint, state)


def _progress(runtime: Runtime, repo_root: str) -> ProgressSnapshot:
    value = (
        runtime.progress_snapshot(repo_root)
        if runtime.progress_snapshot is not None
        else _default_progress_snapshot(repo_root)
    )
    if (
        type(value) is not ProgressSnapshot
        or type(value.exists) is not bool
        or type(value.fingerprint) is not str
        or value.task_state not in {"PENDING", "IN_PROGRESS", "BLOCKED", "COMPLETED"}
    ):
        raise Denied
    return value


def _require_prestart(value: ProgressSnapshot) -> None:
    # T-001 creates the ledger and immediately records itself IN_PROGRESS.  At
    # this pre-task gate, any existing ledger is therefore replay/drift and is
    # safer to reject than to partially reimplement the future strict validator.
    if value.exists or value.task_state != "PENDING":
        raise Denied


def _external_root(runtime: Runtime, repo_root: str) -> str:
    root = runtime.temp_root if runtime.temp_root is not None else tempfile.gettempdir()
    if (
        type(root) is not str
        or not os.path.isabs(root)
        or os.path.normpath(root) != root
        or root == repo_root
        or root.startswith(repo_root + os.sep)
    ):
        raise Denied
    return root


def _open_external_root(path: str) -> tuple[Any, list[int]]:
    owned: list[int] = []
    try:
        root_fd = os.open("/", verifier._flags(directory=True))
        owned.append(root_fd)
        handle = verifier._open_chain(
            root_fd, verifier._absolute_parts(path), owned, final_directory=True
        )
        verifier._audit([handle])
        return handle, owned
    except verifier.Denied:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass
        raise Denied from None


def _audit_directory_handle_identity(handle: Any) -> None:
    """Audit stable directory identity while allowing owned member changes."""
    try:
        retained = _identity(os.fstat(handle.fd))
        if not stat.S_ISDIR(retained[2]) or retained[:3] != handle.identity[:3]:
            raise Denied
        for parent_fd, name, before in handle.chain:
            current = _identity(
                os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            )
            if not stat.S_ISDIR(current[2]) or current[:3] != before[:3]:
                raise Denied
    except OSError:
        raise Denied from None


@contextmanager
def _authorization_lock(
    repo_root: str, task: str, base_commit: str, runtime: Runtime
) -> Iterator[Callable[[], None]]:
    if fcntl is None:
        raise Denied
    external = _external_root(runtime, repo_root)
    parent, owned = _open_external_root(external)
    lock_fd: int | None = None
    stable_lock_fd: int | None = None
    stable_lock_handle: Any | None = None
    try:
        if not owned:
            raise Denied
        stable_lock_handle = verifier._open_chain(
            owned[0],
            verifier._absolute_parts(repo_root),
            owned,
            final_directory=True,
        )
        verifier._audit([stable_lock_handle])
        stable_lock_fd = stable_lock_handle.fd
        stable_info = os.fstat(stable_lock_fd)
        if not stat.S_ISDIR(stable_info.st_mode):
            raise Denied
        try:
            fcntl.flock(stable_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError):
            raise Denied from None
        _audit_directory_handle_identity(stable_lock_handle)
        _audit_directory_handle_identity(parent)

        digest = hashlib.sha256(f"{repo_root}\0{task}\0{base_commit}".encode()).hexdigest()
        name = f"subject-authorization-{digest}.lock"
        flags = os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW
        lock_fd = os.open(name, flags, 0o600, dir_fd=parent.fd)
        owned.append(lock_fd)
        info = os.fstat(lock_fd)
        lock_identity = _identity(info)

        def audit_lock() -> None:
            if lock_fd is None:
                raise Denied
            try:
                if stable_lock_handle is None:
                    raise Denied
                _audit_directory_handle_identity(stable_lock_handle)
                _audit_directory_handle_identity(parent)
                retained = os.fstat(lock_fd)
                current = os.stat(name, dir_fd=parent.fd, follow_symlinks=False)
            except OSError:
                raise Denied from None
            if (
                not stat.S_ISREG(retained.st_mode)
                or stat.S_IMODE(retained.st_mode) != 0o600
                or retained.st_nlink != 1
                or _identity(retained) != lock_identity
                or _identity(current) != lock_identity
            ):
                raise Denied

        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
        ):
            raise Denied
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError):
            raise Denied from None
        audit_lock()
        yield audit_lock
        audit_lock()
    finally:
        if lock_fd is not None and fcntl is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except OSError:
                pass
        if stable_lock_fd is not None and fcntl is not None:
            try:
                fcntl.flock(stable_lock_fd, fcntl.LOCK_UN)
            except OSError:
                pass
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _creation_flags() -> int:
    required = ("O_NOFOLLOW", "O_CLOEXEC")
    if any(not hasattr(os, name) for name in required):
        raise Denied
    return os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC


def _write_all(fd: int, raw: bytes, runtime: Runtime) -> None:
    write = runtime.write if runtime.write is not None else os.write
    offset = 0
    try:
        while offset < len(raw):
            count = write(fd, raw[offset:])
            if type(count) is not int or count <= 0 or count > len(raw) - offset:
                raise InternalFailure
            offset += count
        os.fsync(fd)
        os.lseek(fd, 0, os.SEEK_SET)
    except InternalFailure:
        raise
    except OSError:
        raise InternalFailure from None


def _close_fds(owned: list[int]) -> None:
    for fd in reversed(owned):
        try:
            os.close(fd)
        except OSError:
            pass


def _cleanup_early_directory(
    parent_fd: int,
    dirname: str,
    identity: Identity | None,
    runtime: Runtime,
) -> bool:
    if identity is None:
        return False
    candidate_fd: int | None = None
    try:
        current = os.stat(dirname, dir_fd=parent_fd, follow_symlinks=False)
        if _identity(current) != identity or not stat.S_ISDIR(current.st_mode):
            return False
        candidate_fd = os.open(dirname, verifier._flags(directory=True), dir_fd=parent_fd)
        if _identity(os.fstat(candidate_fd)) != identity or os.listdir(candidate_fd):
            return False
        rmdir = runtime.rmdir if runtime.rmdir is not None else os.rmdir
        if not _retry(lambda: rmdir(dirname, dir_fd=parent_fd)):
            return False
        try:
            os.stat(dirname, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return True
        except OSError:
            return False
        return False
    except OSError:
        return False
    finally:
        if candidate_fd is not None:
            try:
                os.close(candidate_fd)
            except OSError:
                pass


def _new_lifecycle(
    external: str,
    receipt_raw: bytes,
    scope_raw: bytes,
    runtime: Runtime,
    signals: SignalState,
    slot: LifecycleSlot,
) -> Lifecycle:
    parent, owned = _open_external_root(external)
    dirname = "subject-authorization-" + secrets.token_hex(16)
    directory_created = False
    created_identity: Identity | None = None
    lifecycle: Lifecycle | None = None
    try:
        os.mkdir(dirname, 0o700, dir_fd=parent.fd)
        directory_created = True
        created = os.stat(dirname, dir_fd=parent.fd, follow_symlinks=False)
        created_identity = _identity(created)
        if not stat.S_ISDIR(created.st_mode) or stat.S_IMODE(created.st_mode) != 0o700:
            raise Denied
        parent_identity = _identity(os.fstat(parent.fd))
        parent_chain = list(parent.chain)
        chain_parent, chain_name, _old_identity = parent_chain[-1]
        parent_chain[-1] = (chain_parent, chain_name, parent_identity)
        parent = verifier.Handle(parent.fd, parent_identity, tuple(parent_chain))
        dir_fd = os.open(dirname, verifier._flags(directory=True), dir_fd=parent.fd)
        owned.append(dir_fd)
        dir_info = os.fstat(dir_fd)
        if _identity(dir_info) != created_identity:
            raise Denied
        lifecycle = Lifecycle(
            parent,
            parent.fd,
            dirname,
            dir_fd,
            _identity(dir_info),
            None,
            None,
            None,
            None,
            owned,
            receipt_raw,
            scope_raw,
        )
        for name, raw in (("receipt.json", receipt_raw), ("scope.json", scope_raw)):
            fd = os.open(name, _creation_flags(), 0o600, dir_fd=dir_fd)
            owned.append(fd)
            lifecycle.dir_identity = _identity(os.fstat(dir_fd))
            info = os.fstat(fd)
            if name == "receipt.json":
                lifecycle.receipt_fd = fd
                lifecycle.receipt_identity = _identity(info)
            else:
                lifecycle.scope_fd = fd
                lifecycle.scope_identity = _identity(info)
            try:
                _write_all(fd, raw, runtime)
            finally:
                info = os.fstat(fd)
                current = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
                if not _same_object(_identity(info), _identity(current)):
                    raise Denied
                if name == "receipt.json":
                    lifecycle.receipt_identity = _identity(info)
                else:
                    lifecycle.scope_identity = _identity(info)
        lifecycle.dir_identity = _identity(os.fstat(dir_fd))
        _audit_lifecycle(lifecycle)
        slot.value = lifecycle
        return lifecycle
    except (Denied, InternalFailure, Interrupted, PrivateCleanupRequired):
        signals.cleanup_active = True
        if lifecycle is not None:
            cleaned = _cleanup(lifecycle, runtime, invoke_hook=False)
            _close_lifecycle(lifecycle)
            slot.value = None
            if not cleaned:
                raise PrivateCleanupRequired from None
        elif directory_created:
            cleaned = _cleanup_early_directory(
                parent.fd, dirname, created_identity, runtime
            )
            _close_fds(owned)
            if not cleaned:
                raise PrivateCleanupRequired from None
        else:
            _close_fds(owned)
        raise
    except Exception:  # noqa: BLE001 - cleanup must run for every unexpected fault
        signals.cleanup_active = True
        if lifecycle is not None:
            cleaned = _cleanup(lifecycle, runtime, invoke_hook=False)
            _close_lifecycle(lifecycle)
            slot.value = None
            if not cleaned:
                raise PrivateCleanupRequired from None
        elif directory_created:
            cleaned = _cleanup_early_directory(
                parent.fd, dirname, created_identity, runtime
            )
            _close_fds(owned)
            if not cleaned:
                raise PrivateCleanupRequired from None
        else:
            _close_fds(owned)
        raise InternalFailure from None


def _read_retained(fd: int, maximum: int) -> bytes:
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            part = os.read(fd, min(65_536, remaining))
            if not part:
                break
            chunks.append(part)
            remaining -= len(part)
        os.lseek(fd, 0, os.SEEK_SET)
    except OSError:
        raise Denied from None
    raw = b"".join(chunks)
    if len(raw) > maximum:
        raise Denied
    return raw


def _audit_lifecycle(value: Lifecycle) -> None:
    if (
        value.receipt_fd is None
        or value.scope_fd is None
        or value.receipt_identity is None
        or value.scope_identity is None
    ):
        raise Denied
    try:
        verifier._audit([value.parent_handle])
        current_dir = os.stat(value.dirname, dir_fd=value.parent_fd, follow_symlinks=False)
        if _identity(os.fstat(value.dir_fd)) != value.dir_identity:
            raise Denied
        if _identity(current_dir) != value.dir_identity:
            raise Denied
        if stat.S_IMODE(current_dir.st_mode) != 0o700:
            raise Denied
        if set(os.listdir(value.dir_fd)) != {"receipt.json", "scope.json"}:
            raise Denied
        for name, fd, identity, raw in (
            ("receipt.json", value.receipt_fd, value.receipt_identity, value.receipt_raw),
            ("scope.json", value.scope_fd, value.scope_identity, value.scope_raw),
        ):
            current = os.stat(name, dir_fd=value.dir_fd, follow_symlinks=False)
            retained = os.fstat(fd)
            if _identity(current) != identity or _identity(retained) != identity:
                raise Denied
            if not stat.S_ISREG(retained.st_mode) or stat.S_IMODE(retained.st_mode) != 0o600:
                raise Denied
            if _read_retained(fd, verifier.MAX_BYTES) != raw:
                raise Denied
    except verifier.Denied:
        raise Denied from None
    except OSError:
        raise Denied from None


def _retry(operation: Callable[[], None]) -> bool:
    for _ in range(2):
        try:
            operation()
            return True
        except OSError:
            continue
    return False


def _cleanup(value: Lifecycle, runtime: Runtime, *, invoke_hook: bool = True) -> bool:
    if invoke_hook and runtime.hook is not None:
        try:
            runtime.hook("before_cleanup", value)
        except Exception:  # noqa: BLE001, S110 - cleanup cannot trust test/operator hooks
            pass
    unlink = runtime.unlink if runtime.unlink is not None else os.unlink
    rmdir = runtime.rmdir if runtime.rmdir is not None else os.rmdir
    try:
        current_dir = os.stat(value.dirname, dir_fd=value.parent_fd, follow_symlinks=False)
        retained_dir = os.fstat(value.dir_fd)
        members = os.listdir(value.dir_fd)
    except OSError:
        return False
    expected_members = {
        name
        for name, identity in (
            ("receipt.json", value.receipt_identity),
            ("scope.json", value.scope_identity),
        )
        if identity is not None
    }
    if (
        not _same_object(_identity(current_dir), value.dir_identity)
        or not _same_object(_identity(retained_dir), value.dir_identity)
        or set(members) != expected_members
    ):
        return False
    for name, fd, identity in (
        ("receipt.json", value.receipt_fd, value.receipt_identity),
        ("scope.json", value.scope_fd, value.scope_identity),
    ):
        if fd is None and identity is None:
            continue
        if fd is None or identity is None:
            return False
        try:
            current = os.stat(name, dir_fd=value.dir_fd, follow_symlinks=False)
            retained = os.fstat(fd)
        except OSError:
            return False
        if not _same_object(_identity(current), identity) or not _same_object(
            _identity(retained), identity
        ):
            return False
    success = True
    for name, identity in (
        ("receipt.json", value.receipt_identity),
        ("scope.json", value.scope_identity),
    ):
        if identity is None:
            continue
        try:
            current = os.stat(name, dir_fd=value.dir_fd, follow_symlinks=False)
        except FileNotFoundError:
            continue
        except OSError:
            success = False
            continue
        if not _same_object(_identity(current), identity):
            success = False
            continue
        if not _retry(lambda name=name: unlink(name, dir_fd=value.dir_fd)):
            success = False
            continue
        try:
            os.stat(name, dir_fd=value.dir_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        except OSError:
            success = False
        else:
            success = False
    try:
        members = os.listdir(value.dir_fd)
    except OSError:
        members = ["unknown"]
    if members:
        success = False
    try:
        current_dir = os.stat(value.dirname, dir_fd=value.parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        current_dir = None
    except OSError:
        current_dir = None
        success = False
    if current_dir is not None and (
        not _same_object(_identity(current_dir), value.dir_identity)
        or members
        or not _retry(lambda: rmdir(value.dirname, dir_fd=value.parent_fd))
    ):
        success = False
    try:
        os.stat(value.dirname, dir_fd=value.parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        absent = True
    except OSError:
        absent = False
    else:
        absent = False
    success = success and absent
    if success and invoke_hook and runtime.hook is not None:
        try:
            runtime.hook("after_cleanup", value)
        except Exception:  # noqa: BLE001 - hook failure makes cleanup unverifiable
            success = False
    return success


def _close_lifecycle(value: Lifecycle) -> None:
    for fd in reversed(value.owned_fds):
        try:
            os.close(fd)
        except OSError:
            pass


def _default_run_child(
    argv: list[str], cwd: str, env: dict[str, str], timeout: int
) -> ChildResult:
    result = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    return ChildResult(result.returncode, result.stdout, result.stderr)


def _sanitized_environment() -> dict[str, str]:
    value = {"PATH": os.environ.get("PATH", os.defpath), "PYTHONUTF8": "1"}
    for key in ("LANG", "LC_ALL", "LC_CTYPE"):
        if key in os.environ:
            value[key] = os.environ[key]
    return value


def _run_verifier(
    lifecycle: Lifecycle,
    repo_root: str,
    expected_digest: str,
    task: str,
    expected_output: bytes,
    runtime: Runtime,
) -> None:
    external = _external_root(runtime, repo_root)
    directory = os.path.join(external, lifecycle.dirname)
    argv = [
        sys.executable,
        "-I",
        "-c",
        VERIFIER_SOURCE.decode("utf-8", "strict"),
        "--receipt",
        os.path.join(directory, "receipt.json"),
        "--expected-receipt-sha256",
        expected_digest,
        "--scope",
        os.path.join(directory, "scope.json"),
        "--manifest",
        verifier.MANIFEST_PATH,
        "--schema",
        verifier.SCHEMA_PATH,
        "--expected-authority",
        AUTHORITY,
        "--expected-task",
        task,
        "--json",
    ]
    run_child = runtime.run_child if runtime.run_child is not None else _default_run_child
    try:
        result = run_child(argv, repo_root, _sanitized_environment(), CHILD_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise InternalFailure from None
    except OSError:
        raise InternalFailure from None
    if type(result) is not ChildResult:
        raise InternalFailure
    if result.returncode == 0 and result.stderr == b"" and result.stdout == expected_output:
        return
    if (
        result.returncode == 2
        and result.stdout == b""
        and result.stderr == VERIFIER_DENY.encode()
    ):
        raise Denied
    if (
        result.returncode == 3
        and result.stdout == b""
        and result.stderr == VERIFIER_ERROR.encode()
    ):
        raise InternalFailure
    raise InternalFailure


@contextmanager
def _signal_boundary() -> Iterator[SignalState]:
    previous: dict[int, Any] = {}
    state = SignalState()

    def interrupt(_signum: int, _frame: Any) -> None:
        if state.cleanup_active:
            state.interrupted = True
            return
        raise Interrupted

    try:
        for name in ("SIGHUP", "SIGINT", "SIGTERM"):
            if hasattr(signal, name):
                number = int(getattr(signal, name))
                previous[number] = signal.getsignal(number)
                signal.signal(number, interrupt)
        yield state
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def _hook(runtime: Runtime, event: str, lifecycle: Lifecycle) -> None:
    if runtime.hook is not None:
        runtime.hook(event, lifecycle)


def _propose(values: dict[str, str], runtime: Runtime) -> bytes:
    base = values["--implementation-base-commit"]
    task = values["--expected-task"]
    if COMMIT.fullmatch(base) is None or task != "T-001":
        raise Denied
    state = _repository_state(runtime)
    if not state.clean or state.head != base:
        raise Denied
    inputs = _repo_inputs(state.repo_root)
    issued = _clock(runtime).replace(microsecond=0)
    proposal, _receipt_raw, _scope_raw = _derive(inputs, base, task, issued)
    final_state = _repository_state(runtime)
    if final_state != state:
        raise Denied
    return _canonical(proposal)


def _verify_confirmed(values: dict[str, str], runtime: Runtime) -> bytes:
    base = values["--implementation-base-commit"]
    task = values["--expected-task"]
    expected_digest = values["--expected-receipt-sha256"]
    if COMMIT.fullmatch(base) is None or task != "T-001" or HEX64.fullmatch(expected_digest) is None:
        raise Denied
    now = _clock(runtime)
    proposal, issued = _proposal(values["--proposal-json"], now)
    if proposal["implementation_base_commit"] != base or proposal["authorized_task"] != task:
        raise Denied
    state = _repository_state(runtime)
    if not state.clean or state.head != base:
        raise Denied
    external = _external_root(runtime, state.repo_root)
    initial_progress = _progress(runtime, state.repo_root)
    _require_prestart(initial_progress)
    with _authorization_lock(state.repo_root, task, base, runtime) as audit_lock:
        locked_state = _repository_state(runtime)
        if locked_state != state:
            raise Denied
        inputs = _repo_inputs(state.repo_root)
        derived, receipt_raw, scope_raw = _derive(inputs, base, task, issued)
        if not verifier._exact_equal(proposal, derived):
            raise Denied
        if expected_digest != proposal["receipt_sha256"]:
            raise Denied
        if hashlib.sha256(receipt_raw).hexdigest() != expected_digest:
            raise Denied
        before_progress = _progress(runtime, state.repo_root)
        _require_prestart(before_progress)
        if before_progress != initial_progress:
            raise Denied
        slot = LifecycleSlot()
        failure: BaseException | None = None
        output = _canonical(
            {
                "authorization_id": proposal["authorization_id"],
                "authorized_task": task,
                "baseline_id": proposal["baseline_id"],
                "status": "PASS",
            }
        )
        with _signal_boundary() as signals:
            try:
                audit_lock()
                _new_lifecycle(
                    external, receipt_raw, scope_raw, runtime, signals, slot
                )
                lifecycle = slot.value
                if lifecycle is None:
                    raise InternalFailure
                _hook(runtime, "after_materialize", lifecycle)
                _hook(runtime, "before_verifier", lifecycle)
                _audit_lifecycle(lifecycle)
                if hashlib.sha256(_read_retained(lifecycle.receipt_fd, verifier.MAX_BYTES)).hexdigest() != expected_digest:  # type: ignore[arg-type]
                    raise Denied
                _run_verifier(
                    lifecycle,
                    state.repo_root,
                    expected_digest,
                    task,
                    output,
                    runtime,
                )
                audit_lock()
                _hook(runtime, "after_verifier", lifecycle)
                after_progress = _progress(runtime, state.repo_root)
                _require_prestart(after_progress)
                if after_progress != before_progress:
                    raise Denied
                if _repository_state(runtime) != state:
                    raise Denied
                _audit_lifecycle(lifecycle)
            except (Denied, InternalFailure, Interrupted, PrivateCleanupRequired) as exc:
                failure = exc
            except Exception:  # noqa: BLE001 - public boundary is deliberately fail closed
                failure = InternalFailure()
            finally:
                signals.cleanup_active = True
                cleanup_ok = True
                lifecycle = slot.value
                if lifecycle is not None:
                    cleanup_ok = _cleanup(lifecycle, runtime)
                    _close_lifecycle(lifecycle)
                    slot.value = None
        if signals.interrupted and not isinstance(failure, PrivateCleanupRequired):
            failure = Interrupted()
        if not cleanup_ok or isinstance(failure, PrivateCleanupRequired):
            raise PrivateCleanupRequired
        if failure is not None:
            raise failure
        return output


def main(argv: Sequence[str] | None = None, *, _runtime: Runtime | None = None) -> int:
    if verifier is None:
        sys.stderr.write(ERROR)
        return 3
    runtime = _runtime if _runtime is not None else Runtime()
    try:
        mode, values = _parse_arguments(sys.argv[1:] if argv is None else argv)
        output = _propose(values, runtime) if mode == "propose" else _verify_confirmed(values, runtime)
    except PrivateCleanupRequired:
        sys.stdout.write(CLEANUP_REQUIRED)
        return 4
    except (Denied, VERIFIER_DENIED):
        sys.stderr.write(DENY)
        return 2
    except Exception:  # noqa: BLE001 - all public faults are fixed and no-echo
        sys.stderr.write(ERROR)
        return 3
    sys.stdout.write(output.decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
