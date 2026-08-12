#!/usr/bin/env python3
"""Owner-confirmed additive authorization bridge for Subject T-003."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

EXPECTED_V1_RUNNER_SHA256 = "51ebcc00958c77d07cb7249070b91c17b5bb25fa6ed4737379514c7aa01db2c9"
EXPECTED_VERIFIER_SHA256 = "fd233f32a5f7afe506276fc92aae0d77a6144a0537e8b9b8f25cf300b22cdbe3"
EXPECTED_V1_SCHEMA_SHA256 = "73ebc733f482a06b4ba77e507869597a2bc0b5e3ba6eca3ca969d7796d6170fe"
EXPECTED_PROGRESS_VALIDATOR_SHA256 = "8cb33ef1f9b688be90fb093e0fd4437b245c2a9b2dbac3f3141c65005619416f"
EXPECTED_BASELINE_ID = "0dc10cfc4a429662"
EXPECTED_BASELINE_FULL_DIGEST = "0dc10cfc4a429662037f3bb7d6c42e10e7cc832b540f7aa8f4b9e0656e0e459b"
EXPECTED_TASKS_SHA256 = "0150935a1a16e51dc30dff9dff8d01104d7127ee3cf57333caec7586d93f5007"
DENY_TEXT = "SUBJECT_TASK_AUTHORIZATION_V3_DENY\n"
ERROR_TEXT = "SUBJECT_TASK_AUTHORIZATION_V3_ERROR\n"
CLEANUP_REQUIRED = '{"status":"private_cleanup_required"}\n'
AUTHORITY = "github:zycaskevin"
PROTOCOL_DECISION_ID = "SD-TASK-AUTH-V2-T003"
PROPOSAL_KIND = "subject-task-authorization-v3-proposal"
PROOF_KIND = "subject-task-implementation-authorization-proof"
CONTRACT_PATH = "specs/subject-distillation/task-authorization-v3.contract.json"
PROOF_SCHEMA_PATH = "specs/subject-distillation/task-authorization-v3.schema.json"
PROGRESS_PATH = "specs/subject-distillation/implementation-progress.json"
PROGRESS_SCHEMA_PATH = "specs/subject-distillation/implementation-progress.schema.json"
PROGRESS_PENDING_PATH = "specs/subject-distillation/.implementation-progress.pending"
PROOF_PENDING_PATH = "specs/subject-distillation/.task-authorization.pending"
TASKS_PATH = "specs/subject-distillation/tasks.md"
VALIDATOR_PATH = "scripts/validate_subject_task_authorization_v3.py"
UPDATER_PATH = "scripts/update_subject_task_progress_v3.py"
V1_RUNNER_PATH = "scripts/run_subject_implementation_authorization.py"
PROGRESS_VALIDATOR_PATH = "scripts/validate_subject_progress.py"
EXPECTED_ACTIVATION_PROGRESS_SHA256 = (
    "f6b003829b36dc0a8a055590bc90bcf65a503da8cb299d4b15426813a9398094"
)
EXPECTED_BRIDGE_BASE_COMMIT = "c52ef13c1ef986dbf5a66c16107026daa09fc620"
EXPECTED_BRIDGE_DELIVERY = {
    ".github/workflows/ci.yml": ("modify", 0o644),
    "docs/decision_records/2026-08-12-subject-task-authorization-v2-t003.md": (
        "add",
        0o644,
    ),
    "scripts/run_subject_task_authorization_v3.py": ("add", 0o755),
    "scripts/update_subject_task_progress_v3.py": ("add", 0o755),
    "scripts/validate_subject_task_authorization_dispatch.py": ("add", 0o755),
    "scripts/validate_subject_task_authorization_v3.py": ("add", 0o755),
    "specs/subject-distillation/task-authorization-v3.contract.json": ("add", 0o644),
    "specs/subject-distillation/task-authorization-v3.schema.json": ("add", 0o644),
    "specs/subject-distillation/task-scopes/T-003.json": ("add", 0o644),
    "tests/test_repo_hygiene_tools.py": ("modify", 0o644),
    "tests/test_subject_progress_v3.py": ("add", 0o644),
    "tests/test_subject_task_authorization_dispatch.py": ("add", 0o644),
    "tests/test_subject_task_authorization_v3.py": ("add", 0o644),
}
EXPECTED_TRUST_ROOT = {
    "scripts/run_subject_implementation_authorization.py": EXPECTED_V1_RUNNER_SHA256,
    "scripts/run_subject_task_authorization_v2.py": "4f5bbcb87d17fde09075c5939584b881c2082b001cfbd97c3144b77ce4363c49",
    "scripts/update_subject_task_progress_v2.py": "eacb790b748e7abccc9b88d8376d5bea57c11a4e93efabaa517441f26d5f3e66",
    "scripts/validate_subject_progress.py": EXPECTED_PROGRESS_VALIDATOR_SHA256,
    "scripts/validate_subject_task_authorization_v2.py": "aa209054229f4dba4067a9fd8df301b1f1455da396dc9c2c5ccb2547325cc0ba",
    "scripts/verify_subject_implementation_authorization.py": EXPECTED_VERIFIER_SHA256,
    "specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json": EXPECTED_V1_SCHEMA_SHA256,
    "specs/subject-distillation/task-authorization-v2.contract.json": "6a8c0d49848a768f12b5deea26a8552cfc4a376814489804962c01ae33389e9d",
    "specs/subject-distillation/task-authorization-v2.schema.json": "5de3c8a69a6c8339cab74c17e1f76b08dec2a350786536583d52c230143ed448",
    "specs/subject-distillation/task-authorizations/T-002.json": "10affc9a33337fb0931f07a6460ff5ee268493a65dca0e2618bf1226444cc82c",
    "specs/subject-distillation/task-authorizations/T-002.review.json": "dc2669e64f2ee5eceb07c879cb3faca061dfc769f508d9987468aae555bbffea",
    "specs/subject-distillation/task-scopes/T-002.json": "e771bc5d09d74e12a47195427604e3889f8b8ee44cfdc3778f77ddac0a8f3982",
    "tests/fixtures/subject_distillation/fragments/failure-boundary-cases.json": "63b60d163a16eea156597d5deb748d7ab6883e0ec018a6529703e4730577245d",
    "tests/fixtures/subject_distillation/manifest.json": "99d31a8ba46be0ed9e53d0a98677c0bfa3d3b68566d2e426b9366a15a0c3790b",
    "tests/fixtures/subject_distillation/migration/migration-boundary-cases.json": "93e50a98a21eb4122675954404f5d4cb6f06bc0ad8f76499cd9c8131f325c9f1",
    "tests/fixtures/subject_distillation/organization/authority-boundary-cases.json": "53457c485c17de8226731128779c5c833c9058deca4a582ffea97c45faff3aa8",
    "tests/fixtures/subject_distillation/person/person-cases.json": "98cb60e31f460bd18f66a42a7688744907fe30f7a7c994d727e909bdfe20aac6",
    "tests/test_subject_fixture_privacy.py": "2717936249bd1c2ef88168785d1ecbc95f06dc5d0ac0964aff42bf20f057c271",
}
VALIDITY = timedelta(minutes=15)
TASK = re.compile(r"T-[0-9]{3}")
COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
HEX16 = re.compile(r"[0-9a-f]{16}")
HEX64 = re.compile(r"[0-9a-f]{64}")
OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
V3_DIGEST_KEYS = {
    "authorization_proof_sha256",
    "authorization_runner_v1_sha256",
    "authorization_runner_v3_sha256",
    "progress_sha256",
    "progress_before_sha256",
    "progress_validator_sha256",
    "protocol_contract_sha256",
    "scope_descriptor_sha256",
    "reviewed_change_set_sha256",
    "task_header_sha256",
    "task_authorization_schema_sha256",
    "task_authorization_validator_sha256",
    "task_progress_updater_v3_sha256",
}
TASK_IDS = tuple(f"T-{number:03d}" for number in range(1, 34))
STATES = {"PENDING", "IN_PROGRESS", "BLOCKED", "COMPLETED"}
TRANSITIONS = {
    ("PENDING", "IN_PROGRESS"),
    ("PENDING", "BLOCKED"),
    ("IN_PROGRESS", "BLOCKED"),
    ("IN_PROGRESS", "COMPLETED"),
    ("BLOCKED", "IN_PROGRESS"),
}


class Denied(Exception):
    pass


class InternalFailure(Exception):
    pass


def _load_v1():
    path = Path(__file__).with_name("run_subject_implementation_authorization.py")
    flags = os.O_RDONLY
    for name in ("O_NOFOLLOW", "O_CLOEXEC"):
        if not hasattr(os, name):
            raise RuntimeError
        flags |= int(getattr(os, name))
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        raw = b""
        while len(raw) <= 1_048_576:
            part = os.read(fd, min(65_536, 1_048_577 - len(raw)))
            if not part:
                break
            raw += part
        after = os.fstat(fd)
        if (
            not stat.S_ISREG(before.st_mode)
            or len(raw) > 1_048_576
            or hashlib.sha256(raw).hexdigest() != EXPECTED_V1_RUNNER_SHA256
            or (
                before.st_dev,
                before.st_ino,
                before.st_mode,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            )
            != (
                after.st_dev,
                after.st_ino,
                after.st_mode,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            )
        ):
            raise RuntimeError
    finally:
        os.close(fd)
    spec = importlib.util.spec_from_file_location("subject_authorization_v1_pinned", path)
    if spec is None:
        raise RuntimeError
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)  # noqa: S102 - pinned bytes
    return module


try:
    v1 = _load_v1()
except Exception:  # noqa: BLE001 - fixed public startup boundary
    v1 = None


@dataclass(frozen=True)
class TaskProgressSnapshot:
    sequence: int
    raw_sha256: str
    identity: tuple[int, int, int, int, int, int, int]
    task_state: str
    completed_predecessors: tuple[str, ...]


@dataclass
class Runtime:
    now: Callable[[], datetime] = field(default_factory=lambda: lambda: datetime.now(timezone.utc))
    repository_state: Callable[[], Any] | None = None
    task_progress_snapshot: Callable[[Path, str], TaskProgressSnapshot] | None = None
    bridge_release_check: Callable[[Path, str], None] | None = None
    temp_root: str | None = None
    hook: Callable[[str, Any], None] | None = None
    run_child: Callable[[list[str], str, dict[str, str], int], Any] | None = None
    write: Callable[[int, bytes], int] | None = None
    unlink: Callable[..., None] | None = None
    rmdir: Callable[..., None] | None = None


@dataclass
class _GuardEntry:
    handle: Any
    identity: tuple[int, int, int, int, int, int, int]
    raw: bytes
    label: str = ""


@dataclass
class BridgeGuard:
    entries: list[_GuardEntry]
    owned: list[int]

    def audit(self) -> None:
        try:
            for entry in self.entries:
                current = os.fstat(entry.handle.fd)
                if _strong_identity(current) != entry.identity:
                    raise Denied
                if _read_fd(entry.handle.fd) != entry.raw:
                    raise Denied
                for parent, name, before in entry.handle.chain:
                    info = os.stat(name, dir_fd=parent, follow_symlinks=False)
                    current_identity = v1.verifier._identity(info)
                    if stat.S_ISDIR(info.st_mode):
                        if current_identity[:3] != before[:3]:
                            raise Denied
                    elif current_identity != before:
                        raise Denied
        except OSError:
            raise Denied from None

    def close(self) -> None:
        for fd in reversed(self.owned):
            try:
                os.close(fd)
            except OSError:
                pass
        self.owned.clear()

    def snapshot(self) -> dict[str, bytes]:
        if any(not entry.label for entry in self.entries):
            raise Denied
        result = {entry.label: entry.raw for entry in self.entries}
        if len(result) != len(self.entries):
            raise Denied
        return result


def _v1_runtime(runtime: Runtime):
    return v1.Runtime(
        now=runtime.now,
        repository_state=runtime.repository_state,
        temp_root=runtime.temp_root,
        hook=runtime.hook,
        run_child=runtime.run_child,
        write=runtime.write,
        unlink=runtime.unlink,
        rmdir=runtime.rmdir,
    )


def _canonical(value: Any, *, newline: bool = True) -> bytes:
    try:
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
    except (TypeError, ValueError):
        raise Denied from None
    return raw + (b"\n" if newline else b"")


def _strong_identity(info: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _require_public_identity(
    identity: tuple[int, int, int, int, int, int, int], expected_mode: int
) -> None:
    if (
        not stat.S_ISREG(identity[2])
        or stat.S_IMODE(identity[2]) != expected_mode
        or identity[3] != 1
    ):
        raise Denied


def _read_repo_file(
    repo_root: Path, relative: str, *, maximum: int = 1_048_576
) -> tuple[bytes, tuple[int, int, int, int, int, int, int]]:
    if v1 is None:
        raise InternalFailure
    owned: list[int] = []
    handles: list[Any] = []
    try:
        root_fd = os.open("/", v1.verifier._flags(directory=True))
        owned.append(root_fd)
        discovered, repo = v1.verifier._repo_root(root_fd, owned)
        if discovered != os.fspath(repo_root):
            raise Denied
        handles.append(repo)
        handle = v1.verifier._open_chain(repo.fd, relative.split("/"), owned)
        handles.append(handle)
        before = os.fstat(handle.fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise Denied
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            part = os.read(handle.fd, min(65_536, remaining))
            if not part:
                break
            chunks.append(part)
            remaining -= len(part)
        raw = b"".join(chunks)
        after = os.fstat(handle.fd)
        v1.verifier._audit(handles)
        if (
            len(raw) > maximum
            or len(raw) != before.st_size
            or _strong_identity(before) != _strong_identity(after)
        ):
            raise Denied
        return raw, _strong_identity(after)
    except (OSError, v1.verifier.Denied, Denied):
        raise Denied from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _directory_names(repo_root: Path, relative: str) -> list[str]:
    owned: list[int] = []
    try:
        root_fd = os.open("/", v1.verifier._flags(directory=True))
        owned.append(root_fd)
        discovered, repo = v1.verifier._repo_root(root_fd, owned)
        if discovered != os.fspath(repo_root):
            raise Denied
        handle = v1.verifier._open_chain(
            repo.fd, relative.split("/"), owned, final_directory=True
        )
        _audit_directory_handle(handle)
        names = os.listdir(handle.fd)
        if any(type(name) is not str or not name.isascii() for name in names):
            raise Denied
        _audit_directory_handle(handle)
        return sorted(names)
    except (OSError, v1.verifier.Denied, Denied):
        raise Denied from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _open_bridge_guard(
    repo_root: Path,
    task: str,
    *,
    include_proof: bool = False,
    include_progress: bool = True,
    extra_paths: Sequence[str] = (),
) -> BridgeGuard:
    owned: list[int] = []
    entries: list[_GuardEntry] = []
    try:
        root_fd = os.open("/", v1.verifier._flags(directory=True))
        owned.append(root_fd)
        discovered, repo = v1.verifier._repo_root(root_fd, owned)
        if discovered != os.fspath(repo_root):
            raise Denied
        paths = {
            v1.verifier.MANIFEST_PATH,
            *v1.verifier.CANONICAL_PATHS,
            v1.verifier.SCHEMA_PATH,
            v1.verifier.VERIFIER_PATH,
            V1_RUNNER_PATH,
            PROGRESS_VALIDATOR_PATH,
            PROGRESS_SCHEMA_PATH,
            TASKS_PATH,
            CONTRACT_PATH,
            PROOF_SCHEMA_PATH,
            VALIDATOR_PATH,
            UPDATER_PATH,
            "scripts/run_subject_task_authorization_v3.py",
            _scope_path(task),
            *EXPECTED_TRUST_ROOT,
            *{
                path.format(baseline_id=EXPECTED_BASELINE_ID)
                for path in v1.T001_PATHS
                if not path.endswith("implementation-progress.json")
                and not path.endswith(".implementation-progress.pending")
            },
        }
        if include_progress:
            paths.add(PROGRESS_PATH)
        if include_proof:
            paths.add(f"specs/subject-distillation/task-authorizations/{task}.json")
        for relative in extra_paths:
            paths.add(_path(relative))
        for relative in sorted(paths):
            handle = v1.verifier._open_chain(repo.fd, relative.split("/"), owned)
            info = os.fstat(handle.fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > 1_048_576:
                raise Denied
            expected_mode = (
                0o755
                if relative.startswith("scripts/") and relative.endswith(".py")
                else 0o644
            )
            _require_public_identity(_strong_identity(info), expected_mode)
            raw = _read_fd(handle.fd)
            expected_digest = EXPECTED_TRUST_ROOT.get(relative)
            if (
                expected_digest is not None
                and hashlib.sha256(raw).hexdigest() != expected_digest
            ):
                raise Denied
            entries.append(_GuardEntry(handle, _strong_identity(info), raw, relative))
        guard = BridgeGuard(entries, owned)
        guard.audit()
        return guard
    except (OSError, v1.verifier.Denied, Denied):
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass
        raise Denied from None


def _open_external_public_packet(
    path: Path, repo_root: Path, *, maximum: int = 1_048_576
) -> tuple[BridgeGuard, bytes]:
    """Open one public packet outside the repository with retained identity."""
    raw_path = os.fspath(path)
    if (
        type(raw_path) is not str
        or not os.path.isabs(raw_path)
        or os.path.normpath(raw_path) != raw_path
    ):
        raise Denied
    owned: list[int] = []
    try:
        root_fd = os.open("/", v1.verifier._flags(directory=True))
        owned.append(root_fd)
        discovered, repo = v1.verifier._repo_root(root_fd, owned)
        if discovered != os.fspath(repo_root):
            raise Denied
        handle = v1.verifier._open_chain(
            root_fd, v1.verifier._absolute_parts(raw_path), owned
        )
        info = os.fstat(handle.fd)
        identity = _strong_identity(info)
        _require_public_identity(identity, 0o644)
        if info.st_size > maximum:
            raise Denied
        repo_identity = (repo.identity[0], repo.identity[1])
        if any(
            (entry[2][0], entry[2][1]) == repo_identity
            for entry in handle.chain[:-1]
        ):
            raise Denied
        raw = _read_fd(handle.fd, maximum)
        if len(raw) != info.st_size:
            raise Denied
        guard = BridgeGuard([_GuardEntry(handle, identity, raw, raw_path)], owned)
        guard.audit()
        return guard, raw
    except (OSError, v1.verifier.Denied, Denied):
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass
        raise Denied from None


def _parse_status_z(raw: bytes) -> dict[str, str]:
    records = raw.split(b"\0")
    if records[-1] != b"":
        raise Denied
    result: dict[str, str] = {}
    for record in records[:-1]:
        if len(record) < 4 or record[2:3] != b" ":
            raise Denied
        try:
            code = record[:2].decode("ascii")
            path = record[3:].decode("utf-8", "strict")
        except UnicodeError:
            raise Denied from None
        if code in {"??", "A ", "AM"}:
            action = "add"
        elif code in {" M", "M ", "MM"}:
            action = "modify"
        else:
            raise Denied
        if _path(path) != path or path in result:
            raise Denied
        result[path] = action
    return result


def _parse_diff_z(raw: bytes) -> dict[str, str]:
    records = raw.split(b"\0")
    if records[-1] != b"" or len(records) % 2 != 1:
        raise Denied
    result: dict[str, str] = {}
    for index in range(0, len(records) - 1, 2):
        try:
            code = records[index].decode("ascii")
            path = records[index + 1].decode("utf-8", "strict")
        except UnicodeError:
            raise Denied from None
        action = {"A": "add", "M": "modify"}.get(code)
        if action is None or _path(path) != path or path in result:
            raise Denied
        result[path] = action
    return result


def _require_bridge_release(repo_root: Path, base: str) -> None:
    """Bind the owner-authorized additive bridge to its exact reviewed release."""
    if COMMIT.fullmatch(base) is None or Path.cwd().absolute() != repo_root:
        raise Denied
    if v1._exact_line(v1._git(["rev-parse", "HEAD"])) != base:
        raise Denied
    v1._git(["merge-base", "--is-ancestor", EXPECTED_BRIDGE_BASE_COMMIT, base])
    changes = _parse_diff_z(
        v1._git(
            [
                "diff",
                "--name-status",
                "-z",
                EXPECTED_BRIDGE_BASE_COMMIT,
                base,
                "--",
            ]
        )
    )
    if changes != {path: policy[0] for path, policy in EXPECTED_BRIDGE_DELIVERY.items()}:
        raise Denied
    for path, (_action, expected_mode) in EXPECTED_BRIDGE_DELIVERY.items():
        try:
            info = os.stat(repo_root / path, follow_symlinks=False)
        except OSError:
            raise Denied from None
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) != expected_mode
        ):
            raise Denied


def _check_bridge_release(runtime: Runtime, repo_root: Path, base: str) -> None:
    check = runtime.bridge_release_check or _require_bridge_release
    check(repo_root, base)


def _repo_entry_exists(repo_root: Path, relative: str) -> bool:
    """Check one fixed entry without following a hostile final symlink."""
    owned: list[int] = []
    try:
        root_fd = os.open("/", v1.verifier._flags(directory=True))
        owned.append(root_fd)
        discovered, repo = v1.verifier._repo_root(root_fd, owned)
        if discovered != os.fspath(repo_root):
            raise Denied
        parts = _path(relative).split("/")
        parent = v1.verifier._open_chain(
            repo.fd, parts[:-1], owned, final_directory=True
        )
        try:
            info = os.stat(parts[-1], dir_fd=parent.fd, follow_symlinks=False)
        except FileNotFoundError:
            return False
        if not stat.S_ISREG(info.st_mode):
            raise Denied
        return True
    except (OSError, v1.verifier.Denied):
        raise Denied from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _repository_changes(
    repo_root: Path,
    implementation_base_commit: str,
    expected_paths: Sequence[str],
    retained: dict[str, bytes],
) -> list[dict[str, str]]:
    if not implementation_base_commit.startswith("git:"):
        raise Denied
    base = implementation_base_commit[4:]
    if COMMIT.fullmatch(base) is None or Path.cwd().absolute() != repo_root:
        raise Denied
    head = v1._exact_line(v1._git(["rev-parse", "HEAD"]))
    status = v1._git(["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    if head == base:
        changes = _parse_status_z(status)
    else:
        if status:
            raise Denied
        v1._git(["merge-base", "--is-ancestor", base, head])
        changes = _parse_diff_z(v1._git(["diff", "--name-status", "-z", base, head, "--"]))
    if sorted(changes) != sorted(expected_paths):
        raise Denied
    result: list[dict[str, str]] = []
    for path in sorted(expected_paths):
        try:
            raw = retained[path]
            metadata = os.stat(repo_root / path, follow_symlinks=False)
        except KeyError:
            raise Denied from None
        except OSError:
            raise Denied from None
        mode = stat.S_IMODE(metadata.st_mode)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or mode not in {
            0o644,
            0o755,
        }:
            raise Denied
        result.append(
            {
                "action": changes[path],
                "mode": f"100{mode:o}",
                "path": path,
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return result


def _path(value: Any) -> str:
    if type(value) is not str or not 1 <= len(value) <= 256 or not value.isascii():
        raise Denied
    if value.startswith("/") or "\\" in value or "//" in value or value.endswith("/"):
        raise Denied
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise Denied
    return value


def _scan_v3(value: Any, owning_key: str | None = None) -> None:
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str or v1.verifier._normalize_key(key) in v1.verifier.FORBIDDEN_KEYS:
                raise Denied
            v1.verifier._scan_string(key, None)
            _scan_v3(item, key)
    elif type(value) is list:
        for item in value:
            _scan_v3(item, owning_key)
    elif type(value) is str:
        normalized = v1.verifier._normalize_key(owning_key) if owning_key else None
        if normalized == "implementation_base_commit":
            if COMMIT.fullmatch(value) is None and re.fullmatch(
                r"git:(?:[0-9a-f]{40}|[0-9a-f]{64})", value
            ) is None:
                raise Denied
            return
        if normalized in V3_DIGEST_KEYS:
            if HEX64.fullmatch(value) is None:
                raise Denied
            return
        try:
            v1.verifier._scan_string(value, owning_key)
        except v1.verifier.Denied:
            raise Denied from None


def _sorted_strings(value: Any, *, minimum: int = 1, maximum: int = 64) -> list[str]:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise Denied
    if any(type(item) is not str or not item.isascii() for item in value):
        raise Denied
    if value != sorted(value) or len(value) != len(set(value)):
        raise Denied
    return value


DESCRIPTOR_KEYS = {
    "schema_version",
    "artifact_kind",
    "scope_version",
    "task_header_sha256",
    "authorized_task",
    "baseline_id",
    "baseline_full_digest",
    "tasks_sha256",
    "predecessor_tasks",
    "allowed_repo_relative_paths",
    "writable_path_policies",
    "completion_repo_relative_paths",
    "proof_repo_relative_path",
    "non_goals",
    "prohibited_operations",
    "verification_commands",
}


def _validate_contract(value: Any, raw: bytes) -> dict[str, Any]:
    try:
        _scan_v3(value)
    except (v1.verifier.Denied, Denied):
        raise Denied from None
    if raw != _canonical(value) or type(value) is not dict or set(value) != {
        "schema_version",
        "artifact_kind",
        "repository",
        "authority",
        "activation",
        "allowed_tasks",
        "allowed_risk_classes",
        "descriptor_policy",
        "reopen_conditions",
        "trust_root",
    }:
        raise Denied
    if (
        value["schema_version"] != 3
        or value["artifact_kind"] != "subject-task-authorization-v3-contract"
        or value["repository"] != "zycaskevin/Vault-Agent-Memory"
        or value["allowed_tasks"] != {"first": "T-003", "last": "T-003"}
        or value["allowed_risk_classes"] != ["L0", "L1"]
        or value["reopen_conditions"]
        != [
            "baseline_changed",
            "descriptor_changed",
            "owner_revoked",
            "product_or_risk_boundary_changed",
            "trust_root_changed",
        ]
    ):
        raise Denied
    if value["authority"] != {
        "authorizing_principal": AUTHORITY,
        "delegates_task_authority": False,
        "owner_confirmation_required_per_task": True,
        "owner_decision_id": PROTOCOL_DECISION_ID,
        "owner_decision_ref": "owner-message:SD-TASK-AUTH-V2-T003",
    }:
        raise Denied
    if value["descriptor_policy"] != {
        "path_template": "specs/subject-distillation/task-scopes/{task}.json",
        "registration": "proposal-and-proof-bound",
        "task_header_binding_required": True,
    }:
        raise Denied
    activation = value["activation"]
    if activation != {
        "baseline_full_digest": EXPECTED_BASELINE_FULL_DIGEST,
        "baseline_id": EXPECTED_BASELINE_ID,
        "implementation_base_commit": "git:c52ef13c1ef986dbf5a66c16107026daa09fc620",
        "progress": {
            "path": PROGRESS_PATH,
            "sha256": EXPECTED_ACTIVATION_PROGRESS_SHA256,
        },
        "t001_completion_event": {
            "sha256": "a7dd60bdb8e9280a98ad905a74f38eb659c6f011ade7da4d8668d46831158e7a"
        },
        "t001_events": {
            "sha256": "bd28b4a3bbd47ceed803e259e62a06cb34b8f4b65d38de27a36fce0271a3a83d"
        },
        "t002_completion_event": {
            "sha256": "637601aa48c50280579cceba65d8220a6df5609141385cb4a12c6a451764ffb5"
        },
        "t002_events": {
            "sha256": "b9727a5262dacc43c19f4784e6f584dbbc07a13cfc422c16fba1e673eebbde71"
        },
        "tasks_sha256": EXPECTED_TASKS_SHA256,
    }:
        raise Denied
    expected_trust = [
        {"path": path, "sha256": digest}
        for path, digest in sorted(EXPECTED_TRUST_ROOT.items())
    ]
    if value["trust_root"] != expected_trust:
        raise Denied
    return value


def _load_contract(repo_root: Path) -> tuple[dict[str, Any], bytes]:
    raw, identity = _read_repo_file(repo_root, CONTRACT_PATH)
    _require_public_identity(identity, 0o644)
    try:
        value = v1.verifier._parse(raw)
    except v1.verifier.Denied:
        raise Denied from None
    _validate_contract(value, raw)
    return value, raw


def _validate_scope_descriptor(value: Any, raw: bytes, task: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != DESCRIPTOR_KEYS:
        raise Denied
    if raw != _canonical(value) or value["schema_version"] != 3:
        raise Denied
    if value["artifact_kind"] != "subject-task-authorization-scope-descriptor":
        raise Denied
    if value["scope_version"] != 1 or value["authorized_task"] != task:
        raise Denied
    if HEX16.fullmatch(value["baseline_id"]) is None:
        raise Denied
    if HEX64.fullmatch(value["baseline_full_digest"]) is None or HEX64.fullmatch(
        value["tasks_sha256"]
    ) is None:
        raise Denied
    if HEX64.fullmatch(value["task_header_sha256"]) is None:
        raise Denied
    if (
        value["baseline_id"] != EXPECTED_BASELINE_ID
        or value["baseline_full_digest"] != EXPECTED_BASELINE_FULL_DIGEST
        or value["tasks_sha256"] != EXPECTED_TASKS_SHA256
    ):
        raise Denied
    predecessors = _sorted_strings(value["predecessor_tasks"], maximum=32)
    number = int(task[2:])
    if predecessors != [f"T-{item:03d}" for item in range(1, number)]:
        raise Denied
    paths = _sorted_strings(value["allowed_repo_relative_paths"])
    if any(_path(item) != item for item in paths):
        raise Denied
    completion = _sorted_strings(value["completion_repo_relative_paths"])
    if (
        not 1 <= len(completion) <= 12
        or not set(completion) < set(paths)
        or any(_path(item) != item for item in completion)
    ):
        raise Denied
    proof_path = _path(value["proof_repo_relative_path"])
    if proof_path not in paths or proof_path != f"specs/subject-distillation/task-authorizations/{task}.json":
        raise Denied
    policies = value["writable_path_policies"]
    if type(policies) is not list or len(policies) != len(paths):
        raise Denied
    policy_paths: list[str] = []
    for policy in policies:
        if type(policy) is not dict or set(policy) != {"path", "action", "final_mode"}:
            raise Denied
        policy_paths.append(_path(policy["path"]))
        if policy["action"] not in {"create", "modify", "transient"}:
            raise Denied
        expected_mode = (
            "absent"
            if policy["action"] == "transient"
            else "0755"
            if policy["path"].startswith("scripts/")
            and policy["path"].endswith(".py")
            else "0644"
        )
        if policy["final_mode"] != expected_mode:
            raise Denied
    if policy_paths != paths:
        raise Denied
    non_goals = _sorted_strings(value["non_goals"], maximum=16)
    prohibited = _sorted_strings(value["prohibited_operations"], maximum=16)
    if not v1.verifier.REQUIRED_PROHIBITED <= set(prohibited):
        raise Denied
    if any(v1.verifier.NON_GOAL.fullmatch(item) is None for item in non_goals):
        raise Denied
    commands = value["verification_commands"]
    if type(commands) is not list or not 1 <= len(commands) <= 8:
        raise Denied
    for argv in commands:
        if (
            type(argv) is not list
            or not 1 <= len(argv) <= 32
            or any(
                type(item) is not str or not 1 <= len(item) <= 256
                for item in argv
            )
        ):
            raise Denied
    try:
        _scan_v3(value)
    except (v1.verifier.Denied, Denied):
        raise Denied from None
    return value


def _scope_path(task: str) -> str:
    if TASK.fullmatch(task) is None or task == "T-001":
        raise Denied
    return f"specs/subject-distillation/task-scopes/{task}.json"


def _task_header(raw: bytes, task: str) -> bytes:
    marker = f"### {task} ".encode("ascii")
    try:
        start = raw.index(marker)
    except ValueError:
        raise Denied from None
    next_number = int(task[2:]) + 1
    if next_number <= 33:
        next_marker = f"\n### T-{next_number:03d} ".encode("ascii")
        try:
            end = raw.index(next_marker, start)
        except ValueError:
            raise Denied from None
        return raw[start : end + 1]
    return raw[start:]


def _load_scope_descriptor(repo_root: Path, task: str) -> tuple[dict[str, Any], bytes]:
    raw, identity = _read_repo_file(repo_root, _scope_path(task))
    _require_public_identity(identity, 0o644)
    try:
        value = v1.verifier._parse(raw)
    except v1.verifier.Denied:
        raise Denied from None
    return _validate_scope_descriptor(value, raw, task), raw


def _dependencies_allow(task: str, states: dict[str, str]) -> bool:
    number = int(task[2:])
    return all(states[f"T-{index:03d}"] == "COMPLETED" for index in range(1, number))


def _validate_repo_ref(repo_root: Path, value: Any) -> None:
    if type(value) is not dict:
        raise Denied
    if set(value) == {"kind", "id"} and value["kind"] == "opaque":
        if type(value["id"]) is not str or OPAQUE.fullmatch(value["id"]) is None:
            raise Denied
        return
    if set(value) != {"kind", "path", "sha256"} or value["kind"] != "repo_file":
        raise Denied
    relative = _path(value["path"])
    if type(value["sha256"]) is not str or HEX64.fullmatch(value["sha256"]) is None:
        raise Denied
    raw, _identity = _read_repo_file(repo_root, relative, maximum=16_777_216)
    if hashlib.sha256(raw).hexdigest() != value["sha256"]:
        raise Denied


def _validate_t001_completion(value: dict[str, Any], baseline_id: str) -> None:
    refs = value["evidence_refs"]
    if len(refs) != 16:
        raise Denied
    expected_paths = sorted(
        path.format(baseline_id=baseline_id)
        for path in v1.T001_PATHS
        if not path.endswith("implementation-progress.json")
        and not path.endswith(".implementation-progress.pending")
    )
    actual_paths = sorted(
        item["path"] for item in refs if type(item) is dict and item.get("kind") == "repo_file"
    )
    opaque = [
        item["id"] for item in refs if type(item) is dict and item.get("kind") == "opaque"
    ]
    if actual_paths != expected_paths or len(opaque) != 2:
        raise Denied
    if not any(re.fullmatch(r"t001-authorization:[0-9a-f]{64}", item) for item in opaque):
        raise Denied
    if not any(re.fullmatch(r"t001-review:[0-9a-f]{64}", item) for item in opaque):
        raise Denied


def _default_task_progress_snapshot(repo_root: Path, task: str) -> TaskProgressSnapshot:
    pending = repo_root / PROGRESS_PENDING_PATH
    try:
        os.lstat(pending)
    except FileNotFoundError:
        pass
    except OSError:
        raise Denied from None
    else:
        raise Denied
    raw, identity = _read_repo_file(repo_root, PROGRESS_PATH)
    tasks_raw, _tasks_identity = _read_repo_file(repo_root, TASKS_PATH)
    try:
        value = v1.verifier._parse(raw)
        v1.verifier._scan(value)
    except v1.verifier.Denied:
        raise Denied from None
    if raw != _canonical(value) or type(value) is not dict or set(value) != {
        "schema_version",
        "baseline_id",
        "baseline_full_digest",
        "tasks_sha256",
        "updated_at_utc",
        "tasks",
        "events",
    }:
        raise Denied
    if value["schema_version"] != 1 or value["tasks_sha256"] != hashlib.sha256(tasks_raw).hexdigest():
        raise Denied
    if tuple(sorted(value["tasks"])) != TASK_IDS:
        raise Denied
    states = {item: "PENDING" for item in TASK_IDS}
    events = value["events"]
    if type(events) is not list or not events or len(events) > 4_096:
        raise Denied
    previous_time: datetime | None = None
    for sequence, event in enumerate(events, 1):
        if type(event) is not dict or set(event) != {
            "sequence",
            "task_id",
            "from",
            "to",
            "at_utc",
            "evidence_refs",
            "blocker",
        }:
            raise Denied
        event_task = event["task_id"]
        before, after = event["from"], event["to"]
        if (
            event["sequence"] != sequence
            or event_task not in TASK_IDS
            or states[event_task] != before
            or (before, after) not in TRANSITIONS
            or not _dependencies_allow(event_task, states)
        ):
            raise Denied
        when = v1.verifier._timestamp(event["at_utc"])
        if previous_time is not None and when < previous_time:
            raise Denied
        previous_time = when
        refs = event["evidence_refs"]
        if type(refs) is not list or len(refs) > 16:
            raise Denied
        canonical_refs = [_canonical(item) for item in refs]
        if canonical_refs != sorted(canonical_refs) or len(canonical_refs) != len(set(canonical_refs)):
            raise Denied
        for ref in refs:
            _validate_repo_ref(repo_root, ref)
        if event_task == "T-001" and after == "COMPLETED":
            _validate_t001_completion(event, value["baseline_id"])
        if after == "BLOCKED":
            if type(event["blocker"]) is not str:
                raise Denied
        elif event["blocker"] is not None:
            raise Denied
        if after == "COMPLETED" and not refs:
            raise Denied
        states[event_task] = after
        if sum(item == "IN_PROGRESS" for item in states.values()) > 1:
            raise Denied
    if value["tasks"] != states or value["updated_at_utc"] != events[-1]["at_utc"]:
        raise Denied
    contract, _contract_raw = _load_contract(repo_root)
    t001_events = [event for event in events if event["task_id"] == "T-001"]
    t002_events = [event for event in events if event["task_id"] == "T-002"]
    if (
        not t001_events
        or hashlib.sha256(_canonical(t001_events[-1], newline=False)).hexdigest()
        != contract["activation"]["t001_completion_event"]["sha256"]
        or hashlib.sha256(_canonical(t001_events, newline=False)).hexdigest()
        != contract["activation"]["t001_events"]["sha256"]
        or not t002_events
        or hashlib.sha256(_canonical(t002_events[-1], newline=False)).hexdigest()
        != contract["activation"]["t002_completion_event"]["sha256"]
        or hashlib.sha256(_canonical(t002_events, newline=False)).hexdigest()
        != contract["activation"]["t002_events"]["sha256"]
    ):
        raise Denied
    number = int(task[2:])
    expected_predecessors = tuple(f"T-{item:03d}" for item in range(1, number))
    if any(states[item] != "COMPLETED" for item in expected_predecessors):
        raise Denied
    if states[task] != "PENDING" or any(
        states[f"T-{item:03d}"] != "PENDING" for item in range(number + 1, 34)
    ):
        raise Denied
    if hashlib.sha256(raw).hexdigest() != EXPECTED_ACTIVATION_PROGRESS_SHA256:
        raise Denied
    return TaskProgressSnapshot(
        sequence=len(events),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        identity=identity,
        task_state=states[task],
        completed_predecessors=expected_predecessors,
    )


def _progress(runtime: Runtime, repo_root: Path, task: str) -> TaskProgressSnapshot:
    value = (
        runtime.task_progress_snapshot(repo_root, task)
        if runtime.task_progress_snapshot is not None
        else _default_task_progress_snapshot(repo_root, task)
    )
    if (
        type(value) is not TaskProgressSnapshot
        or type(value.sequence) is not int
        or value.sequence < 1
        or HEX64.fullmatch(value.raw_sha256) is None
        or value.task_state != "PENDING"
    ):
        raise Denied
    return value


def _clock(runtime: Runtime) -> datetime:
    value = runtime.now()
    if type(value) is not datetime or value.tzinfo != timezone.utc:
        raise Denied
    return value


def _format_time(value: datetime) -> str:
    if value.tzinfo != timezone.utc or value.microsecond:
        raise Denied
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _support_hashes(repo_root: Path) -> dict[str, str]:
    paths = {
        "protocol_contract_sha256": CONTRACT_PATH,
        "task_authorization_schema_sha256": PROOF_SCHEMA_PATH,
        "task_authorization_validator_sha256": VALIDATOR_PATH,
        "task_progress_updater_v3_sha256": UPDATER_PATH,
        "authorization_runner_v1_sha256": V1_RUNNER_PATH,
        "progress_validator_sha256": PROGRESS_VALIDATOR_PATH,
    }
    result: dict[str, str] = {}
    for key, path in paths.items():
        raw, identity = _read_repo_file(repo_root, path)
        _require_public_identity(identity, 0o755 if path.endswith(".py") else 0o644)
        result[key] = hashlib.sha256(raw).hexdigest()
    if result["authorization_runner_v1_sha256"] != EXPECTED_V1_RUNNER_SHA256:
        raise Denied
    if result["progress_validator_sha256"] != EXPECTED_PROGRESS_VALIDATOR_SHA256:
        raise Denied
    self_raw, identity = _read_repo_file(
        repo_root, "scripts/run_subject_task_authorization_v3.py"
    )
    _require_public_identity(identity, 0o755)
    result["authorization_runner_v3_sha256"] = hashlib.sha256(self_raw).hexdigest()
    return result


def _derive(
    repo_root: Path,
    inputs: Any,
    base: str,
    task: str,
    issued: datetime,
    progress: TaskProgressSnapshot,
) -> tuple[dict[str, Any], bytes, bytes]:
    descriptor, descriptor_raw = _load_scope_descriptor(repo_root, task)
    if (descriptor["baseline_id"], descriptor["baseline_full_digest"]) != (
        inputs.baseline_id,
        inputs.full_digest,
    ):
        raise Denied
    tasks_raw, identity = _read_repo_file(repo_root, TASKS_PATH)
    _require_public_identity(identity, 0o644)
    if (
        descriptor["tasks_sha256"] != hashlib.sha256(tasks_raw).hexdigest()
        or descriptor["task_header_sha256"]
        != hashlib.sha256(_task_header(tasks_raw, task)).hexdigest()
    ):
        raise Denied
    support = _support_hashes(repo_root)
    contract, _contract_raw = _load_contract(repo_root)
    if task != contract["allowed_tasks"]["first"] or task != contract["allowed_tasks"]["last"]:
        raise Denied
    if task == "T-003" and (
        progress.sequence != 4
        or progress.raw_sha256 != contract["activation"]["progress"]["sha256"]
    ):
        raise Denied
    scope = {
        "schema_version": 1,
        "artifact_kind": v1.SCOPE_KIND,
        "baseline_id": inputs.baseline_id,
        "baseline_full_digest": inputs.full_digest,
        "authorized_task": task,
        "allowed_repo_relative_paths": descriptor["allowed_repo_relative_paths"],
        "non_goals": descriptor["non_goals"],
        "prohibited_operations": descriptor["prohibited_operations"],
    }
    scope_raw = _canonical(scope)
    issued_text = _format_time(issued)
    expires_text = _format_time(issued + VALIDITY)
    receipt = {
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
    receipt["authorization_id"] = hashlib.sha256(_canonical(receipt, newline=False)).hexdigest()
    receipt_raw = _canonical(receipt)
    proposal = {
        "schema_version": 3,
        "artifact_kind": PROPOSAL_KIND,
        "protocol_decision_id": PROTOCOL_DECISION_ID,
        "protocol_contract_sha256": support["protocol_contract_sha256"],
        "authorized_task": task,
        "implementation_base_commit": base,
        "baseline_id": inputs.baseline_id,
        "baseline_full_digest": inputs.full_digest,
        "authorizing_principal": AUTHORITY,
        "allowed_repo_relative_paths": descriptor["allowed_repo_relative_paths"],
        "non_goals": descriptor["non_goals"],
        "prohibited_operations": descriptor["prohibited_operations"],
        "issued_at_utc": issued_text,
        "expires_at_utc": expires_text,
        "scope_descriptor_path": _scope_path(task),
        "scope_descriptor_sha256": hashlib.sha256(descriptor_raw).hexdigest(),
        "progress_sequence": progress.sequence,
        "progress_sha256": progress.raw_sha256,
        "receipt_sha256": hashlib.sha256(receipt_raw).hexdigest(),
        "scope_sha256": receipt["scope_sha256"],
        "authorization_verifier_sha256": receipt["authorization_verifier_sha256"],
        "authorization_schema_sha256": receipt["authorization_schema_sha256"],
        "authorization_id": receipt["authorization_id"],
        "authorization_runner_v1_sha256": support["authorization_runner_v1_sha256"],
        "authorization_runner_v3_sha256": support["authorization_runner_v3_sha256"],
        "task_authorization_schema_sha256": support["task_authorization_schema_sha256"],
        "task_authorization_validator_sha256": support["task_authorization_validator_sha256"],
        "task_progress_updater_v3_sha256": support["task_progress_updater_v3_sha256"],
        "proof_repo_relative_path": descriptor["proof_repo_relative_path"],
    }
    proposal["proposal_id"] = hashlib.sha256(_canonical(proposal)).hexdigest()
    return proposal, receipt_raw, scope_raw


PROPOSAL_KEYS = {
    "schema_version",
    "artifact_kind",
    "protocol_decision_id",
    "protocol_contract_sha256",
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
    "scope_descriptor_path",
    "scope_descriptor_sha256",
    "progress_sequence",
    "progress_sha256",
    "receipt_sha256",
    "scope_sha256",
    "authorization_verifier_sha256",
    "authorization_schema_sha256",
    "authorization_id",
    "authorization_runner_v1_sha256",
    "authorization_runner_v3_sha256",
    "task_authorization_schema_sha256",
    "task_authorization_validator_sha256",
    "task_progress_updater_v3_sha256",
    "proof_repo_relative_path",
    "proposal_id",
}


def _parse_proposal(raw_text: str, now: datetime) -> tuple[dict[str, Any], datetime]:
    if type(raw_text) is not str:
        raise Denied
    raw = raw_text.encode("utf-8")
    try:
        value = v1.verifier._parse(raw)
        _scan_v3(value)
    except (v1.verifier.Denied, Denied):
        raise Denied from None
    if type(value) is not dict or set(value) != PROPOSAL_KEYS or raw != _canonical(value):
        raise Denied
    if value["schema_version"] != 3 or value["artifact_kind"] != PROPOSAL_KIND:
        raise Denied
    if value["protocol_decision_id"] != PROTOCOL_DECISION_ID:
        raise Denied
    if value["authorizing_principal"] != AUTHORITY or TASK.fullmatch(value["authorized_task"]) is None:
        raise Denied
    if COMMIT.fullmatch(value["implementation_base_commit"]) is None:
        raise Denied
    for key in PROPOSAL_KEYS & {
        "protocol_contract_sha256",
        "baseline_full_digest",
        "scope_descriptor_sha256",
        "progress_sha256",
        "receipt_sha256",
        "scope_sha256",
        "authorization_verifier_sha256",
        "authorization_schema_sha256",
        "authorization_id",
        "authorization_runner_v1_sha256",
        "authorization_runner_v3_sha256",
        "task_authorization_schema_sha256",
        "task_authorization_validator_sha256",
        "task_progress_updater_v3_sha256",
        "proposal_id",
    }:
        if type(value[key]) is not str or HEX64.fullmatch(value[key]) is None:
            raise Denied
    issued = v1.verifier._timestamp(value["issued_at_utc"])
    expires = v1.verifier._timestamp(value["expires_at_utc"])
    if issued.microsecond or expires - issued != VALIDITY or issued > now or now >= expires:
        raise Denied
    without_id = dict(value)
    without_id.pop("proposal_id")
    if value["proposal_id"] != hashlib.sha256(_canonical(without_id)).hexdigest():
        raise Denied
    return value, issued


def _repository_state(runtime: Runtime):
    return v1._repository_state(_v1_runtime(runtime))


def _propose(values: dict[str, str], runtime: Runtime) -> bytes:
    base, task = values["--implementation-base-commit"], values["--expected-task"]
    if COMMIT.fullmatch(base) is None or TASK.fullmatch(task) is None or task == "T-001":
        raise Denied
    state = _repository_state(runtime)
    if not state.clean or state.head != base:
        raise Denied
    root = Path(state.repo_root)
    _check_bridge_release(runtime, root, base)
    progress = _progress(runtime, root, task)
    inputs = v1._repo_inputs(state.repo_root)
    issued = _clock(runtime).replace(microsecond=0)
    proposal, _receipt, _scope = _derive(root, inputs, base, task, issued, progress)
    if _repository_state(runtime) != state or _progress(runtime, root, task) != progress:
        raise Denied
    _check_bridge_release(runtime, root, base)
    return _canonical(proposal)


def _proof(proposal: dict[str, Any], recorded: datetime, owner_ref: str) -> dict[str, Any]:
    if OPAQUE.fullmatch(owner_ref) is None:
        raise Denied
    return {
        "schema_version": 3,
        "artifact_kind": PROOF_KIND,
        "status": "PASS",
        "protocol_decision_id": proposal["protocol_decision_id"],
        "protocol_contract_sha256": proposal["protocol_contract_sha256"],
        "authorized_task": proposal["authorized_task"],
        "implementation_base_commit": "git:" + proposal["implementation_base_commit"],
        "baseline_id": proposal["baseline_id"],
        "baseline_full_digest": proposal["baseline_full_digest"],
        "authorizing_principal": proposal["authorizing_principal"],
        "allowed_repo_relative_paths": proposal["allowed_repo_relative_paths"],
        "non_goals": proposal["non_goals"],
        "prohibited_operations": proposal["prohibited_operations"],
        "issued_at_utc": proposal["issued_at_utc"],
        "expires_at_utc": proposal["expires_at_utc"],
        "recorded_at_utc": _format_time(recorded.replace(microsecond=0)),
        "scope_descriptor_path": proposal["scope_descriptor_path"],
        "scope_descriptor_sha256": proposal["scope_descriptor_sha256"],
        "progress_sequence": proposal["progress_sequence"],
        "progress_sha256": proposal["progress_sha256"],
        "receipt_sha256": proposal["receipt_sha256"],
        "scope_sha256": proposal["scope_sha256"],
        "authorization_verifier_sha256": proposal["authorization_verifier_sha256"],
        "authorization_schema_sha256": proposal["authorization_schema_sha256"],
        "authorization_id": proposal["authorization_id"],
        "proposal_id": proposal["proposal_id"],
        "authorization_runner_v1_sha256": proposal["authorization_runner_v1_sha256"],
        "authorization_runner_v3_sha256": proposal["authorization_runner_v3_sha256"],
        "task_authorization_schema_sha256": proposal["task_authorization_schema_sha256"],
        "task_authorization_validator_sha256": proposal["task_authorization_validator_sha256"],
        "task_progress_updater_v3_sha256": proposal["task_progress_updater_v3_sha256"],
        "owner_confirmation_ref": owner_ref,
        "proof_repo_relative_path": proposal["proof_repo_relative_path"],
    }


def _require_recorded_freshness(
    proposal: dict[str, Any], issued: datetime, recorded: datetime
) -> None:
    expires = v1.verifier._timestamp(proposal["expires_at_utc"])
    if recorded < issued or recorded >= expires:
        raise Denied


def _recoverable_proof_raw(
    repo_root: Path,
    proposal: dict[str, Any],
    issued: datetime,
    owner_ref: str,
) -> bytes:
    """Validate the only dirty proof-publication states that may be retried."""
    final_path = proposal["proof_repo_relative_path"]
    allowed = {PROOF_PENDING_PATH, final_path}
    status = _parse_status_z(
        v1._git(["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    )
    if not status or not set(status) <= allowed or set(status.values()) != {"add"}:
        raise Denied
    present = {path for path in allowed if _repo_entry_exists(repo_root, path)}
    if set(status) != present or not present:
        raise Denied
    raws: dict[str, bytes] = {}
    identities: dict[str, tuple[int, int, int, int, int, int, int]] = {}
    for path in present:
        raw, identity = _read_repo_file(repo_root, path)
        mode = stat.S_IMODE(identity[2])
        if path == PROOF_PENDING_PATH:
            if mode not in {0o600, 0o644} or identity[3] not in {1, 2}:
                raise Denied
        elif mode != 0o644 or identity[3] not in {1, 2}:
            raise Denied
        raws[path], identities[path] = raw, identity
    if len(set(raws.values())) != 1:
        raise Denied
    if present == allowed:
        pending, final = identities[PROOF_PENDING_PATH], identities[final_path]
        if pending[:2] != final[:2] or pending[3] != 2 or final[3] != 2:
            raise Denied
    elif present == {PROOF_PENDING_PATH}:
        if identities[PROOF_PENDING_PATH][3] != 1:
            raise Denied
    elif present == {final_path}:
        if identities[final_path][3] != 1:
            raise Denied
    else:
        raise Denied
    raw = next(iter(raws.values()))
    try:
        value = v1.verifier._parse(raw)
        _scan_v3(value)
        recorded = v1.verifier._timestamp(value["recorded_at_utc"])
    except (KeyError, TypeError, v1.verifier.Denied):
        raise Denied from None
    _require_recorded_freshness(proposal, issued, recorded)
    if raw != _canonical(value) or raw != _canonical(_proof(proposal, recorded, owner_ref)):
        raise Denied
    return raw


def _write_all(fd: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        count = os.write(fd, raw[offset:])
        if count <= 0:
            raise InternalFailure
        offset += count


def _read_fd(fd: int, maximum: int = 1_048_576) -> bytes:
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
        raw = b"".join(chunks)
        if len(raw) > maximum:
            raise Denied
        return raw
    except OSError:
        raise Denied from None


def _audit_directory_handle(handle: Any) -> None:
    try:
        current = os.fstat(handle.fd)
        if not stat.S_ISDIR(current.st_mode) or _strong_identity(current)[:3] != (
            handle.identity[0],
            handle.identity[1],
            handle.identity[2],
        ):
            raise Denied
        for parent, name, before in handle.chain:
            info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISDIR(info.st_mode) or _strong_identity(info)[:3] != before[:3]:
                raise Denied
    except OSError:
        raise Denied from None


def _audit_published_path(
    proof_dir: Any,
    name: str,
    fd: int,
    raw: bytes,
    *,
    links: set[int],
) -> None:
    try:
        _audit_directory_handle(proof_dir)
        descriptor = os.fstat(fd)
        pathname = os.stat(name, dir_fd=proof_dir.fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(descriptor.st_mode)
            or _strong_identity(descriptor) != _strong_identity(pathname)
            or descriptor.st_nlink not in links
            or stat.S_IMODE(descriptor.st_mode) != 0o644
            or _read_fd(fd) != raw
        ):
            raise Denied
    except OSError:
        raise Denied from None


def _publish_proof(
    repo_root: Path,
    relative: str,
    raw: bytes,
    *,
    audit: Callable[[], None] | None = None,
) -> bool:
    owned: list[int] = []
    subject: Any | None = None
    proof_dir: Any | None = None
    pending_fd: int | None = None
    pending_name = PROOF_PENDING_PATH.rsplit("/", 1)[1]
    name = relative.rsplit("/", 1)[1]
    linked_by_us = False
    finished = False
    try:
        root_fd = os.open("/", v1.verifier._flags(directory=True))
        owned.append(root_fd)
        discovered, repo = v1.verifier._repo_root(root_fd, owned)
        if discovered != os.fspath(repo_root):
            raise Denied
        subject = v1.verifier._open_chain(
            repo.fd, ("specs", "subject-distillation"), owned, final_directory=True
        )
        proof_dir = v1.verifier._open_chain(
            repo.fd,
            ("specs", "subject-distillation", "task-authorizations"),
            owned,
            final_directory=True,
        )
        try:
            final_fd = os.open(name, v1.verifier._flags(directory=False), dir_fd=proof_dir.fd)
        except FileNotFoundError:
            final_fd = None
        try:
            pending_fd = os.open(
                pending_name,
                os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=subject.fd,
            )
        except FileNotFoundError:
            pending_fd = None
        if pending_fd is not None:
            owned.append(pending_fd)
        if final_fd is not None:
            owned.append(final_fd)
            before = os.fstat(final_fd)
            existing = _read_fd(final_fd)
            after = os.fstat(final_fd)
            if (
                existing != raw
                or _strong_identity(before) != _strong_identity(after)
                or stat.S_IMODE(after.st_mode) != 0o644
                or after.st_nlink not in {1, 2}
            ):
                raise Denied
            if after.st_nlink == 2:
                if pending_fd is None:
                    raise Denied
                pending_info = os.fstat(pending_fd)
                if (
                    _read_fd(pending_fd) != raw
                    or (pending_info.st_dev, pending_info.st_ino)
                    != (after.st_dev, after.st_ino)
                ):
                    raise Denied
                os.unlink(pending_name, dir_fd=subject.fd)
                os.fsync(subject.fd)
            elif pending_fd is not None:
                raise Denied
            if audit is not None:
                audit()
            _audit_directory_handle(subject)
            _audit_published_path(proof_dir, name, final_fd, raw, links={1})
            finished = True
            return True
        if pending_fd is None:
            flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
            pending_fd = os.open(pending_name, flags, 0o600, dir_fd=subject.fd)
            owned.append(pending_fd)
            _write_all(pending_fd, raw)
            os.fsync(pending_fd)
        else:
            pending_before = os.fstat(pending_fd)
            if (
                not stat.S_ISREG(pending_before.st_mode)
                or pending_before.st_nlink != 1
                or stat.S_IMODE(pending_before.st_mode) not in {0o600, 0o644}
                or _read_fd(pending_fd) != raw
                or _strong_identity(pending_before) != _strong_identity(os.fstat(pending_fd))
            ):
                raise Denied
        os.fchmod(pending_fd, 0o644)
        os.fsync(pending_fd)
        pending_info = os.fstat(pending_fd)
        if stat.S_IMODE(pending_info.st_mode) != 0o644 or pending_info.st_nlink != 1:
            raise Denied
        if audit is not None:
            audit()
        os.link(
            pending_name,
            name,
            src_dir_fd=subject.fd,
            dst_dir_fd=proof_dir.fd,
            follow_symlinks=False,
        )
        linked_by_us = True
        os.fsync(proof_dir.fd)
        final_info = os.stat(name, dir_fd=proof_dir.fd, follow_symlinks=False)
        final_identity = _strong_identity(final_info)
        pending_identity = _strong_identity(pending_info)
        if (
            final_identity[0],
            final_identity[1],
            final_identity[2],
            final_identity[4],
        ) != (
            pending_identity[0],
            pending_identity[1],
            pending_identity[2],
            pending_identity[4],
        ):
            raise Denied
        if audit is not None:
            try:
                audit()
            except Exception:
                current = os.stat(name, dir_fd=proof_dir.fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == (
                    pending_info.st_dev,
                    pending_info.st_ino,
                ):
                    os.unlink(name, dir_fd=proof_dir.fd)
                    os.fsync(proof_dir.fd)
                    linked_by_us = False
                raise
        _audit_directory_handle(subject)
        _audit_published_path(proof_dir, name, pending_fd, raw, links={2})
        os.unlink(pending_name, dir_fd=subject.fd)
        os.fsync(subject.fd)
        if audit is not None:
            try:
                audit()
            except Exception:
                current = os.stat(name, dir_fd=proof_dir.fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == (
                    pending_info.st_dev,
                    pending_info.st_ino,
                ):
                    os.unlink(name, dir_fd=proof_dir.fd)
                    os.fsync(proof_dir.fd)
                    linked_by_us = False
                raise
        _audit_directory_handle(subject)
        _audit_published_path(proof_dir, name, pending_fd, raw, links={1})
        finished = True
        return False
    except BaseException as exc:
        if not finished and pending_fd is not None and subject is not None:
            try:
                pending_info = os.fstat(pending_fd)
                if linked_by_us and proof_dir is not None:
                    try:
                        final_info = os.stat(
                            name, dir_fd=proof_dir.fd, follow_symlinks=False
                        )
                    except FileNotFoundError:
                        pass
                    else:
                        if (final_info.st_dev, final_info.st_ino) == (
                            pending_info.st_dev,
                            pending_info.st_ino,
                        ):
                            os.unlink(name, dir_fd=proof_dir.fd)
                            os.fsync(proof_dir.fd)
                try:
                    current = os.stat(
                        pending_name, dir_fd=subject.fd, follow_symlinks=False
                    )
                except FileNotFoundError:
                    pass
                else:
                    if (current.st_dev, current.st_ino) == (
                        pending_info.st_dev,
                        pending_info.st_ino,
                    ):
                        os.unlink(pending_name, dir_fd=subject.fd)
                        os.fsync(subject.fd)
            except OSError:
                pass
        if isinstance(exc, (Denied, v1.verifier.Denied)):
            raise Denied from None
        if isinstance(exc, OSError):
            raise Denied from None
        raise
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _verify_confirmed(values: dict[str, str], runtime: Runtime) -> bytes:
    base = values["--implementation-base-commit"]
    task = values["--expected-task"]
    expected_digest = values["--expected-receipt-sha256"]
    expected_proposal = values["--expected-proposal-id"]
    owner_ref = values["--owner-confirmation-ref"]
    if (
        COMMIT.fullmatch(base) is None
        or TASK.fullmatch(task) is None
        or task == "T-001"
        or HEX64.fullmatch(expected_digest) is None
        or HEX64.fullmatch(expected_proposal) is None
    ):
        raise Denied
    now = _clock(runtime)
    proposal, issued = _parse_proposal(values["--proposal-json"], now)
    if (
        proposal["implementation_base_commit"] != base
        or proposal["authorized_task"] != task
        or proposal["proposal_id"] != expected_proposal
    ):
        raise Denied
    state = _repository_state(runtime)
    if state.head != base:
        raise Denied
    root = Path(state.repo_root)
    _check_bridge_release(runtime, root, base)
    recovery_raw = (
        None
        if state.clean
        else _recoverable_proof_raw(root, proposal, issued, owner_ref)
    )
    initial_progress = _progress(runtime, root, task)
    if (
        initial_progress.raw_sha256 != proposal["progress_sha256"]
        or initial_progress.sequence != proposal["progress_sequence"]
    ):
        raise Denied
    v1_runtime = _v1_runtime(runtime)
    with v1._authorization_lock(state.repo_root, "task-auth-v3", base, v1_runtime) as audit_lock:
        def audit_repository() -> None:
            current = _repository_state(runtime)
            if current.repo_root != state.repo_root or current.head != state.head:
                raise Denied
            _check_bridge_release(runtime, root, base)
            if recovery_raw is None:
                if current != state:
                    raise Denied
            elif _recoverable_proof_raw(root, proposal, issued, owner_ref) != recovery_raw:
                raise Denied

        audit_repository()
        inputs = v1._repo_inputs(state.repo_root)
        derived, receipt_raw, scope_raw = _derive(
            root, inputs, base, task, issued, initial_progress
        )
        if not v1.verifier._exact_equal(proposal, derived):
            raise Denied
        if expected_digest != proposal["receipt_sha256"] or hashlib.sha256(
            receipt_raw
        ).hexdigest() != expected_digest:
            raise Denied
        external = v1._external_root(v1_runtime, state.repo_root)
        slot = v1.LifecycleSlot()
        failure: BaseException | None = None
        verifier_output = _canonical(
            {
                "authorization_id": proposal["authorization_id"],
                "authorized_task": task,
                "baseline_id": proposal["baseline_id"],
                "status": "PASS",
            }
        )
        with v1._signal_boundary() as signals:
            try:
                audit_lock()
                v1._new_lifecycle(external, receipt_raw, scope_raw, v1_runtime, signals, slot)
                lifecycle = slot.value
                if lifecycle is None:
                    raise InternalFailure
                v1._hook(v1_runtime, "after_materialize", lifecycle)
                v1._audit_lifecycle(lifecycle)
                v1._run_verifier(
                    lifecycle,
                    state.repo_root,
                    expected_digest,
                    task,
                    verifier_output,
                    v1_runtime,
                )
                audit_lock()
                v1._hook(v1_runtime, "after_verifier", lifecycle)
                if _progress(runtime, root, task) != initial_progress:
                    raise Denied
                audit_repository()
                v1._audit_lifecycle(lifecycle)
            except (Denied, v1.Denied, v1.InternalFailure, v1.Interrupted, v1.PrivateCleanupRequired) as exc:
                failure = exc
            except Exception:  # noqa: BLE001 - fixed public failure boundary
                failure = InternalFailure()
            finally:
                signals.cleanup_active = True
                cleanup_ok = True
                lifecycle = slot.value
                if lifecycle is not None:
                    cleanup_ok = v1._cleanup(lifecycle, v1_runtime)
                    v1._close_lifecycle(lifecycle)
                    slot.value = None
        if not cleanup_ok or isinstance(failure, v1.PrivateCleanupRequired):
            raise v1.PrivateCleanupRequired
        if failure is not None:
            raise failure
        if _progress(runtime, root, task) != initial_progress:
            raise Denied
        audit_repository()
        if recovery_raw is None:
            recorded = _clock(runtime).replace(microsecond=0)
            _require_recorded_freshness(proposal, issued, recorded)
            proof_raw = _canonical(_proof(proposal, recorded, owner_ref))
        else:
            proof_raw = recovery_raw
        guard = _open_bridge_guard(root, task)
        try:
            def audit_publication() -> None:
                current = _repository_state(runtime)
                if current.repo_root != state.repo_root or current.head != state.head:
                    raise Denied
                _check_bridge_release(runtime, root, base)
                if (
                    _progress(runtime, root, task) != initial_progress
                    or _recoverable_proof_raw(root, proposal, issued, owner_ref)
                    != proof_raw
                ):
                    raise Denied
                guard.audit()

            if _progress(runtime, root, task) != initial_progress:
                raise Denied
            audit_repository()
            guard.audit()
            _publish_proof(
                root,
                proposal["proof_repo_relative_path"],
                proof_raw,
                audit=audit_publication,
            )
            audit_publication()
        finally:
            guard.close()
        return proof_raw


def _parse_arguments(argv: Sequence[str]) -> tuple[str, dict[str, str]]:
    if not argv or argv[0] not in {"propose", "verify-confirmed"}:
        raise Denied
    mode = argv[0]
    values = {"--implementation-base-commit", "--expected-task"}
    if mode == "verify-confirmed":
        values |= {
            "--proposal-json",
            "--expected-proposal-id",
            "--expected-receipt-sha256",
            "--owner-confirmation-ref",
        }
    required = values | {"--json"}
    seen: set[str] = set()
    parsed: dict[str, str] = {}
    index = 1
    while index < len(argv):
        flag = argv[index]
        if flag in seen or flag not in required:
            raise Denied
        seen.add(flag)
        if flag == "--json":
            index += 1
            continue
        if index + 1 >= len(argv) or argv[index + 1].startswith("--"):
            raise Denied
        parsed[flag] = argv[index + 1]
        index += 2
    if seen != required or set(parsed) != values:
        raise Denied
    return mode, parsed


def main(argv: Sequence[str] | None = None, *, _runtime: Runtime | None = None) -> int:
    if v1 is None:
        sys.stderr.write(ERROR_TEXT)
        return 3
    runtime = _runtime if _runtime is not None else Runtime()
    try:
        mode, values = _parse_arguments(sys.argv[1:] if argv is None else argv)
        output = _propose(values, runtime) if mode == "propose" else _verify_confirmed(values, runtime)
    except v1.PrivateCleanupRequired:
        sys.stdout.write(CLEANUP_REQUIRED)
        return 4
    except (Denied, v1.Denied, v1.VERIFIER_DENIED):
        sys.stderr.write(DENY_TEXT)
        return 2
    except Exception:  # noqa: BLE001 - fixed no-echo public boundary
        sys.stderr.write(ERROR_TEXT)
        return 3
    sys.stdout.write(output.decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
