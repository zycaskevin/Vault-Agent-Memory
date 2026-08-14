#!/usr/bin/env python3
"""One owner-confirmed Development Mission root for Subject T-004..T-033."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
import sys
import types
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _load_sibling_dependency(module_name: str, filename: str) -> object:
    path = Path(os.path.abspath(Path(__file__).with_name(filename)))
    flags = os.O_RDONLY
    for name in ("O_NOFOLLOW", "O_CLOEXEC"):
        if not hasattr(os, name):
            raise RuntimeError
        flags |= int(getattr(os, name))
    before_path = os.lstat(path)
    if stat.S_ISLNK(before_path.st_mode):
        raise RuntimeError
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        raw = b""
        while len(raw) <= 1_048_576:
            chunk = os.read(fd, min(65_536, 1_048_577 - len(raw)))
            if not chunk:
                break
            raw += chunk
        after = os.fstat(fd)
    finally:
        os.close(fd)
    def identity(info: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
        return (
            info.st_dev,
            info.st_ino,
            info.st_mode,
            info.st_nlink,
            info.st_size,
            info.st_mtime_ns,
            info.st_ctime_ns,
        )
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o755
        or before.st_nlink != 1
        or len(raw) > 1_048_576
        or identity(before_path) != identity(before)
        or identity(before) != identity(after)
        or identity(os.lstat(path)) != identity(before)
    ):
        raise RuntimeError
    existing = sys.modules.get(module_name)
    if existing is not None:
        if getattr(existing, "__file__", None) != os.fspath(path):
            raise RuntimeError
        return existing
    module = types.ModuleType(module_name)
    module.__file__ = os.fspath(path)
    module.__package__ = module_name.rpartition(".")[0]
    sys.modules[module_name] = module
    try:
        exec(compile(raw, "<subject-v5-sibling>", "exec"), module.__dict__)  # noqa: S102
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


try:
    legacy = _load_sibling_dependency(
        "scripts.run_subject_task_authorization_v3",
        "run_subject_task_authorization_v3.py",
    )
except Exception:
    if __name__ == "__main__":
        sys.stderr.write("SUBJECT_DEVELOPMENT_MISSION_V5_ERROR\n")
        raise SystemExit(3) from None
    raise


Denied = legacy.Denied
InternalFailure = legacy.InternalFailure
CONTRACT_PATH = "specs/subject-distillation/development-mission-v5.contract.json"
SCHEMA_PATH = "specs/subject-distillation/development-mission-v5.schema.json"
SCOPE_REGISTRY_PATH = "specs/subject-distillation/task-scope-manifest-v5.json"
MISSION_PROOF_PATH = "specs/subject-distillation/task-authorizations/MISSION-V5-T004-T033.json"
REVOCATION_PATH = "specs/subject-distillation/development-missions/T004-T033.v5.revocation.json"
REVOCATION_PENDING_PATH = (
    "specs/subject-distillation/.development-mission-v5-revocation.pending"
)
PENDING_PATH = "specs/subject-distillation/.task-authorization.pending"
PROGRESS_PATH = legacy.PROGRESS_PATH
TASKS_PATH = legacy.TASKS_PATH
BRIDGE_BASE = "03dcdabc873658cd7de24dfeeef8b85090cf2321"
V4_PROTOCOL_BASE = "0308ebe37929ee0cdf5a8de748d5ae99c6e246f0"
V4_MISSION_ID = "a9f3ffe1c5628fd4425a119797717174ccd7096c46e782f8aea143efb6fde0bc"
TASKS_SHA256 = "0150935a1a16e51dc30dff9dff8d01104d7127ee3cf57333caec7586d93f5007"
ACTIVATION_PROGRESS_SHA256 = "28478445e3eeb5b838b010fa81518d4fcbbb5c6a37422cb3aa58dabdcbf87626"
AUTHORITY = "github:zycaskevin"
DECISION_ID = "SD-MISSION-V5-POST-START-CI-RECOVERY"
MISSION_DURATION = timedelta(seconds=7_776_000)
PROPOSAL_VALIDITY = timedelta(seconds=900)
HEX64 = re.compile(r"[0-9a-f]{64}")
COMMIT = re.compile(r"[0-9a-f]{40}")
TASK = re.compile(r"T-(?:00[4-9]|0[12][0-9]|03[0-3])")
TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
BRANCH_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,255}")
DENY_TEXT = "SUBJECT_DEVELOPMENT_MISSION_V5_DENY\n"
ERROR_TEXT = "SUBJECT_DEVELOPMENT_MISSION_V5_ERROR\n"
CLEANUP_REQUIRED = legacy.CLEANUP_REQUIRED

TRUST_ROOT_PATHS = sorted(
    [
        ".github/workflows/ci.yml",
        "docs/decision_records/2026-08-14-subject-development-mission-v5-recovery.md",
        "scripts/run_subject_development_mission_v5.py",
        "scripts/update_subject_task_progress_v5.py",
        "scripts/validate_subject_development_mission_v5.py",
        "scripts/validate_subject_task_authorization_dispatch_v5.py",
        CONTRACT_PATH,
        SCHEMA_PATH,
        "specs/subject-distillation/development-missions/README.md",
        SCOPE_REGISTRY_PATH,
    ]
)
PREDECESSOR_IMMUTABLE_HASHES = {
    "docs/decision_records/2026-08-13-subject-development-mission-v4.md":
        "461ceca4a894d73c05414be7d0ba8f145b52cd1a4d2ab83b76e5ca62d3cbb499",
    "scripts/run_subject_development_mission_v4.py":
        "6a3721de9f6211972d2cadc22fcc427d65eb4d3a2f66352940e03f8c928dee70",
    "scripts/update_subject_task_progress_v4.py":
        "6873bcb7a217901f75ca7c4271202869a3ac348259f5ca7ebcefdba80a5ac61f",
    "scripts/validate_subject_development_mission_v4.py":
        "1ebcb46928474c3b305456b98ab2517872edd52a41e0cd0c83f2b9f273f4fa8e",
    "scripts/validate_subject_task_authorization_dispatch_v4.py":
        "8253fabeebaef5a6aa5655280e0210f90250882da46081951a4a2183891f3d37",
    "specs/subject-distillation/development-mission-v4.contract.json":
        "e264da10e3b8e016eba78029307eaf1cefe6922b8f4172b29ce7ecc87bf411d3",
    "specs/subject-distillation/development-mission-v4.schema.json":
        "b561c8fb2c67bbf3f0360d535c287c6332b45098b846efc08fe1d5473397f06d",
    "specs/subject-distillation/task-authorizations/MISSION-T004-T033.json":
        "8c581721fb3a4da7aa8107ed4c4fc490c9a96e45843f854c4da4c8d77f411411",
    "specs/subject-distillation/task-scope-manifest-v4.json":
        "3b0ae32a35af5ad4e5ef85558f612b6f2a78ba45b28b37fa2272337300b508c4",
    "tests/test_subject_development_mission_v4.py":
        "7b00d9306bbb2f84a03e561c001a3462a4840b8ee106c3e084330b5b555e3f4f",
    "tests/test_subject_task_authorization_dispatch_v4.py":
        "7f31efbc18226688919bbd09cf2112178c69268e9fda13bf6114aa7caf66b5ea",
}
RETAINED_AUTHORITY_PATHS = sorted(
    [
        "scripts/verify_subject_implementation_authorization.py",
        "specs/subject-distillation/baseline-manifest.json",
        "specs/subject-distillation/design.md",
        "specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json",
        "specs/subject-distillation/requirements.md",
        "specs/subject-distillation/schema.v15.sql",
        "specs/subject-distillation/tasks.md",
        "specs/subject-distillation/traceability.md",
        *PREDECESSOR_IMMUTABLE_HASHES,
    ]
)
PROHIBITED_OPERATIONS = [
    "billing",
    "credentials",
    "customer_communication",
    "deploy_production",
    "destructive_operation",
    "legal_commitment",
    "live_private_data",
    "l2_product_decision",
    "l3_operation",
    "payment",
    "production_migration",
    "provider_console",
    "release",
    "store_console",
]
REQUIRED_HOSTED_CHECKS = sorted(
    [
        "Build, twine check, and wheel smoke",
        "Full history privacy scan",
        "Lightweight secret scan",
        "Lint raw/ knowledge files",
        "Memory foundation governance contract",
        "Module size gate",
        "One-click installer smoke (Linux)",
        "One-click installer smoke (Windows)",
        "README documented command smoke",
        "Release version parity",
        "Search QA regression gate",
        "Tests (Python 3.10)",
        "Tests (Python 3.11)",
        "Tests (Python 3.12)",
        "uv dev workflow smoke",
    ]
)
TASK_PHASES = {
    **{f"T-{number:03d}": "B" for number in range(4, 8)},
    **{f"T-{number:03d}": "C" for number in range(8, 11)},
    **{f"T-{number:03d}": "D" for number in range(11, 14)},
    **{f"T-{number:03d}": "E" for number in range(14, 17)},
    **{f"T-{number:03d}": "F" for number in range(17, 21)},
    **{f"T-{number:03d}": "G" for number in range(21, 25)},
    **{f"T-{number:03d}": "H" for number in range(25, 27)},
    **{f"T-{number:03d}": "I" for number in range(27, 30)},
    **{f"T-{number:03d}": "J" for number in range(30, 34)},
}

BRIDGE_PATHS = sorted(
    [
        ".github/workflows/ci.yml",
        "docs/decision_records/2026-08-14-subject-development-mission-v5-recovery.md",
        "scripts/run_subject_development_mission_v5.py",
        "scripts/update_subject_task_progress_v5.py",
        "scripts/validate_subject_development_mission_v5.py",
        "scripts/validate_subject_task_authorization_dispatch_v5.py",
        CONTRACT_PATH,
        SCHEMA_PATH,
        "specs/subject-distillation/development-missions/README.md",
        SCOPE_REGISTRY_PATH,
        "tests/test_repo_hygiene_tools.py",
        "tests/test_subject_development_mission_v5.py",
        "tests/test_subject_task_authorization_dispatch_v5.py",
    ]
)


def canonical(value: Any, *, newline: bool = True) -> bytes:
    return legacy._canonical(value, newline=newline)


def _parse(raw: bytes) -> Any:
    try:
        return legacy.v1.verifier._parse(raw)
    except legacy.v1.verifier.Denied:
        raise Denied from None


def _timestamp(value: Any) -> datetime:
    if type(value) is not str or TIME.fullmatch(value) is None:
        raise Denied
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise Denied from None
    return parsed


def _time(value: datetime) -> str:
    if type(value) is not datetime or value.tzinfo != timezone.utc or value.microsecond:
        raise Denied
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _now(text: str | None = None) -> datetime:
    if text is not None:
        return _timestamp(text)
    return datetime.now(timezone.utc).replace(microsecond=0)


def _read(repo_root: Path, path: str, *, mode: int = 0o644) -> bytes:
    raw, identity = legacy._read_repo_file(repo_root, path, maximum=16_777_216)
    legacy._require_public_identity(identity, mode)
    return raw


def _snapshot_read(
    repo_root: Path,
    path: str,
    retained: dict[str, bytes] | None,
    *,
    mode: int = 0o644,
) -> bytes:
    if retained is None:
        return _read(repo_root, path, mode=mode)
    try:
        return retained[path]
    except KeyError:
        raise Denied from None


def open_paths_guard(repo_root: Path, paths: Sequence[str]) -> legacy.BridgeGuard:
    """Retain one identity-audited snapshot for exact public repo files."""
    owned: list[int] = []
    entries: list[Any] = []
    try:
        root_fd = os.open("/", legacy.v1.verifier._flags(directory=True))
        owned.append(root_fd)
        discovered, repo = legacy.v1.verifier._repo_root(root_fd, owned)
        if discovered != os.fspath(repo_root):
            raise Denied
        normalized = sorted(legacy._path(path) for path in paths)
        if len(normalized) != len(set(normalized)):
            raise Denied
        for relative in normalized:
            handle = legacy.v1.verifier._open_chain(repo.fd, relative.split("/"), owned)
            info = os.fstat(handle.fd)
            mode = 0o755 if relative.startswith("scripts/") and relative.endswith(".py") else 0o644
            identity = legacy._strong_identity(info)
            legacy._require_public_identity(identity, mode)
            if info.st_size > 16_777_216:
                raise Denied
            raw = legacy._read_fd(handle.fd, 16_777_216)
            if len(raw) != info.st_size:
                raise Denied
            entries.append(legacy._GuardEntry(handle, identity, raw, relative))
        guard = legacy.BridgeGuard(entries, owned)
        guard.audit()
        return guard
    except (OSError, legacy.v1.verifier.Denied, Denied):
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass
        raise Denied from None


def publish_revocation_record(
    repo_root: Path,
    raw: bytes,
    *,
    audit: Callable[[], None] | None = None,
) -> bool:
    """Atomically publish or recover the one irreversible epoch-1 revocation."""
    owned: list[int] = []
    pending_fd: int | None = None
    final_fd: int | None = None
    pending_name = REVOCATION_PENDING_PATH.rsplit("/", 1)[1]
    final_name = REVOCATION_PATH.rsplit("/", 1)[1]
    try:
        root_fd = os.open("/", legacy.v1.verifier._flags(directory=True))
        owned.append(root_fd)
        discovered, repo = legacy.v1.verifier._repo_root(root_fd, owned)
        if discovered != os.fspath(repo_root):
            raise Denied
        subject = legacy.v1.verifier._open_chain(
            repo.fd, ("specs", "subject-distillation"), owned, final_directory=True
        )
        mission_dir = legacy.v1.verifier._open_chain(
            repo.fd,
            ("specs", "subject-distillation", "development-missions"),
            owned,
            final_directory=True,
        )
        try:
            final_fd = os.open(
                final_name,
                legacy.v1.verifier._flags(directory=False),
                dir_fd=mission_dir.fd,
            )
            owned.append(final_fd)
        except FileNotFoundError:
            final_fd = None
        try:
            pending_fd = os.open(
                pending_name,
                os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=subject.fd,
            )
            owned.append(pending_fd)
        except FileNotFoundError:
            pending_fd = None
        if final_fd is not None:
            final_info = os.fstat(final_fd)
            if (
                stat.S_IMODE(final_info.st_mode) != 0o644
                or final_info.st_nlink not in {1, 2}
                or legacy._read_fd(final_fd) != raw
            ):
                raise Denied
            if final_info.st_nlink == 2:
                if pending_fd is None:
                    raise Denied
                pending_info = os.fstat(pending_fd)
                if (
                    (pending_info.st_dev, pending_info.st_ino)
                    != (final_info.st_dev, final_info.st_ino)
                    or legacy._read_fd(pending_fd) != raw
                ):
                    raise Denied
                os.unlink(pending_name, dir_fd=subject.fd)
                os.fsync(subject.fd)
            elif pending_fd is not None:
                raise Denied
            if audit is not None:
                audit()
            if legacy._read_fd(final_fd) != raw or os.fstat(final_fd).st_nlink != 1:
                raise Denied
            return True
        if pending_fd is None:
            pending_fd = os.open(
                pending_name,
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                0o600,
                dir_fd=subject.fd,
            )
            owned.append(pending_fd)
            legacy._write_all(pending_fd, raw)
            os.fsync(pending_fd)
        elif (
            os.fstat(pending_fd).st_nlink != 1
            or stat.S_IMODE(os.fstat(pending_fd).st_mode) not in {0o600, 0o644}
            or legacy._read_fd(pending_fd) != raw
        ):
            raise Denied
        os.fchmod(pending_fd, 0o644)
        os.fsync(pending_fd)
        if audit is not None:
            audit()
        os.link(
            pending_name,
            final_name,
            src_dir_fd=subject.fd,
            dst_dir_fd=mission_dir.fd,
            follow_symlinks=False,
        )
        os.fsync(mission_dir.fd)
        if os.fstat(pending_fd).st_nlink != 2:
            raise Denied
        os.unlink(pending_name, dir_fd=subject.fd)
        os.fsync(subject.fd)
        if audit is not None:
            audit()
        final_fd = os.open(
            final_name,
            legacy.v1.verifier._flags(directory=False),
            dir_fd=mission_dir.fd,
        )
        owned.append(final_fd)
        if (
            legacy._read_fd(final_fd) != raw
            or stat.S_IMODE(os.fstat(final_fd).st_mode) != 0o644
            or os.fstat(final_fd).st_nlink != 1
        ):
            raise Denied
        return False
    except (OSError, legacy.v1.verifier.Denied):
        raise Denied from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def required_read_files(
    repo_root: Path,
    descriptor: dict[str, Any],
    *,
    retained: dict[str, bytes] | None = None,
) -> list[dict[str, str]]:
    """Bind every declared prerequisite to exact public bytes and mode."""
    paths = descriptor.get("required_read_paths")
    if type(paths) is not list or paths != sorted(paths) or len(paths) != len(set(paths)):
        raise Denied
    result: list[dict[str, str]] = []
    for path in paths:
        if type(path) is not str:
            raise Denied
        mode = 0o755 if path.startswith("scripts/") and path.endswith(".py") else 0o644
        result.append(
            {
                "mode": f"100{mode:o}",
                "path": path,
                "sha256": hashlib.sha256(
                    _snapshot_read(repo_root, path, retained, mode=mode)
                ).hexdigest(),
            }
        )
    return result


def required_read_files_at_commit(
    repo_root: Path, descriptor: dict[str, Any], commit: str
) -> list[dict[str, str]]:
    """Reconstruct historical prerequisite bytes from the task start commit."""
    paths = descriptor.get("required_read_paths")
    if type(paths) is not list or paths != sorted(paths) or len(paths) != len(set(paths)):
        raise Denied
    result = []
    for path in paths:
        expected_mode = (
            "100755" if path.startswith("scripts/") and path.endswith(".py") else "100644"
        )
        mode, raw = _git_object(repo_root, commit, path)
        if mode != expected_mode:
            raise Denied
        result.append(
            {"mode": mode, "path": path, "sha256": hashlib.sha256(raw).hexdigest()}
        )
    return result


def load_contract(
    repo_root: Path, *, retained: dict[str, bytes] | None = None
) -> tuple[dict[str, Any], bytes]:
    raw = _snapshot_read(repo_root, CONTRACT_PATH, retained)
    value = _parse(raw)
    required = {
        "activation",
        "allowed_environments",
        "allowed_risk_classes",
        "allowed_tasks",
        "artifact_kind",
        "authority",
        "canonicalization",
        "mission_duration_seconds",
        "mission_proof_path",
        "predecessor_protocol",
        "prohibited_operations",
        "proposal_confirmation_window_seconds",
        "protocol_base_policy",
        "repository",
        "required_hosted_checks",
        "reopen_conditions",
        "revocation",
        "schema_version",
        "scope_registry_path",
        "scope_registry_sha256",
        "special_boundaries",
        "supersession",
        "trust_root_paths",
    }
    if (
        type(value) is not dict
        or set(value) != required
        or raw != canonical(value)
        or value["schema_version"] != 5
        or value["artifact_kind"] != "subject-development-mission-v5-contract"
        or value["repository"] != "zycaskevin/Vault-Agent-Memory"
        or value["allowed_tasks"] != [f"T-{number:03d}" for number in range(4, 34)]
        or value["allowed_risk_classes"] != ["L0", "L1"]
        or value["allowed_environments"] != ["development", "local", "staging", "test"]
        or value["mission_duration_seconds"] != 7_776_000
        or value["proposal_confirmation_window_seconds"] != 900
        or value["mission_proof_path"] != MISSION_PROOF_PATH
        or value["scope_registry_path"] != SCOPE_REGISTRY_PATH
        or value["protocol_base_policy"]
        != "exact-current-origin-main-after-reviewed-v5-bridge-merge"
        or value["canonicalization"]
        != {
            "digest": "sha256",
            "domain_separator": "vault-subject-development-mission-v5",
            "encoding": "recursive-sorted-keys-utf8-no-whitespace-final-lf",
        }
        or value["prohibited_operations"] != PROHIBITED_OPERATIONS
        or value["required_hosted_checks"] != REQUIRED_HOSTED_CHECKS
        or value["reopen_conditions"]
        != [
            "baseline_changed",
            "canonical_task_header_changed",
            "mission_expired",
            "mission_revoked",
            "product_or_risk_boundary_changed",
            "scope_registry_changed",
            "trust_root_changed",
        ]
        or value["revocation"]
        != {
            "blocked_code_expired": "MISSION_EXPIRED",
            "blocked_code_revoked": "MISSION_REVOKED",
            "epoch": 1,
            "path": REVOCATION_PATH,
            "pending_path": REVOCATION_PENDING_PATH,
            "resume_requires_new_owner_confirmed_protocol_version": True,
            "terminal_epoch": True,
        }
        or value["special_boundaries"]
        != {
            "T-032": "operational-blocked-only-without-separate-L3-package",
            "T-033": "experimental-only-without-separate-L3-package",
            "generic_t033_completion": False,
        }
        or value["trust_root_paths"] != TRUST_ROOT_PATHS
        or value["authority"]
        != {
            "authorizing_principal": AUTHORITY,
            "delegates_task_authority": True,
            "owner_confirmation_required_for_mission": True,
            "owner_confirmation_required_per_task": False,
            "owner_decision_id": DECISION_ID,
            "owner_decision_ref": "owner-message:SD-MISSION-V5-POST-START-CI-RECOVERY",
        }
    ):
        raise Denied
    predecessor = value["predecessor_protocol"]
    expected_predecessor = {
        "activation_commit": "git:" + BRIDGE_BASE,
        "activation_progress_sequence": 6,
        "activation_progress_sha256": ACTIVATION_PROGRESS_SHA256,
        "contract_path": "specs/subject-distillation/development-mission-v4.contract.json",
        "contract_sha256": PREDECESSOR_IMMUTABLE_HASHES[
            "specs/subject-distillation/development-mission-v4.contract.json"
        ],
        "mission_id": V4_MISSION_ID,
        "proof_path": "specs/subject-distillation/task-authorizations/MISSION-T004-T033.json",
        "proof_sha256": PREDECESSOR_IMMUTABLE_HASHES[
            "specs/subject-distillation/task-authorizations/MISSION-T004-T033.json"
        ],
        "protocol_base_commit": "git:" + V4_PROTOCOL_BASE,
        "protocol_version": 4,
        "supersession": "task-authority-and-ci-routing-for-t004-t033",
        "trust_root_sha256":
            "511e24bbffb1b88566d7a3cc10deee4e8f260ae29d6a0d029b2e5d4070d457b9",
    }
    if predecessor != expected_predecessor:
        raise Denied
    for path, digest in PREDECESSOR_IMMUTABLE_HASHES.items():
        mode = 0o755 if path.startswith("scripts/") else 0o644
        if hashlib.sha256(_snapshot_read(repo_root, path, retained, mode=mode)).hexdigest() != digest:
            raise Denied
    predecessor_proof = _parse(
        _snapshot_read(
            repo_root,
            expected_predecessor["proof_path"],
            retained,
        )
    )
    if (
        type(predecessor_proof) is not dict
        or predecessor_proof.get("schema_version") != 4
        or predecessor_proof.get("artifact_kind") != "subject-development-mission-v4-proof"
        or predecessor_proof.get("status") != "PASS"
        or predecessor_proof.get("mission_id") != V4_MISSION_ID
        or predecessor_proof.get("protocol_base_commit") != "git:" + V4_PROTOCOL_BASE
        or predecessor_proof.get("progress_sequence") != 6
        or predecessor_proof.get("progress_sha256") != ACTIVATION_PROGRESS_SHA256
        or predecessor_proof.get("trust_root_sha256")
        != expected_predecessor["trust_root_sha256"]
    ):
        raise Denied
    activation = value["activation"]
    if (
        type(activation) is not dict
        or set(activation)
        != {
            "baseline_full_digest",
            "baseline_id",
            "bridge_implementation_base_commit",
            "progress",
            "t001_t003_event_prefix_sha256",
            "tasks_sha256",
        }
        or activation["bridge_implementation_base_commit"] != "git:" + BRIDGE_BASE
        or activation["baseline_id"] != "0dc10cfc4a429662"
        or activation["baseline_full_digest"]
        != "0dc10cfc4a429662037f3bb7d6c42e10e7cc832b540f7aa8f4b9e0656e0e459b"
        or activation["tasks_sha256"] != TASKS_SHA256
        or activation["t001_t003_event_prefix_sha256"]
        != "e70c33f3c1a1e6abc71cd59b694ed5785fa58b608804d02888362c85cf090006"
        or activation["progress"]
        != {
            "path": PROGRESS_PATH,
            "sequence": 6,
            "sha256": ACTIVATION_PROGRESS_SHA256,
        }
    ):
        raise Denied
    supersession = value["supersession"]
    if (
        type(supersession) is not dict
        or set(supersession)
        != {
            "applicable_tasks",
            "precedence",
            "preserved_rules",
            "replacement_rule",
            "targets",
        }
        or supersession.get("applicable_tasks") != value["allowed_tasks"]
        or supersession.get("precedence") != "later-direct-owner-decision-overlay"
        or supersession.get("replacement_rule")
        != "one-owner-confirmed-exact-mission-root-replaces-only-per-task-owner-confirmation-for-t004-t033"
        or supersession.get("preserved_rules")
        != [
            "all-product-sdd-and-sbe-semantics",
            "all-t001-t003-authority-and-terminal-history",
            "exact-scope-and-review-gates",
            "l2-l3-and-operational-action-boundaries",
        ]
        or len(supersession.get("targets", [])) != 3
    ):
        raise Denied
    for target in supersession["targets"]:
        if type(target) is not dict or set(target) != {
            "clause_refs",
            "path",
            "sha256",
        }:
            raise Denied
        if (
            hashlib.sha256(
                _snapshot_read(repo_root, target["path"], retained)
            ).hexdigest()
            != target["sha256"]
        ):
            raise Denied
    if supersession["targets"] != [
        {
            "clause_refs": [
                "implementation-authorization-table",
                "coding-mission-bound-authorization",
            ],
            "path": "specs/subject-distillation/requirements.md",
            "sha256": "11f9dfc66f8cf0aa48d7fbddbba6509c4116ecf66248d1e87d0a111acf96d8f6",
        },
        {
            "clause_refs": [
                "section-21-two-stage-owner-confirmed-task-protocol",
                "section-22-implementation-authorization-binding",
            ],
            "path": "specs/subject-distillation/design.md",
            "sha256": "3127c8323bb43f09fef1fb70d036c4efc786887431de8256e9783bee484b20fa",
        },
        {
            "clause_refs": [
                "section-0-rule-4",
                "common-task-checkpoints",
                "first-product-task-gate",
            ],
            "path": TASKS_PATH,
            "sha256": TASKS_SHA256,
        },
    ]:
        raise Denied
    return value, raw


def load_registry(
    repo_root: Path,
    contract: dict[str, Any],
    *,
    retained: dict[str, bytes] | None = None,
) -> tuple[dict[str, Any], bytes]:
    raw = _snapshot_read(repo_root, SCOPE_REGISTRY_PATH, retained)
    if hashlib.sha256(raw).hexdigest() != contract["scope_registry_sha256"]:
        raise Denied
    value = _parse(raw)
    if (
        type(value) is not dict
        or set(value)
        != {
            "artifact_kind",
            "baseline_full_digest",
            "baseline_id",
            "schema_version",
            "tasks",
            "tasks_sha256",
        }
        or raw != canonical(value)
        or value["schema_version"] != 5
        or value["artifact_kind"] != "subject-development-mission-v5-scope-registry"
        or value["tasks_sha256"] != TASKS_SHA256
        or [entry.get("task") for entry in value["tasks"]] != contract["allowed_tasks"]
    ):
        raise Denied
    tasks_raw = _snapshot_read(repo_root, TASKS_PATH, retained)
    if hashlib.sha256(tasks_raw).hexdigest() != TASKS_SHA256:
        raise Denied
    for entry in value["tasks"]:
        _validate_registry_entry(entry, tasks_raw)
    return value, raw


def _validate_registry_entry(entry: Any, tasks_raw: bytes) -> None:
    keys = {
        "completion_repo_relative_paths",
        "phase_id",
        "required_control_api",
        "required_read_paths",
        "risk_class",
        "stable_requires_operational_authority",
        "task",
        "task_header_sha256",
        "terminal_policy",
        "verification_steps",
        "writable_path_policies",
    }
    if type(entry) is not dict or set(entry) != keys or TASK.fullmatch(entry["task"]) is None:
        raise Denied
    task = entry["task"]
    expected_control_api = (
        "scripts.validate_subject_development_mission_v5:validate_t033_action"
        if task in {"T-031", "T-033"}
        else None
    )
    if entry["required_control_api"] != expected_control_api:
        raise Denied
    if entry["phase_id"] != TASK_PHASES[task]:
        raise Denied
    if (
        hashlib.sha256(legacy._task_header(tasks_raw, task)).hexdigest()
        != entry["task_header_sha256"]
    ):
        raise Denied
    if entry["risk_class"] not in {"L0", "L1", "OPERATIONAL"}:
        raise Denied
    if entry["terminal_policy"] not in {
        "completed",
        "blocked_only",
        "experimental_only",
    }:
        raise Denied
    policies = entry["writable_path_policies"]
    if type(policies) is not list:
        raise Denied
    paths = []
    for policy in policies:
        if type(policy) is not dict or set(policy) != {
            "action",
            "final_mode",
            "path",
        }:
            raise Denied
        path = legacy._path(policy["path"])
        if "*" in path or "$" in path or policy["action"] not in {"create", "modify"}:
            raise Denied
        mode = "0755" if path.startswith("scripts/") and path.endswith(".py") else "0644"
        if policy["final_mode"] != mode:
            raise Denied
        paths.append(path)
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise Denied
    if entry["completion_repo_relative_paths"] != paths:
        raise Denied
    reads = entry["required_read_paths"]
    if (
        type(reads) is not list
        or reads != sorted(reads)
        or len(reads) != len(set(reads))
    ):
        raise Denied
    for path in reads:
        normalized = legacy._path(path)
        if "*" in normalized or "$" in normalized:
            raise Denied
    if set(reads) & set(paths):
        raise Denied
    steps = entry["verification_steps"]
    if type(steps) is not list or not 1 <= len(steps) <= 16:
        raise Denied
    for step in steps:
        if type(step) is not dict or set(step) != {
            "argv",
            "effects",
            "required_exit",
            "step_id",
        }:
            raise Denied
        argv = step["argv"]
        if (
            type(argv) is not list
            or not 1 <= len(argv) <= 96
            or any(type(item) is not str or not 1 <= len(item) <= 512 for item in argv)
            or step["required_exit"] != 0
            or step["effects"] not in {"read_only", "declared_outputs", "control_only"}
            or OPAQUE.fullmatch(step["step_id"]) is None
        ):
            raise Denied
    if task == "T-032" and (
        entry["risk_class"] != "OPERATIONAL" or entry["terminal_policy"] != "blocked_only" or paths
    ):
        raise Denied
    if task == "T-033" and (
        entry["terminal_policy"] != "experimental_only"
        or entry["stable_requires_operational_authority"] is not True
    ):
        raise Denied


def _trust_root(
    repo_root: Path,
    contract: dict[str, Any],
    *,
    retained: dict[str, bytes] | None = None,
) -> list[dict[str, str]]:
    result = []
    for path in contract["trust_root_paths"]:
        mode = 0o755 if path.startswith("scripts/") and path.endswith(".py") else 0o644
        result.append(
            {
                "path": path,
                "sha256": hashlib.sha256(
                    _snapshot_read(repo_root, path, retained, mode=mode)
                ).hexdigest(),
            }
        )
    return result


def _git(repo_root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args], cwd=repo_root, capture_output=True, check=False, timeout=30
    )
    if completed.returncode or completed.stderr:
        raise Denied
    return completed.stdout


def check_repository_identity(repo_root: Path) -> None:
    raw = _git(repo_root, "remote", "get-url", "origin")
    if not raw.endswith(b"\n") or b"\n" in raw[:-1]:
        raise Denied
    try:
        remote = raw[:-1].decode("ascii")
    except UnicodeDecodeError:
        raise Denied from None
    if remote not in {
        "git@github.com:zycaskevin/Vault-Agent-Memory.git",
        "https://github.com/zycaskevin/Vault-Agent-Memory",
        "https://github.com/zycaskevin/Vault-Agent-Memory.git",
    }:
        raise Denied


def _git_object(repo_root: Path, commit: str, path: str) -> tuple[str, bytes]:
    """Read one exact regular blob from an already validated Git commit."""
    if COMMIT.fullmatch(commit) is None or legacy._path(path) != path:
        raise Denied
    entry = _git(repo_root, "ls-tree", commit, "--", path).decode().strip()
    if not entry.endswith("\t" + path):
        raise Denied
    header = entry.removesuffix("\t" + path).split()
    if len(header) != 3 or header[0] not in {"100644", "100755"} or header[1] != "blob":
        raise Denied
    raw = _git(repo_root, "show", f"{commit}:{path}")
    return header[0], raw


def validate_preliminary_delivery(
    repo_root: Path,
    proof: dict[str, Any],
    descriptor: dict[str, Any],
    review: dict[str, Any],
) -> None:
    """Recompute the exact implementation commit and hosted-CI binding."""
    check_repository_identity(repo_root)
    base = proof["implementation_base_commit"][4:]
    head = review["preliminary_head_commit"][4:]
    if COMMIT.fullmatch(base) is None or COMMIT.fullmatch(head) is None or head == base:
        raise Denied
    parents = _git(repo_root, "rev-list", "--parents", "-n", "1", head).decode().split()
    if parents != [head, base]:
        raise Denied
    changed = _git(repo_root, "diff", "--name-only", f"{base}..{head}").decode().splitlines()
    expected = sorted(
        [
            proof["proof_repo_relative_path"],
            PROGRESS_PATH,
            *descriptor["completion_repo_relative_paths"],
        ]
    )
    if changed != expected:
        raise Denied
    policy = {item["path"]: item for item in descriptor["writable_path_policies"]}
    expected_status = []
    for path in expected:
        if path == PROGRESS_PATH:
            status = "M"
        elif path == proof["proof_repo_relative_path"]:
            status = "A"
        else:
            status = "A" if policy[path]["action"] == "create" else "M"
        expected_status.append(f"{status}\t{path}")
    if _git(
        repo_root,
        "diff",
        "--name-status",
        "--no-renames",
        f"{base}..{head}",
    ).decode().splitlines() != expected_status:
        raise Denied
    tree = _git(repo_root, "rev-parse", f"{head}^{{tree}}").strip().decode()
    if COMMIT.fullmatch(tree) is None or review["preliminary_tree_git_oid"] != "git:" + tree:
        raise Denied
    reviewed = {item["path"]: item for item in review["reviewed_changes"]}
    for path in expected:
        mode, raw = _git_object(repo_root, head, path)
        if path == PROGRESS_PATH:
            if mode != "100644" or hashlib.sha256(raw).hexdigest() != review[
                "progress_before_sha256"
            ]:
                raise Denied
            continue
        expected_mode = (
            "100644"
            if path == proof["proof_repo_relative_path"]
            else f"10{policy[path]['final_mode']}"
        )
        if mode != expected_mode or reviewed[path]["sha256"] != hashlib.sha256(raw).hexdigest():
            raise Denied
    ci = review["required_ci"]
    if (
        ci["repository"] != "zycaskevin/Vault-Agent-Memory"
        or ci["workflow"] != ".github/workflows/ci.yml"
        or ci["head_commit"] != review["preliminary_head_commit"]
        or ci["conclusion"] != "success"
        or ci["workflow_sha256"]
        != hashlib.sha256(_git_object(repo_root, head, ".github/workflows/ci.yml")[1]).hexdigest()
    ):
        raise Denied


def validate_mission_activation_delivery(
    repo_root: Path,
    *,
    protocol_base: str,
    mission_raw: bytes,
) -> str:
    """Locate the one direct-child commit that publishes the mission proof."""
    if COMMIT.fullmatch(protocol_base) is None or type(mission_raw) is not bytes:
        raise Denied
    check_repository_identity(repo_root)
    head = _git(repo_root, "rev-parse", "HEAD").strip().decode()
    if COMMIT.fullmatch(head) is None:
        raise Denied
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", protocol_base, head],
        cwd=repo_root,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if ancestor.returncode or ancestor.stdout or ancestor.stderr:
        raise Denied
    commits = _git(
        repo_root,
        "rev-list",
        "--ancestry-path",
        "--reverse",
        f"{protocol_base}..{head}",
    ).decode().splitlines()
    if len(commits) > 128 or any(COMMIT.fullmatch(item) is None for item in commits):
        raise Denied
    matches: list[str] = []
    for commit in commits:
        parents = _git(repo_root, "rev-list", "--parents", "-n", "1", commit).decode().split()
        if parents != [commit, protocol_base]:
            continue
        if _git(repo_root, "diff", "--name-only", f"{protocol_base}..{commit}").decode().splitlines() != [MISSION_PROOF_PATH]:
            continue
        if _git(
            repo_root,
            "diff",
            "--name-status",
            "--no-renames",
            f"{protocol_base}..{commit}",
        ).decode().splitlines() != [f"A\t{MISSION_PROOF_PATH}"]:
            continue
        try:
            mode, raw = _git_object(repo_root, commit, MISSION_PROOF_PATH)
        except Denied:
            continue
        if mode == "100644" and raw == mission_raw:
            matches.append(commit)
    if len(matches) != 1:
        raise Denied
    return matches[0]


def validate_progress_only_delivery(
    repo_root: Path,
    *,
    parent_commit: str,
    progress_raw: bytes,
) -> str:
    """Locate the exact direct-child T-032 BLOCKED ledger delivery."""
    if COMMIT.fullmatch(parent_commit) is None or type(progress_raw) is not bytes:
        raise Denied
    check_repository_identity(repo_root)
    head = _git(repo_root, "rev-parse", "HEAD").strip().decode()
    if COMMIT.fullmatch(head) is None:
        raise Denied
    if head == parent_commit:
        if _git_status(repo_root) != {PROGRESS_PATH: "modify"}:
            raise Denied
        if _read(repo_root, PROGRESS_PATH) != progress_raw:
            raise Denied
        return "WORKTREE"
    commits = _git(
        repo_root,
        "rev-list",
        "--ancestry-path",
        "--reverse",
        f"{parent_commit}..{head}",
    ).decode().splitlines()
    if not commits or len(commits) > 128 or any(COMMIT.fullmatch(item) is None for item in commits):
        raise Denied
    matches: list[str] = []
    for commit in commits:
        parents = _git(repo_root, "rev-list", "--parents", "-n", "1", commit).decode().split()
        if parents != [commit, parent_commit]:
            continue
        if _git(repo_root, "diff", "--name-only", f"{parent_commit}..{commit}").decode().splitlines() != [PROGRESS_PATH]:
            continue
        if _git(
            repo_root,
            "diff",
            "--name-status",
            "--no-renames",
            f"{parent_commit}..{commit}",
        ).decode().splitlines() != [f"M\t{PROGRESS_PATH}"]:
            continue
        try:
            mode, raw = _git_object(repo_root, commit, PROGRESS_PATH)
        except Denied:
            continue
        if mode == "100644" and raw == progress_raw:
            matches.append(commit)
    if len(matches) != 1:
        raise Denied
    return matches[0]


def _task_execution_anchor(
    repo_root: Path,
    *,
    proof: dict[str, Any],
    proof_raw: bytes,
    progress_raw: bytes,
) -> str:
    """Locate the exact direct-child implementation head for an active task."""
    if (
        type(proof) is not dict
        or type(proof_raw) is not bytes
        or type(progress_raw) is not bytes
        or proof_raw != canonical(proof)
    ):
        raise Denied
    task = proof.get("authorized_task")
    base_ref = proof.get("implementation_base_commit")
    proof_path = proof.get("proof_repo_relative_path")
    if (
        type(task) is not str
        or TASK.fullmatch(task) is None
        or type(base_ref) is not str
        or not base_ref.startswith("git:")
        or COMMIT.fullmatch(base_ref[4:]) is None
        or type(proof_path) is not str
        or legacy._path(proof_path) != proof_path
    ):
        raise Denied
    contract, _contract_raw = load_contract(repo_root)
    registry, _registry_raw = load_registry(repo_root, contract)
    descriptor = registry["tasks"][int(task[2:]) - 4]
    base = base_ref[4:]
    head = _git(repo_root, "rev-parse", "HEAD").strip().decode()
    commits = _git(
        repo_root,
        "rev-list",
        "--ancestry-path",
        "--reverse",
        f"{base}..{head}",
    ).decode().splitlines()
    if not commits or len(commits) > 3 or any(COMMIT.fullmatch(item) is None for item in commits):
        raise Denied
    expected_paths = sorted(
        [proof_path, PROGRESS_PATH, *descriptor["completion_repo_relative_paths"]]
    )
    policy = {item["path"]: item for item in descriptor["writable_path_policies"]}
    expected_status = []
    for path in expected_paths:
        if path == PROGRESS_PATH:
            status = "M"
        elif path == proof_path:
            status = "A"
        else:
            status = "A" if policy[path]["action"] == "create" else "M"
        expected_status.append(f"{status}\t{path}")
    matches: list[str] = []
    for commit in commits:
        parents = _git(repo_root, "rev-list", "--parents", "-n", "1", commit).decode().split()
        if parents != [commit, base]:
            continue
        if _git(repo_root, "diff", "--name-only", f"{base}..{commit}").decode().splitlines() != expected_paths:
            continue
        if _git(
            repo_root,
            "diff",
            "--name-status",
            "--no-renames",
            f"{base}..{commit}",
        ).decode().splitlines() != expected_status:
            continue
        try:
            proof_mode, committed_proof = _git_object(repo_root, commit, proof_path)
            progress_mode, committed_progress = _git_object(
                repo_root, commit, PROGRESS_PATH
            )
            if (
                proof_mode != "100644"
                or committed_proof != proof_raw
                or progress_mode != "100644"
                or committed_progress != progress_raw
            ):
                continue
            for path in descriptor["completion_repo_relative_paths"]:
                mode, _raw = _git_object(repo_root, commit, path)
                if mode != f"10{policy[path]['final_mode']}":
                    raise Denied
        except Denied:
            continue
        matches.append(commit)
    if len(matches) != 1:
        raise Denied
    return matches[0]


def validate_active_task_anchor(
    repo_root: Path,
    *,
    proof: dict[str, Any],
    proof_raw: bytes,
    progress_raw: bytes,
    allowed_status: dict[str, str],
) -> str:
    """Require the clean exact implementation head before authority blocking."""
    check_repository_identity(repo_root)
    anchor = _task_execution_anchor(
        repo_root,
        proof=proof,
        proof_raw=proof_raw,
        progress_raw=progress_raw,
    )
    head = _git(repo_root, "rev-parse", "HEAD").strip().decode()
    origin = _git(repo_root, "rev-parse", "origin/main").strip().decode()
    if head != anchor or origin != anchor or _git_status(repo_root) != allowed_status:
        raise Denied
    return anchor


def validate_authority_block_delivery(
    repo_root: Path,
    *,
    proof: dict[str, Any],
    proof_raw: bytes,
    progress_before_raw: bytes,
    progress_after_raw: bytes,
    revocation_raw: bytes | None,
) -> str:
    """Validate the exact worktree or direct-child authority BLOCKED delivery."""
    check_repository_identity(repo_root)
    anchor = _task_execution_anchor(
        repo_root,
        proof=proof,
        proof_raw=proof_raw,
        progress_raw=progress_before_raw,
    )
    head = _git(repo_root, "rev-parse", "HEAD").strip().decode()
    origin = _git(repo_root, "rev-parse", "origin/main").strip().decode()
    expected_status = {PROGRESS_PATH: "modify"}
    if revocation_raw is not None:
        expected_status[REVOCATION_PATH] = "add"
    if head == anchor:
        if origin != anchor or _git_status(repo_root) != expected_status:
            raise Denied
        if _read(repo_root, PROGRESS_PATH) != progress_after_raw:
            raise Denied
        if revocation_raw is not None and _read(repo_root, REVOCATION_PATH) != revocation_raw:
            raise Denied
        return "WORKTREE"
    parents = _git(repo_root, "rev-list", "--parents", "-n", "1", head).decode().split()
    expected_paths = [PROGRESS_PATH]
    expected_changes = [f"M\t{PROGRESS_PATH}"]
    if revocation_raw is not None:
        expected_paths.append(REVOCATION_PATH)
        expected_changes.append(f"A\t{REVOCATION_PATH}")
    expected_paths.sort()
    expected_changes.sort(key=lambda item: item.split("\t", 1)[1])
    if (
        parents != [head, anchor]
        or origin != head
        or _git_status(repo_root)
        or _git(repo_root, "diff", "--name-only", f"{anchor}..{head}").decode().splitlines()
        != expected_paths
        or _git(
            repo_root,
            "diff",
            "--name-status",
            "--no-renames",
            f"{anchor}..{head}",
        ).decode().splitlines()
        != expected_changes
    ):
        raise Denied
    progress_mode, committed_progress = _git_object(repo_root, head, PROGRESS_PATH)
    if progress_mode != "100644" or committed_progress != progress_after_raw:
        raise Denied
    if revocation_raw is not None:
        revocation_mode, committed_revocation = _git_object(
            repo_root, head, REVOCATION_PATH
        )
        if revocation_mode != "100644" or committed_revocation != revocation_raw:
            raise Denied
    return head


def _git_status(repo_root: Path) -> dict[str, str]:
    return legacy._parse_status_z(
        _git(repo_root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    )


def validate_final_delivery(
    repo_root: Path,
    *,
    preliminary_head: str,
    review_path: str,
    review_raw: bytes,
    progress_raw: bytes,
) -> str:
    """Locate the exact review+ledger delivery without trusting current bytes."""
    if (
        COMMIT.fullmatch(preliminary_head) is None
        or legacy._path(review_path) != review_path
        or not review_path.endswith(".review.json")
        or type(review_raw) is not bytes
        or type(progress_raw) is not bytes
    ):
        raise Denied
    check_repository_identity(repo_root)
    head = _git(repo_root, "rev-parse", "HEAD").strip().decode()
    if COMMIT.fullmatch(head) is None:
        raise Denied
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", preliminary_head, head],
        cwd=repo_root,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if ancestor.returncode or ancestor.stdout or ancestor.stderr:
        raise Denied
    expected_paths = sorted([review_path, PROGRESS_PATH])
    expected_status = [
        ("M" if path == PROGRESS_PATH else "A") + "\t" + path
        for path in expected_paths
    ]
    if head == preliminary_head:
        if _git_status(repo_root) != {review_path: "add", PROGRESS_PATH: "modify"}:
            raise Denied
        if (
            _read(repo_root, review_path) != review_raw
            or _read(repo_root, PROGRESS_PATH) != progress_raw
        ):
            raise Denied
        return "WORKTREE"
    commits = _git(
        repo_root,
        "rev-list",
        "--ancestry-path",
        "--reverse",
        f"{preliminary_head}..{head}",
    ).decode().splitlines()
    if not commits or len(commits) > 128 or any(COMMIT.fullmatch(item) is None for item in commits):
        raise Denied
    matches: list[str] = []
    for commit in commits:
        parents = _git(repo_root, "rev-list", "--parents", "-n", "1", commit).decode().split()
        if parents != [commit, preliminary_head]:
            continue
        changed = _git(
            repo_root, "diff", "--name-only", f"{preliminary_head}..{commit}"
        ).decode().splitlines()
        if changed != expected_paths:
            continue
        status = _git(
            repo_root,
            "diff",
            "--name-status",
            "--no-renames",
            f"{preliminary_head}..{commit}",
        ).decode().splitlines()
        if status != expected_status:
            continue
        try:
            review_mode, historical_review = _git_object(repo_root, commit, review_path)
            progress_mode, historical_progress = _git_object(repo_root, commit, PROGRESS_PATH)
        except Denied:
            continue
        if (
            review_mode == "100644"
            and progress_mode == "100644"
            and historical_review == review_raw
            and historical_progress == progress_raw
        ):
            matches.append(commit)
    if len(matches) != 1:
        raise Denied
    return matches[0]


def _check_protocol_release_commit(repo_root: Path, base: str) -> None:
    check_repository_identity(repo_root)
    _check_predecessor_activation_commit(repo_root)
    if COMMIT.fullmatch(base) is None or base == BRIDGE_BASE:
        raise Denied
    if _git(repo_root, "rev-parse", "HEAD").strip() != base.encode():
        raise Denied
    if _git(repo_root, "rev-parse", "origin/main").strip() != base.encode():
        raise Denied
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BRIDGE_BASE, base],
        cwd=repo_root,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if ancestor.returncode != 0:
        raise Denied
    changed = _git(repo_root, "diff", "--name-only", f"{BRIDGE_BASE}..{base}").decode().splitlines()
    if changed != BRIDGE_PATHS:
        raise Denied
    name_status = _git(
        repo_root, "diff", "--name-status", "--no-renames", f"{BRIDGE_BASE}..{base}"
    ).decode().splitlines()
    modified_paths = {
        ".github/workflows/ci.yml",
        "specs/subject-distillation/development-missions/README.md",
        "tests/test_repo_hygiene_tools.py",
    }
    expected_status = [
        ("M" if path in modified_paths else "A") + "\t" + path
        for path in BRIDGE_PATHS
    ]
    if name_status != expected_status:
        raise Denied
    for path in BRIDGE_PATHS:
        tree_entry = _git(repo_root, "ls-tree", base, "--", path).decode().strip()
        expected_mode = (
            "100755"
            if path.startswith("scripts/") and path.endswith(".py")
            else "100644"
        )
        if not tree_entry.startswith(expected_mode + " blob ") or not tree_entry.endswith(
            "\t" + path
        ):
            raise Denied


def _check_predecessor_activation_commit(repo_root: Path) -> None:
    """Bind V5 to the exact immutable V4 activation delivery."""
    parents = _git(
        repo_root, "rev-list", "--parents", "-n", "1", BRIDGE_BASE
    ).decode().split()
    if parents != [BRIDGE_BASE, V4_PROTOCOL_BASE]:
        raise Denied
    predecessor_path = (
        "specs/subject-distillation/task-authorizations/MISSION-T004-T033.json"
    )
    if _git(
        repo_root,
        "diff",
        "--name-status",
        "--no-renames",
        f"{V4_PROTOCOL_BASE}..{BRIDGE_BASE}",
    ).decode().splitlines() != [f"A\t{predecessor_path}"]:
        raise Denied
    mode, raw = _git_object(repo_root, BRIDGE_BASE, predecessor_path)
    if (
        mode != "100644"
        or hashlib.sha256(raw).hexdigest()
        != PREDECESSOR_IMMUTABLE_HASHES[predecessor_path]
    ):
        raise Denied


def _check_protocol_release(repo_root: Path, base: str) -> None:
    _check_protocol_release_commit(repo_root, base)
    if _git(repo_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise Denied


def check_task_base(
    repo_root: Path,
    base: str,
    proof: dict[str, Any],
    *,
    require_clean: bool,
) -> None:
    check_repository_identity(repo_root)
    if COMMIT.fullmatch(base) is None:
        raise Denied
    if _git(repo_root, "rev-parse", "HEAD").strip() != base.encode():
        raise Denied
    if _git(repo_root, "rev-parse", "origin/main").strip() != base.encode():
        raise Denied
    protocol_base = proof["protocol_base_commit"][4:]
    if COMMIT.fullmatch(protocol_base) is None:
        raise Denied
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", protocol_base, base],
        cwd=repo_root,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if ancestor.returncode != 0:
        raise Denied
    if require_clean and _git(repo_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise Denied


def check_active_protocol_ancestry(repo_root: Path, protocol_base: str) -> None:
    """Bind active work to the reviewed bridge without requiring a clean task tree."""
    if COMMIT.fullmatch(protocol_base) is None:
        raise Denied
    head = _git(repo_root, "rev-parse", "HEAD").strip().decode()
    if COMMIT.fullmatch(head) is None:
        raise Denied
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", protocol_base, head],
        cwd=repo_root,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if ancestor.returncode != 0 or ancestor.stdout or ancestor.stderr:
        raise Denied


def check_task_proof_ancestry(
    repo_root: Path, implementation_base: str, mission_proof: dict[str, Any]
) -> None:
    """Replay one historical task base inside the reviewed protocol lineage."""
    check_repository_identity(repo_root)
    protocol_base = mission_proof["protocol_base_commit"][4:]
    head = _git(repo_root, "rev-parse", "HEAD").strip().decode()
    if any(
        COMMIT.fullmatch(value) is None
        for value in (implementation_base, protocol_base, head)
    ):
        raise Denied
    for ancestor_commit, descendant_commit in (
        (protocol_base, implementation_base),
        (implementation_base, head),
    ):
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor_commit, descendant_commit],
            cwd=repo_root,
            capture_output=True,
            check=False,
            timeout=30,
        )
        if result.returncode or result.stdout or result.stderr:
            raise Denied


def _load_progress(repo_root: Path) -> tuple[dict[str, Any], bytes]:
    raw = _read(repo_root, PROGRESS_PATH)
    value = _parse(raw)
    if raw != canonical(value):
        raise Denied
    return value, raw


def _scope(contract: dict[str, Any], registry_raw: bytes) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "artifact_kind": legacy.v1.SCOPE_KIND,
        "baseline_id": contract["activation"]["baseline_id"],
        "baseline_full_digest": contract["activation"]["baseline_full_digest"],
        "authorized_task": "T-004",
        "allowed_repo_relative_paths": sorted([MISSION_PROOF_PATH, PENDING_PATH]),
        "non_goals": [
            "no.live.private.data",
            "no.release",
            "no.t032.private.operation",
            "no_production_migration",
        ],
        "prohibited_operations": sorted(legacy.v1.verifier.REQUIRED_PROHIBITED),
    }


def _supersession_sha(contract: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(contract["supersession"], newline=False)).hexdigest()


def _derive_proposal(
    repo_root: Path, base: str, issued: datetime
) -> tuple[dict[str, Any], bytes, bytes]:
    contract, contract_raw = load_contract(repo_root)
    _registry, registry_raw = load_registry(repo_root, contract)
    progress, progress_raw = _load_progress(repo_root)
    if (
        len(progress.get("events", [])) != 6
        or hashlib.sha256(progress_raw).hexdigest() != ACTIVATION_PROGRESS_SHA256
        or any(progress["tasks"][f"T-{n:03d}"] != "PENDING" for n in range(4, 34))
    ):
        raise Denied
    inputs = legacy.v1._repo_inputs(os.fspath(repo_root))
    scope = _scope(contract, registry_raw)
    scope_raw = canonical(scope)
    issued_text = _time(issued)
    expires_text = _time(issued + PROPOSAL_VALIDITY)
    receipt = {
        "schema_version": 1,
        "artifact_kind": "subject-distillation-implementation-authorization",
        "baseline_id": contract["activation"]["baseline_id"],
        "baseline_full_digest": contract["activation"]["baseline_full_digest"],
        "authorizing_principal": AUTHORITY,
        "authorized_task": "T-004",
        "scope_sha256": hashlib.sha256(scope_raw).hexdigest(),
        "authorization_verifier_sha256": hashlib.sha256(inputs.verifier_raw).hexdigest(),
        "authorization_schema_sha256": hashlib.sha256(inputs.schema_raw).hexdigest(),
        "issued_at_utc": issued_text,
        "expires_at_utc": expires_text,
    }
    receipt["authorization_id"] = hashlib.sha256(canonical(receipt, newline=False)).hexdigest()
    receipt_raw = canonical(receipt)
    trust = _trust_root(repo_root, contract)
    proposal = {
        "schema_version": 5,
        "artifact_kind": "subject-development-mission-v5-proposal",
        "protocol_decision_id": DECISION_ID,
        "repository": contract["repository"],
        "authorizing_principal": AUTHORITY,
        "protocol_base_commit": base,
        "baseline_id": contract["activation"]["baseline_id"],
        "baseline_full_digest": contract["activation"]["baseline_full_digest"],
        "tasks_sha256": TASKS_SHA256,
        "contract_sha256": hashlib.sha256(contract_raw).hexdigest(),
        "scope_registry_sha256": hashlib.sha256(registry_raw).hexdigest(),
        "supersession_sha256": _supersession_sha(contract),
        "trust_root": trust,
        "trust_root_sha256": hashlib.sha256(canonical(trust, newline=False)).hexdigest(),
        "progress_sequence": 6,
        "progress_sha256": hashlib.sha256(progress_raw).hexdigest(),
        "issued_at_utc": issued_text,
        "expires_at_utc": expires_text,
        "mission_duration_seconds": 7_776_000,
        "receipt_sha256": hashlib.sha256(receipt_raw).hexdigest(),
        "scope_sha256": receipt["scope_sha256"],
        "authorization_id": receipt["authorization_id"],
        "authorization_verifier_sha256": receipt["authorization_verifier_sha256"],
        "authorization_schema_sha256": receipt["authorization_schema_sha256"],
        "mission_proof_path": MISSION_PROOF_PATH,
    }
    proposal["proposal_id"] = hashlib.sha256(canonical(proposal)).hexdigest()
    return proposal, receipt_raw, scope_raw


def _proof_from_proposal(
    proposal: dict[str, Any], recorded: datetime, owner_ref: str
) -> dict[str, Any]:
    if OPAQUE.fullmatch(owner_ref) is None:
        raise Denied
    proof = {
        "schema_version": 5,
        "artifact_kind": "subject-development-mission-v5-proof",
        "status": "PASS",
        "repository": proposal["repository"],
        "authorizing_principal": proposal["authorizing_principal"],
        "protocol_decision_id": proposal["protocol_decision_id"],
        "protocol_base_commit": "git:" + proposal["protocol_base_commit"],
        "baseline_id": proposal["baseline_id"],
        "baseline_full_digest": proposal["baseline_full_digest"],
        "tasks_sha256": proposal["tasks_sha256"],
        "contract_sha256": proposal["contract_sha256"],
        "scope_registry_sha256": proposal["scope_registry_sha256"],
        "supersession_sha256": proposal["supersession_sha256"],
        "trust_root": proposal["trust_root"],
        "trust_root_sha256": proposal["trust_root_sha256"],
        "progress_sequence": proposal["progress_sequence"],
        "progress_sha256": proposal["progress_sha256"],
        "issued_at_utc": proposal["issued_at_utc"],
        "expires_at_utc": proposal["expires_at_utc"],
        "mission_duration_seconds": proposal["mission_duration_seconds"],
        "proposal_id": proposal["proposal_id"],
        "receipt_sha256": proposal["receipt_sha256"],
        "scope_sha256": proposal["scope_sha256"],
        "authorization_id": proposal["authorization_id"],
        "authorization_verifier_sha256": proposal["authorization_verifier_sha256"],
        "authorization_schema_sha256": proposal["authorization_schema_sha256"],
        "mission_proof_path": proposal["mission_proof_path"],
        "recorded_at_utc": _time(recorded),
        "active_from_utc": _time(recorded),
        "mission_not_after_utc": _time(recorded + MISSION_DURATION),
        "owner_confirmation_ref": owner_ref,
    }
    proof["mission_id"] = hashlib.sha256(canonical(proof, newline=False)).hexdigest()
    return proof


def build_unsigned_test_proof(
    contract: dict[str, Any], *, proposal_id: str, receipt_sha256: str, recorded_at_utc: str
) -> dict[str, Any]:
    """Build a deliberately incomplete public mutation used only by tests."""
    root = Path.cwd().absolute()
    trust = _trust_root(root, contract)
    proof = {
        "schema_version": 5,
        "artifact_kind": "subject-development-mission-v5-proof",
        "status": "PASS",
        "repository": contract["repository"],
        "authorizing_principal": AUTHORITY,
        "protocol_decision_id": DECISION_ID,
        "protocol_base_commit": contract["activation"]["bridge_implementation_base_commit"],
        "baseline_id": contract["activation"]["baseline_id"],
        "baseline_full_digest": contract["activation"]["baseline_full_digest"],
        "tasks_sha256": TASKS_SHA256,
        "contract_sha256": hashlib.sha256(canonical(contract)).hexdigest(),
        "scope_registry_sha256": contract["scope_registry_sha256"],
        "supersession_sha256": _supersession_sha(contract),
        "trust_root": trust,
        "trust_root_sha256": hashlib.sha256(canonical(trust, newline=False)).hexdigest(),
        "progress_sequence": 6,
        "progress_sha256": ACTIVATION_PROGRESS_SHA256,
        "issued_at_utc": recorded_at_utc,
        "expires_at_utc": _time(_timestamp(recorded_at_utc) + PROPOSAL_VALIDITY),
        "mission_duration_seconds": 7_776_000,
        "proposal_id": proposal_id,
        "receipt_sha256": receipt_sha256,
        "scope_sha256": "3" * 64,
        "authorization_id": "4" * 64,
        "authorization_verifier_sha256": "5" * 64,
        "authorization_schema_sha256": "6" * 64,
        "mission_proof_path": MISSION_PROOF_PATH,
        "recorded_at_utc": recorded_at_utc,
        "active_from_utc": recorded_at_utc,
        "mission_not_after_utc": _time(_timestamp(recorded_at_utc) + MISSION_DURATION),
        "owner_confirmation_ref": "test-owner-confirmation",
    }
    proof["mission_id"] = hashlib.sha256(canonical(proof, newline=False)).hexdigest()
    return proof


def build_signed_test_proof(contract: dict[str, Any], *, recorded_at_utc: str) -> dict[str, Any]:
    """Build exact public bytes for structural unit tests; never publication authority."""
    root = Path.cwd().absolute()
    issued = _timestamp(recorded_at_utc)
    proposal, _receipt, _scope_raw = _derive_proposal(root, BRIDGE_BASE, issued)
    return _proof_from_proposal(proposal, issued, "test-owner-confirmation")


def derive_task_authorization(
    repo_root: Path,
    mission_proof: dict[str, Any],
    task: str,
    base: str,
    *,
    now_utc: str,
    revocation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from scripts import validate_subject_development_mission_v5 as validator

    validator.validate_mission_proof_value(
        mission_proof, canonical(mission_proof), repo_root, now_utc=now_utc
    )
    check_task_base(repo_root, base, mission_proof, require_clean=True)
    if revocation is not None:
        raise Denied
    contract, _ = load_contract(repo_root)
    registry, _ = load_registry(repo_root, contract)
    if task not in contract["allowed_tasks"] or TASK.fullmatch(task) is None:
        raise Denied
    progress, progress_raw = _load_progress(repo_root)
    number = int(task[2:])
    predecessors_complete = all(
        progress["tasks"][f"T-{index:03d}"] == "COMPLETED" for index in range(1, min(number, 32))
    )
    t032_allows_t033 = task != "T-033" or progress["tasks"]["T-032"] in {
        "BLOCKED",
        "COMPLETED",
    }
    if progress["tasks"][task] != "PENDING" or not predecessors_complete or not t032_allows_t033:
        raise Denied
    history = validator.validate_ledger_value(
        progress,
        repo_root,
        include_delivery_anchor=True,
    )
    if task == "T-004":
        expected_base = validate_mission_activation_delivery(
            repo_root,
            protocol_base=mission_proof["protocol_base_commit"][4:],
            mission_raw=canonical(mission_proof),
        )
    else:
        expected_base = history["delivery_anchor"]
        if type(expected_base) is not str or COMMIT.fullmatch(expected_base) is None:
            raise Denied
    if base != expected_base:
        raise Denied
    descriptor = registry["tasks"][number - 4]
    value = {
        "schema_version": 5,
        "artifact_kind": "subject-task-authorization-v5",
        "status": "PASS",
        "mission_id": mission_proof["mission_id"],
        "mission_proof_sha256": hashlib.sha256(canonical(mission_proof)).hexdigest(),
        "authorized_task": task,
        "implementation_base_commit": "git:" + base,
        "scope_registry_sha256": contract["scope_registry_sha256"],
        "task_header_sha256": descriptor["task_header_sha256"],
        "descriptor_sha256": hashlib.sha256(canonical(descriptor, newline=False)).hexdigest(),
        "progress_sequence": len(progress["events"]),
        "progress_sha256": hashlib.sha256(progress_raw).hexdigest(),
        "required_read_files": required_read_files(repo_root, descriptor),
        "derived_at_utc": now_utc,
        "proof_repo_relative_path": (f"specs/subject-distillation/task-authorizations/{task}.json"),
    }
    value["task_authorization_id"] = hashlib.sha256(canonical(value, newline=False)).hexdigest()
    return value


@dataclass
class Runtime:
    now: Callable[[], datetime] = field(
        default_factory=lambda: lambda: datetime.now(timezone.utc).replace(microsecond=0)
    )


def _propose(values: dict[str, str], runtime: Runtime) -> bytes:
    base = values["--implementation-base-commit"]
    repo_root = Path.cwd().absolute()
    _check_protocol_release(repo_root, base)
    proposal, _receipt, _scope_raw = _derive_proposal(repo_root, base, runtime.now())
    return canonical(proposal)


def _parse_arguments(argv: Sequence[str]) -> tuple[str, dict[str, str]]:
    if not argv or argv[0] not in {"propose-mission", "verify-confirmed"}:
        raise Denied
    mode = argv[0]
    flags = {"--implementation-base-commit"}
    if mode == "verify-confirmed":
        flags |= {
            "--proposal-json",
            "--expected-proposal-id",
            "--expected-receipt-sha256",
            "--owner-confirmation-ref",
        }
    required = flags | {"--json"}
    values: dict[str, str] = {}
    seen: set[str] = set()
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
        values[flag] = argv[index + 1]
        index += 2
    if seen != required or set(values) != flags:
        raise Denied
    return mode, values


def _recoverable_mission_proof_raw(
    repo_root: Path,
    proposal: dict[str, Any],
    owner_ref: str,
) -> bytes:
    """Validate the only dirty mission-proof publication states accepted on retry."""
    allowed = {PENDING_PATH, MISSION_PROOF_PATH}
    status = legacy._parse_status_z(
        legacy.v1._git(["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    )
    present = {path for path in allowed if legacy._repo_entry_exists(repo_root, path)}
    if not present or set(status) != present or set(status.values()) != {"add"}:
        raise Denied
    raws: dict[str, bytes] = {}
    identities: dict[str, tuple[int, int, int, int, int, int, int]] = {}
    for path in present:
        raw, identity = legacy._read_repo_file(repo_root, path)
        mode = stat.S_IMODE(identity[2])
        if path == PENDING_PATH:
            if mode not in {0o600, 0o644} or identity[3] not in {1, 2}:
                raise Denied
        elif mode != 0o644 or identity[3] not in {1, 2}:
            raise Denied
        raws[path] = raw
        identities[path] = identity
    if len(set(raws.values())) != 1:
        raise Denied
    if present == allowed:
        pending = identities[PENDING_PATH]
        final = identities[MISSION_PROOF_PATH]
        if pending[:2] != final[:2] or pending[3] != 2 or final[3] != 2:
            raise Denied
    elif present == {PENDING_PATH}:
        if identities[PENDING_PATH][3] != 1:
            raise Denied
    elif present == {MISSION_PROOF_PATH}:
        if identities[MISSION_PROOF_PATH][3] != 1:
            raise Denied
    else:
        raise Denied
    raw = next(iter(raws.values()))
    value = _parse(raw)
    recorded = _timestamp(value.get("recorded_at_utc"))
    issued = _timestamp(proposal["issued_at_utc"])
    expires = _timestamp(proposal["expires_at_utc"])
    if not issued <= recorded < expires:
        raise Denied
    if raw != canonical(value) or raw != canonical(
        _proof_from_proposal(proposal, recorded, owner_ref)
    ):
        raise Denied
    return raw


def _verify_confirmed(_values: dict[str, str], _runtime: Runtime) -> bytes:
    values = _values
    runtime = _runtime
    base = values["--implementation-base-commit"]
    if (
        COMMIT.fullmatch(base) is None
        or HEX64.fullmatch(values["--expected-proposal-id"]) is None
        or HEX64.fullmatch(values["--expected-receipt-sha256"]) is None
        or OPAQUE.fullmatch(values["--owner-confirmation-ref"]) is None
    ):
        raise Denied
    raw = values["--proposal-json"].encode("utf-8")
    proposal = _parse(raw)
    if type(proposal) is not dict or raw != canonical(proposal):
        raise Denied
    issued = _timestamp(proposal.get("issued_at_utc"))
    expires = _timestamp(proposal.get("expires_at_utc"))
    now = runtime.now()
    if (
        type(now) is not datetime
        or now.tzinfo != timezone.utc
        or expires - issued != PROPOSAL_VALIDITY
        or not issued <= now.replace(microsecond=0) < expires
        or proposal.get("protocol_base_commit") != base
        or proposal.get("proposal_id") != values["--expected-proposal-id"]
        or proposal.get("receipt_sha256") != values["--expected-receipt-sha256"]
    ):
        raise Denied
    repo_root = Path.cwd().absolute()
    derived, receipt_raw, scope_raw = _derive_proposal(repo_root, base, issued)
    if not legacy.v1.verifier._exact_equal(proposal, derived):
        raise Denied
    state = legacy._repository_state(legacy.Runtime())
    if state.head != base or Path(state.repo_root) != repo_root:
        raise Denied
    recovery_raw = (
        None
        if state.clean
        else _recoverable_mission_proof_raw(repo_root, proposal, values["--owner-confirmation-ref"])
    )
    _check_protocol_release_commit(repo_root, base)
    v1_runtime = legacy.v1.Runtime()
    with legacy.v1._authorization_lock(
        state.repo_root, "subject-development-mission-v5", base, v1_runtime
    ) as audit_lock:

        def audit_clean() -> None:
            current = legacy._repository_state(legacy.Runtime())
            if current.repo_root != state.repo_root or current.head != state.head:
                raise Denied
            _check_protocol_release_commit(repo_root, base)
            if recovery_raw is None:
                if not current.clean:
                    raise Denied
            elif (
                _recoverable_mission_proof_raw(
                    repo_root, proposal, values["--owner-confirmation-ref"]
                )
                != recovery_raw
            ):
                raise Denied

        audit_clean()
        external = legacy.v1._external_root(v1_runtime, state.repo_root)
        slot = legacy.v1.LifecycleSlot()
        failure: BaseException | None = None
        cleanup_ok = True
        verifier_output = canonical(
            {
                "authorization_id": proposal["authorization_id"],
                "authorized_task": "T-004",
                "baseline_id": proposal["baseline_id"],
                "status": "PASS",
            }
        )
        with legacy.v1._signal_boundary() as signals:
            try:
                audit_lock()
                legacy.v1._new_lifecycle(
                    external, receipt_raw, scope_raw, v1_runtime, signals, slot
                )
                lifecycle = slot.value
                if lifecycle is None:
                    raise InternalFailure
                legacy.v1._audit_lifecycle(lifecycle)
                legacy.v1._run_verifier(
                    lifecycle,
                    state.repo_root,
                    proposal["receipt_sha256"],
                    "T-004",
                    verifier_output,
                    v1_runtime,
                )
                audit_lock()
                audit_clean()
                legacy.v1._audit_lifecycle(lifecycle)
            except (
                Denied,
                legacy.v1.Denied,
                legacy.v1.InternalFailure,
                legacy.v1.Interrupted,
                legacy.v1.PrivateCleanupRequired,
            ) as exc:
                failure = exc
            except Exception:  # noqa: BLE001 - fixed no-echo boundary
                failure = InternalFailure()
            finally:
                signals.cleanup_active = True
                lifecycle = slot.value
                if lifecycle is not None:
                    cleanup_ok = legacy.v1._cleanup(lifecycle, v1_runtime)
                    legacy.v1._close_lifecycle(lifecycle)
                    slot.value = None
        if not cleanup_ok or isinstance(failure, legacy.v1.PrivateCleanupRequired):
            raise legacy.v1.PrivateCleanupRequired
        if failure is not None:
            raise failure
        audit_clean()
        if recovery_raw is None:
            recorded = runtime.now().replace(microsecond=0)
            if not issued <= recorded < expires:
                raise Denied
            proof_raw = canonical(
                _proof_from_proposal(proposal, recorded, values["--owner-confirmation-ref"])
            )
        else:
            proof_raw = recovery_raw

        def audit_publication() -> None:
            current = legacy._repository_state(legacy.Runtime())
            if current.repo_root != state.repo_root or current.head != state.head:
                raise Denied
            status = legacy._parse_status_z(
                legacy.v1._git(["status", "--porcelain=v1", "-z", "--untracked-files=all"])
            )
            if not status or not set(status) <= {PENDING_PATH, MISSION_PROOF_PATH}:
                raise Denied
            _check_protocol_release_with_publication(repo_root, base, proof_raw)

        legacy._publish_proof(
            repo_root,
            MISSION_PROOF_PATH,
            proof_raw,
            audit=audit_publication,
        )
        audit_publication()
        return proof_raw


def _check_protocol_release_with_publication(repo_root: Path, base: str, proof_raw: bytes) -> None:
    _check_protocol_release_commit(repo_root, base)
    for path in (PENDING_PATH, MISSION_PROOF_PATH):
        if not legacy._repo_entry_exists(repo_root, path):
            continue
        raw, identity = legacy._read_repo_file(repo_root, path)
        mode = os.stat(repo_root / path, follow_symlinks=False).st_mode & 0o777
        if raw != proof_raw or mode not in {0o600, 0o644} or identity[3] not in {1, 2}:
            raise Denied


def main(argv: Sequence[str] | None = None, *, _runtime: Runtime | None = None) -> int:
    try:
        mode, values = _parse_arguments(sys.argv[1:] if argv is None else argv)
        runtime = _runtime if _runtime is not None else Runtime()
        output = (
            _propose(values, runtime)
            if mode == "propose-mission"
            else _verify_confirmed(values, runtime)
        )
    except legacy.v1.PrivateCleanupRequired:
        sys.stdout.write(CLEANUP_REQUIRED)
        return 4
    except (Denied, legacy.v1.Denied, legacy.v1.VERIFIER_DENIED):
        sys.stderr.write(DENY_TEXT)
        return 2
    except Exception:  # noqa: BLE001 - fixed no-echo boundary
        sys.stderr.write(ERROR_TEXT)
        return 3
    sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
