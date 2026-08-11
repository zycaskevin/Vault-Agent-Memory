#!/usr/bin/env python3
"""Atomically initialize and transition the Subject Distillation progress ledger."""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import run_subject_implementation_authorization as authorization_runner
    import validate_subject_baseline as baseline
    import validate_subject_evidence as evidence
    import validate_subject_progress as progress
except ImportError:  # pragma: no cover - import path used by test loaders
    from scripts import run_subject_implementation_authorization as authorization_runner
    from scripts import validate_subject_baseline as baseline
    from scripts import validate_subject_evidence as evidence
    from scripts import validate_subject_progress as progress


DENY_TEXT = "SUBJECT_PROGRESS_DENY\n"
ERROR_TEXT = "SUBJECT_PROGRESS_ERROR\n"
PENDING_NAME = ".implementation-progress.pending"
T001_PATHS = tuple(
    sorted(
        path.format(baseline_id="5dd83dd8b3d3696a")
        for path in authorization_runner.T001_PATHS
        if not path.endswith("implementation-progress.json")
        and not path.endswith(PENDING_NAME)
    )
)
COMMAND_IDS = (
    "baseline-control",
    "evidence-environment",
    "progress-tests",
    "progress-validator-in-progress",
    "legacy-regression",
    "readme-smoke",
    "release-parity",
    "ruff",
    "diff-check",
)
AUTHORIZATION_TRUST_PATHS = (
    "scripts/run_subject_implementation_authorization.py",
    "scripts/verify_subject_implementation_authorization.py",
    "specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json",
)
PRIVATE_NONE: tuple[str | None, str | None, str | None, str | None] = (
    None,
    None,
    None,
    None,
)
Denied = evidence.Denied


class _Parser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise Denied


@dataclass(frozen=True)
class Paths:
    repo_root: Path
    manifest: Path
    schema: Path
    tasks: Path
    progress: Path
    pending: Path


@dataclass(frozen=True)
class Runtime:
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    write: Callable[[int, bytes], int] = os.write
    fsync: Callable[[int], None] = os.fsync
    replace: Callable[..., None] = os.replace


@dataclass
class SourceReviewGuard:
    audit_handles: list[authorization_runner.verifier.Handle]
    file_handles: list[authorization_runner.verifier.Handle]
    raw_files: list[bytes]
    owned: list[int]
    subject_directory: authorization_runner.verifier.Handle
    subject_directory_entries: tuple[str, ...]

    def _audit_handle(self, handle: authorization_runner.verifier.Handle) -> None:
        if authorization_runner.verifier._identity(os.fstat(handle.fd)) != handle.identity:
            raise Denied
        for parent, name, before in handle.chain:
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            current_identity = authorization_runner.verifier._identity(current)
            if before[:3] == self.subject_directory.identity[:3]:
                if current_identity[:3] != before[:3]:
                    raise Denied
            elif current_identity != before:
                raise Denied

    def audit(self, *, allow_pending: bool = False) -> None:
        try:
            directory_info = os.fstat(self.subject_directory.fd)
            if (
                authorization_runner.verifier._identity(directory_info)[:3]
                != self.subject_directory.identity[:3]
            ):
                raise Denied
            expected_entries = set(self.subject_directory_entries)
            if allow_pending:
                expected_entries.add(PENDING_NAME)
            if set(os.listdir(self.subject_directory.fd)) != expected_entries:
                raise Denied
            for handle in self.audit_handles:
                self._audit_handle(handle)
            for handle, expected in zip(
                self.file_handles, self.raw_files, strict=True
            ):
                os.lseek(handle.fd, 0, os.SEEK_SET)
                if authorization_runner.verifier._read(handle) != expected:
                    raise Denied
            for handle in self.audit_handles:
                self._audit_handle(handle)
        except (OSError, authorization_runner.verifier.Denied):
            raise Denied from None

    def close(self) -> None:
        for fd in reversed(self.owned):
            try:
                os.close(fd)
            except OSError:
                pass
        self.owned.clear()


def _paths(repo_root: Path | None = None) -> Paths:
    root = repo_root if repo_root is not None else Path(__file__).absolute().parents[1]
    subject = root / "specs/subject-distillation"
    return Paths(
        root,
        subject / "baseline-manifest.json",
        subject / "implementation-progress.schema.json",
        subject / "tasks.md",
        subject / "implementation-progress.json",
        subject / PENDING_NAME,
    )


def _time(runtime: Runtime) -> str:
    value = runtime.now()
    if type(value) is not datetime or value.tzinfo != timezone.utc:
        raise Denied
    value = value.replace(microsecond=0)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _inputs(paths: Paths) -> tuple[dict[str, str], str]:
    try:
        manifest = baseline.validate(paths.manifest, paths.repo_root)
    except baseline.ValidationError:
        raise Denied from None
    progress._load_schema(paths.schema)
    tasks_raw = evidence._read_file(paths.tasks)
    return manifest, hashlib.sha256(tasks_raw).hexdigest()


def _validate_candidate(
    paths: Paths,
    value: dict[str, Any],
    *,
    private_inputs: tuple[str | None, str | None, str | None, str | None] = PRIVATE_NONE,
) -> dict[str, Any]:
    manifest, tasks_sha256 = _inputs(paths)
    return progress.validate_value(
        value,
        repo_root=paths.repo_root,
        manifest_result=manifest,
        tasks_sha256=tasks_sha256,
        private_inputs=private_inputs,
    )


def _seed(paths: Paths, runtime: Runtime) -> dict[str, Any]:
    manifest, tasks_sha256 = _inputs(paths)
    when = _time(runtime)
    tasks = {task: "PENDING" for task in progress.TASK_IDS}
    tasks["T-001"] = "IN_PROGRESS"
    return {
        "schema_version": 1,
        "baseline_id": manifest["baseline_id"],
        "baseline_full_digest": manifest["full_digest"],
        "tasks_sha256": tasks_sha256,
        "updated_at_utc": when,
        "tasks": tasks,
        "events": [
            {
                "sequence": 1,
                "task_id": "T-001",
                "from": "PENDING",
                "to": "IN_PROGRESS",
                "at_utc": when,
                "evidence_refs": [],
                "blocker": None,
            }
        ],
    }


def _existing(
    paths: Paths,
    *,
    private_inputs: tuple[str | None, str | None, str | None, str | None] = PRIVATE_NONE,
) -> dict[str, Any]:
    value, _raw = evidence._load_json(paths.progress)
    if type(value) is not dict:
        raise Denied
    _validate_candidate(paths, value, private_inputs=private_inputs)
    return value


def _write_all(fd: int, raw: bytes, runtime: Runtime) -> None:
    offset = 0
    try:
        while offset < len(raw):
            written = runtime.write(fd, raw[offset:])
            if type(written) is not int or written <= 0 or written > len(raw) - offset:
                raise OSError
            offset += written
        runtime.fsync(fd)
    except OSError:
        raise RuntimeError from None


def _open_parent(paths: Paths) -> tuple[Any, list[int]]:
    owned: list[int] = []
    try:
        anchor = os.open("/", authorization_runner.verifier._flags(directory=True))
        owned.append(anchor)
        handle = authorization_runner.verifier._open_chain(
            anchor,
            authorization_runner.verifier._absolute_parts(
                os.fspath(paths.progress.parent)
            ),
            owned,
            final_directory=True,
        )
        authorization_runner._audit_directory_handle_identity(handle)
        return handle, owned
    except (OSError, authorization_runner.Denied, authorization_runner.verifier.Denied):
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass
        raise Denied from None


def _read_retained(fd: int, maximum: int = evidence.MAX_BYTES) -> bytes:
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        before = os.fstat(fd)
        if before.st_size > maximum:
            raise Denied
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(fd, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        if (
            len(raw) > maximum
            or len(raw) != before.st_size
            or authorization_runner.verifier._identity(before)
            != authorization_runner.verifier._identity(after)
        ):
            raise Denied
        return raw
    except OSError:
        raise Denied from None


def _pending_value(
    paths: Paths,
    *,
    private_inputs: tuple[str | None, str | None, str | None, str | None] = PRIVATE_NONE,
) -> dict[str, Any] | None:
    parent, owned = _open_parent(paths)
    try:
        try:
            fd = os.open(
                paths.pending.name,
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=parent.fd,
            )
        except FileNotFoundError:
            return None
        owned.append(fd)
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) not in {0o600, 0o644}
            or info.st_nlink not in {1, 2}
        ):
            raise Denied
        raw = _read_retained(fd)
        current = os.stat(
            paths.pending.name, dir_fd=parent.fd, follow_symlinks=False
        )
        if authorization_runner.verifier._identity(current) != authorization_runner.verifier._identity(info):
            raise Denied
        value = authorization_runner.verifier._parse(raw)
        if type(value) is not dict or raw != evidence._canonical(value):
            raise Denied
        _validate_candidate(paths, value, private_inputs=private_inputs)
        return value
    except (OSError, authorization_runner.verifier.Denied):
        raise Denied from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _discard_matching_pending(paths: Paths, raw: bytes, runtime: Runtime) -> None:
    parent, owned = _open_parent(paths)
    try:
        fd = os.open(
            paths.pending.name,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=parent.fd,
        )
        owned.append(fd)
        before = os.fstat(fd)
        if _read_retained(fd) != raw:
            raise Denied
        current = os.stat(
            paths.pending.name, dir_fd=parent.fd, follow_symlinks=False
        )
        if authorization_runner.verifier._identity(current) != authorization_runner.verifier._identity(before):
            raise Denied
        os.unlink(paths.pending.name, dir_fd=parent.fd)
        runtime.fsync(parent.fd)
    except (OSError, authorization_runner.verifier.Denied):
        raise Denied from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _publish(
    paths: Paths,
    value: dict[str, Any],
    *,
    initialize: bool,
    runtime: Runtime,
    pre_publish: Callable[[tuple[int, int, int, int, int]], None] | None = None,
    post_publish: Callable[[], None] | None = None,
    private_inputs: tuple[str | None, str | None, str | None, str | None] = PRIVATE_NONE,
) -> bool:
    raw = evidence._canonical(value)
    _validate_candidate(paths, value, private_inputs=private_inputs)
    parent = None
    owned: list[int] = []
    pending_fd: int | None = None
    pending_identity: tuple[int, int] | None = None
    created = False
    published = False
    old_raw: bytes | None = None
    try:
        parent, owned = _open_parent(paths)
        if not initialize:
            old_fd = os.open(
                paths.progress.name,
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=parent.fd,
            )
            owned.append(old_fd)
            old_info = os.fstat(old_fd)
            if (
                not stat.S_ISREG(old_info.st_mode)
                or stat.S_IMODE(old_info.st_mode) != 0o644
            ):
                raise Denied
            old_raw = _read_retained(old_fd)
        try:
            pending_fd = os.open(
                paths.pending.name,
                os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=parent.fd,
            )
            retained = _read_retained(pending_fd)
            if retained != raw:
                raise Denied
        except FileNotFoundError:
            flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
            pending_fd = os.open(paths.pending.name, flags, 0o600, dir_fd=parent.fd)
            created = True
            created_info = os.fstat(pending_fd)
            pending_identity = (created_info.st_dev, created_info.st_ino)
            _write_all(pending_fd, raw, runtime)
        info = os.fstat(pending_fd)
        pending_identity = (info.st_dev, info.st_ino)
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) not in {0o600, 0o644}
            or info.st_nlink != 1
        ):
            raise Denied
        retained = _read_retained(pending_fd)
        if retained != raw:
            raise RuntimeError
        parsed = authorization_runner.verifier._parse(retained)
        if parsed != value:
            raise Denied
        _validate_candidate(paths, parsed, private_inputs=private_inputs)
        os.fchmod(pending_fd, 0o644)
        runtime.fsync(pending_fd)
        final_info = os.fstat(pending_fd)
        final_identity = authorization_runner.verifier._identity(final_info)
        if (final_info.st_dev, final_info.st_ino) != pending_identity or stat.S_IMODE(final_info.st_mode) != 0o644:
            raise Denied
        current = os.stat(paths.pending.name, dir_fd=parent.fd, follow_symlinks=False)
        if authorization_runner.verifier._identity(current) != final_identity:
            raise Denied
        if pre_publish is not None:
            pre_publish(final_identity)
            current = os.stat(
                paths.pending.name, dir_fd=parent.fd, follow_symlinks=False
            )
            if authorization_runner.verifier._identity(current) != final_identity:
                raise Denied
        if initialize:
            os.link(
                paths.pending.name,
                paths.progress.name,
                src_dir_fd=parent.fd,
                dst_dir_fd=parent.fd,
                follow_symlinks=False,
            )
            os.unlink(paths.pending.name, dir_fd=parent.fd)
        else:
            runtime.replace(
                paths.pending.name,
                paths.progress.name,
                src_dir_fd=parent.fd,
                dst_dir_fd=parent.fd,
            )
        published = True
        runtime.fsync(parent.fd)
        def audit_published() -> None:
            try:
                current_progress = os.stat(
                    paths.progress.name,
                    dir_fd=parent.fd,
                    follow_symlinks=False,
                )
            except OSError:
                raise Denied from None
            if (
                authorization_runner.verifier._identity(current_progress)
                != final_identity
                or not stat.S_ISREG(current_progress.st_mode)
                or stat.S_IMODE(current_progress.st_mode) != 0o644
                or current_progress.st_nlink != 1
                or _read_retained(pending_fd) != raw
            ):
                raise Denied
            parsed_progress = authorization_runner.verifier._parse(raw)
            if parsed_progress != value:
                raise Denied
            _validate_candidate(
                paths,
                parsed_progress,
                private_inputs=private_inputs,
            )
            authorization_runner._audit_directory_handle_identity(parent)

        try:
            audit_published()
            if post_publish is not None:
                post_publish()
            audit_published()
        except Exception:
            if old_raw is None:
                raise
            recovery_fd: int | None = None
            try:
                recovery_fd = os.open(
                    paths.pending.name,
                    os.O_RDWR
                    | os.O_CREAT
                    | os.O_EXCL
                    | os.O_CLOEXEC
                    | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=parent.fd,
                )
                offset = 0
                while offset < len(old_raw):
                    written = os.write(recovery_fd, old_raw[offset:])
                    if written <= 0:
                        raise OSError
                    offset += written
                os.fsync(recovery_fd)
                os.fchmod(recovery_fd, 0o644)
                os.fsync(recovery_fd)
                recovery_info = os.fstat(recovery_fd)
                os.replace(
                    paths.pending.name,
                    paths.progress.name,
                    src_dir_fd=parent.fd,
                    dst_dir_fd=parent.fd,
                )
                os.fsync(parent.fd)
                restored = os.stat(
                    paths.progress.name,
                    dir_fd=parent.fd,
                    follow_symlinks=False,
                )
                if (
                    authorization_runner.verifier._identity(restored)
                    != authorization_runner.verifier._identity(recovery_info)
                    or stat.S_IMODE(restored.st_mode) != 0o644
                    or restored.st_nlink != 1
                    or _read_retained(recovery_fd) != old_raw
                ):
                    raise OSError
                authorization_runner._audit_directory_handle_identity(parent)
            except OSError:
                raise RuntimeError from None
            finally:
                if recovery_fd is not None:
                    os.close(recovery_fd)
            raise
        return not created
    except FileExistsError:
        raise Denied from None
    finally:
        if created and not published and parent is not None and pending_identity is not None:
            try:
                current = os.stat(
                    paths.pending.name, dir_fd=parent.fd, follow_symlinks=False
                )
                if (current.st_dev, current.st_ino) == pending_identity:
                    os.unlink(paths.pending.name, dir_fd=parent.fd)
            except OSError:
                pass
        if pending_fd is not None:
            os.close(pending_fd)
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _repo_entry(paths: Paths, path: str) -> tuple[bytes, os.stat_result]:
    if (
        type(path) is not str
        or path.startswith("/")
        or "\\" in path
        or any(part in {"", ".", ".."} for part in path.split("/"))
    ):
        raise Denied
    owned: list[int] = []
    try:
        anchor = os.open("/", authorization_runner.verifier._flags(directory=True))
        owned.append(anchor)
        root = authorization_runner.verifier._open_chain(
            anchor,
            authorization_runner.verifier._absolute_parts(os.fspath(paths.repo_root)),
            owned,
            final_directory=True,
        )
        target = authorization_runner.verifier._open_chain(
            root.fd, tuple(path.split("/")), owned
        )
        authorization_runner.verifier._audit([root, target])
        info = os.fstat(target.fd)
        raw = authorization_runner.verifier._read(target)
        authorization_runner.verifier._audit([root, target])
        return raw, info
    except (OSError, authorization_runner.verifier.Denied):
        raise Denied from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _immutable_entries(paths: Paths) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path in T001_PATHS:
        raw, info = _repo_entry(paths, path)
        expected_mode = "100755" if path.startswith("scripts/") else "100644"
        mode = f"100{stat.S_IMODE(info.st_mode):03o}"
        if not stat.S_ISREG(info.st_mode) or mode != expected_mode:
            raise Denied
        entries.append(
            {"path": path, "mode": mode, "sha256": hashlib.sha256(raw).hexdigest()}
        )
    return entries


def _open_source_review_guard(
    paths: Paths,
    packet_path: Path,
    refs: list[dict[str, str]],
    review_id: str,
    authorization_proof: dict[str, Any],
) -> SourceReviewGuard:
    repo_refs = {
        item["path"]: item["sha256"]
        for item in refs
        if item.get("kind") == "repo_file"
    }
    if set(repo_refs) != set(T001_PATHS) or progress.HEX64.fullmatch(review_id) is None:
        raise Denied
    owned: list[int] = []
    try:
        anchor = os.open("/", authorization_runner.verifier._flags(directory=True))
        owned.append(anchor)
        repo = authorization_runner.verifier._open_chain(
            anchor,
            authorization_runner.verifier._absolute_parts(os.fspath(paths.repo_root)),
            owned,
            final_directory=True,
        )
        packet = authorization_runner.verifier._open_chain(
            anchor,
            authorization_runner.verifier._absolute_parts(os.fspath(packet_path)),
            owned,
        )
        subject_directory = authorization_runner.verifier._open_chain(
            repo.fd,
            ("specs", "subject-distillation"),
            owned,
            final_directory=True,
        )
        subject_directory_entries = tuple(sorted(os.listdir(subject_directory.fd)))
        if PENDING_NAME in subject_directory_entries:
            raise Denied
        manifest = authorization_runner.verifier._open_chain(
            repo.fd,
            tuple(os.fspath(paths.manifest.relative_to(paths.repo_root)).split("/")),
            owned,
        )
        canonical_handles: list[authorization_runner.verifier.Handle] = []
        for path in baseline.CANONICAL_PATHS:
            canonical_handles.append(
                authorization_runner.verifier._open_chain(
                    repo.fd,
                    tuple(path.split("/")),
                    owned,
                )
            )
        trust_handles: list[authorization_runner.verifier.Handle] = []
        for path in AUTHORIZATION_TRUST_PATHS:
            trust_handles.append(
                authorization_runner.verifier._open_chain(
                    repo.fd,
                    tuple(path.split("/")),
                    owned,
                )
            )
        source_handles: list[authorization_runner.verifier.Handle] = []
        for path in T001_PATHS:
            handle = authorization_runner.verifier._open_chain(
                repo.fd,
                tuple(path.split("/")),
                owned,
            )
            info = os.fstat(handle.fd)
            expected_mode = 0o755 if path.startswith("scripts/") else 0o644
            if stat.S_IMODE(info.st_mode) != expected_mode:
                raise Denied
            source_handles.append(handle)
        audit_handles = [
            repo,
            packet,
            manifest,
            *canonical_handles,
            *trust_handles,
            *source_handles,
        ]
        authorization_runner.verifier._audit(audit_handles)
        file_handles = [
            packet,
            manifest,
            *canonical_handles,
            *trust_handles,
            *source_handles,
        ]
        raw_files: list[bytes] = []
        for handle in file_handles:
            raw_files.append(authorization_runner.verifier._read(handle))
        if hashlib.sha256(raw_files[0]).hexdigest() != review_id:
            raise Denied
        try:
            packet_value = authorization_runner.verifier._parse(raw_files[0])
            manifest_value = authorization_runner.verifier._parse(raw_files[1])
        except authorization_runner.verifier.Denied:
            raise Denied from None
        if (
            type(packet_value) is not dict
            or type(manifest_value) is not dict
            or set(manifest_value) != baseline.TOP_KEYS
            or type(manifest_value.get("schema_version")) is not int
            or manifest_value["schema_version"] != 1
            or manifest_value.get("artifact_kind")
            != "subject-distillation-baseline"
            or manifest_value.get("baseline_state") != "frozen"
            or manifest_value.get("algorithm")
            != {
                "name": "subject-distillation-baseline-v1",
                "domain_separator_utf8_hex": baseline.DOMAIN_SEPARATOR_UTF8_HEX,
                "digest": "sha256",
                "baseline_id_hex_length": 16,
            }
            or manifest_value.get("scope")
            != {
                "generic_subject_core": True,
                "person_v1": True,
                "organization": "contract-only",
            }
            or type(manifest_value.get("closure")) is not dict
            or packet_value.get("baseline_id")
            != manifest_value["closure"].get("baseline_id")
            or packet_value.get("baseline_full_digest")
            != manifest_value["closure"].get("full_digest")
            or type(manifest_value.get("files")) is not list
            or len(manifest_value["files"]) != len(baseline.CANONICAL_PATHS)
        ):
            raise Denied
        payload = bytearray(baseline.EXPECTED_DOMAIN)
        total = 0
        for index, path in enumerate(baseline.CANONICAL_PATHS):
            entry = manifest_value["files"][index]
            canonical_raw = raw_files[2 + index]
            digest = hashlib.sha256(canonical_raw).hexdigest()
            if (
                type(entry) is not dict
                or set(entry) != baseline.FILE_KEYS
                or entry["path"] != path
                or entry["sha256"] != digest
                or type(entry["size_bytes"]) is not int
                or entry["size_bytes"] != len(canonical_raw)
            ):
                raise Denied
            total += len(canonical_raw)
            if (
                len(canonical_raw) > baseline.CANONICAL_MAX_BYTES
                or total > baseline.CANONICAL_TOTAL_MAX_BYTES
            ):
                raise Denied
            payload.extend(
                path.encode("utf-8")
                + b"\0"
                + digest.encode("ascii")
                + b"\0"
                + str(len(canonical_raw)).encode("ascii")
                + b"\n"
            )
        computed_full = hashlib.sha256(payload).hexdigest()
        if manifest_value["closure"] != {
            "full_digest": computed_full,
            "baseline_id": computed_full[:16],
        }:
            raise Denied
        trust_offset = 2 + len(baseline.CANONICAL_PATHS)
        trust_raws = raw_files[
            trust_offset : trust_offset + len(AUTHORIZATION_TRUST_PATHS)
        ]
        if (
            type(authorization_proof) is not dict
            or type(authorization_proof.get("runner")) is not dict
            or authorization_proof["runner"].get("path")
            != AUTHORIZATION_TRUST_PATHS[0]
            or authorization_proof["runner"].get("sha256")
            != hashlib.sha256(trust_raws[0]).hexdigest()
            or authorization_proof.get("authorization_verifier_sha256")
            != hashlib.sha256(trust_raws[1]).hexdigest()
            or authorization_proof.get("authorization_schema_sha256")
            != hashlib.sha256(trust_raws[2]).hexdigest()
        ):
            raise Denied
        source_offset = trust_offset + len(AUTHORIZATION_TRUST_PATHS)
        for path, raw in zip(T001_PATHS, raw_files[source_offset:], strict=True):
            if hashlib.sha256(raw).hexdigest() != repo_refs[path]:
                raise Denied
        guard = SourceReviewGuard(
            audit_handles,
            file_handles,
            raw_files,
            owned,
            subject_directory,
            subject_directory_entries,
        )
        guard.audit()
        return guard
    except (OSError, ValueError, Denied, authorization_runner.verifier.Denied):
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass
        raise Denied from None


def _source_review(
    paths: Paths,
    packet_path: Path,
    *,
    allowed_pending_identity: tuple[int, int, int, int, int] | None = None,
) -> tuple[str, dict[str, Any], datetime]:
    if (
        not packet_path.is_absolute()
        or os.path.commonpath([packet_path, paths.repo_root])
        == os.fspath(paths.repo_root)
    ):
        raise Denied
    value, raw = evidence._load_json(packet_path)
    if type(value) is not dict or set(value) != {
        "schema_version", "artifact_kind", "implementation_base_commit", "baseline_id",
        "baseline_full_digest", "builder_principal", "reviewer_principal", "reviewed_at_utc",
        "immutable_outputs", "authorization", "command_results", "pending_absent",
        "p0", "p1", "p2", "verdict",
    }:
        raise Denied
    manifest, _tasks_sha = _inputs(paths)
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["artifact_kind"] != "subject-distillation-t001-source-review"
        or value["implementation_base_commit"] != "git:24e1a126a1022a53480b7126f5f393dc0be85613"
        or value["baseline_id"] != manifest["baseline_id"]
        or value["baseline_full_digest"] != manifest["full_digest"]
        or type(value["builder_principal"]) is not str
        or progress.OPAQUE.fullmatch(value["builder_principal"]) is None
        or type(value["reviewer_principal"]) is not str
        or progress.OPAQUE.fullmatch(value["reviewer_principal"]) is None
        or value["builder_principal"] == value["reviewer_principal"]
        or value["immutable_outputs"] != _immutable_entries(paths)
        or value["pending_absent"] is not True
        or type(value["p0"]) is not int
        or value["p0"] != 0
        or type(value["p1"]) is not int
        or value["p1"] != 0
        or type(value["p2"]) is not int
        or not 0 <= value["p2"] <= 65_535
        or value["verdict"] != "PASS"
    ):
        raise Denied
    parent, owned = _open_parent(paths)
    try:
        try:
            pending_info = os.stat(
                paths.pending.name, dir_fd=parent.fd, follow_symlinks=False
            )
        except FileNotFoundError:
            pending_info = None
        if allowed_pending_identity is None:
            if pending_info is not None:
                raise Denied
        elif (
            pending_info is None
            or authorization_runner.verifier._identity(pending_info)
            != allowed_pending_identity
            or not stat.S_ISREG(pending_info.st_mode)
            or stat.S_IMODE(pending_info.st_mode) != 0o644
            or pending_info.st_nlink != 1
        ):
            raise Denied
    except OSError:
        raise Denied from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass
    reviewed_at = evidence._timestamp(value["reviewed_at_utc"])
    expected_commands = [
        {"command_id": command_id, "exit_code": 0, "status": "PASS"}
        for command_id in COMMAND_IDS
    ]
    if value["command_results"] != expected_commands:
        raise Denied
    environment_path = f"specs/subject-distillation/evidence/{manifest['baseline_id']}/environment.json"
    environment_value, environment_raw = evidence._load_json(
        paths.repo_root / environment_path
    )
    if type(environment_value) is not dict:
        raise Denied
    proof = environment_value["implementation_authorization"]
    if reviewed_at < evidence._timestamp(proof["recorded_at_utc"]):
        raise Denied
    expected_authorization = {
        "environment_path": environment_path,
        "environment_sha256": hashlib.sha256(environment_raw).hexdigest(),
        "authorization_id": proof["authorization_id"],
        "authorization_pass_packet_sha256": proof["authorization_pass_packet_sha256"],
        "status": "PASS",
    }
    if value["authorization"] != expected_authorization:
        raise Denied
    evidence._validate_environment(
        paths.repo_root,
        environment_value,
        evidence._load_json(paths.manifest, canonical=False)[0],
        evidence._expected_schemas()["environment"],
    )
    return hashlib.sha256(raw).hexdigest(), proof, reviewed_at


def _is_seed(value: dict[str, Any]) -> bool:
    return (
        len(value["events"]) == 1
        and value["events"][0]["sequence"] == 1
        and value["events"][0]["task_id"] == "T-001"
        and value["events"][0]["from"] == "PENDING"
        and value["events"][0]["to"] == "IN_PROGRESS"
        and value["events"][0]["evidence_refs"] == []
        and value["events"][0]["blocker"] is None
        and value["tasks"]["T-001"] == "IN_PROGRESS"
        and all(value["tasks"][task] == "PENDING" for task in progress.TASK_IDS[1:])
    )


def init(paths: Paths, runtime: Runtime) -> dict[str, Any]:
    manifest, _tasks_sha = _inputs(paths)
    with authorization_runner._authorization_lock(
        os.fspath(paths.repo_root),
        "subject-progress",
        manifest["baseline_id"],
        authorization_runner.Runtime(),
    ):
        if paths.progress.exists():
            value = _existing(paths)
            if not _is_seed(value):
                raise Denied
            pending = _pending_value(paths)
            if pending is not None:
                if pending != value:
                    raise Denied
                _discard_matching_pending(paths, evidence._canonical(value), runtime)
            return {
                "sequence": 1,
                "status": "RECOVERED_COMMITTED",
                "task_id": "T-001",
            }
        pending = _pending_value(paths)
        if pending is not None:
            if not _is_seed(pending):
                raise Denied
            value = pending
            recovered = _publish(paths, value, initialize=True, runtime=runtime)
        else:
            value = _seed(paths, runtime)
            recovered = _publish(paths, value, initialize=True, runtime=runtime)
    return {
        "sequence": 1,
        "status": "RECOVERED_COMMITTED" if recovered else "PASS",
        "task_id": "T-001",
    }


def _parse_refs(repo_refs: list[str], opaque_refs: list[str]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for raw in repo_refs:
        if type(raw) is not str or "=" not in raw:
            raise Denied
        path, digest = raw.rsplit("=", 1)
        refs.append({"kind": "repo_file", "path": path, "sha256": digest})
    for value in opaque_refs:
        if type(value) is not str:
            raise Denied
        refs.append({"kind": "opaque", "id": value})
    refs.sort(key=evidence._canonical)
    return refs


def _event_matches(
    event: Any,
    *,
    task: str,
    expected: str,
    target: str,
    refs: list[dict[str, str]],
    blocker: str | None,
) -> bool:
    return (
        type(event) is dict
        and event.get("task_id") == task
        and event.get("from") == expected
        and event.get("to") == target
        and event.get("evidence_refs") == refs
        and event.get("blocker") == blocker
    )


def _completion_refs(
    paths: Paths,
    packet: Path,
    *,
    allowed_pending_identity: tuple[int, int, int, int, int] | None = None,
) -> tuple[list[dict[str, str]], str, datetime, dict[str, Any]]:
    review_id, proof, reviewed_at = _source_review(
        paths,
        packet,
        allowed_pending_identity=allowed_pending_identity,
    )
    exact_refs = [
        {"kind": "repo_file", "path": item["path"], "sha256": item["sha256"]}
        for item in _immutable_entries(paths)
    ] + [
        {"kind": "opaque", "id": f"t001-authorization:{proof['authorization_id']}"},
        {"kind": "opaque", "id": f"t001-review:{review_id}"},
    ]
    exact_refs.sort(key=evidence._canonical)
    return exact_refs, review_id, reviewed_at, proof


def _transition_impl(
    paths: Paths,
    runtime: Runtime,
    *,
    task: str,
    expected: str,
    target: str,
    repo_refs: list[str],
    opaque_refs: list[str],
    blocker: str | None,
    source_review_packet: str | None,
    private_inputs: tuple[str | None, str | None, str | None, str | None] = PRIVATE_NONE,
) -> dict[str, Any]:
    if (
        task not in progress.TASK_IDS
        or expected not in progress.STATES
        or target not in progress.STATES
    ):
        raise Denied
    refs = _parse_refs(repo_refs, opaque_refs)
    packet = Path(source_review_packet) if source_review_packet is not None else None
    is_t001_completion = task == "T-001" and expected == "IN_PROGRESS" and target == "COMPLETED"
    if is_t001_completion != (packet is not None):
        raise Denied
    manifest, _tasks_sha = _inputs(paths)
    with authorization_runner._authorization_lock(
        os.fspath(paths.repo_root),
        "subject-progress",
        manifest["baseline_id"],
        authorization_runner.Runtime(),
    ):
        try:
            current = _existing(paths)
        except Denied:
            if task != "T-033" or target != "COMPLETED":
                raise
            current = _existing(paths, private_inputs=private_inputs)
        review_id: str | None = None
        reviewed_at: datetime | None = None
        authorization_proof: dict[str, Any] | None = None
        if packet is not None:
            exact_refs, review_id, reviewed_at, authorization_proof = _completion_refs(
                paths, packet
            )
            if refs != exact_refs:
                raise Denied
        if current["tasks"][task] == target:
            if not _event_matches(
                current["events"][-1],
                task=task,
                expected=expected,
                target=target,
                refs=refs,
                blocker=blocker,
            ):
                raise Denied
            return {
                "sequence": len(current["events"]),
                "status": "RECOVERED_COMMITTED",
                "task_id": task,
            }
        if current["tasks"][task] != expected:
            raise Denied
        pending = _pending_value(paths, private_inputs=private_inputs)
        if pending is not None:
            if len(pending["events"]) != len(current["events"]) + 1:
                raise Denied
            prior = __import__("copy").deepcopy(pending)
            pending_event = prior["events"].pop()
            prior["tasks"][task] = expected
            prior["updated_at_utc"] = current["updated_at_utc"]
            if prior != current or not _event_matches(
                pending_event,
                task=task,
                expected=expected,
                target=target,
                refs=refs,
                blocker=blocker,
            ):
                raise Denied
            candidate = pending
        else:
            when = _time(runtime)
            candidate = __import__("copy").deepcopy(current)
            candidate["tasks"][task] = target
            candidate["events"].append(
                {
                    "sequence": len(candidate["events"]) + 1,
                    "task_id": task,
                    "from": expected,
                    "to": target,
                    "at_utc": when,
                    "evidence_refs": refs,
                    "blocker": blocker,
                }
            )
            candidate["updated_at_utc"] = when
        if reviewed_at is not None and evidence._timestamp(
            candidate["events"][-1]["at_utc"]
        ) < reviewed_at:
            raise Denied
        _validate_candidate(paths, candidate, private_inputs=private_inputs)
        def final_source_review(
            pending_identity: tuple[int, int, int, int, int],
        ) -> None:
            if packet is None:
                return
            if guard is None:
                raise Denied
            guard.audit(
                allow_pending=(
                    paths.pending.parent
                    == paths.repo_root / "specs/subject-distillation"
                )
            )
            (
                final_refs,
                final_review_id,
                final_reviewed_at,
                final_authorization_proof,
            ) = _completion_refs(
                paths,
                packet,
                allowed_pending_identity=pending_identity,
            )
            if (
                final_refs != refs
                or final_review_id != review_id
                or final_reviewed_at != reviewed_at
                or final_authorization_proof != authorization_proof
            ):
                raise Denied
        guard: SourceReviewGuard | None = None
        try:
            if packet is not None:
                if review_id is None or authorization_proof is None:
                    raise Denied
                guard = _open_source_review_guard(
                    paths,
                    packet,
                    refs,
                    review_id,
                    authorization_proof,
                )
            recovered = _publish(
                paths,
                candidate,
                initialize=False,
                runtime=runtime,
                pre_publish=final_source_review,
                post_publish=guard.audit if guard is not None else None,
                private_inputs=private_inputs,
            )
        finally:
            if guard is not None:
                guard.close()
    return {
        "sequence": len(candidate["events"]),
        "status": "RECOVERED_COMMITTED" if recovered else "PASS",
        "task_id": task,
    }


def transition(
    paths: Paths,
    runtime: Runtime,
    *,
    task: str,
    expected: str,
    target: str,
    repo_refs: list[str],
    opaque_refs: list[str],
    blocker: str | None,
    source_review_packet: str | None,
    private_inputs: tuple[str | None, str | None, str | None, str | None] = PRIVATE_NONE,
) -> dict[str, Any]:
    """Apply an ordinary progress transition; final attestation is excluded."""
    if task == "T-033" and target == "COMPLETED":
        raise Denied
    return _transition_impl(
        paths,
        runtime,
        task=task,
        expected=expected,
        target=target,
        repo_refs=repo_refs,
        opaque_refs=opaque_refs,
        blocker=blocker,
        source_review_packet=source_review_packet,
        private_inputs=private_inputs,
    )


def _finalize_attested_t033(
    paths: Paths,
    runtime: Runtime,
    *,
    task: str,
    expected: str,
    target: str,
    repo_refs: list[str],
    opaque_refs: list[str],
    blocker: str | None,
    private_inputs: tuple[str | None, str | None, str | None, str | None],
) -> dict[str, Any]:
    """Final validator-bound publication core; never exposed through argparse."""
    if (
        task != "T-033"
        or expected != "IN_PROGRESS"
        or target != "COMPLETED"
        or blocker is not None
    ):
        raise Denied
    return _transition_impl(
        paths,
        runtime,
        task=task,
        expected=expected,
        target=target,
        repo_refs=repo_refs,
        opaque_refs=opaque_refs,
        blocker=None,
        source_review_packet=None,
        private_inputs=private_inputs,
    )


def _reject_duplicate_scalars(argv: list[str]) -> None:
    for name in (
        "--task",
        "--expected",
        "--to",
        "--blocker",
        "--source-review-packet",
        "--json",
    ):
        if sum(item == name or item.startswith(name + "=") for item in argv) > 1:
            raise Denied


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(add_help=False)
    sub = parser.add_subparsers(dest="command", required=True)
    init_parser = sub.add_parser("init", add_help=False)
    init_parser.add_argument("--json", action="store_true", required=True)
    transition_parser = sub.add_parser("transition", add_help=False)
    transition_parser.add_argument("--task", required=True)
    transition_parser.add_argument("--expected", required=True)
    transition_parser.add_argument("--to", required=True)
    transition_parser.add_argument("--repo-ref", action="append", default=[])
    transition_parser.add_argument("--opaque-ref", action="append", default=[])
    transition_parser.add_argument("--blocker")
    transition_parser.add_argument("--source-review-packet")
    transition_parser.add_argument("--json", action="store_true", required=True)
    try:
        raw_argv = list(sys.argv[1:] if argv is None else argv)
        _reject_duplicate_scalars(raw_argv)
        args = parser.parse_args(raw_argv)
        paths = _paths()
        runtime = Runtime()
        if args.command == "init":
            result = init(paths, runtime)
        else:
            result = transition(
                paths,
                runtime,
                task=args.task,
                expected=args.expected,
                target=args.to,
                repo_refs=args.repo_ref,
                opaque_refs=args.opaque_ref,
                blocker=args.blocker,
                source_review_packet=args.source_review_packet,
            )
    except (Denied, SystemExit, baseline.ValidationError, authorization_runner.Denied):
        sys.stderr.write(DENY_TEXT)
        return 2
    except Exception:  # noqa: BLE001 - fixed public boundary must not echo faults
        sys.stderr.write(ERROR_TEXT)
        return 3
    sys.stdout.write(evidence._canonical(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
