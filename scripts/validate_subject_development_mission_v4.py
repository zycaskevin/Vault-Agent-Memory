#!/usr/bin/env python3
"""Fail-closed validator for the Subject Development Mission v4 root."""

from __future__ import annotations

import copy
import hashlib
import os
import stat
import sys
import types
from collections.abc import Callable
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
    identity = lambda info: (
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
        exec(compile(raw, "<subject-v4-sibling>", "exec"), module.__dict__)  # noqa: S102
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


try:
    mission = _load_sibling_dependency(
        "scripts.run_subject_development_mission_v4",
        "run_subject_development_mission_v4.py",
    )
    progress_writer = _load_sibling_dependency(
        "scripts.update_subject_progress", "update_subject_progress.py"
    )
    progress_core = _load_sibling_dependency(
        "scripts.validate_subject_progress", "validate_subject_progress.py"
    )
    legacy_validator = _load_sibling_dependency(
        "scripts.validate_subject_task_authorization_v3",
        "validate_subject_task_authorization_v3.py",
    )
except Exception:
    if __name__ == "__main__":
        sys.stderr.write("SUBJECT_DEVELOPMENT_MISSION_V4_VALIDATION_ERROR\n")
        raise SystemExit(3) from None
    raise


Denied = mission.Denied
DENY_TEXT = "SUBJECT_DEVELOPMENT_MISSION_V4_VALIDATION_DENY\n"
ERROR_TEXT = "SUBJECT_DEVELOPMENT_MISSION_V4_VALIDATION_ERROR\n"

PROOF_KEYS = {
    "active_from_utc",
    "artifact_kind",
    "authorization_id",
    "authorization_schema_sha256",
    "authorization_verifier_sha256",
    "authorizing_principal",
    "baseline_full_digest",
    "baseline_id",
    "contract_sha256",
    "expires_at_utc",
    "issued_at_utc",
    "mission_duration_seconds",
    "mission_id",
    "mission_not_after_utc",
    "mission_proof_path",
    "owner_confirmation_ref",
    "progress_sequence",
    "progress_sha256",
    "proposal_id",
    "protocol_base_commit",
    "protocol_decision_id",
    "receipt_sha256",
    "recorded_at_utc",
    "repository",
    "schema_version",
    "scope_registry_sha256",
    "scope_sha256",
    "status",
    "supersession_sha256",
    "tasks_sha256",
    "trust_root",
    "trust_root_sha256",
}


def _proposal_from_proof(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 4,
        "artifact_kind": "subject-development-mission-v4-proposal",
        "protocol_decision_id": value["protocol_decision_id"],
        "repository": value["repository"],
        "authorizing_principal": value["authorizing_principal"],
        "protocol_base_commit": value["protocol_base_commit"][4:],
        "baseline_id": value["baseline_id"],
        "baseline_full_digest": value["baseline_full_digest"],
        "tasks_sha256": value["tasks_sha256"],
        "contract_sha256": value["contract_sha256"],
        "scope_registry_sha256": value["scope_registry_sha256"],
        "supersession_sha256": value["supersession_sha256"],
        "trust_root": value["trust_root"],
        "trust_root_sha256": value["trust_root_sha256"],
        "progress_sequence": value["progress_sequence"],
        "progress_sha256": value["progress_sha256"],
        "issued_at_utc": value["issued_at_utc"],
        "expires_at_utc": value["expires_at_utc"],
        "mission_duration_seconds": value["mission_duration_seconds"],
        "receipt_sha256": value["receipt_sha256"],
        "scope_sha256": value["scope_sha256"],
        "authorization_id": value["authorization_id"],
        "authorization_verifier_sha256": value["authorization_verifier_sha256"],
        "authorization_schema_sha256": value["authorization_schema_sha256"],
        "mission_proof_path": value["mission_proof_path"],
    }


def _retained_authorization_inputs(
    repo_root: Path, retained: dict[str, bytes]
) -> tuple[str, str, bytes, bytes]:
    verifier = mission.legacy.v1.verifier
    manifest_raw = mission._snapshot_read(
        repo_root, verifier.MANIFEST_PATH, retained
    )
    schema_raw = mission._snapshot_read(repo_root, verifier.SCHEMA_PATH, retained)
    verifier_raw = mission._snapshot_read(
        repo_root, verifier.VERIFIER_PATH, retained, mode=0o755
    )
    manifest = mission._parse(manifest_raw)
    schema = mission._parse(schema_raw)
    verifier._scan(manifest)
    verifier._scan(schema)
    baseline_id, full_digest = verifier._manifest(manifest)
    verifier._schema_shape(schema)
    if verifier_raw != mission.legacy.v1.VERIFIER_SOURCE:
        raise Denied
    files = manifest.get("files") if type(manifest) is dict else None
    if type(files) is not list:
        raise Denied
    for item in files:
        if (
            type(item) is not dict
            or set(item) != {"path", "sha256", "size_bytes"}
            or type(item["path"]) is not str
        ):
            raise Denied
        content = mission._snapshot_read(repo_root, item["path"], retained)
        if (
            len(content) != item["size_bytes"]
            or hashlib.sha256(content).hexdigest() != item["sha256"]
        ):
            raise Denied
    return baseline_id, full_digest, schema_raw, verifier_raw


def validate_mission_proof_value(
    value: Any,
    raw: bytes,
    repo_root: Path,
    *,
    now_utc: str | None = None,
    retained: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    contract, contract_raw = mission.load_contract(repo_root, retained=retained)
    _registry, registry_raw = mission.load_registry(
        repo_root, contract, retained=retained
    )
    if (
        type(value) is not dict
        or set(value) != PROOF_KEYS
        or raw != mission.canonical(value)
        or value["schema_version"] != 4
        or value["artifact_kind"] != "subject-development-mission-v4-proof"
        or value["status"] != "PASS"
        or value["repository"] != contract["repository"]
        or value["authorizing_principal"] != mission.AUTHORITY
        or value["protocol_decision_id"] != mission.DECISION_ID
        or value["baseline_id"] != contract["activation"]["baseline_id"]
        or value["baseline_full_digest"] != contract["activation"]["baseline_full_digest"]
        or value["tasks_sha256"] != mission.TASKS_SHA256
        or value["contract_sha256"] != hashlib.sha256(contract_raw).hexdigest()
        or value["scope_registry_sha256"] != hashlib.sha256(registry_raw).hexdigest()
        or value["supersession_sha256"] != mission._supersession_sha(contract)
        or value["progress_sequence"] != 6
        or value["progress_sha256"] != mission.ACTIVATION_PROGRESS_SHA256
        or value["mission_duration_seconds"] != 7_776_000
        or value["mission_proof_path"] != mission.MISSION_PROOF_PATH
        or type(value["protocol_base_commit"]) is not str
        or not value["protocol_base_commit"].startswith("git:")
        or mission.COMMIT.fullmatch(value["protocol_base_commit"][4:]) is None
        or mission.OPAQUE.fullmatch(value["owner_confirmation_ref"]) is None
    ):
        raise Denied
    for key in PROOF_KEYS & {
        "authorization_id",
        "authorization_schema_sha256",
        "authorization_verifier_sha256",
        "baseline_full_digest",
        "contract_sha256",
        "mission_id",
        "progress_sha256",
        "proposal_id",
        "receipt_sha256",
        "scope_registry_sha256",
        "scope_sha256",
        "supersession_sha256",
        "tasks_sha256",
        "trust_root_sha256",
    }:
        if type(value[key]) is not str or mission.HEX64.fullmatch(value[key]) is None:
            raise Denied
    expected_trust = mission._trust_root(repo_root, contract, retained=retained)
    if (
        value["trust_root"] != expected_trust
        or value["trust_root_sha256"]
        != hashlib.sha256(mission.canonical(expected_trust, newline=False)).hexdigest()
    ):
        raise Denied
    issued = mission._timestamp(value["issued_at_utc"])
    expires = mission._timestamp(value["expires_at_utc"])
    recorded = mission._timestamp(value["recorded_at_utc"])
    active = mission._timestamp(value["active_from_utc"])
    not_after = mission._timestamp(value["mission_not_after_utc"])
    now = mission._now(now_utc)
    if (
        expires - issued != mission.PROPOSAL_VALIDITY
        or not issued <= recorded < expires
        or active != recorded
        or not_after != active + mission.MISSION_DURATION
        or not active <= now < not_after
    ):
        raise Denied
    if retained is None:
        inputs = mission.legacy.v1._repo_inputs(os.fspath(repo_root))
        baseline_id = inputs.baseline_id
        full_digest = inputs.full_digest
        schema_raw = inputs.schema_raw
        verifier_raw = inputs.verifier_raw
    else:
        baseline_id, full_digest, schema_raw, verifier_raw = (
            _retained_authorization_inputs(repo_root, retained)
        )
    if value["baseline_id"] != baseline_id or value["baseline_full_digest"] != full_digest:
        raise Denied
    scope_raw = mission.canonical(mission._scope(contract, registry_raw))
    receipt = {
        "schema_version": 1,
        "artifact_kind": "subject-distillation-implementation-authorization",
        "baseline_id": value["baseline_id"],
        "baseline_full_digest": value["baseline_full_digest"],
        "authorizing_principal": mission.AUTHORITY,
        "authorized_task": "T-004",
        "scope_sha256": hashlib.sha256(scope_raw).hexdigest(),
        "authorization_verifier_sha256": hashlib.sha256(verifier_raw).hexdigest(),
        "authorization_schema_sha256": hashlib.sha256(schema_raw).hexdigest(),
        "issued_at_utc": value["issued_at_utc"],
        "expires_at_utc": value["expires_at_utc"],
    }
    receipt["authorization_id"] = hashlib.sha256(
        mission.canonical(receipt, newline=False)
    ).hexdigest()
    receipt_raw = mission.canonical(receipt)
    if (
        value["scope_sha256"] != receipt["scope_sha256"]
        or value["authorization_verifier_sha256"] != receipt["authorization_verifier_sha256"]
        or value["authorization_schema_sha256"] != receipt["authorization_schema_sha256"]
        or value["authorization_id"] != receipt["authorization_id"]
        or value["receipt_sha256"] != hashlib.sha256(receipt_raw).hexdigest()
    ):
        raise Denied
    proposal = _proposal_from_proof(value)
    proposal["proposal_id"] = hashlib.sha256(mission.canonical(proposal)).hexdigest()
    if value["proposal_id"] != proposal["proposal_id"]:
        raise Denied
    without_id = dict(value)
    without_id.pop("mission_id")
    if (
        value["mission_id"]
        != hashlib.sha256(mission.canonical(without_id, newline=False)).hexdigest()
    ):
        raise Denied
    return {
        "active_from_utc": value["active_from_utc"],
        "mission_id": value["mission_id"],
        "mission_not_after_utc": value["mission_not_after_utc"],
        "protocol_base_commit": value["protocol_base_commit"],
        "status": "PASS",
    }


def validate_revocation_value(value: Any, raw: bytes, proof: dict[str, Any]) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value)
        != {
            "artifact_kind",
            "authorizing_principal",
            "mission_id",
            "mission_epoch",
            "owner_confirmation_ref",
            "previous_ledger_sequence",
            "previous_ledger_sha256",
            "reason_code",
            "revoked_at_utc",
            "revocation_id",
            "schema_version",
        }
        or raw != mission.canonical(value)
        or value["schema_version"] != 1
        or value["artifact_kind"] != "subject-development-mission-revocation"
        or value["authorizing_principal"] != mission.AUTHORITY
        or value["mission_id"] != proof["mission_id"]
        or value["mission_epoch"] != 1
        or mission.OPAQUE.fullmatch(value["owner_confirmation_ref"]) is None
        or type(value["previous_ledger_sequence"]) is not int
        or value["previous_ledger_sequence"] < 6
        or mission.HEX64.fullmatch(value["previous_ledger_sha256"]) is None
        or mission.HEX64.fullmatch(value["revocation_id"]) is None
        or value["reason_code"]
        not in {
            "OWNER_REVOKED",
            "RISK_BOUNDARY_CHANGED",
            "TRUST_ROOT_CHANGED",
        }
        or mission._timestamp(value["revoked_at_utc"])
        < mission._timestamp(proof["active_from_utc"])
    ):
        raise Denied
    without_id = dict(value)
    without_id.pop("revocation_id")
    if value["revocation_id"] != hashlib.sha256(
        mission.canonical(without_id, newline=False)
    ).hexdigest():
        raise Denied
    return {"mission_id": value["mission_id"], "status": "REVOKED"}


def validate_revocation_progress(
    revocation: dict[str, Any], progress: dict[str, Any]
) -> dict[str, Any]:
    previous = copy.deepcopy(progress)
    events = previous["events"]
    if events and events[-1].get("blocker") == "MISSION_REVOKED":
        event = events.pop()
        previous["tasks"][event["task_id"]] = "IN_PROGRESS"
        previous["updated_at_utc"] = events[-1]["at_utc"]
    if (
        revocation["previous_ledger_sequence"] != len(events)
        or revocation["previous_ledger_sha256"]
        != hashlib.sha256(mission.canonical(previous)).hexdigest()
    ):
        raise Denied
    return previous


TASK_PROOF_KEYS = {
    "artifact_kind",
    "authorized_task",
    "derived_at_utc",
    "descriptor_sha256",
    "implementation_base_commit",
    "mission_id",
    "mission_proof_sha256",
    "progress_sequence",
    "progress_sha256",
    "proof_repo_relative_path",
    "required_read_files",
    "schema_version",
    "scope_registry_sha256",
    "status",
    "task_authorization_id",
    "task_header_sha256",
}


def _load_mission_proof(repo_root: Path) -> tuple[dict[str, Any], bytes]:
    raw = mission._read(repo_root, mission.MISSION_PROOF_PATH)
    value = mission._parse(raw)
    if raw != mission.canonical(value):
        raise Denied
    return value, raw


def _descriptor(
    repo_root: Path,
    task: str,
    *,
    retained: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    contract, _ = mission.load_contract(repo_root, retained=retained)
    registry, _ = mission.load_registry(repo_root, contract, retained=retained)
    if mission.TASK.fullmatch(task) is None:
        raise Denied
    return registry["tasks"][int(task[2:]) - 4]


def validate_task_authorization_value(
    value: Any,
    raw: bytes,
    repo_root: Path,
    *,
    mission_proof: dict[str, Any] | None = None,
    mission_raw: bytes | None = None,
    retained: dict[str, bytes] | None = None,
    historical: bool = False,
) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != TASK_PROOF_KEYS
        or raw != mission.canonical(value)
        or value["schema_version"] != 4
        or value["artifact_kind"] != "subject-task-authorization-v4"
        or value["status"] != "PASS"
        or mission.TASK.fullmatch(value["authorized_task"]) is None
        or type(value["progress_sequence"]) is not int
        or value["progress_sequence"] < 6
        or type(value["implementation_base_commit"]) is not str
        or not value["implementation_base_commit"].startswith("git:")
        or mission.COMMIT.fullmatch(value["implementation_base_commit"][4:]) is None
        or value["proof_repo_relative_path"]
        != f"specs/subject-distillation/task-authorizations/{value['authorized_task']}.json"
    ):
        raise Denied
    for key in TASK_PROOF_KEYS & {
        "descriptor_sha256",
        "mission_id",
        "mission_proof_sha256",
        "progress_sha256",
        "scope_registry_sha256",
        "task_authorization_id",
        "task_header_sha256",
    }:
        if type(value[key]) is not str or mission.HEX64.fullmatch(value[key]) is None:
            raise Denied
    if mission_proof is None or mission_raw is None:
        if retained is not None and mission.MISSION_PROOF_PATH in retained:
            mission_raw = retained[mission.MISSION_PROOF_PATH]
            mission_proof = mission._parse(mission_raw)
            if mission_raw != mission.canonical(mission_proof):
                raise Denied
        else:
            mission_proof, mission_raw = _load_mission_proof(repo_root)
    derived_at = value["derived_at_utc"]
    validate_mission_proof_value(
        mission_proof,
        mission_raw,
        repo_root,
        now_utc=derived_at,
        retained=retained,
    )
    mission.check_task_proof_ancestry(
        repo_root, value["implementation_base_commit"][4:], mission_proof
    )
    descriptor = _descriptor(
        repo_root, value["authorized_task"], retained=retained
    )
    contract, _ = mission.load_contract(repo_root, retained=retained)
    expected_reads = (
        mission.required_read_files_at_commit(
            repo_root, descriptor, value["implementation_base_commit"][4:]
        )
        if historical
        else mission.required_read_files(repo_root, descriptor, retained=retained)
    )
    if (
        value["mission_id"] != mission_proof["mission_id"]
        or value["mission_proof_sha256"] != hashlib.sha256(mission_raw).hexdigest()
        or value["scope_registry_sha256"] != contract["scope_registry_sha256"]
        or value["task_header_sha256"] != descriptor["task_header_sha256"]
        or value["descriptor_sha256"]
        != hashlib.sha256(mission.canonical(descriptor, newline=False)).hexdigest()
        or value["required_read_files"] != expected_reads
    ):
        raise Denied
    without_id = dict(value)
    without_id.pop("task_authorization_id")
    if (
        value["task_authorization_id"]
        != hashlib.sha256(mission.canonical(without_id, newline=False)).hexdigest()
    ):
        raise Denied
    return {
        "authorization_id": value["task_authorization_id"],
        "authorized_task": value["authorized_task"],
        "descriptor": descriptor,
        "implementation_base_commit": value["implementation_base_commit"],
        "mission_id": value["mission_id"],
        "status": "PASS",
    }


def _start_refs(task: str, proof: dict[str, Any], raw: bytes) -> list[dict[str, str]]:
    refs = [
        {
            "kind": "opaque",
            "id": f"{task.lower().replace('-', '')}-authorization:{proof['task_authorization_id']}",
        },
        {
            "kind": "repo_file",
            "path": proof["proof_repo_relative_path"],
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
    ]
    return sorted(refs, key=mission.canonical)


SOURCE_REVIEW_KEYS = {
    "artifact_kind",
    "authorized_task",
    "builder_principal",
    "implementation_base_commit",
    "mission_id",
    "p0",
    "p1",
    "p2",
    "progress_before_sequence",
    "progress_before_sha256",
    "proof_sha256",
    "required_read_files",
    "source_review_id",
    "reviewed_at_utc",
    "reviewed_change_set_sha256",
    "reviewed_changes",
    "reviewed_outputs",
    "reviewer_principal",
    "schema_version",
    "status",
    "verdict",
    "verification_results",
}


def validate_source_review_value(
    value: Any,
    raw: bytes,
    repo_root: Path,
    task: str,
    *,
    proof: dict[str, Any] | None = None,
    proof_raw: bytes | None = None,
    retained: dict[str, bytes] | None = None,
    historical_head: str | None = None,
) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != SOURCE_REVIEW_KEYS
        or raw != mission.canonical(value)
        or value["schema_version"] != 4
        or value["artifact_kind"] != "subject-task-source-review-v4"
        or value["status"] != "PASS"
        or value["verdict"] != "PASS"
        or value["authorized_task"] != task
        or value["p0"] != 0
        or value["p1"] != 0
        or type(value["p2"]) is not int
        or not 0 <= value["p2"] <= 65_535
        or type(value["builder_principal"]) is not str
        or type(value["reviewer_principal"]) is not str
        or value["builder_principal"] == value["reviewer_principal"]
        or mission.OPAQUE.fullmatch(value["builder_principal"]) is None
        or mission.OPAQUE.fullmatch(value["reviewer_principal"]) is None
        or mission.HEX64.fullmatch(value.get("progress_before_sha256", "")) is None
        or mission.HEX64.fullmatch(value.get("proof_sha256", "")) is None
    ):
        raise Denied
    if proof is None or proof_raw is None:
        proof_path = f"specs/subject-distillation/task-authorizations/{task}.json"
        proof_raw = (
            retained[proof_path]
            if retained is not None and proof_path in retained
            else mission._read(repo_root, proof_path)
        )
        proof = mission._parse(proof_raw)
    proof_result = validate_task_authorization_value(
        proof,
        proof_raw,
        repo_root,
        retained=retained,
        historical=historical_head is not None,
    )
    descriptor = proof_result["descriptor"]
    if (
        value["mission_id"] != proof_result["mission_id"]
        or value["implementation_base_commit"] != proof_result["implementation_base_commit"]
        or value["proof_sha256"] != hashlib.sha256(proof_raw).hexdigest()
        or value["required_read_files"] != proof["required_read_files"]
        or value["progress_before_sequence"] < proof["progress_sequence"] + 1
        or mission._timestamp(value["reviewed_at_utc"])
        < mission._timestamp(proof["derived_at_utc"])
    ):
        raise Denied
    outputs = []
    policy = {item["path"]: item for item in descriptor["writable_path_policies"]}
    for path in descriptor["completion_repo_relative_paths"]:
        expected_mode = f"10{policy[path]['final_mode']}"
        if historical_head is None:
            data = mission._snapshot_read(
                repo_root,
                path,
                retained,
                mode=0o755 if policy[path]["final_mode"] == "0755" else 0o644,
            )
        else:
            actual_mode, data = mission._git_object(repo_root, historical_head, path)
            if actual_mode != expected_mode:
                raise Denied
        outputs.append(
            {
                "mode": expected_mode,
                "path": path,
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    if value["reviewed_outputs"] != outputs:
        raise Denied
    verification_results = value["verification_results"]
    steps = descriptor["verification_steps"]
    if type(verification_results) is not list or len(verification_results) != len(steps):
        raise Denied
    expected_results = []
    for step, item in zip(steps, verification_results, strict=True):
        if type(item) is not dict or set(item) != {
            "exit_code",
            "status",
            "stderr_sha256",
            "stdout_sha256",
            "step_id",
        }:
            raise Denied
        expected_results.append(
            {
                "exit_code": 0,
                "status": "PASS",
                "step_id": step["step_id"],
                "stderr_sha256": item["stderr_sha256"],
                "stdout_sha256": item["stdout_sha256"],
            }
        )
    if value["verification_results"] != expected_results:
        raise Denied
    for item in expected_results:
        if (
            mission.HEX64.fullmatch(item["stdout_sha256"]) is None
            or mission.HEX64.fullmatch(item["stderr_sha256"]) is None
        ):
            raise Denied
    changes = value["reviewed_changes"]
    expected_paths = sorted(
        [proof["proof_repo_relative_path"], *descriptor["completion_repo_relative_paths"]]
    )
    if (
        type(changes) is not list
        or len(changes) != len(expected_paths)
        or [item.get("path") if type(item) is dict else None for item in changes] != expected_paths
    ):
        raise Denied
    for item in changes:
        if type(item) is not dict or set(item) != {"action", "mode", "path", "sha256"}:
            raise Denied
        expected_mode = (
            "100644"
            if item["path"] == proof["proof_repo_relative_path"]
            else f"10{policy.get(item['path'], {}).get('final_mode', '')}"
        )
        expected_action = (
            "add"
            if item["path"] == proof["proof_repo_relative_path"]
            else (
                "add" if policy[item["path"]]["action"] == "create" else "modify"
            )
        )
        if (
            item["action"] != expected_action
            or item["mode"] != expected_mode
            or type(item["sha256"]) is not str
            or mission.HEX64.fullmatch(item["sha256"]) is None
        ):
            raise Denied
        if historical_head is None:
            data = mission._snapshot_read(
                repo_root,
                item["path"],
                retained,
                mode=int(expected_mode[-3:], 8),
            )
        else:
            actual_mode, data = mission._git_object(
                repo_root, historical_head, item["path"]
            )
            if actual_mode != expected_mode:
                raise Denied
        if item["sha256"] != hashlib.sha256(data).hexdigest():
            raise Denied
    if (
        value["reviewed_change_set_sha256"]
        != hashlib.sha256(mission.canonical(changes, newline=False)).hexdigest()
    ):
        raise Denied
    without_id = dict(value)
    without_id.pop("source_review_id")
    if (
        value["source_review_id"]
        != hashlib.sha256(mission.canonical(without_id, newline=False)).hexdigest()
    ):
        raise Denied
    return {
        "authorization_id": proof_result["authorization_id"],
        "descriptor": descriptor,
        "source_review_id": value["source_review_id"],
        "reviewed_at_utc": value["reviewed_at_utc"],
        "status": "PASS",
    }


DELIVERY_KEYS = {
    "artifact_kind",
    "authorization_proof_sha256",
    "authorized_task",
    "delivery_id",
    "implementation_base_commit",
    "mission_epoch",
    "mission_id",
    "preliminary_change_set_sha256",
    "preliminary_changes",
    "preliminary_head_commit",
    "preliminary_tree_git_oid",
    "pull_request_head_ref",
    "pull_request_head_repository",
    "pull_request_number",
    "readback_at_utc",
    "readback_principal",
    "repository",
    "required_checks",
    "required_checks_sha256",
    "schema_version",
    "source_review_id",
    "source_review_sha256",
    "status",
    "workflow",
    "workflow_sha256",
}


def validate_preliminary_delivery_value(
    value: Any,
    raw: bytes,
    repo_root: Path,
    task: str,
    *,
    proof: dict[str, Any],
    proof_raw: bytes,
    source_review: dict[str, Any],
    source_review_raw: bytes,
    retained: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != DELIVERY_KEYS
        or raw != mission.canonical(value)
        or value["schema_version"] != 4
        or value["artifact_kind"] != "subject-task-preliminary-delivery-v4"
        or value["status"] != "PASS"
        or value["repository"] != "zycaskevin/Vault-Agent-Memory"
        or value["authorized_task"] != task
        or value["mission_id"] != proof["mission_id"]
        or value["mission_epoch"] != 1
        or value["authorization_proof_sha256"] != hashlib.sha256(proof_raw).hexdigest()
        or value["source_review_id"] != source_review["source_review_id"]
        or value["source_review_sha256"] != hashlib.sha256(source_review_raw).hexdigest()
        or value["implementation_base_commit"] != proof["implementation_base_commit"]
        or value["workflow"] != ".github/workflows/ci.yml"
        or mission.HEX64.fullmatch(value["workflow_sha256"]) is None
        or mission.OPAQUE.fullmatch(value["readback_principal"]) is None
        or type(value["preliminary_head_commit"]) is not str
        or not value["preliminary_head_commit"].startswith("git:")
        or mission.COMMIT.fullmatch(value["preliminary_head_commit"][4:]) is None
        or type(value["preliminary_tree_git_oid"]) is not str
        or not value["preliminary_tree_git_oid"].startswith("git:")
        or mission.COMMIT.fullmatch(value["preliminary_tree_git_oid"][4:]) is None
        or type(value["pull_request_number"]) is not int
        or not 1 <= value["pull_request_number"] <= 2_147_483_647
        or value["pull_request_head_repository"] != "zycaskevin/Vault-Agent-Memory"
        or type(value["pull_request_head_ref"]) is not str
        or mission.BRANCH_REF.fullmatch(value["pull_request_head_ref"]) is None
        or value["pull_request_head_ref"].startswith("/")
        or ".." in value["pull_request_head_ref"].split("/")
        or mission._timestamp(value["readback_at_utc"])
        < mission._timestamp(source_review["reviewed_at_utc"])
    ):
        raise Denied
    checks = value["required_checks"]
    if (
        type(checks) is not list
        or [item.get("name") if type(item) is dict else None for item in checks]
        != mission.REQUIRED_HOSTED_CHECKS
    ):
        raise Denied
    for check in checks:
        if (
            type(check) is not dict
            or set(check)
            != {
                "completed_at_utc",
                "conclusion",
                "head_commit",
                "name",
                "run_attempt",
                "run_id",
            }
            or check["conclusion"] != "SUCCESS"
            or check["head_commit"] != value["preliminary_head_commit"]
            or type(check["run_attempt"]) is not int
            or not 1 <= check["run_attempt"] <= 1_000_000
            or mission.OPAQUE.fullmatch(check["run_id"]) is None
            or mission._timestamp(check["completed_at_utc"])
            < mission._timestamp(source_review["reviewed_at_utc"])
            or mission._timestamp(check["completed_at_utc"])
            > mission._timestamp(value["readback_at_utc"])
        ):
            raise Denied
    if value["required_checks_sha256"] != hashlib.sha256(
        mission.canonical(checks, newline=False)
    ).hexdigest():
        raise Denied
    descriptor = _descriptor(repo_root, task, retained=retained)
    expected_paths = sorted(
        [proof["proof_repo_relative_path"], mission.PROGRESS_PATH, *descriptor["completion_repo_relative_paths"]]
    )
    changes = value["preliminary_changes"]
    if (
        type(changes) is not list
        or [item.get("path") if type(item) is dict else None for item in changes]
        != expected_paths
        or value["preliminary_change_set_sha256"]
        != hashlib.sha256(mission.canonical(changes, newline=False)).hexdigest()
    ):
        raise Denied
    reviewed = {item["path"]: item for item in source_review["reviewed_changes"]}
    for item in changes:
        if type(item) is not dict or set(item) != {"action", "mode", "path", "sha256"}:
            raise Denied
        if item["path"] == mission.PROGRESS_PATH:
            expected_sha = source_review["progress_before_sha256"]
            expected_mode = "100644"
            expected_action = "modify"
        else:
            expected_sha = reviewed[item["path"]]["sha256"]
            expected_mode = reviewed[item["path"]]["mode"]
            expected_action = reviewed[item["path"]]["action"]
        if (
            item["action"] != expected_action
            or item["mode"] != expected_mode
            or item["sha256"] != expected_sha
        ):
            raise Denied
    mission.validate_preliminary_delivery(repo_root, proof, descriptor, {
        "preliminary_head_commit": value["preliminary_head_commit"],
        "preliminary_tree_git_oid": value["preliminary_tree_git_oid"],
        "progress_before_sha256": source_review["progress_before_sha256"],
        "reviewed_changes": source_review["reviewed_changes"],
        "required_ci": {
            "repository": value["repository"],
            "workflow": value["workflow"],
            "head_commit": value["preliminary_head_commit"],
            "conclusion": "success",
            "workflow_sha256": value["workflow_sha256"],
        },
    })
    without_id = dict(value)
    without_id.pop("delivery_id")
    if value["delivery_id"] != hashlib.sha256(
        mission.canonical(without_id, newline=False)
    ).hexdigest():
        raise Denied
    return {"delivery_id": value["delivery_id"], "status": "PASS"}


COMPLETION_REVIEW_KEYS = {
    "artifact_kind",
    "authorized_task",
    "mission_id",
    "preliminary_delivery",
    "preliminary_delivery_sha256",
    "review_id",
    "schema_version",
    "source_review",
    "source_review_sha256",
    "status",
}


def build_completion_review(
    source_review: dict[str, Any],
    source_review_raw: bytes,
    delivery: dict[str, Any],
    delivery_raw: bytes,
) -> dict[str, Any]:
    value = {
        "schema_version": 4,
        "artifact_kind": "subject-task-completion-review-v4",
        "status": "PASS",
        "authorized_task": source_review["authorized_task"],
        "mission_id": source_review["mission_id"],
        "source_review": source_review,
        "source_review_sha256": hashlib.sha256(source_review_raw).hexdigest(),
        "preliminary_delivery": delivery,
        "preliminary_delivery_sha256": hashlib.sha256(delivery_raw).hexdigest(),
    }
    value["review_id"] = hashlib.sha256(
        mission.canonical(value, newline=False)
    ).hexdigest()
    return value


def validate_completion_review_value(
    value: Any,
    raw: bytes,
    repo_root: Path,
    task: str,
    *,
    proof: dict[str, Any] | None = None,
    proof_raw: bytes | None = None,
    retained: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != COMPLETION_REVIEW_KEYS
        or raw != mission.canonical(value)
        or value["schema_version"] != 4
        or value["artifact_kind"] != "subject-task-completion-review-v4"
        or value["status"] != "PASS"
        or value["authorized_task"] != task
    ):
        raise Denied
    source = value["source_review"]
    source_raw = mission.canonical(source)
    delivery = value["preliminary_delivery"]
    delivery_raw = mission.canonical(delivery)
    if (
        value["source_review_sha256"] != hashlib.sha256(source_raw).hexdigest()
        or value["preliminary_delivery_sha256"] != hashlib.sha256(delivery_raw).hexdigest()
    ):
        raise Denied
    preliminary_head = delivery.get("preliminary_head_commit")
    if (
        type(preliminary_head) is not str
        or not preliminary_head.startswith("git:")
        or mission.COMMIT.fullmatch(preliminary_head[4:]) is None
    ):
        raise Denied
    source_result = validate_source_review_value(
        source,
        source_raw,
        repo_root,
        task,
        proof=proof,
        proof_raw=proof_raw,
        retained=retained,
        historical_head=preliminary_head[4:],
    )
    if proof is None or proof_raw is None:
        proof_path = f"specs/subject-distillation/task-authorizations/{task}.json"
        proof_raw = retained[proof_path] if retained and proof_path in retained else mission._read(repo_root, proof_path)
        proof = mission._parse(proof_raw)
    validate_preliminary_delivery_value(
        delivery,
        delivery_raw,
        repo_root,
        task,
        proof=proof,
        proof_raw=proof_raw,
        source_review=source,
        source_review_raw=source_raw,
        retained=retained,
    )
    if value["mission_id"] != source["mission_id"]:
        raise Denied
    without_id = dict(value)
    without_id.pop("review_id")
    if value["review_id"] != hashlib.sha256(
        mission.canonical(without_id, newline=False)
    ).hexdigest():
        raise Denied
    return {
        "authorization_id": source_result["authorization_id"],
        "descriptor": source_result["descriptor"],
        "review_id": value["review_id"],
        "reviewed_at_utc": delivery["readback_at_utc"],
        "status": "PASS",
    }


def _completion_refs(
    task: str,
    proof: dict[str, Any],
    proof_raw: bytes,
    review: dict[str, Any],
    review_raw: bytes,
) -> list[dict[str, str]]:
    review_path = f"specs/subject-distillation/task-authorizations/{task}.review.json"
    refs = _start_refs(task, proof, proof_raw) + [
        {"kind": "opaque", "id": f"{task.lower().replace('-', '')}-review:{review['review_id']}"},
        {
            "kind": "repo_file",
            "path": review_path,
            "sha256": hashlib.sha256(review_raw).hexdigest(),
        },
    ]
    return sorted(refs, key=mission.canonical)


def _prefix(value: dict[str, Any], count: int) -> dict[str, Any]:
    result = {
        "schema_version": value["schema_version"],
        "baseline_id": value["baseline_id"],
        "baseline_full_digest": value["baseline_full_digest"],
        "tasks_sha256": value["tasks_sha256"],
        "updated_at_utc": value["events"][count - 1]["at_utc"],
        "tasks": {f"T-{n:03d}": "PENDING" for n in range(1, 34)},
        "events": value["events"][:count],
    }
    for event in result["events"]:
        result["tasks"][event["task_id"]] = event["to"]
    return result


def _validate_review_progress_prefix(
    source_review: dict[str, Any],
    ledger: dict[str, Any],
    event_index: int,
) -> None:
    before = _prefix(ledger, event_index)
    if (
        source_review["progress_before_sequence"] != event_index
        or source_review["progress_before_sha256"]
        != hashlib.sha256(mission.canonical(before)).hexdigest()
    ):
        raise Denied


def _snapshot_raw(
    repo_root: Path, path: str, retained: dict[str, bytes] | None
) -> bytes:
    if retained is None:
        return mission._read(repo_root, path)
    try:
        return retained[path]
    except KeyError:
        raise Denied from None


def _validate_retained_progress_core(
    value: Any, retained: dict[str, bytes]
) -> dict[str, Any]:
    """Replay the immutable progress grammar without reopening repository paths."""
    if (
        type(value) is not dict
        or set(value)
        != {
            "schema_version",
            "baseline_id",
            "baseline_full_digest",
            "tasks_sha256",
            "updated_at_utc",
            "tasks",
            "events",
        }
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["baseline_id"] != "0dc10cfc4a429662"
        or value["baseline_full_digest"]
        != "0dc10cfc4a429662037f3bb7d6c42e10e7cc832b540f7aa8f4b9e0656e0e459b"
        or value["tasks_sha256"] != mission.TASKS_SHA256
        or type(value["tasks"]) is not dict
        or tuple(sorted(value["tasks"])) != progress_core.TASK_IDS
        or any(
            type(state) is not str or state not in progress_core.STATES
            for state in value["tasks"].values()
        )
        or type(value["events"]) is not list
        or not 6 <= len(value["events"]) <= 4_096
    ):
        raise Denied
    progress_core.evidence._scan_public(value)
    if (
        hashlib.sha256(
            mission.canonical(value["events"][:6], newline=False)
        ).hexdigest()
        != "e70c33f3c1a1e6abc71cd59b694ed5785fa58b608804d02888362c85cf090006"
    ):
        raise Denied
    states = {task: "PENDING" for task in progress_core.TASK_IDS}
    previous_time = None
    for sequence, event in enumerate(value["events"], 1):
        if (
            type(event) is not dict
            or set(event)
            != {
                "sequence",
                "task_id",
                "from",
                "to",
                "at_utc",
                "evidence_refs",
                "blocker",
            }
            or type(event["sequence"]) is not int
            or event["sequence"] != sequence
        ):
            raise Denied
        task = event["task_id"]
        before = event["from"]
        after = event["to"]
        if (
            task not in progress_core.TASK_IDS
            or states[task] != before
            or (before, after) not in progress_core.TRANSITIONS
            or before == "COMPLETED"
        ):
            raise Denied
        when = progress_core.evidence._timestamp(event["at_utc"])
        if previous_time is not None and when < previous_time:
            raise Denied
        previous_time = when
        refs = event["evidence_refs"]
        if type(refs) is not list or len(refs) > 16:
            raise Denied
        canonical_refs = [mission.canonical(ref) for ref in refs]
        if canonical_refs != sorted(canonical_refs) or len(canonical_refs) != len(
            set(canonical_refs)
        ):
            raise Denied
        for ref in refs:
            if type(ref) is not dict:
                raise Denied
            if set(ref) == {"kind", "id"} and ref["kind"] == "opaque":
                if type(ref["id"]) is not str or progress_core.OPAQUE.fullmatch(ref["id"]) is None:
                    raise Denied
            elif (
                set(ref) == {"kind", "path", "sha256"}
                and ref["kind"] == "repo_file"
                and type(ref["path"]) is str
                and type(ref["sha256"]) is str
                and progress_core.HEX64.fullmatch(ref["sha256"]) is not None
            ):
                if sequence > 6:
                    raw = _snapshot_raw(Path("."), ref["path"], retained)
                    if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
                        raise Denied
            else:
                raise Denied
        if after == "BLOCKED":
            if (
                type(event["blocker"]) is not str
                or progress_core.BLOCKER.fullmatch(event["blocker"]) is None
            ):
                raise Denied
        elif event["blocker"] is not None:
            raise Denied
        if after == "COMPLETED" and not refs:
            raise Denied
        if after in {"IN_PROGRESS", "COMPLETED"} and not progress_core._dependencies_allow(
            task, states
        ):
            raise Denied
        states[task] = after
        if sum(state == "IN_PROGRESS" for state in states.values()) > 1:
            raise Denied
    if value["tasks"] != states or value["updated_at_utc"] != value["events"][-1]["at_utc"]:
        raise Denied
    return {"sequence": len(value["events"]), "status": "PASS"}


def validate_ledger_value(
    value: Any,
    repo_root: Path,
    *,
    retained: dict[str, bytes] | None = None,
    pending_final_delivery_task: str | None = None,
    pending_progress_only_task: str | None = None,
    include_delivery_anchor: bool = False,
) -> dict[str, Any]:
    if pending_final_delivery_task is not None and mission.TASK.fullmatch(
        pending_final_delivery_task
    ) is None:
        raise Denied
    if retained is None:
        paths = progress_writer._paths(repo_root)
        manifest, tasks_sha = progress_writer._inputs(paths)
        progress_core.validate_value(
            value,
            repo_root=repo_root,
            manifest_result=manifest,
            tasks_sha256=tasks_sha,
        )
    else:
        _validate_retained_progress_core(value, retained)
    if (
        hashlib.sha256(mission.canonical(value["events"][:6], newline=False)).hexdigest()
        != "e70c33f3c1a1e6abc71cd59b694ed5785fa58b608804d02888362c85cf090006"
    ):
        raise Denied
    proof_context: dict[str, tuple[dict[str, Any], bytes]] = {}
    last_delivery_commit: str | None = None
    for index, event in enumerate(value["events"][6:], start=6):
        task = event["task_id"]
        if mission.TASK.fullmatch(task) is None:
            raise Denied
        if event["from"] == "PENDING" and event["to"] == "BLOCKED":
            if task != "T-032" or event["blocker"] != "OPERATIONAL_ACTION_REQUIRED":
                raise Denied
            if last_delivery_commit is None:
                raise Denied
            if task != pending_progress_only_task:
                last_delivery_commit = mission.validate_progress_only_delivery(
                    repo_root,
                    parent_commit=last_delivery_commit,
                    progress_raw=mission.canonical(_prefix(value, index + 1)),
                )
            continue
        if event["to"] == "IN_PROGRESS":
            if event["from"] != "PENDING" or task in proof_context:
                raise Denied
            proof_path = f"specs/subject-distillation/task-authorizations/{task}.json"
            proof_raw = _snapshot_raw(repo_root, proof_path, retained)
            proof = mission._parse(proof_raw)
            validate_task_authorization_value(
                proof,
                proof_raw,
                repo_root,
                retained=retained,
                historical=True,
            )
            before = _prefix(value, index)
            if task == "T-004":
                mission_raw = _snapshot_raw(
                    repo_root, mission.MISSION_PROOF_PATH, retained
                )
                mission_proof = mission._parse(mission_raw)
                expected_base = mission.validate_mission_activation_delivery(
                    repo_root,
                    protocol_base=mission_proof["protocol_base_commit"][4:],
                    mission_raw=mission_raw,
                )
            else:
                if last_delivery_commit is None:
                    raise Denied
                expected_base = last_delivery_commit
            if (
                proof["progress_sequence"] != index
                or proof["progress_sha256"] != hashlib.sha256(mission.canonical(before)).hexdigest()
                or proof["implementation_base_commit"] != "git:" + expected_base
                or event["evidence_refs"] != _start_refs(task, proof, proof_raw)
                or mission._timestamp(event["at_utc"]) < mission._timestamp(proof["derived_at_utc"])
            ):
                raise Denied
            proof_context[task] = (proof, proof_raw)
            continue
        if event["from"] == "IN_PROGRESS" and event["to"] == "BLOCKED":
            if task not in proof_context or event["blocker"] not in {
                "MISSION_EXPIRED",
                "MISSION_REVOKED",
            }:
                raise Denied
            continue
        if event["from"] == "IN_PROGRESS" and event["to"] == "COMPLETED":
            if task not in proof_context:
                raise Denied
            if task == "T-033":
                # The frozen progress core has already run its exact attestation
                # and private/experimental final gate.  V4 only proves that the
                # attester finalized a mission-authorized T-033 start; the public
                # generic updater never exposes this transition.
                continue
            proof, proof_raw = proof_context[task]
            review_path = f"specs/subject-distillation/task-authorizations/{task}.review.json"
            review_raw = _snapshot_raw(repo_root, review_path, retained)
            review = mission._parse(review_raw)
            review_result = validate_completion_review_value(
                review,
                review_raw,
                repo_root,
                task,
                proof=proof,
                proof_raw=proof_raw,
                retained=retained,
            )
            _validate_review_progress_prefix(review["source_review"], value, index)
            if (
                event["evidence_refs"]
                != _completion_refs(task, proof, proof_raw, review, review_raw)
                or mission._timestamp(event["at_utc"])
                < mission._timestamp(review_result["reviewed_at_utc"])
            ):
                raise Denied
            if task != pending_final_delivery_task:
                last_delivery_commit = mission.validate_final_delivery(
                    repo_root,
                    preliminary_head=review["preliminary_delivery"][
                        "preliminary_head_commit"
                    ][4:],
                    review_path=review_path,
                    review_raw=review_raw,
                    progress_raw=mission.canonical(_prefix(value, index + 1)),
                )
            continue
        raise Denied
    result: dict[str, Any] = {
        "proofs": len(proof_context),
        "sequence": len(value["events"]),
        "status": "PASS",
    }
    if include_delivery_anchor:
        result["delivery_anchor"] = last_delivery_commit
    return result


def validate_t033_candidate(
    repo_root: Path,
    candidate_ledger: dict[str, Any],
    *,
    expected_attestation_ref: dict[str, str],
    retained_snapshot: dict[str, bytes],
) -> dict[str, Any]:
    """Historical replay for a temporary T-033 final ledger candidate."""
    if type(retained_snapshot) is not dict or type(candidate_ledger) is not dict:
        raise Denied
    if (
        mission.PROGRESS_PATH not in retained_snapshot
        or retained_snapshot[mission.PROGRESS_PATH] != mission.canonical(candidate_ledger)
    ):
        raise Denied
    tasks = candidate_ledger.get("tasks")
    if type(tasks) is not dict:
        raise Denied
    if any(tasks[f"T-{number:03d}"] != "COMPLETED" for number in range(1, 32)):
        raise Denied
    if tasks["T-032"] not in {"BLOCKED", "COMPLETED"} or tasks["T-033"] != "COMPLETED":
        raise Denied
    events = candidate_ledger["events"]
    if (
        not events
        or events[-1]["task_id"] != "T-033"
        or events[-1]["from"] != "IN_PROGRESS"
        or events[-1]["to"] != "COMPLETED"
        or events[-1]["evidence_refs"] != [expected_attestation_ref]
        or expected_attestation_ref.get("kind") != "repo_file"
        or expected_attestation_ref.get("path")
        != "specs/subject-distillation/evidence/0dc10cfc4a429662/attestation.json"
        or mission.HEX64.fullmatch(expected_attestation_ref.get("sha256", "")) is None
    ):
        raise Denied
    required_paths = {
        mission.MISSION_PROOF_PATH,
        mission.PROGRESS_PATH,
        expected_attestation_ref["path"],
        *mission.RETAINED_AUTHORITY_PATHS,
    }
    if mission.MISSION_PROOF_PATH not in retained_snapshot:
        raise Denied
    mission_value = mission._parse(retained_snapshot[mission.MISSION_PROOF_PATH])
    trust_root = mission_value.get("trust_root") if type(mission_value) is dict else None
    if type(trust_root) is not list:
        raise Denied
    expected_hashes: dict[str, str] = {
        expected_attestation_ref["path"]: expected_attestation_ref["sha256"]
    }
    for item in trust_root:
        if (
            type(item) is not dict
            or set(item) != {"path", "sha256"}
            or type(item["path"]) is not str
            or mission.HEX64.fullmatch(item["sha256"]) is None
        ):
            raise Denied
        required_paths.add(item["path"])
        expected_hashes[item["path"]] = item["sha256"]
    for event in events[6:]:
        for ref in event["evidence_refs"]:
            if ref.get("kind") == "repo_file":
                required_paths.add(ref["path"])
                expected_hashes[ref["path"]] = ref["sha256"]
    if not required_paths <= set(retained_snapshot):
        raise Denied
    for path, expected in expected_hashes.items():
        if hashlib.sha256(retained_snapshot[path]).hexdigest() != expected:
            raise Denied
    overlay = validate_ledger_value(
        candidate_ledger, repo_root, retained=retained_snapshot
    )
    proof_raw = retained_snapshot[mission.MISSION_PROOF_PATH]
    replay = [
        {
            "kind": "mission_root",
            "path": mission.MISSION_PROOF_PATH,
            "sha256": hashlib.sha256(proof_raw).hexdigest(),
        }
    ]
    for event in events[6:]:
        replay.append(
            {
                "event_sha256": hashlib.sha256(
                    mission.canonical(event, newline=False)
                ).hexdigest(),
                "sequence": event["sequence"],
                "task_id": event["task_id"],
            }
        )
    return {
        "mission_replay_sha256": hashlib.sha256(
            mission.canonical(replay, newline=False)
        ).hexdigest(),
        "sequence": overlay["sequence"],
        "status": "PASS",
    }


def validate_t033_action(
    repo_root: Path,
    candidate_ledger: dict[str, Any],
    *,
    expected_attestation_ref: dict[str, str],
    retained_snapshot: dict[str, bytes],
    _clock: Callable[[], str] | None = None,
) -> dict[str, Any]:
    """Fresh attester-only action gate layered over historical replay."""
    first_now = (
        _clock() if _clock is not None else mission._time(mission._now())
    )
    if mission.REVOCATION_PATH in retained_snapshot or _entry_exists(
        repo_root, mission.REVOCATION_PATH
    ):
        raise Denied
    proof_raw = _snapshot_raw(
        repo_root, mission.MISSION_PROOF_PATH, retained_snapshot
    )
    proof = mission._parse(proof_raw)
    validate_mission_proof_value(
        proof,
        proof_raw,
        repo_root,
        now_utc=first_now,
        retained=retained_snapshot,
    )
    result = validate_t033_candidate(
        repo_root,
        candidate_ledger,
        expected_attestation_ref=expected_attestation_ref,
        retained_snapshot=retained_snapshot,
    )
    if _entry_exists(repo_root, mission.REVOCATION_PATH):
        raise Denied
    final_now = _clock() if _clock is not None else mission._time(mission._now())
    if mission._timestamp(final_now) < mission._timestamp(first_now):
        raise Denied
    validate_mission_proof_value(
        proof,
        proof_raw,
        repo_root,
        now_utc=final_now,
        retained=retained_snapshot,
    )
    return result


def validate_t033_current(
    repo_root: Path, candidate_ledger: dict[str, Any]
) -> dict[str, Any]:
    """Required-CI replay using one retained current-tree snapshot."""
    events = candidate_ledger.get("events")
    if type(events) is not list or not events:
        raise Denied
    final_refs = events[-1].get("evidence_refs")
    if type(final_refs) is not list or len(final_refs) != 1:
        raise Denied
    paths = {
        mission.MISSION_PROOF_PATH,
        mission.PROGRESS_PATH,
        *mission.RETAINED_AUTHORITY_PATHS,
    }
    for event in events[6:]:
        refs = event.get("evidence_refs")
        if type(refs) is not list:
            raise Denied
        for ref in refs:
            if type(ref) is not dict:
                raise Denied
            if ref.get("kind") == "repo_file":
                paths.add(ref.get("path"))
    if not all(type(path) is str for path in paths):
        raise Denied
    discovery = mission.open_paths_guard(repo_root, sorted(paths))
    try:
        first = discovery.snapshot()
        root = mission._parse(first[mission.MISSION_PROOF_PATH])
        trust_root = root.get("trust_root") if type(root) is dict else None
        if type(trust_root) is not list:
            raise Denied
        for item in trust_root:
            if type(item) is not dict or type(item.get("path")) is not str:
                raise Denied
            paths.add(item["path"])
        discovery.audit()
    finally:
        discovery.close()
    retained = mission.open_paths_guard(repo_root, sorted(paths))
    try:
        snapshot = retained.snapshot()
        result = validate_t033_candidate(
            repo_root,
            candidate_ledger,
            expected_attestation_ref=final_refs[0],
            retained_snapshot=snapshot,
        )
        retained.audit()
        return result
    finally:
        retained.close()


def _entry_exists(repo_root: Path, path: str) -> bool:
    return mission.legacy._repo_entry_exists(repo_root, path)


def validate(repo_root: Path, *, now_utc: str | None = None) -> dict[str, Any]:
    contract, _contract_raw = mission.load_contract(repo_root)
    mission.load_registry(repo_root, contract)
    progress, progress_raw = mission._load_progress(repo_root)
    proof_present = _entry_exists(repo_root, mission.MISSION_PROOF_PATH)
    revoked_present = _entry_exists(repo_root, mission.REVOCATION_PATH)
    if not proof_present:
        if (
            revoked_present
            or hashlib.sha256(progress_raw).hexdigest() != mission.ACTIVATION_PROGRESS_SHA256
            or len(progress.get("events", [])) != 6
            or any(progress["tasks"][f"T-{number:03d}"] != "PENDING" for number in range(4, 34))
        ):
            raise Denied
        # The frozen v3 full delivery validator correctly rejects additive v4
        # Git paths. Replay its pure content-addressed ledger predicate here;
        # hosted CI separately replays the exact v3 delivery checkpoint.
        legacy_validator.validate_ledger_value(progress, repo_root)
        return {
            "active": False,
            "authorized_tasks": 0,
            "mission_id": None,
            "mission_state": "INACTIVE",
            "sequence": 6,
            "status": "PASS",
        }
    proof_raw = mission._read(repo_root, mission.MISSION_PROOF_PATH)
    proof = mission._parse(proof_raw)
    # Historical validity is evaluated at activation. Current eligibility is a
    # separate action gate so expiry/revocation can be delivered through CI.
    result = validate_mission_proof_value(
        proof, proof_raw, repo_root, now_utc=proof["active_from_utc"]
    )
    mission.check_active_protocol_ancestry(repo_root, result["protocol_base_commit"][4:])
    mission.validate_mission_activation_delivery(
        repo_root,
        protocol_base=result["protocol_base_commit"][4:],
        mission_raw=proof_raw,
    )
    overlay = validate_ledger_value(progress, repo_root)
    if progress["tasks"]["T-033"] == "COMPLETED":
        validate_t033_current(repo_root, progress)
    state = "ACTIVE"
    if revoked_present:
        revocation_raw = mission._read(repo_root, mission.REVOCATION_PATH)
        revocation = mission._parse(revocation_raw)
        validate_revocation_value(revocation, revocation_raw, proof)
        validate_revocation_progress(revocation, progress)
        state = "REVOKED"
    elif mission._now(now_utc) >= mission._timestamp(proof["mission_not_after_utc"]):
        state = "EXPIRED"
    if state != "ACTIVE" and any(value == "IN_PROGRESS" for value in progress["tasks"].values()):
        raise Denied
    return {
        "active": state == "ACTIVE",
        "authorized_tasks": 30 if state == "ACTIVE" else 0,
        "mission_id": result["mission_id"],
        "mission_state": state,
        "sequence": overlay["sequence"],
        "status": "PASS",
    }


def main(argv: list[str] | None = None) -> int:
    try:
        if argv not in (None, ["--json"]):
            raise Denied
        result = validate(Path.cwd().absolute())
        sys.stdout.buffer.write(mission.canonical(result))
        return 0
    except (Denied, mission.legacy.v1.Denied):
        sys.stderr.write(DENY_TEXT)
        return 2
    except Exception:  # noqa: BLE001 - fixed no-echo boundary
        sys.stderr.write(ERROR_TEXT)
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
