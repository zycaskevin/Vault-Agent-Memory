#!/usr/bin/env python3
"""Fail-closed validator for public Subject Distillation evidence."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import run_subject_implementation_authorization as runner
    import validate_subject_baseline as baseline
    import verify_subject_implementation_authorization as authorization
except ImportError:  # pragma: no cover - import path used by test loaders
    from scripts import run_subject_implementation_authorization as runner
    from scripts import validate_subject_baseline as baseline
    from scripts import verify_subject_implementation_authorization as authorization


DENY_TEXT = "SUBJECT_EVIDENCE_DENY\n"
ERROR_TEXT = "SUBJECT_EVIDENCE_ERROR\n"
MAX_BYTES = 1_048_576
SCHEMA_DIR = "specs/subject-distillation/evidence-schemas"
MANIFEST_PATH = "specs/subject-distillation/baseline-manifest.json"
RUNNER_PATH = "scripts/run_subject_implementation_authorization.py"
KINDS = (
    "attestation",
    "backup-restore",
    "environment",
    "fresh-review",
    "migration",
    "unit",
    "fixture",
    "surface",
    "legacy",
)
HEX16 = re.compile(r"[0-9a-f]{16}")
HEX64 = re.compile(r"[0-9a-f]{64}")
GIT_REF = re.compile(r"git:(?:[0-9a-f]{40}|[0-9a-f]{64})")
OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
STAGES = ("unit", "fixture", "surface", "legacy")
STAGE_REQUIRES = {"unit": None, "fixture": "unit", "surface": "fixture", "legacy": "surface"}
STAGE_COMMANDS = {
    "unit": "python -m pytest -q tests/test_subject_assertions.py tests/test_subject_auth.py tests/test_subject_candidates.py tests/test_subject_context.py tests/test_subject_contracts.py tests/test_subject_counterparty.py tests/test_subject_db_schema.py tests/test_subject_decisions.py tests/test_subject_evaluation.py tests/test_subject_evidence.py tests/test_subject_fragments.py tests/test_subject_grants.py tests/test_subject_migration_deferred_fk.py tests/test_subject_models.py tests/test_subject_policy.py tests/test_subject_privacy_gate.py tests/test_subject_private_evidence.py tests/test_subject_progress.py tests/test_subject_purge.py tests/test_subject_relationship_expiry.py tests/test_subject_relationships.py tests/test_subject_setup.py tests/test_subject_store.py tests/test_subject_store_failure.py tests/test_memory_curator.py tests/test_agent_setup.py",
    "fixture": "python scripts/run_subject_sbe_fixture_gate.py --mapping specs/subject-distillation/sbe-traceability.json --require-count 43 --extra tests/test_subject_fixture_privacy.py tests/test_subject_sbe_traceability.py tests/test_subject_organization_contract.py tests/test_subject_migration.py tests/test_db_migrations.py tests/test_db_backup.py",
    "surface": "python -m pytest -q tests/test_subject_cli.py tests/test_subject_mcp.py tests/test_gateway.py tests/test_cli_json_contract.py tests/test_mcp_memory.py",
    "legacy": "python scripts/run_subject_legacy_gate.py --pytest 'python -m pytest -q' --ruff 'ruff check vault tests scripts' --readme-smoke 'python scripts/readme_command_smoke.py' --release-parity 'python scripts/check_release_parity.py' --diff-check 'git diff --check'",
}
STAGE_ARGV = {name: shlex.split(command) for name, command in STAGE_COMMANDS.items()}
KNOWN_EVIDENCE_FILES = {
    "environment.json",
    "migration.json",
    "backup-restore.json",
    "fresh-review.json",
    "attestation.json",
    "unit.txt",
    "fixture.txt",
    "surface.txt",
    "legacy.txt",
}
REVIEW_FILES = {
    "requirements-architecture.json",
    "security-privacy.json",
    "execution-traceability.json",
}
REVIEW_TASKS_SHA256 = "0150935a1a16e51dc30dff9dff8d01104d7127ee3cf57333caec7586d93f5007"
REVIEW_LITERAL_PATHS = (
    "CHANGELOG.md",
    "README.md",
    "README.zh-CN.md",
    "README.zh-Hant.md",
    "SCHEMA.md",
    "docs/memory_governance.md",
    "docs/subject_operations.md",
    "scripts/attest_subject_closure.py",
    "scripts/capture_subject_closure.py",
    "scripts/capture_subject_recovery_evidence.py",
    "scripts/export_subject_sbe_traceability.py",
    "scripts/hash_subject_review_tree.py",
    "scripts/read_subject_baseline_id.py",
    "scripts/record_subject_fresh_review.py",
    "scripts/run_subject_legacy_gate.py",
    "scripts/run_subject_sbe_fixture_gate.py",
    "scripts/update_subject_progress.py",
    "scripts/validate_subject_baseline.py",
    "scripts/validate_subject_evidence.py",
    "scripts/validate_subject_progress.py",
    "specs/subject-distillation/design.md",
    "specs/subject-distillation/evidence-schemas/attestation.schema.json",
    "specs/subject-distillation/evidence-schemas/backup-restore.schema.json",
    "specs/subject-distillation/evidence-schemas/environment.schema.json",
    "specs/subject-distillation/evidence-schemas/fresh-review.schema.json",
    "specs/subject-distillation/evidence-schemas/migration.schema.json",
    "specs/subject-distillation/evidence-schemas/review-result.schema.json",
    "specs/subject-distillation/implementation-progress.schema.json",
    "specs/subject-distillation/requirements.md",
    "specs/subject-distillation/sbe-traceability.json",
    "specs/subject-distillation/schema.v15.sql",
    "specs/subject-distillation/tasks.md",
    "specs/subject-distillation/traceability.md",
    "tests/fixtures/subject_distillation/manifest.json",
    "tests/test_cli_json_contract.py",
    "tests/test_db_backup.py",
    "tests/test_gateway.py",
    "tests/test_subject_assertions.py",
    "tests/test_subject_attestation.py",
    "tests/test_subject_auth.py",
    "tests/test_subject_baseline_control.py",
    "tests/test_subject_candidates.py",
    "tests/test_subject_cli.py",
    "tests/test_subject_context.py",
    "tests/test_subject_contracts.py",
    "tests/test_subject_counterparty.py",
    "tests/test_subject_db_schema.py",
    "tests/test_subject_decisions.py",
    "tests/test_subject_evaluation.py",
    "tests/test_subject_evidence.py",
    "tests/test_subject_fixture_privacy.py",
    "tests/test_subject_fragments.py",
    "tests/test_subject_grants.py",
    "tests/test_subject_mcp.py",
    "tests/test_subject_migration.py",
    "tests/test_subject_migration_deferred_fk.py",
    "tests/test_subject_models.py",
    "tests/test_subject_organization_contract.py",
    "tests/test_subject_policy.py",
    "tests/test_subject_privacy_gate.py",
    "tests/test_subject_private_evidence.py",
    "tests/test_subject_progress.py",
    "tests/test_subject_purge.py",
    "tests/test_subject_relationship_expiry.py",
    "tests/test_subject_relationships.py",
    "tests/test_subject_sbe_traceability.py",
    "tests/test_subject_setup.py",
    "tests/test_subject_store.py",
    "tests/test_subject_store_failure.py",
    "vault/agent_setup.py",
    "vault/cli.py",
    "vault/cli_flow.py",
    "vault/cli_quickstart.py",
    "vault/cli_subject.py",
    "vault/db.py",
    "vault/db_backup.py",
    "vault/db_migrations.py",
    "vault/db_runtime.py",
    "vault/db_schema.py",
    "vault/db_subject_schema.py",
    "vault/db_subject_store.py",
    "vault/gateway.py",
    "vault/gateway_openapi.py",
    "vault/gateway_subject.py",
    "vault/mcp_subject.py",
    "vault/mcp_tools.py",
    "vault/memory.py",
    "vault/subject_assertions.py",
    "vault/subject_auth.py",
    "vault/subject_candidates.py",
    "vault/subject_context.py",
    "vault/subject_contracts.py",
    "vault/subject_decisions.py",
    "vault/subject_evaluation.py",
    "vault/subject_evidence.py",
    "vault/subject_fragments.py",
    "vault/subject_models.py",
    "vault/subject_policy.py",
    "vault/subject_privacy.py",
    "vault/subject_private_evidence.py",
    "vault/subject_relationships.py",
    "vault/subject_service.py",
)
REVIEW_GLOB_PATTERNS = (
    "tests/fixtures/subject_distillation/fragments/*.json",
    "tests/fixtures/subject_distillation/migration/*.json",
    "tests/fixtures/subject_distillation/organization/*.json",
    "tests/fixtures/subject_distillation/person/*.json",
)
REVIEW_EXCLUDED_PREFIX = "specs/subject-distillation/evidence/"
REVIEW_EXCLUDED_PATHS = {"specs/subject-distillation/implementation-progress.json"}
MAX_REVIEW_PATHS = 256
MAX_REVIEW_BYTES = 83_886_080
REVIEW_ROOT_FILES = {
    "CHANGELOG.md",
    "README.md",
    "README.zh-CN.md",
    "README.zh-Hant.md",
    "SCHEMA.md",
}
REVIEW_REQUIRED_PATHS = {
    "CHANGELOG.md",
    "scripts/attest_subject_closure.py",
    "scripts/update_subject_progress.py",
    "scripts/validate_subject_progress.py",
    "specs/subject-distillation/design.md",
    "specs/subject-distillation/implementation-progress.schema.json",
    "specs/subject-distillation/requirements.md",
    "specs/subject-distillation/schema.v15.sql",
    "specs/subject-distillation/tasks.md",
    "specs/subject-distillation/traceability.md",
    "tests/test_subject_attestation.py",
    "tests/test_subject_progress.py",
}


class Denied(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise Denied


def _canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise Denied from None


def _scan_public(value: Any) -> None:
    try:
        authorization._scan(value)
    except authorization.Denied:
        raise Denied from None


def _closed(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _string(*, const: str | None = None, pattern: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "string"}
    if const is not None:
        result["const"] = const
    if pattern is not None:
        result["pattern"] = pattern
    return result


def _integer(minimum: int = 0, maximum: int = 65_535) -> dict[str, Any]:
    return {"type": "integer", "minimum": minimum, "maximum": maximum}


def _array(items: dict[str, Any], minimum: int, maximum: int) -> dict[str, Any]:
    return {
        "type": "array",
        "items": items,
        "minItems": minimum,
        "maxItems": maximum,
    }


def _common(kind: str, task: str) -> dict[str, Any]:
    return {
        "schema_version": {"type": "integer", "const": 1},
        "artifact_kind": _string(const=kind),
        "baseline_id": _string(pattern="^[0-9a-f]{16}$"),
        "source_commit": _string(pattern="^git:(?:[0-9a-f]{40}|[0-9a-f]{64})$"),
        "created_at_utc": _string(pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"),
        "producer_task": _string(const=task),
    }


def _hash_entry() -> dict[str, Any]:
    return _closed(
        {
            "path": _string(pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$"),
            "sha256": _string(pattern="^[0-9a-f]{64}$"),
        }
    )


def _proof_schema() -> dict[str, Any]:
    return _closed(
        {
            "schema_version": {"type": "integer", "const": 1},
            "artifact_kind": _string(const="subject-distillation-implementation-authorization-proof"),
            "status": _string(const="PASS"),
            "authorized_task": _string(const="T-001"),
            "implementation_base_commit": _string(pattern="^git:(?:[0-9a-f]{40}|[0-9a-f]{64})$"),
            "baseline_id": _string(pattern="^[0-9a-f]{16}$"),
            "baseline_full_digest": _string(pattern="^[0-9a-f]{64}$"),
            "authorizing_principal": _string(const="github:zycaskevin"),
            "allowed_repo_relative_paths": _array(_string(pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$"), 16, 16),
            "non_goals": _array(_string(pattern=r"^[a-z][a-z0-9._:-]{0,127}$"), 4, 4),
            "prohibited_operations": _array(_string(pattern=r"^[a-z][a-z0-9_]{0,127}$"), 7, 7),
            "issued_at_utc": _string(pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"),
            "expires_at_utc": _string(pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"),
            "recorded_at_utc": _string(pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"),
            "scope_sha256": _string(pattern="^[0-9a-f]{64}$"),
            "receipt_sha256": _string(pattern="^[0-9a-f]{64}$"),
            "authorization_verifier_sha256": _string(pattern="^[0-9a-f]{64}$"),
            "authorization_schema_sha256": _string(pattern="^[0-9a-f]{64}$"),
            "authorization_id": _string(pattern="^[0-9a-f]{64}$"),
            "authorization_pass_packet_sha256": _string(pattern="^[0-9a-f]{64}$"),
            "proposal_id": _string(pattern="^[0-9a-f]{64}$"),
            "runner": _closed(
                {
                    "path": _string(const="scripts/run_subject_implementation_authorization.py"),
                    "sha256": _string(pattern="^[0-9a-f]{64}$"),
                }
            ),
            "owner_confirmation_ref": _string(pattern="^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
        }
    )


def _expected_schemas() -> dict[str, dict[str, Any]]:
    prefix = "https://vault-agent-memory.invalid/subject-distillation/"
    schemas: dict[str, dict[str, Any]] = {}

    env = _common("subject-distillation-environment", "T-001")
    env.update(
        {
            "git_status": _closed(
                {
                    "captured_phase": _string(const="pre_implementation"),
                    "clean": {"type": "boolean", "const": True},
                    "head_kind": {"type": "string", "enum": ["branch", "detached"]},
                }
            ),
            "python": _closed(
                {
                    "implementation": _string(const="CPython"),
                    "version": _array(_integer(0, 999), 3, 3),
                }
            ),
            "sqlite": _closed({"version": _array(_integer(0, 999), 3, 3)}),
            "schema_contract_version": _integer(0, 65_535),
            "normative_hashes": _array(_hash_entry(), 5, 5),
            "implementation_authorization": _proof_schema(),
        }
    )
    schemas["environment"] = _closed(env)

    for name, kind in (
        ("migration", "subject-distillation-migration-evidence"),
        ("backup-restore", "subject-distillation-backup-restore-evidence"),
    ):
        props = _common(kind, "T-027")
        props.update(
            {
                "command": _array(_string(pattern=r"^[ -~]{1,256}$"), 6, 6),
                "exit_code": _integer(0, 255),
                "input_hash": _string(pattern="^[0-9a-f]{64}$"),
                "output_hash": _string(pattern="^[0-9a-f]{64}$"),
                "rollback_path": _closed(
                    {
                        "kind": _string(const="public_safe_locator"),
                        "id": _string(pattern="^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
                    }
                ),
                "result": {"type": "string", "enum": ["PASS", "FAIL"]},
            }
        )
        schemas[name] = _closed(props)

    finding = _closed(
        {
            "finding_id": _string(pattern="^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
            "severity": {"type": "string", "enum": ["P0", "P1", "P2"]},
            "summary_code": _string(pattern="^[A-Z][A-Z0-9_]{0,63}$"),
            "disposition": {"type": ["string", "null"], "enum": [None, "ACCEPTED", "DEFERRED", "FOLLOW_UP"]},
        }
    )
    review = _common("subject-distillation-review-result", "T-031")
    review.update(
        {
            "review_id": _string(pattern="^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
            "builder_principal": _string(pattern="^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
            "reviewer_principal": _string(pattern="^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
            "review_scope": {"type": "string", "enum": ["requirements-architecture", "security-privacy", "execution-traceability"]},
            "reviewed_normative_hashes": _array(_hash_entry(), 5, 5),
            "reviewed_tree_sha256": _string(pattern="^[0-9a-f]{64}$"),
            "p0": _integer(),
            "p1": _integer(),
            "p2": _integer(),
            "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
            "findings": _array(finding, 0, 256),
        }
    )
    schemas["review-result"] = _closed(review)

    review_projection = _closed(
        {
            "review_scope": {"type": "string", "enum": ["requirements-architecture", "security-privacy", "execution-traceability"]},
            "review_id": _string(pattern="^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
            "reviewer_principal": _string(pattern="^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
            "artifact_sha256": _string(pattern="^[0-9a-f]{64}$"),
            "p0": _integer(),
            "p1": _integer(),
            "p2": _integer(),
            "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
        }
    )
    fresh = _common("subject-distillation-fresh-review", "T-031")
    fresh.update(
        {
            "builder_principal": _string(pattern="^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
            "reviews": _array(review_projection, 3, 3),
            "reviewed_normative_hashes": _array(_hash_entry(), 5, 5),
            "reviewed_tree_sha256": _string(pattern="^[0-9a-f]{64}$"),
            "p0": _integer(),
            "p1": _integer(),
            "p2": _integer(),
            "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
        }
    )
    schemas["fresh-review"] = _closed(fresh)

    attestation = _common("subject-distillation-attestation", "T-033")
    attestation.update(
        {
            "artifact_sha256": _array(_hash_entry(), 15, 15),
            "implementation_authorization": _closed(
                {
                    "environment_path": _string(pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$"),
                    "environment_sha256": _string(pattern="^[0-9a-f]{64}$"),
                    "authorization_id": _string(pattern="^[0-9a-f]{64}$"),
                    "authorization_pass_packet_sha256": _string(pattern="^[0-9a-f]{64}$"),
                    "proposal_id": _string(pattern="^[0-9a-f]{64}$"),
                    "receipt_sha256": _string(pattern="^[0-9a-f]{64}$"),
                    "scope_sha256": _string(pattern="^[0-9a-f]{64}$"),
                    "owner_confirmation_ref": _string(pattern="^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
                    "status": _string(const="PASS"),
                }
            ),
            "reviewer_set": _array(
                _closed(
                    {
                        "review_scope": {"type": "string", "enum": ["requirements-architecture", "security-privacy", "execution-traceability"]},
                        "review_id": _string(pattern="^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
                        "reviewer_principal": _string(pattern="^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
                        "artifact_sha256": _string(pattern="^[0-9a-f]{64}$"),
                    }
                ),
                3,
                3,
            ),
            "reviewed_tree_sha256": _string(pattern="^[0-9a-f]{64}$"),
            "release_label": {"type": "string", "enum": ["experimental", "stable"]},
            "private_shadow_receipt_sha256": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
        }
    )
    schemas["attestation"] = _closed(attestation)

    for name, schema in schemas.items():
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = prefix + name + ".schema.json"
    return schemas


def _type_matches(expected: Any, value: Any) -> bool:
    values = expected if isinstance(expected, list) else [expected]
    for item in values:
        if item == "object" and type(value) is dict:
            return True
        if item == "array" and type(value) is list:
            return True
        if item == "string" and type(value) is str:
            return True
        if item == "integer" and type(value) is int:
            return True
        if item == "boolean" and type(value) is bool:
            return True
        if item == "null" and value is None:
            return True
    return False


def _validate_schema(schema: dict[str, Any], value: Any) -> None:
    expected = schema.get("type")
    if expected is not None and not _type_matches(expected, value):
        raise Denied
    if "const" in schema and value != schema["const"]:
        raise Denied
    if "enum" in schema and value not in schema["enum"]:
        raise Denied
    if type(value) is str:
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            raise Denied
    elif type(value) is int:
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            raise Denied
    elif type(value) is list:
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", len(value)):
            raise Denied
        for item in value:
            _validate_schema(schema["items"], item)
    elif type(value) is dict:
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is not False or set(value) != set(schema.get("required", [])):
            raise Denied
        for key, item in value.items():
            if key not in properties:
                raise Denied
            _validate_schema(properties[key], item)


def _read_file(path: Path, maximum: int = MAX_BYTES) -> bytes:
    owned: list[int] = []
    root_fd: int | None = None
    try:
        if not path.is_absolute():
            raise Denied
        root_fd = os.open("/", authorization._flags(directory=True))
        owned.append(root_fd)
        handle = authorization._open_chain(
            root_fd,
            authorization._absolute_parts(os.fspath(path)),
            owned,
        )
        before = os.fstat(handle.fd)
        if before.st_size > maximum:
            raise Denied
        raw = authorization._read(handle)
        authorization._audit([handle])
        if len(raw) > maximum:
            raise Denied
        return raw
    except authorization.Denied:
        raise Denied from None
    except OSError:
        raise Denied from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _read_large_file(path: Path, maximum: int) -> bytes:
    if maximum <= MAX_BYTES:
        return _read_file(path, maximum)
    owned: list[int] = []
    try:
        root_fd = os.open("/", authorization._flags(directory=True))
        owned.append(root_fd)
        handle = authorization._open_chain(
            root_fd, authorization._absolute_parts(os.fspath(path)), owned
        )
        before = os.fstat(handle.fd)
        if before.st_size > maximum:
            raise Denied
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(handle.fd, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(handle.fd)
        authorization._audit([handle])
        if len(raw) > maximum or len(raw) != before.st_size or authorization._identity(before) != authorization._identity(after):
            raise Denied
        return raw
    except (OSError, authorization.Denied):
        raise Denied from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _load_json(path: Path, *, canonical: bool = True) -> tuple[Any, bytes]:
    raw = _read_file(path)
    try:
        value = authorization._parse(raw)
    except authorization.Denied:
        raise Denied from None
    if canonical and raw != _canonical(value):
        raise Denied
    _scan_public(value)
    return value, raw


def _timestamp(value: str) -> datetime:
    if type(value) is not str or TIME.fullmatch(value) is None:
        raise Denied
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise Denied from None


def _git_object_hex_length(repo_root: Path) -> int:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-object-format"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        raise Denied from None
    if completed.returncode != 0 or completed.stderr or completed.stdout not in {
        b"sha1\n",
        b"sha256\n",
    }:
        raise Denied
    return 40 if completed.stdout == b"sha1\n" else 64


def _schema_version_at_commit(repo_root: Path, source_commit: str) -> int:
    if GIT_REF.fullmatch(source_commit) is None:
        raise Denied
    try:
        completed = subprocess.run(
            ["git", "show", f"{source_commit[4:]}:vault/db_schema.py"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        raise Denied from None
    if (
        completed.returncode != 0
        or completed.stderr
        or not completed.stdout
        or len(completed.stdout) > MAX_BYTES
    ):
        raise Denied
    try:
        tree = ast.parse(completed.stdout, filename="vault/db_schema.py")
    except (SyntaxError, ValueError):
        raise Denied from None
    versions: list[int] = []
    for node in tree.body:
        target = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
        elif isinstance(node, ast.AnnAssign):
            target = node.target
        if (
            isinstance(target, ast.Name)
            and target.id == "SCHEMA_VERSION"
            and isinstance(node.value, ast.Constant)
            and type(node.value.value) is int
        ):
            versions.append(node.value.value)
    if len(versions) != 1 or not 0 <= versions[0] <= 65_535:
        raise Denied
    return versions[0]


def _inventory(evidence_dir: Path) -> None:
    owned: list[int] = []
    try:
        anchor = os.open("/", authorization._flags(directory=True))
        owned.append(anchor)
        root = authorization._open_chain(
            anchor,
            authorization._absolute_parts(os.fspath(evidence_dir)),
            owned,
            final_directory=True,
        )
        authorization._audit([root])
        count = 0
        total = 0
        root_names = os.listdir(root.fd)
        if len(root_names) != len(set(root_names)):
            raise Denied
        for name in root_names:
            info = os.stat(name, dir_fd=root.fd, follow_symlinks=False)
            if stat.S_ISREG(info.st_mode) and name in KNOWN_EVIDENCE_FILES:
                count += 1
                total += info.st_size
            elif stat.S_ISDIR(info.st_mode) and name == "reviews":
                reviews = authorization._open_chain(
                    root.fd, ("reviews",), owned, final_directory=True
                )
                authorization._audit([root, reviews])
                names = os.listdir(reviews.fd)
                if set(names) != REVIEW_FILES or len(names) != len(set(names)):
                    raise Denied
                for child in names:
                    child_info = os.stat(
                        child, dir_fd=reviews.fd, follow_symlinks=False
                    )
                    if not stat.S_ISREG(child_info.st_mode):
                        raise Denied
                    count += 1
                    total += child_info.st_size
                authorization._audit([root, reviews])
            else:
                raise Denied
        authorization._audit([root])
        if count > 32 or total > 80 * 1024 * 1024:
            raise Denied
    except (OSError, authorization.Denied):
        raise Denied from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _safe_stream(raw: bytes, repo_root: Path) -> None:
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeError:
        raise Denied from None
    if b"\x00" in raw or b"\r" in raw:
        raise Denied
    home = os.path.expanduser("~")
    if home.encode() in raw or os.fspath(repo_root).encode() in raw:
        raise Denied
    for char in text:
        if unicodedata.category(char) in {"Cc", "Cf"} and char not in {"\t", "\n"}:
            raise Denied
    split = re.compile(r'''[\s"'()\[\]{}<>,;]+''')
    for line in text.splitlines():
        _scan_public(line)
        candidates = [token for token in split.split(line) if token]
        for token in list(candidates):
            if "=" in token:
                candidates.append(token.split("=", 1)[1])
            marker = re.match(r"(?i)(?:path|file|dir|cwd|root):(.*)", token)
            if marker is not None:
                candidates.append(marker.group(1))
        for token in candidates:
            if token.startswith(("/", "~/", "\\\\")) or re.match(r"^[A-Za-z]:[\\/]", token):
                raise Denied


def _split_stage(raw: bytes) -> tuple[bytes, bytes]:
    newline = raw.find(b"\n")
    if newline < 0 or newline + 1 > 65_536:
        raise Denied
    return raw[: newline + 1], raw[newline + 1 :]


def _validate_stage(
    repo_root: Path,
    path: Path,
    stage: str,
    manifest: dict[str, Any],
) -> None:
    raw = _read_large_file(path, 16_777_216)
    header_raw, body = _split_stage(raw)
    try:
        header = authorization._parse(header_raw)
    except authorization.Denied:
        raise Denied from None
    if type(header) is not dict or header_raw != _canonical(header):
        raise Denied
    keys = {
        "schema_version", "artifact_kind", "baseline_id", "source_commit",
        "created_at_utc", "producer_task", "stage", "requires", "argv",
        "started_at_utc", "completed_at_utc", "exit_code", "result",
        "stdout_size_bytes", "stderr_size_bytes", "stdout_sha256", "stderr_sha256",
    }
    if set(header) != keys:
        raise Denied
    _scan_public(header)
    if (
        type(header["schema_version"]) is not int
        or header["schema_version"] != 1
        or header["artifact_kind"] != "subject-distillation-stage-evidence"
        or header["baseline_id"] != manifest["closure"]["baseline_id"]
        or GIT_REF.fullmatch(header["source_commit"]) is None
        or len(header["source_commit"])
        != 4 + _git_object_hex_length(repo_root)
        or header["producer_task"] != "T-029"
        or header["stage"] != stage
        or header["requires"] != STAGE_REQUIRES[stage]
        or header["argv"] != STAGE_ARGV[stage]
        or type(header["exit_code"]) is not int
        or not -255 <= header["exit_code"] <= 255
        or header["result"] != "PASS"
        or header["exit_code"] != 0
    ):
        raise Denied
    _timestamp(header["created_at_utc"])
    started = _timestamp(header["started_at_utc"])
    completed = _timestamp(header["completed_at_utc"])
    if started > completed:
        raise Denied
    sizes = (header["stdout_size_bytes"], header["stderr_size_bytes"])
    if any(type(size) is not int or not 0 <= size <= 16_777_216 for size in sizes):
        raise Denied
    if len(body) != sum(sizes):
        raise Denied
    stdout = body[: sizes[0]]
    stderr = body[sizes[0] :]
    if hashlib.sha256(stdout).hexdigest() != header["stdout_sha256"] or hashlib.sha256(stderr).hexdigest() != header["stderr_sha256"]:
        raise Denied
    _safe_stream(stdout, repo_root)
    _safe_stream(stderr, repo_root)


def _manifest(repo_root: Path, manifest_path: Path) -> tuple[dict[str, Any], dict[str, str]]:
    try:
        result = baseline.validate(manifest_path, repo_root)
    except baseline.ValidationError:
        raise Denied from None
    value, _raw = _load_json(manifest_path, canonical=False)
    if type(value) is not dict:
        raise Denied
    return value, result


def _schema_files(repo_root: Path) -> dict[str, dict[str, Any]]:
    expected = _expected_schemas()
    for name, schema in expected.items():
        path = repo_root / SCHEMA_DIR / f"{name}.schema.json"
        value, raw = _load_json(path)
        if raw != _canonical(schema) or value != schema:
            raise Denied
    return expected


def _validate_common(
    value: dict[str, Any],
    manifest: dict[str, Any],
    schema: dict[str, Any],
    repo_root: Path,
) -> None:
    _validate_schema(schema, value)
    _scan_public(value)
    if value["baseline_id"] != manifest["closure"]["baseline_id"]:
        raise Denied
    _timestamp(value["created_at_utc"])
    if (
        GIT_REF.fullmatch(value["source_commit"]) is None
        or len(value["source_commit"]) != 4 + _git_object_hex_length(repo_root)
    ):
        raise Denied


def _validate_authorization(
    repo_root: Path,
    environment: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    proof = environment["implementation_authorization"]
    base_ref = proof["implementation_base_commit"]
    if base_ref != environment["source_commit"] or GIT_REF.fullmatch(base_ref) is None:
        raise Denied
    raw_base = base_ref[4:]
    issued = _timestamp(proof["issued_at_utc"])
    recorded = _timestamp(proof["recorded_at_utc"])
    expires = _timestamp(proof["expires_at_utc"])
    if not issued <= recorded < expires:
        raise Denied
    inputs = _authorization_repo_inputs(repo_root)
    proposal, receipt_raw, scope_raw = runner._derive(inputs, raw_base, "T-001", issued)
    runner_hash = hashlib.sha256(_read_file(repo_root / RUNNER_PATH)).hexdigest()
    packet = {
        "schema_version": 1,
        "artifact_kind": "subject-distillation-t001-authorization-pass-packet",
        "proposal": proposal,
        "runner_pass": {
            "authorization_id": proposal["authorization_id"],
            "authorized_task": "T-001",
            "baseline_id": proposal["baseline_id"],
            "status": "PASS",
        },
        "recorded_at_utc": proof["recorded_at_utc"],
        "owner_confirmation_ref": proof["owner_confirmation_ref"],
    }
    expected = {
        "schema_version": 1,
        "artifact_kind": "subject-distillation-implementation-authorization-proof",
        "status": "PASS",
        "authorized_task": "T-001",
        "implementation_base_commit": base_ref,
        "baseline_id": proposal["baseline_id"],
        "baseline_full_digest": proposal["baseline_full_digest"],
        "authorizing_principal": proposal["authorizing_principal"],
        "allowed_repo_relative_paths": proposal["allowed_repo_relative_paths"],
        "non_goals": proposal["non_goals"],
        "prohibited_operations": proposal["prohibited_operations"],
        "issued_at_utc": proposal["issued_at_utc"],
        "expires_at_utc": proposal["expires_at_utc"],
        "recorded_at_utc": proof["recorded_at_utc"],
        "scope_sha256": hashlib.sha256(scope_raw).hexdigest(),
        "receipt_sha256": hashlib.sha256(receipt_raw).hexdigest(),
        "authorization_verifier_sha256": proposal["authorization_verifier_sha256"],
        "authorization_schema_sha256": proposal["authorization_schema_sha256"],
        "authorization_id": proposal["authorization_id"],
        "authorization_pass_packet_sha256": hashlib.sha256(_canonical(packet)).hexdigest(),
        "proposal_id": proposal["proposal_id"],
        "runner": {"path": RUNNER_PATH, "sha256": runner_hash},
        "owner_confirmation_ref": proof["owner_confirmation_ref"],
    }
    if proof != expected or proof["baseline_id"] != manifest["closure"]["baseline_id"]:
        raise Denied


def _authorization_repo_inputs(repo_root: Path) -> runner.RepoInputs:
    """Read the B-000 trust inputs from the explicit repo, never process CWD."""
    verifier = runner.verifier
    owned: list[int] = []
    handles: list[Any] = []
    try:
        root_fd = os.open("/", verifier._flags(directory=True))
        owned.append(root_fd)
        repo = verifier._open_chain(
            root_fd,
            verifier._absolute_parts(os.fspath(repo_root)),
            owned,
            final_directory=True,
        )
        handles.append(repo)
        manifest_handle = verifier._open_chain(
            repo.fd, verifier.MANIFEST_PATH.split("/"), owned
        )
        schema_handle = verifier._open_chain(
            repo.fd, verifier.SCHEMA_PATH.split("/"), owned
        )
        verifier_handle = verifier._open_chain(
            repo.fd, verifier.VERIFIER_PATH.split("/"), owned
        )
        handles.extend([manifest_handle, schema_handle, verifier_handle])
        manifest_raw = verifier._read(manifest_handle)
        schema_raw = verifier._read(schema_handle)
        verifier_raw = verifier._read(verifier_handle)
        if verifier_raw != runner.VERIFIER_SOURCE:
            raise Denied
        manifest = verifier._parse(manifest_raw)
        schema = verifier._parse(schema_raw)
        verifier._scan(manifest)
        verifier._scan(schema)
        baseline_id, full_digest = verifier._manifest(manifest)
        verifier._bind_manifest_files(manifest, repo, owned, handles)
        verifier._schema_shape(schema)
        verifier._audit(handles)
        return runner.RepoInputs(
            baseline_id,
            full_digest,
            schema_raw,
            verifier_raw,
        )
    except (OSError, ValueError, verifier.Denied, runner.Denied):
        raise Denied from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _validate_environment(
    repo_root: Path,
    value: dict[str, Any],
    manifest: dict[str, Any],
    schema: dict[str, Any],
) -> None:
    _validate_common(value, manifest, schema, repo_root)
    if value["schema_contract_version"] != _schema_version_at_commit(
        repo_root, value["source_commit"]
    ):
        raise Denied
    if value["git_status"] not in (
        {"captured_phase": "pre_implementation", "clean": True, "head_kind": "branch"},
        {"captured_phase": "pre_implementation", "clean": True, "head_kind": "detached"},
    ):
        raise Denied
    if value["python"]["version"][0] != 3 or value["python"]["version"][1] < 10:
        raise Denied
    entries = [
        {"path": item["path"], "sha256": item["sha256"]}
        for item in manifest["files"]
    ]
    if value["normative_hashes"] != entries:
        raise Denied
    for item in entries:
        if hashlib.sha256(_read_file(repo_root / item["path"])).hexdigest() != item["sha256"]:
            raise Denied
    _validate_authorization(repo_root, value, manifest)


def _normative_entries(manifest: dict[str, Any]) -> list[dict[str, str]]:
    return [{"path": item["path"], "sha256": item["sha256"]} for item in manifest["files"]]


def _attestation_paths(baseline_id: str) -> list[str]:
    return sorted(
        [
            "specs/subject-distillation/baseline-manifest.json",
            "specs/subject-distillation/design.md",
            f"specs/subject-distillation/evidence/{baseline_id}/backup-restore.json",
            f"specs/subject-distillation/evidence/{baseline_id}/environment.json",
            f"specs/subject-distillation/evidence/{baseline_id}/fixture.txt",
            f"specs/subject-distillation/evidence/{baseline_id}/fresh-review.json",
            f"specs/subject-distillation/evidence/{baseline_id}/legacy.txt",
            f"specs/subject-distillation/evidence/{baseline_id}/migration.json",
            f"specs/subject-distillation/evidence/{baseline_id}/surface.txt",
            f"specs/subject-distillation/evidence/{baseline_id}/unit.txt",
            "specs/subject-distillation/requirements.md",
            "specs/subject-distillation/sbe-traceability.json",
            "specs/subject-distillation/schema.v15.sql",
            "specs/subject-distillation/tasks.md",
            "specs/subject-distillation/traceability.md",
        ]
    )


def _validate_simple(
    name: str,
    value: dict[str, Any],
    *,
    repo_root: Path,
    evidence_dir: Path,
    manifest: dict[str, Any],
) -> None:
    if name in {"migration", "backup-restore"}:
        expected = ["python", "-m", "pytest", "-q", "tests/test_subject_migration.py", "tests/test_db_backup.py"]
        if value["command"] != expected or (value["result"] == "PASS") != (value["exit_code"] == 0):
            raise Denied
    elif name == "review-result":
        findings = value["findings"]
        ids = [item["finding_id"] for item in findings]
        if ids != sorted(ids) or len(ids) != len(set(ids)) or value["builder_principal"] == value["reviewer_principal"]:
            raise Denied
        counts = {severity: sum(item["severity"] == severity for item in findings) for severity in ("P0", "P1", "P2")}
        if [value["p0"], value["p1"], value["p2"]] != [counts["P0"], counts["P1"], counts["P2"]]:
            raise Denied
        if any((item["severity"] in {"P0", "P1"}) != (item["disposition"] is None) for item in findings):
            raise Denied
        passed = value["p0"] == value["p1"] == 0 and all(item["severity"] != "P2" or item["disposition"] is not None for item in findings)
        if (value["verdict"] == "PASS") != passed:
            raise Denied
        if value["reviewed_normative_hashes"] != _normative_entries(manifest):
            raise Denied
    elif name == "fresh-review":
        scopes = [
            "requirements-architecture",
            "security-privacy",
            "execution-traceability",
        ]
        if [item["review_scope"] for item in value["reviews"]] != scopes:
            raise Denied
        principals = [item["reviewer_principal"] for item in value["reviews"]]
        if len(set(principals)) != 3 or value["builder_principal"] in principals:
            raise Denied
        actual: list[dict[str, Any]] = []
        for scope, projection in zip(scopes, value["reviews"], strict=True):
            review_path = evidence_dir / "reviews" / f"{scope}.json"
            review, raw = _load_json(review_path)
            if type(review) is not dict:
                raise Denied
            _validate_common(
                review,
                manifest,
                _expected_schemas()["review-result"],
                repo_root,
            )
            _validate_simple(
                "review-result",
                review,
                repo_root=repo_root,
                evidence_dir=evidence_dir,
                manifest=manifest,
            )
            if review["review_scope"] != scope or review["builder_principal"] != value["builder_principal"]:
                raise Denied
            actual.append(
                {
                    "review_scope": scope,
                    "review_id": review["review_id"],
                    "reviewer_principal": review["reviewer_principal"],
                    "artifact_sha256": hashlib.sha256(raw).hexdigest(),
                    "p0": review["p0"],
                    "p1": review["p1"],
                    "p2": review["p2"],
                    "verdict": review["verdict"],
                }
            )
        if value["reviews"] != actual:
            raise Denied
        counts = [sum(item[key] for item in actual) for key in ("p0", "p1", "p2")]
        if [value["p0"], value["p1"], value["p2"]] != counts:
            raise Denied
        if value["reviewed_normative_hashes"] != _normative_entries(manifest):
            raise Denied
        if len({value["reviewed_tree_sha256"], *(review["reviewed_tree_sha256"] for review in [
            _load_json(evidence_dir / "reviews" / f"{scope}.json")[0] for scope in scopes
        ])}) != 1:
            raise Denied
        passed = all(item["verdict"] == "PASS" for item in actual) and value["p0"] == value["p1"] == 0
        if (value["verdict"] == "PASS") != passed:
            raise Denied
    elif name == "attestation":
        baseline_id = manifest["closure"]["baseline_id"]
        paths = _attestation_paths(baseline_id)
        expected_entries = [
            {"path": path, "sha256": hashlib.sha256(_read_large_file(repo_root / path, 16_777_216)).hexdigest()}
            for path in paths
        ]
        if value["artifact_sha256"] != expected_entries:
            raise Denied
        environment_path = f"specs/subject-distillation/evidence/{baseline_id}/environment.json"
        environment, environment_raw = _load_json(repo_root / environment_path)
        _validate_environment(repo_root, environment, manifest, _expected_schemas()["environment"])
        proof = environment["implementation_authorization"]
        projection = {
            "environment_path": environment_path,
            "environment_sha256": hashlib.sha256(environment_raw).hexdigest(),
            "authorization_id": proof["authorization_id"],
            "authorization_pass_packet_sha256": proof["authorization_pass_packet_sha256"],
            "proposal_id": proof["proposal_id"],
            "receipt_sha256": proof["receipt_sha256"],
            "scope_sha256": proof["scope_sha256"],
            "owner_confirmation_ref": proof["owner_confirmation_ref"],
            "status": "PASS",
        }
        fresh, _fresh_raw = _load_json(evidence_dir / "fresh-review.json")
        _validate_simple(
            "fresh-review",
            fresh,
            repo_root=repo_root,
            evidence_dir=evidence_dir,
            manifest=manifest,
        )
        reviewer_set = [
            {key: item[key] for key in ("review_scope", "review_id", "reviewer_principal", "artifact_sha256")}
            for item in fresh["reviews"]
        ]
        if (
            value["implementation_authorization"] != projection
            or value["reviewer_set"] != reviewer_set
            or value["reviewed_tree_sha256"] != fresh["reviewed_tree_sha256"]
            or (value["release_label"] == "experimental") != (value["private_shadow_receipt_sha256"] is None)
        ):
            raise Denied


def validate(
    manifest_path: Path,
    evidence_dir: Path,
    required: list[str],
    *,
    require_reviewed_tree_hash_match: bool = False,
) -> dict[str, Any]:
    repo_root = Path.cwd().absolute()
    manifest, result = _manifest(repo_root, manifest_path.absolute())
    schemas = _schema_files(repo_root)
    baseline_id = result["baseline_id"]
    expected_dir = repo_root / "specs/subject-distillation/evidence" / baseline_id
    if evidence_dir.absolute() != expected_dir:
        raise Denied
    _inventory(expected_dir)
    if len(required) != len(set(required)) or any(name not in KINDS for name in required):
        raise Denied
    validated: list[str] = []
    resolved_evidence_dir = evidence_dir.absolute()
    for name in required:
        if name in STAGES:
            _validate_stage(repo_root, resolved_evidence_dir / f"{name}.txt", name, manifest)
            validated.append(name)
            continue
        filename = "environment.json" if name == "environment" else f"{name}.json"
        value, _raw = _load_json(resolved_evidence_dir / filename)
        if type(value) is not dict:
            raise Denied
        _validate_common(value, manifest, schemas[name], repo_root)
        if name == "environment":
            _validate_environment(repo_root, value, manifest, schemas[name])
        else:
            _validate_simple(
                name,
                value,
                repo_root=repo_root,
                evidence_dir=resolved_evidence_dir,
                manifest=manifest,
            )
        validated.append(name)
    if require_reviewed_tree_hash_match:
        if "fresh-review" not in required:
            raise Denied
        fresh, _raw = _load_json(resolved_evidence_dir / "fresh-review.json")
        if (
            type(fresh) is not dict
            or fresh["reviewed_tree_sha256"]
            != _current_reviewed_tree_sha256(repo_root)
        ):
            raise Denied
        if "attestation" in required:
            attestation, _attestation_raw = _load_json(resolved_evidence_dir / "attestation.json")
            if attestation["reviewed_tree_sha256"] != fresh["reviewed_tree_sha256"]:
                raise Denied
    return {"baseline_id": baseline_id, "status": "PASS", "validated": validated}


def _parse_required(values: list[str]) -> list[str]:
    required: list[str] = []
    for value in values:
        if type(value) is not str:
            raise Denied
        names = value.split(",")
        if any(not name for name in names):
            raise Denied
        required.extend(names)
    if len(required) != len(set(required)):
        raise Denied
    return required


def _parse_declared_review_sources(raw: bytes) -> tuple[set[str], set[str]]:
    if hashlib.sha256(raw).hexdigest() != REVIEW_TASKS_SHA256:
        raise Denied
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        raise Denied from None
    headers: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.startswith("**Files:**"):
            index += 1
            continue
        parts = [line.removeprefix("**Files:**")]
        index += 1
        while index < len(lines) and not lines[index]:
            index += 1
        while (
            index < len(lines)
            and lines[index].startswith("- ")
            and not lines[index].startswith("- [ ]")
        ):
            parts.append(lines[index])
            index += 1
        headers.extend(parts)
    if len([line for line in lines if line.startswith("**Files:**")]) != 32:
        raise Denied
    literals: set[str] = set(REVIEW_REQUIRED_PATHS)
    globs: set[str] = set()
    schema_dir = "specs/subject-distillation/evidence-schemas/"
    for token in re.findall(r"`([^`]+)`", "\n".join(headers)):
        if token.startswith(("$EVIDENCE_DIR/", REVIEW_EXCLUDED_PREFIX)):
            continue
        if token in REVIEW_EXCLUDED_PATHS or token == (
            "specs/subject-distillation/.implementation-progress.pending"
        ):
            continue
        if token == schema_dir:
            literals.update(
                path for path in REVIEW_LITERAL_PATHS if path.startswith(schema_dir)
            )
            continue
        if token in REVIEW_GLOB_PATTERNS:
            globs.add(token)
            continue
        if "*" in token:
            raise Denied
        if token in REVIEW_ROOT_FILES or token.startswith(
            ("docs/", "scripts/", "specs/", "tests/", "vault/")
        ):
            if (
                token.endswith("/")
                or token.startswith("/")
                or "\\" in token
                or any(part in {"", ".", ".."} for part in token.split("/"))
            ):
                raise Denied
            literals.add(token)
        elif "/" in token:
            raise Denied
    for pattern in globs:
        directory = pattern.removesuffix("/*.json")
        literals = {
            path
            for path in literals
            if not (
                path.startswith(f"{directory}/")
                and "/" not in path[len(directory) + 1 :]
                and path.endswith(".json")
            )
        }
    return literals, globs


def _declared_review_sources(repo_root: Path) -> tuple[set[str], set[str]]:
    return _parse_declared_review_sources(
        _read_file(repo_root / "specs/subject-distillation/tasks.md")
    )


def _review_glob(repo_root: Path, pattern: str) -> list[str]:
    if pattern not in REVIEW_GLOB_PATTERNS or not pattern.endswith("/*.json"):
        raise Denied
    directory = pattern.removesuffix("/*.json")
    try:
        names = os.listdir(repo_root / directory)
    except OSError:
        raise Denied from None
    if len(names) > 4_096:
        raise Denied
    matches = [
        f"{directory}/{name}"
        for name in names
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.json", name)
    ]
    if not matches:
        raise Denied
    return sorted(matches, key=lambda item: item.encode("ascii"))


def _reviewed_source_paths(repo_root: Path) -> tuple[str, ...]:
    declared_literals, declared_globs = _declared_review_sources(repo_root)
    if declared_literals != set(REVIEW_LITERAL_PATHS) or declared_globs != set(
        REVIEW_GLOB_PATTERNS
    ):
        raise Denied
    paths = list(REVIEW_LITERAL_PATHS)
    for pattern in REVIEW_GLOB_PATTERNS:
        paths.extend(_review_glob(repo_root, pattern))
    if len(paths) > MAX_REVIEW_PATHS or len(paths) != len(set(paths)):
        raise Denied
    for path in paths:
        if (
            not path
            or len(path) > 256
            or path.startswith(("/", REVIEW_EXCLUDED_PREFIX))
            or "\\" in path
            or any(part in {"", ".", ".."} for part in path.split("/"))
            or path in REVIEW_EXCLUDED_PATHS
        ):
            raise Denied
    return tuple(sorted(paths, key=lambda item: item.encode("ascii")))


def _git_path_set(repo_root: Path, args: list[str]) -> set[str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=False,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        raise Denied from None
    if completed.returncode != 0 or completed.stderr:
        raise Denied
    result: set[str] = set()
    for raw in completed.stdout.split(b"\0"):
        if not raw:
            continue
        try:
            path = raw.decode("ascii")
        except UnicodeDecodeError:
            raise Denied from None
        if (
            not path
            or path.startswith("/")
            or "\\" in path
            or any(part in {"", ".", ".."} for part in path.split("/"))
        ):
            raise Denied
        result.add(path)
    return result


def _review_scope(repo_root: Path, expected: set[str]) -> None:
    tracked = _git_path_set(repo_root, ["ls-files", "-z"])
    untracked = _git_path_set(
        repo_root,
        ["ls-files", "--others", "--exclude-standard", "-z"],
    )
    if not expected <= tracked | untracked:
        raise Denied
    try:
        status = subprocess.run(
            [
                "git",
                "-c",
                "status.renames=false",
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
            ],
            cwd=repo_root,
            check=False,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        raise Denied from None
    if status.returncode != 0 or status.stderr:
        raise Denied
    for raw in status.stdout.split(b"\0"):
        if not raw:
            continue
        if len(raw) < 4 or raw[2:3] != b" ":
            raise Denied
        try:
            path = raw[3:].decode("ascii")
        except UnicodeDecodeError:
            raise Denied from None
        if path == "specs/subject-distillation/.implementation-progress.pending":
            raise Denied
        if (
            path not in expected
            and path not in REVIEW_EXCLUDED_PATHS
            and not path.startswith(REVIEW_EXCLUDED_PREFIX)
        ):
            raise Denied


def _hash_reviewed_source_paths(repo_root: Path, paths: tuple[str, ...]) -> str:
    owned: list[int] = []
    handles: list[tuple[str, authorization.Handle]] = []
    try:
        anchor = os.open("/", authorization._flags(directory=True))
        owned.append(anchor)
        repo = authorization._open_chain(
            anchor,
            authorization._absolute_parts(os.fspath(repo_root)),
            owned,
            final_directory=True,
        )
        for path in paths:
            handle = authorization._open_chain(
                repo.fd,
                tuple(path.split("/")),
                owned,
            )
            handles.append((path, handle))
        authorization._audit([repo, *(handle for _path, handle in handles)])
        entries: list[dict[str, str]] = []
        total = 0
        for path, handle in handles:
            raw = authorization._read(handle)
            total += len(raw)
            if total > MAX_REVIEW_BYTES:
                raise Denied
            entries.append({"path": path, "sha256": hashlib.sha256(raw).hexdigest()})
        authorization._audit([repo, *(handle for _path, handle in handles)])
    except (OSError, authorization.Denied):
        raise Denied from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass
    return hashlib.sha256(_canonical(entries)).hexdigest()


def compute_reviewed_tree_sha256(repo_root: Path) -> str:
    """Compute the review tree in the T-001 validator, never in mutable T-031 code."""
    manifest, _result = _manifest(repo_root, repo_root / MANIFEST_PATH)
    tasks_entry = next(
        (item for item in manifest["files"] if item["path"] == "specs/subject-distillation/tasks.md"),
        None,
    )
    if tasks_entry != {
        "path": "specs/subject-distillation/tasks.md",
        "sha256": REVIEW_TASKS_SHA256,
    }:
        raise Denied
    paths = _reviewed_source_paths(repo_root)
    expected = set(paths)
    _review_scope(repo_root, expected)
    digest = _hash_reviewed_source_paths(repo_root, paths)
    if _reviewed_source_paths(repo_root) != paths:
        raise Denied
    _review_scope(repo_root, expected)
    return digest


def _current_reviewed_tree_sha256(repo_root: Path) -> str:
    return compute_reviewed_tree_sha256(repo_root)


def _reject_duplicate_scalars(argv: list[str]) -> None:
    for name in (
        "--manifest",
        "--evidence-dir",
        "--require-reviewed-tree-hash-match",
    ):
        if sum(item == name or item.startswith(name + "=") for item in argv) > 1:
            raise Denied


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(add_help=False)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--require", action="append", default=[])
    parser.add_argument("--require-reviewed-tree-hash-match", action="store_true")
    try:
        raw_argv = list(sys.argv[1:] if argv is None else argv)
        _reject_duplicate_scalars(raw_argv)
        args = parser.parse_args(raw_argv)
        required = _parse_required(args.require)
        result = validate(
            Path(args.manifest),
            Path(args.evidence_dir),
            required,
            require_reviewed_tree_hash_match=args.require_reviewed_tree_hash_match,
        )
    except (Denied, SystemExit, authorization.Denied, baseline.ValidationError):
        sys.stderr.write(DENY_TEXT)
        return 2
    except Exception:  # noqa: BLE001 - fixed public boundary must not echo faults
        sys.stderr.write(ERROR_TEXT)
        return 3
    sys.stdout.write(_canonical(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
