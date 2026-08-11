#!/usr/bin/env python3
"""Validate the strict Subject Distillation implementation progress ledger."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import re
import selectors
import signal
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import validate_subject_baseline as baseline
    import validate_subject_evidence as evidence
    import verify_subject_implementation_authorization as authorization
except ImportError:  # pragma: no cover - import path used by test loaders
    from scripts import validate_subject_baseline as baseline
    from scripts import validate_subject_evidence as evidence
    from scripts import verify_subject_implementation_authorization as authorization


DENY_TEXT = "SUBJECT_PROGRESS_DENY\n"
ERROR_TEXT = "SUBJECT_PROGRESS_ERROR\n"
TASK_IDS = tuple(f"T-{number:03d}" for number in range(1, 34))
STATES = {"PENDING", "IN_PROGRESS", "BLOCKED", "COMPLETED"}
TRANSITIONS = {
    ("PENDING", "IN_PROGRESS"),
    ("PENDING", "BLOCKED"),
    ("IN_PROGRESS", "BLOCKED"),
    ("IN_PROGRESS", "COMPLETED"),
    ("BLOCKED", "IN_PROGRESS"),
}
BLOCKER = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
HEX64 = re.compile(r"[0-9a-f]{64}")
PRIVATE_CONFIG_KIND = "subject-distillation-private-shadow-verifier-config"
PRIVATE_HMAC_DOMAIN = b"vault-subject-private-shadow-release-v1\x00"
PRIVATE_STDOUT_MAX = 85
PRIVATE_STDERR_MAX = 96
PRIVATE_CHILD_TIMEOUT_SECONDS = 300.0
PRIVATE_CHILD_TERMINATE_GRACE_SECONDS = 5.0
T001_COMPLETION_PATHS = (
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
    "specs/subject-distillation/implementation-progress.schema.json",
    "tests/test_subject_baseline_control.py",
    "tests/test_subject_progress.py",
)


Denied = evidence.Denied


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


@dataclass(frozen=True)
class _PrivateHandle:
    fd: int
    identity: tuple[int, int, int, int, int, int, int]
    chain: tuple[
        tuple[int, str, tuple[int, int, int, int, int, int, int]], ...
    ]


@dataclass(frozen=True)
class _PrivateChildResult:
    returncode: int
    stdout: bytes
    stderr: bytes


def _open_private_chain(
    start_fd: int,
    parts: tuple[str, ...],
    owned: list[int],
    *,
    final_directory: bool = False,
) -> _PrivateHandle:
    parent = start_fd
    chain: list[
        tuple[int, str, tuple[int, int, int, int, int, int, int]]
    ] = []
    try:
        for index, part in enumerate(parts):
            directory = index < len(parts) - 1 or final_directory
            fd = os.open(
                part,
                authorization._flags(directory=directory),
                dir_fd=parent,
            )
            owned.append(fd)
            info = os.fstat(fd)
            if directory and not stat.S_ISDIR(info.st_mode):
                raise OSError
            if not directory and not stat.S_ISREG(info.st_mode):
                raise OSError
            identity = _strong_identity(info)
            chain.append((parent, part, identity))
            parent = fd
        return _PrivateHandle(parent, chain[-1][2], tuple(chain))
    except (OSError, ValueError):
        raise Denied from None


def _audit_private_inputs(handles: list[_PrivateHandle]) -> None:
    try:
        for handle in handles:
            if _strong_identity(os.fstat(handle.fd)) != handle.identity:
                raise Denied
            for parent, name, before in handle.chain:
                current = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if _strong_identity(current) != before:
                    raise Denied
    except OSError:
        raise Denied from None


class _Parser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise Denied


def _repo_ref_schema() -> dict[str, Any]:
    return {
        "oneOf": [
            evidence._closed(
                {
                    "kind": evidence._string(const="repo_file"),
                    "path": evidence._string(pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$"),
                    "sha256": evidence._string(pattern="^[0-9a-f]{64}$"),
                }
            ),
            evidence._closed(
                {
                    "kind": evidence._string(const="opaque"),
                    "id": evidence._string(pattern="^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
                }
            ),
        ]
    }


def _expected_schema() -> dict[str, Any]:
    event = evidence._closed(
        {
            "sequence": evidence._integer(1, 4_096),
            "task_id": {"type": "string", "enum": list(TASK_IDS)},
            "from": {"type": "string", "enum": sorted(STATES)},
            "to": {"type": "string", "enum": sorted(STATES)},
            "at_utc": evidence._string(pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"),
            "evidence_refs": {
                "type": "array",
                "items": _repo_ref_schema(),
                "minItems": 0,
                "maxItems": 16,
            },
            "blocker": {
                "type": ["string", "null"],
                "pattern": "^[A-Z][A-Z0-9_]{0,63}$",
            },
        }
    )
    schema = evidence._closed(
        {
            "schema_version": {"type": "integer", "const": 1},
            "baseline_id": evidence._string(pattern="^[0-9a-f]{16}$"),
            "baseline_full_digest": evidence._string(pattern="^[0-9a-f]{64}$"),
            "tasks_sha256": evidence._string(pattern="^[0-9a-f]{64}$"),
            "updated_at_utc": evidence._string(pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"),
            "tasks": evidence._closed(
                {task: {"type": "string", "enum": sorted(STATES)} for task in TASK_IDS}
            ),
            "events": {
                "type": "array",
                "items": event,
                "minItems": 1,
                "maxItems": 4_096,
            },
        }
    )
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = (
        "https://vault-agent-memory.invalid/subject-distillation/"
        "implementation-progress.schema.json"
    )
    return schema


def _load_schema(path: Path) -> dict[str, Any]:
    value, raw = evidence._load_json(path)
    expected = _expected_schema()
    if type(value) is not dict or value != expected or raw != evidence._canonical(expected):
        raise Denied
    return value


def _validate_repo_path(repo_root: Path, path: str, digest: str) -> None:
    if (
        type(path) is not str
        or len(path) > 256
        or path.startswith("/")
        or "\\" in path
        or any(part in {"", ".", ".."} for part in path.split("/"))
        or HEX64.fullmatch(digest) is None
    ):
        raise Denied
    owned: list[int] = []
    try:
        root_fd = os.open(os.fspath(repo_root), authorization._flags(directory=True))
        owned.append(root_fd)
        handle = authorization._open_chain(root_fd, tuple(path.split("/")), owned)
        authorization._audit([handle])
        info = os.fstat(handle.fd)
        if not stat.S_ISREG(info.st_mode):
            raise Denied
        before = os.fstat(handle.fd)
        if before.st_size > 16_777_216:
            raise Denied
        chunks: list[bytes] = []
        remaining = 16_777_217
        while remaining:
            chunk = os.read(handle.fd, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(handle.fd)
        authorization._audit([handle])
        if (
            len(raw) > 16_777_216
            or len(raw) != before.st_size
            or authorization._identity(before) != authorization._identity(after)
            or hashlib.sha256(raw).hexdigest() != digest
        ):
            raise Denied
    except (OSError, authorization.Denied):
        raise Denied from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _validate_ref(repo_root: Path, value: Any) -> None:
    if type(value) is not dict:
        raise Denied
    if set(value) == {"kind", "path", "sha256"} and value["kind"] == "repo_file":
        _validate_repo_path(repo_root, value["path"], value["sha256"])
    elif set(value) == {"kind", "id"} and value["kind"] == "opaque":
        if type(value["id"]) is not str or OPAQUE.fullmatch(value["id"]) is None:
            raise Denied
    else:
        raise Denied


def _dependencies_allow(task_id: str, states: dict[str, str]) -> bool:
    number = int(task_id[2:])
    if number == 1:
        return True
    if number == 33:
        return all(states[f"T-{index:03d}"] == "COMPLETED" for index in range(1, 32)) and states["T-032"] in {"COMPLETED", "BLOCKED"}
    return all(states[f"T-{index:03d}"] == "COMPLETED" for index in range(1, number))


def _open_private_inputs(
    repo_root: Path,
    values: tuple[str, str, str, str],
) -> tuple[list[_PrivateHandle], list[bytes], list[int]]:
    owned: list[int] = []
    handles: list[_PrivateHandle] = []
    raws: list[bytes] = []
    try:
        anchor = os.open("/", authorization._flags(directory=True))
        owned.append(anchor)
        repo = _open_private_chain(
            anchor,
            authorization._absolute_parts(os.fspath(repo_root)),
            owned,
            final_directory=True,
        )
        for value in values:
            if (
                type(value) is not str
                or not value
                or not os.path.isabs(value)
                or os.path.normpath(value) != value
                or os.path.commonpath([value, os.fspath(repo_root)])
                == os.fspath(repo_root)
            ):
                raise Denied
            handle = _open_private_chain(
                anchor,
                authorization._absolute_parts(value),
                owned,
            )
            info = os.fstat(handle.fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise Denied
            before = os.fstat(handle.fd)
            if before.st_size > 16_777_216:
                raise Denied
            chunks: list[bytes] = []
            remaining = 16_777_217
            while remaining:
                chunk = os.read(handle.fd, min(65_536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            after = os.fstat(handle.fd)
            if (
                len(raw) > 16_777_216
                or len(raw) != before.st_size
                or authorization._identity(before) != authorization._identity(after)
            ):
                raise Denied
            handles.append(handle)
            raws.append(raw)
        _audit_private_inputs([repo, *handles])
        return handles, raws, owned
    except (Denied, OSError, ValueError, authorization.Denied):
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass
        raise Denied from None


def _private_config_keys(raw: bytes) -> dict[str, bytes]:
    if type(raw) is not bytes or not 1 <= len(raw) <= 65_536:
        raise Denied
    try:
        value = authorization._parse(raw)
    except authorization.Denied:
        raise Denied from None
    if (
        type(value) is not dict
        or set(value) != {"schema_version", "artifact_kind", "keys"}
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["artifact_kind"] != PRIVATE_CONFIG_KIND
        or type(value["keys"]) is not list
        or not 1 <= len(value["keys"]) <= 64
        or raw != authorization._canonical(value, newline=False)
    ):
        raise Denied
    result: dict[str, bytes] = {}
    previous: str | None = None
    for entry in value["keys"]:
        if type(entry) is not dict or set(entry) != {
            "key_id",
            "hmac_sha256_key_hex",
        }:
            raise Denied
        key_id = entry["key_id"]
        key_hex = entry["hmac_sha256_key_hex"]
        if (
            type(key_id) is not str
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}", key_id) is None
            or previous is not None
            and key_id <= previous
            or type(key_hex) is not str
            or HEX64.fullmatch(key_hex) is None
        ):
            raise Denied
        try:
            key = bytes.fromhex(key_hex)
        except ValueError:
            raise Denied from None
        if len(key) != 32:
            raise Denied
        result[key_id] = key
        previous = key_id
    return result


def _private_receipt_digest(receipt_raw: bytes, config_raw: bytes) -> str:
    try:
        receipt = authorization._parse(receipt_raw)
    except authorization.Denied:
        raise Denied from None
    if receipt_raw != evidence._canonical(receipt):
        raise Denied
    receipt_keys = {
        "schema_version",
        "artifact_kind",
        "verdict",
        "gate_version",
        "scorecard_sha256",
        "manifest_sha256",
        "subject_controller_signoff_id",
        "fresh_reviewer_signoff_id",
        "created_at_utc",
        "key_id",
        "receipt_hmac_sha256",
    }
    if (
        type(receipt) is not dict
        or set(receipt) != receipt_keys
        or type(receipt["schema_version"]) is not int
        or receipt["schema_version"] != 1
        or receipt["artifact_kind"] != "private-shadow-release"
        or receipt["verdict"] != "PASS"
        or any(
            type(receipt[key]) is not str or OPAQUE.fullmatch(receipt[key]) is None
            for key in (
                "gate_version",
                "subject_controller_signoff_id",
                "fresh_reviewer_signoff_id",
            )
        )
        or receipt["subject_controller_signoff_id"]
        == receipt["fresh_reviewer_signoff_id"]
        or any(
            type(receipt[key]) is not str or HEX64.fullmatch(receipt[key]) is None
            for key in (
                "scorecard_sha256",
                "manifest_sha256",
                "receipt_hmac_sha256",
            )
        )
        or type(receipt["key_id"]) is not str
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}", receipt["key_id"])
        is None
    ):
        raise Denied
    evidence._timestamp(receipt["created_at_utc"])
    keys = _private_config_keys(config_raw)
    key = keys.get(receipt["key_id"])
    if key is None:
        raise Denied
    without_hmac = dict(receipt)
    supplied = without_hmac.pop("receipt_hmac_sha256")
    message = PRIVATE_HMAC_DOMAIN + authorization._canonical(
        without_hmac, newline=False
    )
    expected = hmac.new(key, message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, supplied):
        raise Denied
    return hashlib.sha256(receipt_raw).hexdigest()


def _terminate_private_child(
    child: subprocess.Popen[bytes], *, grace_seconds: float
) -> None:
    def group_exists() -> bool:
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            raise Denied from None
        return True

    def wait_until(deadline: float) -> bool:
        while group_exists():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            if child.poll() is None:
                try:
                    child.wait(timeout=min(0.02, remaining))
                except subprocess.TimeoutExpired:
                    pass
            time.sleep(min(0.01, remaining))
        if child.poll() is None:
            try:
                child.wait(timeout=max(0.01, deadline - time.monotonic()))
            except (OSError, subprocess.TimeoutExpired):
                raise Denied from None
        return True

    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except OSError:
        raise Denied from None
    if wait_until(time.monotonic() + grace_seconds):
        return
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError:
        raise Denied from None
    if not wait_until(time.monotonic() + grace_seconds):
        raise Denied


def _private_group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        raise Denied from None
    return True


def _descriptor_executable(fd: int) -> str:
    if type(fd) is not int or fd < 0:
        raise Denied
    prefix = "/proc/self/fd" if sys.platform.startswith("linux") else "/dev/fd"
    if not os.path.isdir(prefix):
        raise Denied
    return f"{prefix}/{fd}"


def _run_private_child(
    argv: list[str],
    *,
    cwd: Path | None = None,
    executable_fd: int | None = None,
    timeout_seconds: float = PRIVATE_CHILD_TIMEOUT_SECONDS,
    terminate_grace_seconds: float = PRIVATE_CHILD_TERMINATE_GRACE_SECONDS,
) -> _PrivateChildResult:
    if (
        type(argv) is not list
        or not argv
        or any(type(item) is not str or not item for item in argv)
        or type(timeout_seconds) is not float
        or timeout_seconds <= 0
        or type(terminate_grace_seconds) is not float
        or terminate_grace_seconds <= 0
        or executable_fd is not None
        and (type(executable_fd) is not int or executable_fd < 0)
    ):
        raise Denied
    child: subprocess.Popen[bytes] | None = None
    selector = selectors.DefaultSelector()
    stdout = bytearray()
    stderr = bytearray()
    failed = True
    try:
        child = subprocess.Popen(
            argv,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            start_new_session=True,
            executable=(
                _descriptor_executable(executable_fd)
                if executable_fd is not None
                else None
            ),
            pass_fds=(executable_fd,) if executable_fd is not None else (),
        )
        if child.stdout is None or child.stderr is None:
            raise Denied
        selector.register(child.stdout, selectors.EVENT_READ, (stdout, PRIVATE_STDOUT_MAX))
        selector.register(child.stderr, selectors.EVENT_READ, (stderr, PRIVATE_STDERR_MAX))
        deadline = time.monotonic() + timeout_seconds
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise Denied
            ready = selector.select(remaining)
            if not ready:
                raise Denied
            for key, _mask in ready:
                target, limit = key.data
                chunk = os.read(key.fd, min(4096, limit + 1 - len(target)))
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                target.extend(chunk)
                if len(target) > limit:
                    raise Denied
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise Denied
        try:
            returncode = child.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            raise Denied from None
        if _private_group_exists(child.pid):
            _terminate_private_child(
                child, grace_seconds=terminate_grace_seconds
            )
            raise Denied
        failed = False
        return _PrivateChildResult(returncode, bytes(stdout), bytes(stderr))
    except (Denied, OSError, ValueError, subprocess.SubprocessError):
        raise Denied from None
    finally:
        cleanup_failed = False
        if failed and child is not None:
            try:
                _terminate_private_child(
                    child, grace_seconds=terminate_grace_seconds
                )
            except (Denied, OSError, ValueError, subprocess.SubprocessError):
                cleanup_failed = True
        try:
            selector.close()
        except (OSError, ValueError):
            cleanup_failed = True
        if child is not None:
            for stream in (child.stdout, child.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except (OSError, ValueError):
                        cleanup_failed = True
        if failed or cleanup_failed:
            stdout.clear()
            stderr.clear()
        if cleanup_failed:
            raise Denied from None


def _private_gate(
    value: dict[str, Any],
    attestation: dict[str, Any],
    private_inputs: tuple[str | None, str | None, str | None, str | None],
    repo_root: Path,
) -> None:
    verifier, gate, config, receipt_path = private_inputs
    if value["tasks"]["T-032"] == "BLOCKED":
        if any(item is not None for item in private_inputs):
            raise Denied
        if (
            attestation["release_label"] != "experimental"
            or attestation["private_shadow_receipt_sha256"] is not None
        ):
            raise Denied
        return
    if value["tasks"]["T-032"] != "COMPLETED" or any(
        type(item) is not str or not item for item in private_inputs
    ):
        raise Denied
    assert verifier is not None and gate is not None and config is not None
    assert receipt_path is not None
    exact_inputs = (verifier, gate, config, receipt_path)
    handles, raws, owned = _open_private_inputs(repo_root, exact_inputs)
    try:
        verifier_info = os.fstat(handles[0].fd)
        config_info = os.fstat(handles[2].fd)
        if (
            not stat.S_ISREG(verifier_info.st_mode)
            or stat.S_IMODE(verifier_info.st_mode) & 0o111 == 0
            or not stat.S_ISREG(config_info.st_mode)
            or stat.S_IMODE(config_info.st_mode) != 0o600
            or config_info.st_nlink != 1
        ):
            raise Denied
        digest = _private_receipt_digest(raws[3], raws[2])
        completed = _run_private_child(
            [
                verifier,
                "reopen-and-verify-release-receipt",
                "--gate-input",
                gate,
                "--verifier-config",
                config,
                "--release-receipt",
                receipt_path,
                "--public-handoff-output",
                "-",
            ],
            cwd=repo_root,
            executable_fd=handles[0].fd,
        )
        _audit_private_inputs(handles)
    except (Denied, OSError, authorization.Denied):
        raise Denied from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass
    if (
        completed.returncode != 0
        or completed.stderr != b""
        or re.fullmatch(b"private-shadow-pass:[0-9a-f]{64}\\n", completed.stdout)
        is None
    ):
        raise Denied
    if (
        completed.stdout != f"private-shadow-pass:{digest}\n".encode("ascii")
        or attestation["release_label"] != "stable"
        or attestation["private_shadow_receipt_sha256"] != digest
    ):
        raise Denied
    t032 = [
        event
        for event in value["events"]
        if event["task_id"] == "T-032" and event["to"] == "COMPLETED"
    ]
    if len(t032) != 1 or t032[0]["evidence_refs"] != [
        {"kind": "opaque", "id": f"private-shadow-pass:{digest}"}
    ]:
        raise Denied


def _final_gate(
    value: dict[str, Any],
    *,
    repo_root: Path,
    manifest_result: dict[str, str],
    private_inputs: tuple[str | None, str | None, str | None, str | None],
) -> None:
    baseline_id = manifest_result["baseline_id"]
    attestation_path = (
        f"specs/subject-distillation/evidence/{baseline_id}/attestation.json"
    )
    final_event = value["events"][-1]
    attestation_raw = evidence._read_file(repo_root / attestation_path)
    expected_ref = {
        "kind": "repo_file",
        "path": attestation_path,
        "sha256": hashlib.sha256(attestation_raw).hexdigest(),
    }
    if (
        final_event["task_id"] != "T-033"
        or final_event["to"] != "COMPLETED"
        or final_event["evidence_refs"] != [expected_ref]
    ):
        raise Denied
    evidence.validate(
        repo_root / "specs/subject-distillation/baseline-manifest.json",
        repo_root / f"specs/subject-distillation/evidence/{baseline_id}",
        [
            "environment",
            "unit",
            "fixture",
            "surface",
            "legacy",
            "migration",
            "backup-restore",
            "fresh-review",
            "attestation",
        ],
        require_reviewed_tree_hash_match=True,
    )
    attestation, _raw = evidence._load_json(repo_root / attestation_path)
    if type(attestation) is not dict:
        raise Denied
    _private_gate(value, attestation, private_inputs, repo_root)


def _authorization_context(
    repo_root: Path,
    manifest_result: dict[str, str],
) -> tuple[datetime, str]:
    manifest_path = repo_root / "specs/subject-distillation/baseline-manifest.json"
    manifest, current_result = evidence._manifest(repo_root, manifest_path)
    if current_result != manifest_result:
        raise Denied
    environment_path = (
        repo_root
        / "specs/subject-distillation/evidence"
        / manifest_result["baseline_id"]
        / "environment.json"
    )
    environment, _raw = evidence._load_json(environment_path)
    if type(environment) is not dict:
        raise Denied
    evidence._validate_environment(
        repo_root,
        environment,
        manifest,
        evidence._expected_schemas()["environment"],
    )
    proof = environment["implementation_authorization"]
    return (
        evidence._timestamp(proof["recorded_at_utc"]),
        proof["authorization_id"],
    )


def _validate_t001_completion_refs(
    refs: list[Any], *, baseline_id: str, authorization_id: str
) -> None:
    expected_paths = tuple(
        sorted(path.format(baseline_id=baseline_id) for path in T001_COMPLETION_PATHS)
    )
    repo_paths = tuple(
        sorted(
            item["path"]
            for item in refs
            if type(item) is dict and item.get("kind") == "repo_file"
        )
    )
    opaque_ids = [
        item["id"]
        for item in refs
        if type(item) is dict and item.get("kind") == "opaque"
    ]
    if repo_paths != expected_paths or len(opaque_ids) != 2:
        raise Denied
    if f"t001-authorization:{authorization_id}" not in opaque_ids:
        raise Denied
    review_ids = [
        value
        for value in opaque_ids
        if re.fullmatch(r"t001-review:[0-9a-f]{64}", value) is not None
    ]
    if len(review_ids) != 1:
        raise Denied


def validate_value(
    value: Any,
    *,
    repo_root: Path,
    manifest_result: dict[str, str],
    tasks_sha256: str,
    private_inputs: tuple[str | None, str | None, str | None, str | None] = (
        None,
        None,
        None,
        None,
    ),
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "baseline_id",
        "baseline_full_digest",
        "tasks_sha256",
        "updated_at_utc",
        "tasks",
        "events",
    }:
        raise Denied
    evidence._scan_public(value)
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise Denied
    if value["baseline_id"] != manifest_result["baseline_id"] or value["baseline_full_digest"] != manifest_result["full_digest"] or value["tasks_sha256"] != tasks_sha256:
        raise Denied
    if type(value["tasks"]) is not dict or tuple(sorted(value["tasks"])) != TASK_IDS:
        raise Denied
    if any(type(state) is not str or state not in STATES for state in value["tasks"].values()):
        raise Denied
    events = value["events"]
    if type(events) is not list or not events or len(events) > 4_096:
        raise Denied
    authorization_recorded_at, authorization_id = _authorization_context(
        repo_root, manifest_result
    )
    states = {task: "PENDING" for task in TASK_IDS}
    previous_time = None
    for sequence, event in enumerate(events, 1):
        if type(event) is not dict or set(event) != {
            "sequence", "task_id", "from", "to", "at_utc", "evidence_refs", "blocker"
        }:
            raise Denied
        if type(event["sequence"]) is not int or event["sequence"] != sequence:
            raise Denied
        task_id = event["task_id"]
        before, after = event["from"], event["to"]
        if task_id not in TASK_IDS or states[task_id] != before or (before, after) not in TRANSITIONS or before == "COMPLETED":
            raise Denied
        when = evidence._timestamp(event["at_utc"])
        if sequence == 1 and when < authorization_recorded_at:
            raise Denied
        if previous_time is not None and when < previous_time:
            raise Denied
        previous_time = when
        refs = event["evidence_refs"]
        if type(refs) is not list or len(refs) > 16:
            raise Denied
        canonical_refs = [evidence._canonical(item) for item in refs]
        if canonical_refs != sorted(canonical_refs) or len(canonical_refs) != len(set(canonical_refs)):
            raise Denied
        for item in refs:
            _validate_ref(repo_root, item)
        if task_id == "T-001" and after == "COMPLETED":
            _validate_t001_completion_refs(
                refs,
                baseline_id=manifest_result["baseline_id"],
                authorization_id=authorization_id,
            )
        if after == "BLOCKED":
            if type(event["blocker"]) is not str or BLOCKER.fullmatch(event["blocker"]) is None:
                raise Denied
        elif event["blocker"] is not None:
            raise Denied
        if after == "COMPLETED" and not refs:
            raise Denied
        if after in {"IN_PROGRESS", "COMPLETED"} and not _dependencies_allow(task_id, states):
            raise Denied
        states[task_id] = after
        if sum(state == "IN_PROGRESS" for state in states.values()) > 1:
            raise Denied
    if value["tasks"] != states or value["updated_at_utc"] != events[-1]["at_utc"]:
        raise Denied
    if states["T-033"] == "COMPLETED":
        _final_gate(
            value,
            repo_root=repo_root,
            manifest_result=manifest_result,
            private_inputs=private_inputs,
        )
    elif any(item is not None for item in private_inputs):
        raise Denied
    return {
        "baseline_id": value["baseline_id"],
        "sequence": len(events),
        "status": "PASS",
    }


def validate(
    manifest_path: Path,
    schema_path: Path,
    tasks_path: Path,
    progress_path: Path,
    *,
    private_inputs: tuple[str | None, str | None, str | None, str | None] = (
        None,
        None,
        None,
        None,
    ),
) -> dict[str, Any]:
    repo_root = Path.cwd().absolute()
    expected_manifest = repo_root / "specs/subject-distillation/baseline-manifest.json"
    expected_schema = repo_root / "specs/subject-distillation/implementation-progress.schema.json"
    expected_tasks = repo_root / "specs/subject-distillation/tasks.md"
    expected_progress = repo_root / "specs/subject-distillation/implementation-progress.json"
    if (
        manifest_path.absolute() != expected_manifest
        or schema_path.absolute() != expected_schema
        or tasks_path.absolute() != expected_tasks
        or progress_path.absolute() != expected_progress
    ):
        raise Denied
    try:
        progress_info = os.lstat(expected_progress)
    except OSError:
        raise Denied from None
    if (
        not stat.S_ISREG(progress_info.st_mode)
        or stat.S_ISLNK(progress_info.st_mode)
        or stat.S_IMODE(progress_info.st_mode) != 0o644
    ):
        raise Denied
    try:
        manifest_result = baseline.validate(manifest_path.absolute(), repo_root)
    except baseline.ValidationError:
        raise Denied from None
    _load_schema(schema_path.absolute())
    tasks_raw = evidence._read_file(tasks_path.absolute())
    tasks_sha256 = hashlib.sha256(tasks_raw).hexdigest()
    value, _raw = evidence._load_json(progress_path.absolute())
    return validate_value(
        value,
        repo_root=repo_root,
        manifest_result=manifest_result,
        tasks_sha256=tasks_sha256,
        private_inputs=private_inputs,
    )


def _reject_duplicate_scalars(argv: list[str], names: tuple[str, ...]) -> None:
    for name in names:
        count = sum(item == name or item.startswith(name + "=") for item in argv)
        if count > 1:
            raise Denied


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(add_help=False)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--progress", required=True)
    parser.add_argument("--private-shadow-verifier")
    parser.add_argument("--private-shadow-gate-input")
    parser.add_argument("--private-shadow-verifier-config")
    parser.add_argument("--private-shadow-release-receipt")
    try:
        raw_argv = list(sys.argv[1:] if argv is None else argv)
        _reject_duplicate_scalars(
            raw_argv,
            (
                "--manifest",
                "--schema",
                "--tasks",
                "--progress",
                "--private-shadow-verifier",
                "--private-shadow-gate-input",
                "--private-shadow-verifier-config",
                "--private-shadow-release-receipt",
            ),
        )
        args = parser.parse_args(raw_argv)
        result = validate(
            Path(args.manifest),
            Path(args.schema),
            Path(args.tasks),
            Path(args.progress),
            private_inputs=(
                args.private_shadow_verifier,
                args.private_shadow_gate_input,
                args.private_shadow_verifier_config,
                args.private_shadow_release_receipt,
            ),
        )
    except (Denied, SystemExit, authorization.Denied, baseline.ValidationError):
        sys.stderr.write(DENY_TEXT)
        return 2
    except Exception:  # noqa: BLE001 - fixed public boundary must not echo faults
        sys.stderr.write(ERROR_TEXT)
        return 3
    sys.stdout.write(evidence._canonical(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
