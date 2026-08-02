#!/usr/bin/env python3
"""Fail-closed verifier for Subject Distillation implementation receipts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

DENY = "SUBJECT_IMPLEMENTATION_AUTHORIZATION_DENY\n"
ERROR = "SUBJECT_IMPLEMENTATION_AUTHORIZATION_ERROR\n"
MAX_BYTES = 1_048_576
MAX_DEPTH = 32
MAX_NODES = 32_768
MAX_MEMBERS = 4_096
MANIFEST_PATH = "specs/subject-distillation/baseline-manifest.json"
SCHEMA_PATH = (
    "specs/subject-distillation/evidence-schemas/"
    "implementation-authorization.schema.json"
)
VERIFIER_PATH = "scripts/verify_subject_implementation_authorization.py"
DOMAIN_KEY = "domain_separator_utf8_hex"
DOMAIN_HEX = "7375626a6563742d64697374696c6c6174696f6e2d626173656c696e652d76310a"
CANONICAL_PATHS = (
    "specs/subject-distillation/requirements.md",
    "specs/subject-distillation/design.md",
    "specs/subject-distillation/tasks.md",
    "specs/subject-distillation/traceability.md",
    "specs/subject-distillation/schema.v15.sql",
)
HEX64 = re.compile(r"[0-9a-f]{64}")
HEX16 = re.compile(r"[0-9a-f]{16}")
TASK = re.compile(r"T-[0-9]{3}")
TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z")
TOKEN = re.compile(
    r"(?i)^(?:ghp_|gho_|ghu_|ghs_|ghr_|github_pat_|glpat-|sk-|sk_live_"
    r"|sk_test_|rk_live_|rk_test_|pk_live_|whsec_|xoxb-|xoxp-|xoxa-|xoxr-"
    r"|AKIA|ASIA|AIza|ya29\.)"
)
BEARER = re.compile(r"(?i)^bearer(?:[._:-]|$)")
JWT = re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
ASSIGNMENT = re.compile(
    r"(?i)(?:token|secret|password|passwd|api[._-]?key|access[._-]?key"
    r"|private[._-]?key|credential|client[._-]?secret|refresh[._-]?token"
    r"|aws[._-]?secret[._-]?access[._-]?key)[.:=_-].+"
)
PEM = re.compile(r"(?i)-----BEGIN [A-Z0-9 ]*PRIVATE[A-Z0-9 ]*KEY-----")
PRIVATE_SHADOW = re.compile(r"private-shadow-pass:[0-9a-f]{64}")
PRIVATE_SHADOW_RESERVED = re.compile(r"(?i)private-shadow-pass:")
BARE_HEX = re.compile(r"(?i)[0-9a-f]{32,128}")
NON_GOAL = re.compile(r"[a-z][a-z0-9]*(?:[._:-][a-z0-9]+)*")
DIGEST_KEYS = {
    "artifact_sha256",
    "authorization_id",
    "authorization_schema_sha256",
    "authorization_verifier_sha256",
    "baseline_full_digest",
    "full_digest",
    "input_hash",
    "output_hash",
    "private_shadow_receipt_sha256",
    "receipt_sha256",
    "reviewed_tree_sha256",
    "scope_sha256",
    "sha256",
    "tasks_sha256",
}
FORBIDDEN_KEYS = {
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "access_key",
    "private_key",
    "client_secret",
    "refresh_token",
    "aws_secret_access_key",
    "credential",
    "capability_secret",
    "raw",
    "raw_evidence",
    "content_raw",
    "private_path",
    "absolute_path",
}
PROHIBITED = {
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
}
SCHEMA_KEYS = {
    "$schema",
    "$id",
    "type",
    "properties",
    "required",
    "additionalProperties",
    "const",
    "pattern",
}


def _expected_schema() -> dict[str, Any]:
    digest = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": (
            "https://vault-agent-memory.invalid/subject-distillation/"
            "implementation-authorization.schema.json"
        ),
        "type": "object",
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "artifact_kind": {
                "type": "string",
                "const": "subject-distillation-implementation-authorization",
            },
            "baseline_id": {"type": "string", "pattern": "^[0-9a-f]{16}$"},
            "baseline_full_digest": dict(digest),
            "authorizing_principal": {
                "type": "string",
                "const": "github:zycaskevin",
            },
            "authorized_task": {"type": "string", "pattern": "^T-[0-9]{3}$"},
            "scope_sha256": dict(digest),
            "authorization_verifier_sha256": dict(digest),
            "authorization_schema_sha256": dict(digest),
            "issued_at_utc": {"type": "string"},
            "expires_at_utc": {"type": "string"},
            "authorization_id": dict(digest),
        },
        "required": [
            "schema_version",
            "artifact_kind",
            "baseline_id",
            "baseline_full_digest",
            "authorizing_principal",
            "authorized_task",
            "scope_sha256",
            "authorization_verifier_sha256",
            "authorization_schema_sha256",
            "issued_at_utc",
            "expires_at_utc",
            "authorization_id",
        ],
        "additionalProperties": False,
    }


class Denied(Exception):
    pass


def _duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Denied
        result[key] = value
    return result


def _nonfinite(_: str) -> None:
    raise Denied


def _exact_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _exact_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _exact_equal(left_item, right_item)
            for left_item, right_item in zip(left, right, strict=True)
        )
    return bool(left == right)


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns)


@dataclass(frozen=True)
class Handle:
    fd: int
    identity: tuple[int, int, int, int, int]
    chain: tuple[tuple[int, str, tuple[int, int, int, int, int]], ...]


def _flags(*, directory: bool) -> int:
    names = ["O_NOFOLLOW", "O_CLOEXEC"] + (["O_DIRECTORY"] if directory else [])
    if any(not hasattr(os, name) for name in names):
        raise Denied
    value = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    return value | (os.O_DIRECTORY if directory else 0)


def _open_chain(
    start_fd: int,
    parts: Sequence[str],
    owned: list[int],
    *,
    final_directory: bool = False,
) -> Handle:
    parent = start_fd
    chain: list[tuple[int, str, tuple[int, int, int, int, int]]] = []
    try:
        for index, part in enumerate(parts):
            directory = index < len(parts) - 1 or final_directory
            fd = os.open(part, _flags(directory=directory), dir_fd=parent)
            owned.append(fd)
            info = os.fstat(fd)
            if directory and not stat.S_ISDIR(info.st_mode):
                raise OSError
            if not directory and not stat.S_ISREG(info.st_mode):
                raise OSError
            chain.append((parent, part, _identity(info)))
            parent = fd
        return Handle(parent, chain[-1][2], tuple(chain))
    except (OSError, ValueError):
        raise Denied from None


def _audit(handles: Sequence[Handle]) -> None:
    try:
        for handle in handles:
            if _identity(os.fstat(handle.fd)) != handle.identity:
                raise Denied
            for parent, name, before in handle.chain:
                current = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if _identity(current) != before:
                    raise Denied
    except OSError:
        raise Denied from None


def _read(handle: Handle) -> bytes:
    try:
        before = os.fstat(handle.fd)
        if before.st_size > MAX_BYTES:
            raise Denied
        chunks: list[bytes] = []
        remaining = MAX_BYTES + 1
        while remaining:
            chunk = os.read(handle.fd, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(handle.fd)
        if len(raw) > MAX_BYTES or len(raw) != before.st_size:
            raise Denied
        if _identity(before) != _identity(after):
            raise Denied
        return raw
    except OSError:
        raise Denied from None


def _parse(raw: bytes) -> Any:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_duplicates,
            parse_constant=_nonfinite,
        )
    except Denied:
        raise
    except (UnicodeError, ValueError, RecursionError):
        raise Denied from None
    stack = [(value, 1)]
    nodes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if depth > MAX_DEPTH or nodes > MAX_NODES:
            raise Denied
        if type(current) is dict:
            if len(current) > MAX_MEMBERS:
                raise Denied
            stack.extend((item, depth + 1) for item in current.values())
        elif type(current) is list:
            if len(current) > MAX_MEMBERS:
                raise Denied
            stack.extend((item, depth + 1) for item in current)
    return value


def _normalize_key(key: str) -> str:
    return re.sub(r"[._-]+", "_", key.lower())


def _scan_string(value: str, owning_key: str | None) -> None:
    normalized = _normalize_key(owning_key) if owning_key is not None else None
    if TOKEN.search(value) or BEARER.search(value) or JWT.fullmatch(value):
        raise Denied
    if ASSIGNMENT.fullmatch(value) or PEM.search(value):
        raise Denied
    if owning_key == DOMAIN_KEY:
        if value != DOMAIN_HEX:
            raise Denied
        return
    if PRIVATE_SHADOW.fullmatch(value):
        return
    if PRIVATE_SHADOW_RESERVED.search(value):
        raise Denied
    if normalized in DIGEST_KEYS:
        if not HEX64.fullmatch(value):
            raise Denied
        return
    if BARE_HEX.fullmatch(value):
        raise Denied


def _scan(value: Any, owning_key: str | None = None) -> None:
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str or _normalize_key(key) in FORBIDDEN_KEYS:
                raise Denied
            _scan_string(key, None)
            _scan(item, key)
    elif type(value) is list:
        for item in value:
            _scan(item, owning_key)
    elif type(value) is str:
        _scan_string(value, owning_key)


def _canonical(value: Any, *, newline: bool) -> bytes:
    try:
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except (TypeError, ValueError):
        raise Denied from None
    return (text + ("\n" if newline else "")).encode("utf-8")


def _schema_shape(schema: Any) -> None:
    if type(schema) is not dict or not _exact_equal(schema, _expected_schema()):
        raise Denied


def _schema_validate(schema: dict[str, Any], value: Any) -> None:
    if type(value) is not dict:
        raise Denied
    properties = schema["properties"]
    if set(value) != set(schema["required"]):
        raise Denied
    for key, definition in properties.items():
        item = value[key]
        expected = definition["type"]
        if expected == "string" and type(item) is not str:
            raise Denied
        if expected == "integer" and type(item) is not int:
            raise Denied
        if "const" in definition and item != definition["const"]:
            raise Denied
        if "pattern" in definition and re.search(definition["pattern"], item) is None:
            raise Denied


def _manifest(value: Any) -> tuple[str, str]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "artifact_kind",
        "algorithm",
        "baseline_state",
        "scope",
        "files",
        "closure",
    }:
        raise Denied
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise Denied
    if value["artifact_kind"] != "subject-distillation-baseline":
        raise Denied
    if value["baseline_state"] != "frozen":
        raise Denied
    algorithm = value["algorithm"]
    if type(algorithm) is not dict or set(algorithm) != {
        "name",
        DOMAIN_KEY,
        "digest",
        "baseline_id_hex_length",
    }:
        raise Denied
    if algorithm != {
        "name": "subject-distillation-baseline-v1",
        DOMAIN_KEY: DOMAIN_HEX,
        "digest": "sha256",
        "baseline_id_hex_length": 16,
    }:
        raise Denied
    scope = value["scope"]
    if type(scope) is not dict or set(scope) != {
        "generic_subject_core",
        "person_v1",
        "organization",
    }:
        raise Denied
    if (
        type(scope["generic_subject_core"]) is not bool
        or scope["generic_subject_core"] is not True
        or type(scope["person_v1"]) is not bool
        or scope["person_v1"] is not True
        or type(scope["organization"]) is not str
        or scope["organization"] != "contract-only"
    ):
        raise Denied
    files = value["files"]
    if type(files) is not list or len(files) != len(CANONICAL_PATHS):
        raise Denied
    payload = bytearray(b"subject-distillation-baseline-v1\n")
    for expected, entry in zip(CANONICAL_PATHS, files, strict=True):
        if type(entry) is not dict or set(entry) != {"path", "sha256", "size_bytes"}:
            raise Denied
        if entry["path"] != expected or not HEX64.fullmatch(entry["sha256"]):
            raise Denied
        if type(entry["size_bytes"]) is not int or entry["size_bytes"] < 0:
            raise Denied
        payload.extend(
            expected.encode()
            + b"\0"
            + entry["sha256"].encode()
            + b"\0"
            + str(entry["size_bytes"]).encode()
            + b"\n"
        )
    closure = value["closure"]
    if type(closure) is not dict or set(closure) != {"baseline_id", "full_digest"}:
        raise Denied
    full = hashlib.sha256(payload).hexdigest()
    if closure["full_digest"] != full or closure["baseline_id"] != full[:16]:
        raise Denied
    return closure["baseline_id"], closure["full_digest"]


def _bind_manifest_files(
    value: dict[str, Any],
    repo: Handle,
    owned: list[int],
    handles: list[Handle],
) -> None:
    for entry in value["files"]:
        handle = _open_chain(repo.fd, entry["path"].split("/"), owned)
        handles.append(handle)
        raw = _read(handle)
        if len(raw) != entry["size_bytes"]:
            raise Denied
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise Denied


def _sorted_unique_strings(value: Any, minimum: int, maximum: int) -> list[str]:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise Denied
    if any(type(item) is not str or not item.isascii() for item in value):
        raise Denied
    if value != sorted(value) or len(set(value)) != len(value):
        raise Denied
    return value


def _scope(value: Any, baseline_id: str, full_digest: str, task: str, raw: bytes) -> str:
    keys = {
        "schema_version",
        "artifact_kind",
        "baseline_id",
        "baseline_full_digest",
        "authorized_task",
        "allowed_repo_relative_paths",
        "non_goals",
        "prohibited_operations",
    }
    if type(value) is not dict or set(value) != keys:
        raise Denied
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise Denied
    if value["artifact_kind"] != "subject-distillation-implementation-scope":
        raise Denied
    if (value["baseline_id"], value["baseline_full_digest"], value["authorized_task"]) != (
        baseline_id,
        full_digest,
        task,
    ):
        raise Denied
    paths = _sorted_unique_strings(value["allowed_repo_relative_paths"], 1, 64)
    for path in paths:
        parts = path.split("/")
        if not 1 <= len(path) <= 256 or path.startswith("/") or "\\" in path:
            raise Denied
        if any(
            not part
            or part in {".", ".."}
            or any(ord(c) < 32 or ord(c) == 127 for c in part)
            for part in parts
        ):
            raise Denied
    non_goals = _sorted_unique_strings(value["non_goals"], 1, 16)
    if any(not 1 <= len(item) <= 128 or not NON_GOAL.fullmatch(item) for item in non_goals):
        raise Denied
    operations = _sorted_unique_strings(value["prohibited_operations"], 1, 16)
    if any(item not in PROHIBITED for item in operations):
        raise Denied
    if not PROHIBITED - {"migration", "product_runtime"} <= set(operations):
        raise Denied
    if raw != _canonical(value, newline=True):
        raise Denied
    return hashlib.sha256(raw).hexdigest()


def _timestamp(value: Any) -> datetime:
    if type(value) is not str or TIME.fullmatch(value) is None:
        raise Denied
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise Denied from None
    if parsed.tzinfo != timezone.utc:
        raise Denied
    return parsed


def _arguments(argv: Sequence[str]) -> dict[str, str]:
    value_flags = {
        "--receipt",
        "--expected-receipt-sha256",
        "--scope",
        "--manifest",
        "--schema",
        "--expected-authority",
        "--expected-task",
    }
    result: dict[str, str] = {}
    index = 0
    json_seen = False
    while index < len(argv):
        flag = argv[index]
        if flag == "--json":
            if json_seen:
                raise Denied
            json_seen = True
            index += 1
            continue
        if flag not in value_flags or flag in result or index + 1 >= len(argv):
            raise Denied
        value = argv[index + 1]
        if value.startswith("--"):
            raise Denied
        result[flag] = value
        index += 2
    if not json_seen or set(result) != value_flags:
        raise Denied
    return result


def _absolute_parts(path: str) -> tuple[str, ...]:
    if not path.startswith("/") or "\0" in path or "\\" in path:
        raise Denied
    parts = path.split("/")[1:]
    if not parts or any(not part or part in {".", ".."} for part in parts):
        raise Denied
    return tuple(parts)


def _repo_root(root_fd: int, owned: list[int]) -> tuple[str, Handle]:
    try:
        process = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if process.returncode != 0:
            raise Denied
        text = process.stdout.decode("utf-8", "strict")
    except (OSError, UnicodeError):
        raise Denied from None
    if not text.endswith("\n") or "\n" in text[:-1]:
        raise Denied
    path = text[:-1]
    if path != os.getcwd():
        raise Denied
    handle = _open_chain(root_fd, _absolute_parts(path), owned, final_directory=True)
    try:
        dot_fd = os.open(".", _flags(directory=True))
        owned.append(dot_fd)
        if _identity(os.fstat(dot_fd)) != handle.identity:
            raise Denied
    except OSError:
        raise Denied from None
    return path, handle


def _verify(argv: Sequence[str], now: datetime | None, fault: Callable[[], None] | None) -> dict[str, str]:
    args = _arguments(argv)
    if not HEX64.fullmatch(args["--expected-receipt-sha256"]):
        raise Denied
    if args["--expected-authority"] != "github:zycaskevin":
        raise Denied
    if not TASK.fullmatch(args["--expected-task"]):
        raise Denied
    if args["--manifest"] != MANIFEST_PATH or args["--schema"] != SCHEMA_PATH:
        raise Denied
    owned: list[int] = []
    handles: list[Handle] = []
    try:
        root_fd = os.open("/", _flags(directory=True))
        owned.append(root_fd)
        repo_path, repo = _repo_root(root_fd, owned)
        handles.append(repo)
        receipt_path = args["--receipt"]
        scope_path = args["--scope"]
        for path in (receipt_path, scope_path):
            if path == repo_path or path.startswith(repo_path + "/"):
                raise Denied
        receipt_handle = _open_chain(root_fd, _absolute_parts(receipt_path), owned)
        scope_handle = _open_chain(root_fd, _absolute_parts(scope_path), owned)
        manifest_handle = _open_chain(repo.fd, MANIFEST_PATH.split("/"), owned)
        schema_handle = _open_chain(repo.fd, SCHEMA_PATH.split("/"), owned)
        verifier_handle = _open_chain(repo.fd, VERIFIER_PATH.split("/"), owned)
        handles.extend(
            [receipt_handle, scope_handle, manifest_handle, schema_handle, verifier_handle]
        )
        receipt_raw = _read(receipt_handle)
        scope_raw = _read(scope_handle)
        manifest_raw = _read(manifest_handle)
        schema_raw = _read(schema_handle)
        verifier_raw = _read(verifier_handle)
        if hashlib.sha256(receipt_raw).hexdigest() != args["--expected-receipt-sha256"]:
            raise Denied
        receipt = _parse(receipt_raw)
        scope = _parse(scope_raw)
        manifest = _parse(manifest_raw)
        schema = _parse(schema_raw)
        for artifact in (receipt, scope, manifest, schema):
            _scan(artifact)
        baseline_id, full_digest = _manifest(manifest)
        _bind_manifest_files(manifest, repo, owned, handles)
        _schema_shape(schema)
        _schema_validate(schema, receipt)
        scope_digest = _scope(
            scope, baseline_id, full_digest, args["--expected-task"], scope_raw
        )
        if receipt_raw != _canonical(receipt, newline=True):
            raise Denied
        if receipt["authorizing_principal"] != args["--expected-authority"]:
            raise Denied
        if receipt["authorized_task"] != args["--expected-task"]:
            raise Denied
        if (receipt["baseline_id"], receipt["baseline_full_digest"]) != (
            baseline_id,
            full_digest,
        ):
            raise Denied
        if receipt["scope_sha256"] != scope_digest:
            raise Denied
        if receipt["authorization_schema_sha256"] != hashlib.sha256(schema_raw).hexdigest():
            raise Denied
        if receipt["authorization_verifier_sha256"] != hashlib.sha256(verifier_raw).hexdigest():
            raise Denied
        without_id = dict(receipt)
        without_id.pop("authorization_id")
        expected_id = hashlib.sha256(_canonical(without_id, newline=False)).hexdigest()
        if receipt["authorization_id"] != expected_id:
            raise Denied
        issued = _timestamp(receipt["issued_at_utc"])
        expires = _timestamp(receipt["expires_at_utc"])
        current = now if now is not None else datetime.now(timezone.utc)
        if current.tzinfo != timezone.utc or issued >= expires or current >= expires:
            raise Denied
        _audit(handles)
        if fault is not None:
            fault()
        _audit(handles)
        return {
            "authorization_id": receipt["authorization_id"],
            "authorized_task": receipt["authorized_task"],
            "baseline_id": baseline_id,
            "status": "PASS",
        }
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def main(
    argv: Sequence[str] | None = None,
    *,
    _now: datetime | None = None,
    _fault: Callable[[], None] | None = None,
) -> int:
    try:
        result = _verify(sys.argv[1:] if argv is None else argv, _now, _fault)
    except Denied:
        sys.stderr.write(DENY)
        return 2
    except Exception:  # noqa: BLE001 - the public CLI must redact unexpected faults
        sys.stderr.write(ERROR)
        return 3
    sys.stdout.write(_canonical(result, newline=True).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
