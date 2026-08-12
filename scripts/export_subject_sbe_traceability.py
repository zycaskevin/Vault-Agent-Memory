#!/usr/bin/env python3
"""Export the canonical Subject SBE mapping without inventing ownership."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import selectors
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DENY_TEXT = "SUBJECT_SBE_TRACEABILITY_DENY\n"
ERROR_TEXT = "SUBJECT_SBE_TRACEABILITY_ERROR\n"
TRACEABILITY_PATH = "specs/subject-distillation/traceability.md"
REQUIREMENTS_PATH = "specs/subject-distillation/requirements.md"
MAPPING_PATH = "specs/subject-distillation/sbe-traceability.json"
MAPPING_PENDING_PATH = "specs/subject-distillation/.task-authorization.pending"
FIXTURE_MANIFEST_PATH = "tests/fixtures/subject_distillation/manifest.json"
FIXTURE_PATHS = (
    "tests/fixtures/subject_distillation/fragments/failure-boundary-cases.json",
    "tests/fixtures/subject_distillation/migration/migration-boundary-cases.json",
    "tests/fixtures/subject_distillation/organization/authority-boundary-cases.json",
    "tests/fixtures/subject_distillation/person/person-cases.json",
)
EXPECTED_REQUIREMENTS = tuple(f"R-SD-{number:03d}" for number in range(1, 27))
EXPECTED_SBE_IDS = (
    *(f"E-P-{number:03d}" for number in range(1, 19)),
    *(f"E-O-{number:03d}" for number in range(1, 6)),
    *(f"E-F-{number:03d}" for number in range(1, 21)),
)
EXPECTED_COLLECT_COMMAND = (
    "python",
    "-m",
    "pytest",
    "--collect-only",
    "-q",
    "tests/test_subject_*.py",
)
MAX_INPUT_BYTES = 1_048_576
MAX_COLLECT_BYTES = 16_777_216
MAX_COLLECT_STDERR_BYTES = 65_536
COLLECT_TIMEOUT_SECONDS = 300.0
COLLECT_TERMINATE_GRACE_SECONDS = 5.0
COLLECT_HARNESS = r'''
import importlib.abc
import importlib.util
import json
import os
import sys

repo_root = sys.argv[1]
mapping = json.loads(sys.argv[2])
for item in mapping:
    info_before = os.fstat(item["fd"])
    raw = os.pread(item["fd"], info_before.st_size + 1, 0)
    info_after = os.fstat(item["fd"])
    if (
        len(raw) != info_before.st_size
        or (info_before.st_dev, info_before.st_ino, info_before.st_mode,
            info_before.st_nlink, info_before.st_size, info_before.st_mtime_ns,
            info_before.st_ctime_ns)
        != (info_after.st_dev, info_after.st_ino, info_after.st_mode,
            info_after.st_nlink, info_after.st_size, info_after.st_mtime_ns,
            info_after.st_ctime_ns)
    ):
        raise RuntimeError("snapshot drift")
    item["raw"] = raw
for item in mapping:
    os.close(item.pop("fd"))
sys.argv[:] = [sys.argv[0]]

import pytest

by_stem = {item["path"].rsplit("/", 1)[-1][:-3]: item for item in mapping}


class RetainedLoader(importlib.abc.Loader):
    def __init__(self, item):
        self.item = item

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        item = self.item
        filename = os.path.join(repo_root, item["path"])
        module.__file__ = filename
        exec(compile(item["raw"], filename, "exec"), module.__dict__)


class RetainedFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        item = by_stem.get(fullname.rsplit(".", 1)[-1])
        if item is None:
            return None
        filename = os.path.join(repo_root, item["path"])
        return importlib.util.spec_from_loader(
            fullname, RetainedLoader(item), origin=filename
        )


sys.meta_path.insert(0, RetainedFinder())
sys.path.insert(0, repo_root)
raise SystemExit(
    pytest.main(["--assert=plain", "--collect-only", "-q", *[item["path"] for item in mapping]])
)
'''
SBE = re.compile(r"E-(?:P|O|F)-[0-9]{3}")
TASK = re.compile(r"T-[0-9]{3}")
DESIGN = re.compile(r"§[0-9]+(?:\.[0-9]+)?")
TEST_PATH = re.compile(r"tests/test_[a-z0-9_]+\.py")
HEX64 = re.compile(r"[0-9a-f]{64}")
SECRET_TOKEN = re.compile(
    r"(?i)(?:^|[^A-Za-z0-9])(?:ghp_|gho_|ghu_|ghs_|ghr_|github_pat_|glpat-|sk-|sk_live_"
    r"|sk_test_|rk_live_|rk_test_|pk_live_|whsec_|xoxb-|xoxp-|xoxa-|xoxr-"
    r"|AKIA|ASIA|AIza|ya29\.)"
)
BEARER = re.compile(r"(?i)(?:^|[^A-Za-z0-9])bearer(?:[._:-]|$)")
JWT = re.compile(
    r"(?<![A-Za-z0-9_./-])[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
    r"(?![A-Za-z0-9_./-])"
)
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?:^|[^A-Za-z0-9])(?:token|secret|password|passwd|api[._-]?key|access[._-]?key"
    r"|private[._-]?key|credential|client[._-]?secret|refresh[._-]?token"
    r"|aws[._-]?secret[._-]?access[._-]?key)[.:=_-].+"
)
PEM = re.compile(r"(?i)-----BEGIN [A-Z0-9 ]*PRIVATE[A-Z0-9 ]*KEY-----")
ABSOLUTE_PATH = re.compile(
    r"(?m)(?<![-A-Za-z0-9._/\\])(?:"
    r"(?:/[A-Za-z0-9._-]+)+/?(?![-A-Za-z0-9._/\\])"
    r"|[A-Za-z]:\\[A-Za-z0-9._ $-]+(?:\\[A-Za-z0-9._ $-]+)*(?![-A-Za-z0-9._/\\])"
    r"|\\\\[A-Za-z0-9._$ -]+\\[A-Za-z0-9._$ -]+(?:\\[A-Za-z0-9._$ -]+)*(?![-A-Za-z0-9._/\\])"
    r")"
)
LOCAL_FILE_URI = re.compile(r"(?i)(?<![A-Za-z0-9._-])(?:jar:)*file:/")


class Denied(Exception):
    """A public caller, mapping, or repository-state denial."""


class _Parser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise Denied


def _file_identity(
    info: os.stat_result,
) -> tuple[int, int, int, int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _directory_identity(info: os.stat_result) -> tuple[int, int, int]:
    return info.st_dev, info.st_ino, info.st_mode


@dataclass(frozen=True)
class _DirectoryEntry:
    parent_fd: int
    name: str
    fd: int
    identity: tuple[int, int, int, int, int, int, int]
    strong: bool


class _DirectoryChain:
    def __init__(
        self,
        owned: list[int],
        root_fd: int,
        root_identity: tuple[int, int, int],
        entries: list[_DirectoryEntry],
    ) -> None:
        self.owned = owned
        self.root_fd = root_fd
        self.root_identity = root_identity
        self.entries = tuple(entries)

    @property
    def parent_fd(self) -> int:
        return self.entries[-1].fd if self.entries else self.root_fd

    def audit(self, *, allow_leaf_metadata_change: bool = False) -> None:
        try:
            root = os.fstat(self.root_fd)
            if (
                not stat.S_ISDIR(root.st_mode)
                or _directory_identity(root) != self.root_identity
            ):
                raise Denied
            for index, entry in enumerate(self.entries):
                descriptor = os.fstat(entry.fd)
                pathname = os.stat(
                    entry.name,
                    dir_fd=entry.parent_fd,
                    follow_symlinks=False,
                )
                strong = entry.strong and not (
                    allow_leaf_metadata_change and index == len(self.entries) - 1
                )
                if (
                    not stat.S_ISDIR(descriptor.st_mode)
                    or (
                        _file_identity(descriptor)
                        if strong
                        else _directory_identity(descriptor)
                    )
                    != (entry.identity if strong else entry.identity[:3])
                    or (
                        _file_identity(pathname)
                        if strong
                        else _directory_identity(pathname)
                    )
                    != (entry.identity if strong else entry.identity[:3])
                ):
                    raise Denied
        except OSError:
            raise Denied from None

    def close(self) -> None:
        for fd in reversed(self.owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _directory_flags() -> int:
    if not all(hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW")):
        raise Denied
    return (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )


def _file_flags(*, writable: bool = False, create: bool = False) -> int:
    if not hasattr(os, "O_NOFOLLOW"):
        raise Denied
    flags = (os.O_RDWR if writable else os.O_RDONLY) | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)
    if create:
        flags |= os.O_CREAT | os.O_EXCL
    return flags


def _open_parent_chain(
    path: Path, *, strong_after: Path | None = None
) -> tuple[_DirectoryChain, str]:
    absolute = os.path.abspath(os.fspath(path))
    strong_root = (
        os.path.abspath(os.fspath(strong_after)) if strong_after is not None else None
    )
    if (
        not absolute.startswith(os.sep)
        or os.path.normpath(absolute) != absolute
        or absolute == os.sep
    ):
        raise Denied
    parts = Path(absolute).parts
    if not parts or parts[0] != os.sep or any(part in {"", ".", ".."} for part in parts[1:]):
        raise Denied
    owned: list[int] = []
    entries: list[_DirectoryEntry] = []
    try:
        root_fd = os.open(os.sep, _directory_flags())
        owned.append(root_fd)
        root_info = os.fstat(root_fd)
        if not stat.S_ISDIR(root_info.st_mode):
            raise Denied
        parent_fd = root_fd
        current_path = os.sep
        for part in parts[1:-1]:
            fd = os.open(part, _directory_flags(), dir_fd=parent_fd)
            owned.append(fd)
            info = os.fstat(fd)
            if not stat.S_ISDIR(info.st_mode):
                raise Denied
            current_path = os.path.join(current_path, part)
            strong = strong_root is not None and (
                current_path == strong_root
                or current_path.startswith(strong_root + os.sep)
            )
            entries.append(
                _DirectoryEntry(parent_fd, part, fd, _file_identity(info), strong)
            )
            parent_fd = fd
        chain = _DirectoryChain(
            owned,
            root_fd,
            _directory_identity(root_info),
            entries,
        )
        chain.audit()
        return chain, parts[-1]
    except (OSError, Denied):
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass
        raise Denied from None


def _canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError):
        raise Denied from None


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Denied
        result[key] = value
    return result


def _parse_json(raw: bytes) -> Any:
    if not raw or len(raw) > MAX_INPUT_BYTES or b"\x00" in raw or b"\r" in raw:
        raise Denied
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_object)
    except (UnicodeError, json.JSONDecodeError):
        raise Denied from None


def _read_fd(fd: int, limit: int) -> bytes:
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_size > limit
        ):
            raise Denied
        chunks: list[bytes] = []
        offset = 0
        while offset <= limit:
            chunk = os.pread(fd, min(65_536, limit + 1 - offset), offset)
            if not chunk:
                break
            chunks.append(chunk)
            offset += len(chunk)
            if offset > limit:
                raise Denied
        raw = b"".join(chunks)
        if len(raw) != info.st_size or _file_identity(os.fstat(fd)) != _file_identity(info):
            raise Denied
        return raw
    except OSError:
        raise Denied from None


def _write_all(fd: int, raw: bytes) -> None:
    offset = 0
    try:
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            if written <= 0:
                raise OSError
            offset += written
    except OSError:
        raise Denied from None


def _restore_mapping(
    parent_fd: int, pending_name: str, name: str, original_raw: bytes | None
) -> None:
    recovery_fd: int | None = None
    try:
        if original_raw is None:
            os.unlink(name, dir_fd=parent_fd)
            os.fsync(parent_fd)
            try:
                os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                return
            raise OSError
        recovery_fd = os.open(
            pending_name,
            _file_flags(writable=True, create=True),
            0o600,
            dir_fd=parent_fd,
        )
        _write_all(recovery_fd, original_raw)
        os.fsync(recovery_fd)
        os.fchmod(recovery_fd, 0o644)
        os.fsync(recovery_fd)
        expected = os.fstat(recovery_fd)
        os.replace(
            pending_name,
            name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        os.fsync(parent_fd)
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            _file_identity(current) != _file_identity(os.fstat(recovery_fd))
            or (current.st_dev, current.st_ino) != (expected.st_dev, expected.st_ino)
            or _read_fd(recovery_fd, MAX_INPUT_BYTES) != original_raw
        ):
            raise OSError
    except (OSError, Denied):
        raise RuntimeError from None
    finally:
        if recovery_fd is not None:
            try:
                os.close(recovery_fd)
            except OSError:
                pass


def _read_regular(
    path: Path,
    *,
    limit: int = MAX_INPUT_BYTES,
    strong_after: Path | None = None,
) -> bytes:
    chain: _DirectoryChain | None = None
    fd: int | None = None
    try:
        chain, name = _open_parent_chain(path, strong_after=strong_after)
        fd = os.open(name, _file_flags(), dir_fd=chain.parent_fd)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
            raise Denied
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(fd, min(65_536, limit + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > limit:
                raise Denied
        after = os.fstat(fd)
        path_after = os.stat(name, dir_fd=chain.parent_fd, follow_symlinks=False)
        chain.audit()
        raw = b"".join(chunks)
        if (
            _file_identity(info) != _file_identity(after)
            or _file_identity(info) != _file_identity(path_after)
            or len(raw) != info.st_size
        ):
            raise Denied
        return raw
    except (OSError, Denied):
        raise Denied from None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if chain is not None:
            chain.close()


def _repo_path(repo_root: Path, relative: str) -> Path:
    if (
        not relative
        or relative.startswith("/")
        or "\\" in relative
        or any(part in {"", ".", ".."} for part in relative.split("/"))
    ):
        raise Denied
    return repo_root.joinpath(*relative.split("/"))


def _read_repo_file(repo_root: Path, relative: str) -> bytes:
    return _read_regular(
        _repo_path(repo_root, relative), strong_after=repo_root
    )


def _split_exact(cell: str, pattern: re.Pattern[str]) -> list[str]:
    values = [item.strip() for item in cell.split(",")]
    if not values or any(pattern.fullmatch(item) is None for item in values):
        raise Denied
    if len(values) != len(set(values)):
        raise Denied
    return values


def _planned_tests(cell: str) -> list[str]:
    values = re.findall(r"`([^`]+)`", cell)
    if not values or cell != "; ".join(f"`{item}`" for item in values):
        raise Denied
    if any(TEST_PATH.fullmatch(item) is None for item in values):
        raise Denied
    if len(values) != len(set(values)):
        raise Denied
    return sorted(values)


def _public_text(value: str) -> None:
    lowered = value.lower()
    if (
        not value
        or len(value) > 512
        or "tbd" in lowered
        or "manual" in lowered
        or "/users/" in lowered
        or "/home/" in lowered
        or "\\" in value
        or any(ord(char) < 0x20 or ord(char) == 0x7F for char in value)
    ):
        raise Denied


def _public_node_id(value: str, repo_root: Path) -> None:
    if type(value) is not str or "::" not in value:
        raise Denied
    _path, node_suffix = value.split("::", 1)
    if (
        not value
        or len(value) > 512
        or "/" in node_suffix
        or "\\" in node_suffix
        or any(unicodedata.category(char) in {"Cc", "Cf"} for char in value)
        or SECRET_TOKEN.search(value) is not None
        or BEARER.search(value) is not None
        or JWT.search(value) is not None
        or SECRET_ASSIGNMENT.search(value) is not None
        or PEM.search(value) is not None
        or ABSOLUTE_PATH.search(value) is not None
        or LOCAL_FILE_URI.search(value) is not None
    ):
        raise Denied
    lowered = value.casefold()
    private_markers = {
        os.path.abspath(os.path.expanduser("~")).casefold(),
        os.path.abspath(os.fspath(repo_root)).casefold(),
        "arthurliao",
        "zycaskevin",
        "@gmail.com",
        "private-shadow-pass:",
    }
    if any(marker and marker in lowered for marker in private_markers):
        raise Denied


def _parse_traceability(raw: bytes) -> list[dict[str, Any]]:
    if not raw or len(raw) > MAX_INPUT_BYTES or b"\x00" in raw or b"\r" in raw:
        raise Denied
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        raise Denied from None
    header = "| Example | Approved behavior | Design contract | Task(s) | Planned test file(s) |"
    separator = "|---|---|---|---|---|"
    lines = text.splitlines()
    try:
        start = lines.index(header)
    except ValueError:
        raise Denied from None
    if start + 1 >= len(lines) or lines[start + 1] != separator:
        raise Denied
    rows: list[dict[str, Any]] = []
    for line in lines[start + 2 :]:
        if not line.startswith("| E-"):
            break
        if not line.endswith("|"):
            raise Denied
        cells = [cell.strip() for cell in line[1:-1].split("|")]
        if len(cells) != 5:
            raise Denied
        sbe_id, behavior, design_cell, task_cell, tests_cell = cells
        if SBE.fullmatch(sbe_id) is None:
            raise Denied
        _public_text(behavior)
        rows.append(
            {
                "sbe_id": sbe_id,
                "approved_behavior": behavior,
                "design_contracts": _split_exact(design_cell, DESIGN),
                "tasks": _split_exact(task_cell, TASK),
                "planned_tests": _planned_tests(tests_cell),
            }
        )
    ids = [row["sbe_id"] for row in rows]
    if ids != list(EXPECTED_SBE_IDS) or len(ids) != len(set(ids)):
        raise Denied
    return rows


def _fixture_owners(repo_root: Path) -> tuple[dict[str, dict[str, Any]], str]:
    manifest_raw = _read_repo_file(repo_root, FIXTURE_MANIFEST_PATH)
    manifest = _parse_json(manifest_raw)
    if (
        type(manifest) is not dict
        or set(manifest) != {"schema_version", "artifact_kind", "synthetic_only", "files"}
        or manifest["schema_version"] != 1
        or manifest["artifact_kind"] != "subject-distillation-synthetic-fixture-manifest"
        or manifest["synthetic_only"] is not True
        or type(manifest["files"]) is not list
    ):
        raise Denied
    entries = manifest["files"]
    if [entry.get("path") for entry in entries if type(entry) is dict] != list(FIXTURE_PATHS):
        raise Denied
    owners: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if (
            set(entry) != {"case_count", "path", "sbe_ids", "sha256"}
            or type(entry["case_count"]) is not int
            or type(entry["sbe_ids"]) is not list
            or type(entry["sha256"]) is not str
            or HEX64.fullmatch(entry["sha256"]) is None
        ):
            raise Denied
        fixture_raw = _read_repo_file(repo_root, entry["path"])
        if hashlib.sha256(fixture_raw).hexdigest() != entry["sha256"]:
            raise Denied
        fixture = _parse_json(fixture_raw)
        if (
            type(fixture) is not dict
            or fixture.get("artifact_kind") != "subject-distillation-synthetic-fixtures"
            or set(fixture) != {"schema_version", "artifact_kind", "synthetic_only", "cases"}
            or fixture["schema_version"] != 1
            or fixture["synthetic_only"] is not True
            or type(fixture["cases"]) is not list
            or len(fixture["cases"]) != entry["case_count"]
        ):
            raise Denied
        fixture_ids: list[str] = []
        for case in fixture["cases"]:
            if (
                type(case) is not dict
                or type(case.get("sbe_id")) is not str
                or case.get("fixture_id") != "synthetic-" + case.get("sbe_id", "").lower()
                or case.get("synthetic") is not True
                or type(case.get("title")) is not str
                or type(case.get("planned_tests")) is not list
                or case["planned_tests"] != sorted(set(case["planned_tests"]))
                or any(TEST_PATH.fullmatch(item) is None for item in case["planned_tests"])
                or case["sbe_id"] in owners
            ):
                raise Denied
            fixture_ids.append(case["sbe_id"])
            owners[case["sbe_id"]] = {**case, "fixture_path": entry["path"]}
        if fixture_ids != entry["sbe_ids"]:
            raise Denied
    if set(owners) != set(EXPECTED_SBE_IDS):
        raise Denied
    return owners, hashlib.sha256(manifest_raw).hexdigest()


def _build_planned(repo_root: Path, traceability_path: Path) -> dict[str, Any]:
    if traceability_path.absolute() != (repo_root / TRACEABILITY_PATH).absolute():
        raise Denied
    traceability_raw = _read_repo_file(repo_root, TRACEABILITY_PATH)
    requirements_sha256 = _validate_requirements(
        _read_repo_file(repo_root, REQUIREMENTS_PATH)
    )
    rows = _parse_traceability(traceability_raw)
    owners, manifest_sha256 = _fixture_owners(repo_root)
    examples: list[dict[str, Any]] = []
    for row in rows:
        owner = owners[row["sbe_id"]]
        if owner["title"] != row["approved_behavior"] or owner["planned_tests"] != row["planned_tests"]:
            raise Denied
        examples.append(
            {
                **row,
                "fixture_id": owner["fixture_id"],
                "fixture_path": owner["fixture_path"],
            }
        )
    return {
        "schema_version": 1,
        "artifact_kind": "subject-sbe-traceability",
        "mode": "planned",
        "source_traceability_sha256": hashlib.sha256(traceability_raw).hexdigest(),
        "fixture_manifest_sha256": manifest_sha256,
        "requirements_sha256": requirements_sha256,
        "requirement_ids": list(EXPECTED_REQUIREMENTS),
        "examples": examples,
    }


def _bind_collected(
    planned: dict[str, Any],
    node_ids: list[str],
    *,
    require_count: int,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    if require_count != 43 or len(node_ids) != len(set(node_ids)):
        raise Denied
    matches: dict[str, str] = {}
    selected_root = repo_root if repo_root is not None else Path.cwd().absolute()
    for row in planned["examples"]:
        marker = "test_" + row["sbe_id"].lower().replace("-", "_")
        candidates: list[str] = []
        for node_id in node_ids:
            if type(node_id) is not str or not node_id or len(node_id) > 512 or "::" not in node_id:
                raise Denied
            path, *parts = node_id.split("::")
            if path not in row["planned_tests"]:
                continue
            if any(part == marker or part.startswith(marker + "_") for part in parts):
                _public_node_id(node_id, selected_root)
                candidates.append(node_id)
        if len(candidates) != 1 or candidates[0] in matches.values():
            raise Denied
        matches[row["sbe_id"]] = candidates[0]
    if len(matches) != require_count:
        raise Denied
    return {
        **{key: value for key, value in planned.items() if key != "mode"},
        "mode": "collected",
        "examples": [
            {**row, "pytest_node_id": matches[row["sbe_id"]]}
            for row in planned["examples"]
        ],
    }


def _validate_requirements(raw: bytes) -> str:
    if not raw or len(raw) > MAX_INPUT_BYTES or b"\x00" in raw or b"\r" in raw:
        raise Denied
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        raise Denied from None
    ids = re.findall(r"^### (R-SD-[0-9]{3}) — ", text, flags=re.MULTILINE)
    if ids != list(EXPECTED_REQUIREMENTS) or len(ids) != len(set(ids)):
        raise Denied
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class _ChildResult:
    returncode: int
    stdout: bytes
    stderr: bytes


def _process_group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        raise Denied from None
    return True


def _terminate_child_group(
    child: subprocess.Popen[bytes], *, grace_seconds: float
) -> None:
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except OSError:
        raise Denied from None
    deadline = time.monotonic() + grace_seconds
    while _process_group_exists(child.pid) and time.monotonic() < deadline:
        if child.poll() is None:
            try:
                child.wait(timeout=min(0.02, max(0.001, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                pass
        time.sleep(0.005)
    if _process_group_exists(child.pid):
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            raise Denied from None
        deadline = time.monotonic() + grace_seconds
        while _process_group_exists(child.pid) and time.monotonic() < deadline:
            if child.poll() is None:
                try:
                    child.wait(
                        timeout=min(0.02, max(0.001, deadline - time.monotonic()))
                    )
                except subprocess.TimeoutExpired:
                    pass
            time.sleep(0.005)
    if _process_group_exists(child.pid):
        raise Denied
    if child.poll() is None:
        try:
            child.wait(timeout=max(0.01, grace_seconds))
        except (OSError, subprocess.TimeoutExpired):
            raise Denied from None


def _run_bounded_child(
    argv: list[str],
    *,
    cwd: Path,
    stdout_limit: int,
    stderr_limit: int,
    timeout_seconds: float,
    terminate_grace_seconds: float,
    audit: Callable[[], None] | None = None,
    pass_fds: tuple[int, ...] = (),
) -> _ChildResult:
    if (
        type(argv) is not list
        or not argv
        or any(type(item) is not str or not item for item in argv)
        or type(stdout_limit) is not int
        or stdout_limit < 0
        or type(stderr_limit) is not int
        or stderr_limit < 0
        or type(timeout_seconds) is not float
        or timeout_seconds <= 0
        or type(terminate_grace_seconds) is not float
        or terminate_grace_seconds <= 0
        or type(pass_fds) is not tuple
        or any(type(fd) is not int or fd < 0 for fd in pass_fds)
    ):
        raise Denied
    selector = selectors.DefaultSelector()
    stdout = bytearray()
    stderr = bytearray()
    child: subprocess.Popen[bytes] | None = None
    failed = True
    try:
        if audit is not None:
            audit()
        child_env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("PYTHON") and not key.startswith("PYTEST_")
        }
        child_env.update(
            {
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            }
        )
        child = subprocess.Popen(
            argv,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            pass_fds=pass_fds,
            start_new_session=True,
            env=child_env,
        )
        if child.stdout is None or child.stderr is None:
            raise Denied
        selector.register(child.stdout, selectors.EVENT_READ, (stdout, stdout_limit))
        selector.register(child.stderr, selectors.EVENT_READ, (stderr, stderr_limit))
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
                chunk = os.read(key.fd, min(65_536, limit + 1 - len(target)))
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
        if _process_group_exists(child.pid):
            _terminate_child_group(child, grace_seconds=terminate_grace_seconds)
            raise Denied
        if audit is not None:
            audit()
        failed = False
        return _ChildResult(returncode, bytes(stdout), bytes(stderr))
    except (Denied, OSError, ValueError, subprocess.SubprocessError):
        raise Denied from None
    finally:
        cleanup_failed = False
        if failed and child is not None:
            try:
                _terminate_child_group(child, grace_seconds=terminate_grace_seconds)
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


@dataclass(frozen=True)
class _RetainedTest:
    name: str
    fd: int
    snapshot_fd: int
    identity: tuple[int, int, int, int, int, int, int]


class _RetainedTests:
    def __init__(
        self, chain: _DirectoryChain, paths: list[str], files: list[_RetainedTest]
    ) -> None:
        self.chain = chain
        self.paths = paths
        self.files = tuple(files)

    def audit(self) -> None:
        self.chain.audit()
        try:
            for item in self.files:
                descriptor = os.fstat(item.fd)
                pathname = os.stat(
                    item.name,
                    dir_fd=self.chain.parent_fd,
                    follow_symlinks=False,
                )
                if (
                    not stat.S_ISREG(descriptor.st_mode)
                    or stat.S_IMODE(descriptor.st_mode) != 0o644
                    or descriptor.st_nlink != 1
                    or _file_identity(descriptor) != item.identity
                    or _file_identity(pathname) != item.identity
                ):
                    raise Denied
        except OSError:
            raise Denied from None

    def close(self) -> None:
        for item in self.files:
            try:
                os.close(item.snapshot_fd)
            except OSError:
                pass
        self.chain.close()


def _subject_test_paths(repo_root: Path) -> _RetainedTests:
    chain: _DirectoryChain | None = None
    files: list[_RetainedTest] = []
    try:
        chain, _placeholder = _open_parent_chain(
            repo_root / "tests/.subject-collection",
            strong_after=repo_root,
        )
        names = sorted(os.listdir(chain.parent_fd))
        paths: list[str] = []
        for name in names:
            if re.fullmatch(r"test_subject_[a-z0-9_]+\.py", name) is None:
                continue
            fd = os.open(name, _file_flags(), dir_fd=chain.parent_fd)
            chain.owned.append(fd)
            info = os.fstat(fd)
            pathname = os.stat(name, dir_fd=chain.parent_fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != 0o644
                or _file_identity(info) != _file_identity(pathname)
            ):
                raise Denied
            raw = _read_fd(fd, MAX_INPUT_BYTES)
            snapshot_fd, snapshot_path = tempfile.mkstemp(
                prefix="subject-sbe-collection-snapshot-"
            )
            try:
                os.unlink(snapshot_path)
                _write_all(snapshot_fd, raw)
                os.fsync(snapshot_fd)
                os.fchmod(snapshot_fd, 0o400)
                os.fsync(snapshot_fd)
                if os.pread(snapshot_fd, len(raw) + 1, 0) != raw:
                    raise Denied
            except (OSError, Denied):
                os.close(snapshot_fd)
                raise Denied from None
            paths.append(f"tests/{name}")
            files.append(
                _RetainedTest(name, fd, snapshot_fd, _file_identity(info))
            )
        if not paths or len(paths) > 128:
            raise Denied
        retained = _RetainedTests(chain, paths, files)
        retained.audit()
        return retained
    except (OSError, Denied):
        for item in files:
            try:
                os.close(item.snapshot_fd)
            except OSError:
                pass
        if chain is not None:
            chain.close()
        raise Denied from None


def _collect(repo_root: Path, command: str) -> list[str]:
    try:
        argv = tuple(shlex.split(command))
    except ValueError:
        raise Denied from None
    if argv != EXPECTED_COLLECT_COMMAND:
        raise Denied
    retained = _subject_test_paths(repo_root)
    try:
        result = _run_bounded_child(
            [
                sys.executable,
                "-I",
                "-B",
                "-c",
                COLLECT_HARNESS,
                os.fspath(repo_root),
                json.dumps(
                    [
                        {"fd": item.snapshot_fd, "path": path}
                        for item, path in zip(
                            retained.files, retained.paths, strict=True
                        )
                    ],
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            ],
            cwd=repo_root,
            stdout_limit=MAX_COLLECT_BYTES,
            stderr_limit=MAX_COLLECT_STDERR_BYTES,
            timeout_seconds=COLLECT_TIMEOUT_SECONDS,
            terminate_grace_seconds=COLLECT_TERMINATE_GRACE_SECONDS,
            audit=retained.audit,
            pass_fds=tuple(item.snapshot_fd for item in retained.files),
        )
        retained.audit()
    finally:
        retained.close()
    if (
        result.returncode != 0
        or result.stderr
        or b"\x00" in result.stdout
        or b"\r" in result.stdout
    ):
        raise Denied
    try:
        lines = result.stdout.decode("utf-8").splitlines()
    except UnicodeError:
        raise Denied from None
    return [line for line in lines if line.startswith("tests/") and "::" in line]


def _write_fixed(repo_root: Path, output: str, raw: bytes) -> None:
    if output != MAPPING_PATH:
        raise Denied
    path = _repo_path(repo_root, output)
    pending = _repo_path(repo_root, MAPPING_PENDING_PATH)
    path_chain: _DirectoryChain | None = None
    pending_chain: _DirectoryChain | None = None
    pending_fd: int | None = None
    final_fd: int | None = None
    original_final: os.stat_result | None = None
    original_raw: bytes | None = None
    created = False
    published = False
    try:
        path_chain, name = _open_parent_chain(path, strong_after=repo_root)
        pending_chain, pending_name = _open_parent_chain(
            pending, strong_after=repo_root
        )
        if (
            _directory_identity(os.fstat(path_chain.parent_fd))
            != _directory_identity(os.fstat(pending_chain.parent_fd))
        ):
            raise Denied
        parent_fd = path_chain.parent_fd
        try:
            final_fd = os.open(name, _file_flags(), dir_fd=parent_fd)
            original_final = os.fstat(final_fd)
            if (
                not stat.S_ISREG(original_final.st_mode)
                or original_final.st_nlink != 1
                or stat.S_IMODE(original_final.st_mode) != 0o644
            ):
                raise Denied
            original_raw = _read_fd(final_fd, MAX_INPUT_BYTES)
        except FileNotFoundError:
            final_fd = None
            original_final = None
        try:
            pending_fd = os.open(
                pending_name,
                _file_flags(writable=True),
                dir_fd=parent_fd,
            )
            existing = _read_fd(pending_fd, MAX_INPUT_BYTES)
            if existing != raw:
                raise Denied
        except FileNotFoundError:
            pending_fd = os.open(
                pending_name,
                _file_flags(writable=True, create=True),
                0o600,
                dir_fd=parent_fd,
            )
            created = True
            _write_all(pending_fd, raw)
        try:
            info = os.fstat(pending_fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) not in {0o600, 0o644}
                or _read_fd(pending_fd, MAX_INPUT_BYTES) != raw
            ):
                raise Denied
            os.fchmod(pending_fd, 0o644)
            os.fsync(pending_fd)
            final = os.fstat(pending_fd)
            pending_final = os.stat(
                pending_name, dir_fd=parent_fd, follow_symlinks=False
            )
            path_chain.audit(allow_leaf_metadata_change=True)
            pending_chain.audit(allow_leaf_metadata_change=True)
            if (
                not stat.S_ISREG(final.st_mode)
                or final.st_nlink != 1
                or stat.S_IMODE(final.st_mode) != 0o644
                or _file_identity(final) != _file_identity(pending_final)
                or _read_fd(pending_fd, MAX_INPUT_BYTES) != raw
            ):
                raise Denied
            try:
                current_final = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                current_final = None
            if original_final is None:
                if current_final is not None:
                    raise Denied
            elif (
                current_final is None
                or final_fd is None
                or _file_identity(os.fstat(final_fd)) != _file_identity(original_final)
                or _file_identity(current_final) != _file_identity(original_final)
            ):
                raise Denied
            os.replace(
                pending_name,
                name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            published = True
            os.fsync(parent_fd)
            retained_after_publish = os.fstat(pending_fd)
            path_final = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            path_chain.audit(allow_leaf_metadata_change=True)
            pending_chain.audit(allow_leaf_metadata_change=True)
            if (
                _file_identity(retained_after_publish) != _file_identity(path_final)
                or (retained_after_publish.st_dev, retained_after_publish.st_ino)
                != (final.st_dev, final.st_ino)
                or _read_fd(pending_fd, MAX_INPUT_BYTES) != raw
            ):
                raise Denied
        except OSError:
            raise Denied from None
    except (OSError, Denied):
        if published and path_chain is not None:
            _restore_mapping(
                path_chain.parent_fd,
                pending.name,
                path.name,
                original_raw,
            )
        raise Denied from None
    finally:
        if created and not published and pending_chain is not None and pending_fd is not None:
            try:
                current = os.stat(
                    pending.name,
                    dir_fd=pending_chain.parent_fd,
                    follow_symlinks=False,
                )
                retained = os.fstat(pending_fd)
                if (current.st_dev, current.st_ino) == (retained.st_dev, retained.st_ino):
                    os.unlink(pending.name, dir_fd=pending_chain.parent_fd)
            except OSError:
                pass
        if pending_fd is not None:
            try:
                os.close(pending_fd)
            except OSError:
                pass
        if final_fd is not None:
            try:
                os.close(final_fd)
            except OSError:
                pass
        if pending_chain is not None:
            pending_chain.close()
        if path_chain is not None:
            path_chain.close()


def _result(mode: str) -> bytes:
    return _canonical(
        {"examples": 43, "mode": mode, "requirements": 26, "status": "PASS"}
    )


def _run(args: argparse.Namespace, repo_root: Path) -> bytes:
    if args.mode == "planned":
        if args.requirements is not None or args.collect_command is not None or args.require_count is not None:
            raise Denied
        traceability = args.check if args.check is not None else args.traceability
        if traceability != TRACEABILITY_PATH:
            raise Denied
        value = _build_planned(repo_root, repo_root / traceability)
        raw = _canonical(value)
        if args.check is not None:
            if args.output is not None or _read_repo_file(repo_root, MAPPING_PATH) != raw:
                raise Denied
        else:
            if args.output != MAPPING_PATH:
                raise Denied
            _write_fixed(repo_root, args.output, raw)
        return _result("planned")
    if (
        args.mode != "collected"
        or args.check is not None
        or args.traceability != TRACEABILITY_PATH
        or args.requirements != REQUIREMENTS_PATH
        or args.collect_command is None
        or args.require_count != 43
        or args.output != MAPPING_PATH
    ):
        raise Denied
    planned = _build_planned(repo_root, repo_root / TRACEABILITY_PATH)
    requirements_sha256 = _validate_requirements(
        _read_repo_file(repo_root, REQUIREMENTS_PATH)
    )
    if planned["requirements_sha256"] != requirements_sha256:
        raise Denied
    value = _bind_collected(
        planned,
        _collect(repo_root, args.collect_command),
        require_count=args.require_count,
        repo_root=repo_root,
    )
    _write_fixed(repo_root, args.output, _canonical(value))
    return _result("collected")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(add_help=False, allow_abbrev=False)
    parser.add_argument("--mode", choices=("planned", "collected"), required=True)
    parser.add_argument("--check")
    parser.add_argument("--requirements")
    parser.add_argument("--traceability")
    parser.add_argument("--collect-command")
    parser.add_argument("--require-count", type=int)
    parser.add_argument("--output")
    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
        output = _run(args, Path.cwd().absolute())
    except (Denied, SystemExit):
        sys.stderr.write(DENY_TEXT)
        return 2
    except Exception:  # noqa: BLE001 - fixed public boundary
        sys.stderr.write(ERROR_TEXT)
        return 3
    sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
