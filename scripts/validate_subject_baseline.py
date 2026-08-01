"""Validate the content-addressed Subject Distillation baseline manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, NamedTuple

CANONICAL_PATHS = (
    "specs/subject-distillation/requirements.md",
    "specs/subject-distillation/design.md",
    "specs/subject-distillation/tasks.md",
    "specs/subject-distillation/traceability.md",
    "specs/subject-distillation/schema.v15.sql",
)
MANIFEST_PATH = "specs/subject-distillation/baseline-manifest.json"
MANIFEST_MAX_BYTES = 64 * 1024
CANONICAL_MAX_BYTES = 512 * 1024
CANONICAL_TOTAL_MAX_BYTES = 2 * 1024 * 1024
DOMAIN_SEPARATOR_UTF8_HEX = "7375626a6563742d64697374696c6c6174696f6e2d626173656c696e652d76310a"
EXPECTED_DOMAIN = b"subject-distillation-baseline-v1\n"
HEX = frozenset("0123456789abcdef")
TOP_KEYS = {"schema_version", "artifact_kind", "algorithm", "baseline_state", "scope", "files", "closure"}
ALGORITHM_KEYS = {"name", "domain_separator_utf8_hex", "digest", "baseline_id_hex_length"}
SCOPE_KEYS = {"generic_subject_core", "person_v1", "organization"}
FILE_KEYS = {"path", "sha256", "size_bytes"}
CLOSURE_KEYS = {"full_digest", "baseline_id"}


class ValidationError(Exception):
    """A content-redacted validation failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError("duplicate_json_key")
        result[key] = value
    return result


def _exact_dict(value: Any, keys: set[str], code: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise ValidationError(code)
    return value


def _exact_string(value: Any, expected: str, code: str) -> None:
    if type(value) is not str or value != expected:
        raise ValidationError(code)


def _lower_hex(value: Any, length: int, code: str) -> str:
    if type(value) is not str or len(value) != length or any(char not in HEX for char in value):
        raise ValidationError(code)
    return value


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _secure_flags(directory: bool = False) -> int:
    required = ("O_NOFOLLOW", "O_CLOEXEC")
    if directory:
        required += ("O_DIRECTORY",)
    if (
        not hasattr(os, "supports_dir_fd")
        or os.open not in os.supports_dir_fd
        or os.stat not in os.supports_dir_fd
        or not hasattr(os, "supports_follow_symlinks")
        or os.stat not in os.supports_follow_symlinks
    ):
        raise ValidationError("secure_filesystem_unavailable")
    if any(not hasattr(os, name) for name in required):
        raise ValidationError("secure_filesystem_unavailable")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    return flags | (os.O_DIRECTORY if directory else 0)


class _RetainedFile(NamedTuple):
    fd: int
    identity: tuple[int, int, int, int, int, int, int]
    chain: tuple[tuple[int, str, tuple[int, int, int, int, int, int, int]], ...]
    code: str


def _open_chain(root_fd: int, relative: str, code: str, owner: list[int]) -> _RetainedFile:
    checks: list[tuple[int, str, os.stat_result]] = []
    parent = root_fd
    try:
        parts = relative.split("/")
        for part in parts[:-1]:
            fd = os.open(part, _secure_flags(directory=True), dir_fd=parent)
            owner.append(fd)
            info = os.fstat(fd)
            if not stat.S_ISDIR(info.st_mode):
                raise OSError
            checks.append((parent, part, info))
            parent = fd
        fd = os.open(parts[-1], _secure_flags(), dir_fd=parent)
        owner.append(fd)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise OSError
        checks.append((parent, parts[-1], info))
        return _RetainedFile(
            fd,
            _identity(info),
            tuple((chain_parent, name, _identity(before)) for chain_parent, name, before in checks),
            code,
        )
    except (OSError, ValidationError):
        if sys.exc_info()[0] is ValidationError:
            raise
        raise ValidationError(code) from None


def _audit_retained(handles: list[_RetainedFile]) -> None:
    for handle in handles:
        try:
            if _identity(os.fstat(handle.fd)) != handle.identity:
                raise OSError
        except OSError:
            raise ValidationError(handle.code) from None
    depth = 1
    while any(len(handle.chain) >= depth for handle in handles):
        for handle in handles:
            if len(handle.chain) < depth:
                continue
            parent, name, before = handle.chain[-depth]
            try:
                current = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if _identity(current) != before:
                    raise OSError
            except OSError:
                raise ValidationError(handle.code) from None
        depth += 1


def _bounded_read(fd: int, maximum: int, too_large: str, invalid: str) -> bytes:
    before = os.fstat(fd)
    if before.st_size > maximum:
        raise ValidationError(too_large)
    chunks: list[bytes] = []
    remaining = maximum + 1
    try:
        while remaining:
            chunk = os.read(fd, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
    except OSError:
        raise ValidationError(invalid) from None
    if len(raw) > maximum:
        raise ValidationError(too_large)
    if _identity(after) != _identity(before) or len(raw) != before.st_size:
        raise ValidationError(invalid)
    return raw


def _bounded_hash(fd: int, maximum: int) -> tuple[int, str]:
    before = os.fstat(fd)
    if before.st_size > maximum:
        raise ValidationError("canonical_file_too_large")
    digest = hashlib.sha256()
    count = 0
    try:
        while count <= maximum:
            chunk = os.read(fd, min(64 * 1024, maximum + 1 - count))
            if not chunk:
                break
            count += len(chunk)
            digest.update(chunk)
        after = os.fstat(fd)
    except OSError:
        raise ValidationError("canonical_file_invalid") from None
    if count > maximum:
        raise ValidationError("canonical_file_too_large")
    if _identity(after) != _identity(before) or count != before.st_size:
        raise ValidationError("canonical_file_invalid")
    return count, digest.hexdigest()


def _load_manifest(handle: _RetainedFile) -> dict[str, Any]:
    raw = _bounded_read(
        handle.fd, MANIFEST_MAX_BYTES, "manifest_too_large", "manifest_file_invalid"
    )
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicates)
    except ValidationError:
        raise
    except (UnicodeError, json.JSONDecodeError):
        raise ValidationError("manifest_parse_failed") from None
    return _exact_dict(value, TOP_KEYS, "manifest_shape_invalid")


def validate(manifest_path: Path, repo_root: Path) -> dict[str, str]:
    """Validate the fixed manifest against files strictly beneath *repo_root*."""
    root_fd: int | None = None
    owned_fds: list[int] = []
    try:
        if manifest_path.is_absolute():
            expected = repo_root.absolute() / MANIFEST_PATH
            if manifest_path.absolute() != expected:
                raise ValidationError("manifest_path_invalid")
        elif manifest_path.as_posix() != MANIFEST_PATH:
            raise ValidationError("manifest_path_invalid")
        root_fd = os.open(os.fspath(repo_root), _secure_flags(directory=True))
        root_before = os.fstat(root_fd)
        if not stat.S_ISDIR(root_before.st_mode):
            raise OSError
        retained = [_open_chain(root_fd, MANIFEST_PATH, "manifest_file_invalid", owned_fds)]
        data = _load_manifest(retained[0])
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise ValidationError("schema_version_invalid")
        _exact_string(data["artifact_kind"], "subject-distillation-baseline", "artifact_kind_invalid")
        _exact_string(data["baseline_state"], "frozen", "baseline_state_invalid")

        algorithm = _exact_dict(data["algorithm"], ALGORITHM_KEYS, "algorithm_shape_invalid")
        _exact_string(algorithm["name"], "subject-distillation-baseline-v1", "algorithm_invalid")
        domain_hex = _lower_hex(algorithm["domain_separator_utf8_hex"], len(DOMAIN_SEPARATOR_UTF8_HEX), "algorithm_invalid")
        if domain_hex != DOMAIN_SEPARATOR_UTF8_HEX or bytes.fromhex(domain_hex) != EXPECTED_DOMAIN:
            raise ValidationError("algorithm_invalid")
        _exact_string(algorithm["digest"], "sha256", "algorithm_invalid")
        if type(algorithm["baseline_id_hex_length"]) is not int or algorithm["baseline_id_hex_length"] != 16:
            raise ValidationError("algorithm_invalid")

        scope = _exact_dict(data["scope"], SCOPE_KEYS, "scope_shape_invalid")
        if type(scope["generic_subject_core"]) is not bool or scope["generic_subject_core"] is not True:
            raise ValidationError("scope_invalid")
        if type(scope["person_v1"]) is not bool or scope["person_v1"] is not True:
            raise ValidationError("scope_invalid")
        _exact_string(scope["organization"], "contract-only", "scope_invalid")

        files = data["files"]
        if type(files) is not list or len(files) != len(CANONICAL_PATHS):
            raise ValidationError("canonical_file_set_invalid")
        payload = bytearray(EXPECTED_DOMAIN)
        total = 0
        for index, expected_path in enumerate(CANONICAL_PATHS):
            entry = _exact_dict(files[index], FILE_KEYS, "file_entry_shape_invalid")
            _exact_string(entry["path"], expected_path, "canonical_path_invalid")
            digest = _lower_hex(entry["sha256"], 64, "file_digest_invalid")
            size = entry["size_bytes"]
            if type(size) is not int or size < 0:
                raise ValidationError("file_size_invalid")
            if size > CANONICAL_MAX_BYTES or total + size > CANONICAL_TOTAL_MAX_BYTES:
                raise ValidationError("canonical_file_too_large")
            handle = _open_chain(root_fd, expected_path, "canonical_file_invalid", owned_fds)
            retained.append(handle)
            actual_size, actual_digest = _bounded_hash(handle.fd, CANONICAL_MAX_BYTES)
            total += actual_size
            if actual_size != size:
                raise ValidationError("file_size_mismatch")
            if actual_digest != digest:
                raise ValidationError("file_digest_mismatch")
            payload.extend(expected_path.encode("utf-8") + b"\0" + digest.encode("ascii") + b"\0" + str(size).encode("ascii") + b"\n")

        closure = _exact_dict(data["closure"], CLOSURE_KEYS, "closure_shape_invalid")
        recorded_full = _lower_hex(closure["full_digest"], 64, "full_digest_invalid")
        recorded_id = _lower_hex(closure["baseline_id"], 16, "baseline_id_invalid")
        computed_full = hashlib.sha256(payload).hexdigest()
        if recorded_full != computed_full:
            raise ValidationError("closure_mismatch")
        if recorded_id != computed_full[:16]:
            raise ValidationError("baseline_id_mismatch")
        _audit_retained(retained)
        if _identity(os.fstat(root_fd)) != _identity(root_before):
            raise ValidationError("repo_root_invalid")
        try:
            root_path_after = os.stat(repo_root, follow_symlinks=False)
        except OSError:
            raise ValidationError("repo_root_invalid") from None
        if _identity(root_path_after) != _identity(root_before):
            raise ValidationError("repo_root_invalid")
        return {"status": "PASS", "baseline_id": recorded_id, "full_digest": recorded_full}
    except ValidationError:
        raise
    except (OSError, TypeError, NotImplementedError):
        if root_fd is None:
            raise ValidationError("repo_root_invalid") from None
        raise ValidationError("secure_filesystem_unavailable") from None
    finally:
        for fd in reversed(owned_fds):
            os.close(fd)
        if root_fd is not None:
            os.close(root_fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=MANIFEST_PATH)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--json", action="store_true", help="emit one bounded JSON result")
    args = parser.parse_args(argv)
    try:
        result = validate(Path(args.manifest), Path(args.repo_root))
    except ValidationError as error:
        result = {"status": "FAIL", "code": error.code}
        if args.json:
            print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        else:
            print(f"FAIL: {error.code}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(f"PASS baseline_id={result['baseline_id']} full_digest={result['full_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
