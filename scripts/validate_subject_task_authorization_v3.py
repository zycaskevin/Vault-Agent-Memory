#!/usr/bin/env python3
"""Validate additive Subject task authorization proofs and ledger bindings."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Any

_BOOTSTRAP_ERROR = False
try:
    import run_subject_task_authorization_v3 as runner
    import validate_subject_progress as progress_v1
except ImportError:  # pragma: no cover - import path used by test loaders
    try:
        from scripts import run_subject_task_authorization_v3 as runner
        from scripts import validate_subject_progress as progress_v1
    except Exception:  # noqa: BLE001 - fixed startup boundary
        runner = progress_v1 = None
        _BOOTSTRAP_ERROR = True
except Exception:  # noqa: BLE001 - fixed startup boundary
    runner = progress_v1 = None
    _BOOTSTRAP_ERROR = True


DENY_TEXT = "SUBJECT_TASK_AUTHORIZATION_V3_VALIDATOR_DENY\n"
ERROR_TEXT = "SUBJECT_TASK_AUTHORIZATION_V3_VALIDATOR_ERROR\n"
HEX64 = re.compile(r"[0-9a-f]{64}")
TIME_KEYS = {"issued_at_utc", "expires_at_utc", "recorded_at_utc"}
REVIEW_KEYS = {
    "schema_version",
    "artifact_kind",
    "status",
    "authorized_task",
    "implementation_base_commit",
    "baseline_id",
    "baseline_full_digest",
    "scope_descriptor_sha256",
    "authorization_proof_sha256",
    "reviewed_at_utc",
    "builder_principal",
    "reviewer_principal",
    "verification_commands",
    "verification_result",
    "p0",
    "p1",
    "p2",
    "verdict",
    "reviewed_outputs",
    "reviewed_changes",
    "reviewed_change_paths",
    "reviewed_change_set_sha256",
    "progress_before_sequence",
    "progress_before_sha256",
}
PROOF_KEYS = {
    "schema_version",
    "artifact_kind",
    "status",
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
    "recorded_at_utc",
    "scope_descriptor_path",
    "scope_descriptor_sha256",
    "progress_sequence",
    "progress_sha256",
    "receipt_sha256",
    "scope_sha256",
    "authorization_verifier_sha256",
    "authorization_schema_sha256",
    "authorization_id",
    "proposal_id",
    "authorization_runner_v1_sha256",
    "authorization_runner_v3_sha256",
    "task_authorization_schema_sha256",
    "task_authorization_validator_sha256",
    "task_progress_updater_v3_sha256",
    "owner_confirmation_ref",
    "proof_repo_relative_path",
}
if _BOOTSTRAP_ERROR:
    class Denied(Exception):
        pass
else:
    Denied = runner.Denied


class _Parser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise Denied


def _merge_retained_snapshots(
    *snapshots: dict[str, bytes],
) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for snapshot in snapshots:
        for label, raw in snapshot.items():
            if label in result and result[label] != raw:
                raise Denied
            result[label] = raw
    return result


def _retained_json(
    retained: dict[str, bytes], path: str
) -> tuple[Any, bytes]:
    try:
        raw = retained[path]
        value = runner.v1.verifier._parse(raw)
        runner._scan_v3(value)
    except (KeyError, runner.v1.verifier.Denied, runner.Denied):
        raise Denied from None
    if raw != runner._canonical(value):
        raise Denied
    return value, raw


def _require_supported_task(
    repo_root: Path,
    task: Any,
    *,
    retained: dict[str, bytes] | None = None,
) -> str:
    if type(task) is not str or runner.TASK.fullmatch(task) is None:
        raise Denied
    if retained is None:
        contract, _contract_raw = runner._load_contract(repo_root)
    else:
        contract, contract_raw = _retained_json(retained, runner.CONTRACT_PATH)
        runner._validate_contract(contract, contract_raw)
    if (
        task != "T-003"
        or task != contract["allowed_tasks"]["first"]
        or task != contract["allowed_tasks"]["last"]
    ):
        raise Denied
    return task


def _load_json(path: Path) -> tuple[Any, bytes]:
    root = Path.cwd().absolute()
    try:
        relative = path.absolute().relative_to(root).as_posix()
    except ValueError:
        raise Denied from None
    raw, identity = runner._read_repo_file(root, relative)
    runner._require_public_identity(identity, 0o644)
    try:
        value = runner.v1.verifier._parse(raw)
        runner._scan_v3(value)
    except (runner.v1.verifier.Denied, runner.Denied):
        raise Denied from None
    if raw != runner._canonical(value):
        raise Denied
    return value, raw


def _proof_proposal(value: dict[str, Any]) -> dict[str, Any]:
    proposal = {
        key: value[key]
        for key in runner.PROPOSAL_KEYS
        if key != "proposal_id"
    }
    base = value["implementation_base_commit"]
    if type(base) is not str or not base.startswith("git:"):
        raise Denied
    proposal["implementation_base_commit"] = base[4:]
    proposal["artifact_kind"] = runner.PROPOSAL_KIND
    proposal["proposal_id"] = value["proposal_id"]
    return proposal


def validate_proof_value(
    value: Any,
    repo_root: Path,
    *,
    require_current_prestart: bool = False,
    retained: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != PROOF_KEYS:
        raise Denied
    if (
        value["schema_version"] != 3
        or value["artifact_kind"] != runner.PROOF_KIND
        or value["status"] != "PASS"
        or value["protocol_decision_id"] != runner.PROTOCOL_DECISION_ID
        or value["authorizing_principal"] != runner.AUTHORITY
    ):
        raise Denied
    task = _require_supported_task(
        repo_root, value["authorized_task"], retained=retained
    )
    if type(value["progress_sequence"]) is not int or value["progress_sequence"] < 1:
        raise Denied
    for key in PROOF_KEYS - TIME_KEYS - {
        "schema_version",
        "artifact_kind",
        "status",
        "protocol_decision_id",
        "authorized_task",
        "implementation_base_commit",
        "baseline_id",
        "authorizing_principal",
        "allowed_repo_relative_paths",
        "non_goals",
        "prohibited_operations",
        "progress_sequence",
        "scope_descriptor_path",
        "owner_confirmation_ref",
        "proof_repo_relative_path",
    }:
        if type(value[key]) is not str or HEX64.fullmatch(value[key]) is None:
            raise Denied
    if type(value["owner_confirmation_ref"]) is not str or runner.OPAQUE.fullmatch(
        value["owner_confirmation_ref"]
    ) is None:
        raise Denied
    issued = runner.v1.verifier._timestamp(value["issued_at_utc"])
    expires = runner.v1.verifier._timestamp(value["expires_at_utc"])
    recorded = runner.v1.verifier._timestamp(value["recorded_at_utc"])
    if not issued <= recorded < expires or expires - issued != runner.VALIDITY:
        raise Denied
    if retained is None:
        descriptor, descriptor_raw = runner._load_scope_descriptor(repo_root, task)
    else:
        descriptor_value, descriptor_raw = _retained_json(
            retained, runner._scope_path(task)
        )
        descriptor = runner._validate_scope_descriptor(
            descriptor_value, descriptor_raw, task
        )
    if (
        value["scope_descriptor_path"] != runner._scope_path(task)
        or value["scope_descriptor_sha256"]
        != hashlib.sha256(descriptor_raw).hexdigest()
        or value["allowed_repo_relative_paths"]
        != descriptor["allowed_repo_relative_paths"]
        or value["non_goals"] != descriptor["non_goals"]
        or value["prohibited_operations"] != descriptor["prohibited_operations"]
        or value["proof_repo_relative_path"] != descriptor["proof_repo_relative_path"]
        or (value["baseline_id"], value["baseline_full_digest"])
        != (descriptor["baseline_id"], descriptor["baseline_full_digest"])
    ):
        raise Denied
    if retained is None:
        support = runner._support_hashes(repo_root)
    else:
        support_paths = {
            "protocol_contract_sha256": runner.CONTRACT_PATH,
            "task_authorization_schema_sha256": runner.PROOF_SCHEMA_PATH,
            "task_authorization_validator_sha256": runner.VALIDATOR_PATH,
            "task_progress_updater_v3_sha256": runner.UPDATER_PATH,
            "authorization_runner_v1_sha256": runner.V1_RUNNER_PATH,
            "progress_validator_sha256": runner.PROGRESS_VALIDATOR_PATH,
            "authorization_runner_v3_sha256": "scripts/run_subject_task_authorization_v3.py",
        }
        try:
            support = {
                key: hashlib.sha256(retained[path]).hexdigest()
                for key, path in support_paths.items()
            }
        except KeyError:
            raise Denied from None
        if (
            support["authorization_runner_v1_sha256"]
            != runner.EXPECTED_V1_RUNNER_SHA256
            or support["progress_validator_sha256"]
            != runner.EXPECTED_PROGRESS_VALIDATOR_SHA256
        ):
            raise Denied
    for key in (
        "protocol_contract_sha256",
        "authorization_runner_v1_sha256",
        "authorization_runner_v3_sha256",
        "task_authorization_schema_sha256",
        "task_authorization_validator_sha256",
        "task_progress_updater_v3_sha256",
    ):
        if value[key] != support[key]:
            raise Denied
    if (
        value["authorization_verifier_sha256"] != runner.EXPECTED_VERIFIER_SHA256
        or value["authorization_schema_sha256"] != runner.EXPECTED_V1_SCHEMA_SHA256
    ):
        raise Denied
    if retained is not None:
        try:
            verifier_raw = retained[runner.v1.verifier.VERIFIER_PATH]
            authorization_schema_raw = retained[runner.v1.verifier.SCHEMA_PATH]
        except KeyError:
            raise Denied from None
        if (
            hashlib.sha256(verifier_raw).hexdigest()
            != runner.EXPECTED_VERIFIER_SHA256
            or hashlib.sha256(authorization_schema_raw).hexdigest()
            != runner.EXPECTED_V1_SCHEMA_SHA256
        ):
            raise Denied
    scope = {
        "schema_version": 1,
        "artifact_kind": runner.v1.SCOPE_KIND,
        "baseline_id": value["baseline_id"],
        "baseline_full_digest": value["baseline_full_digest"],
        "authorized_task": task,
        "allowed_repo_relative_paths": value["allowed_repo_relative_paths"],
        "non_goals": value["non_goals"],
        "prohibited_operations": value["prohibited_operations"],
    }
    scope_raw = runner._canonical(scope)
    if value["scope_sha256"] != hashlib.sha256(scope_raw).hexdigest():
        raise Denied
    receipt = {
        "schema_version": 1,
        "artifact_kind": "subject-distillation-implementation-authorization",
        "baseline_id": value["baseline_id"],
        "baseline_full_digest": value["baseline_full_digest"],
        "authorizing_principal": value["authorizing_principal"],
        "authorized_task": task,
        "scope_sha256": value["scope_sha256"],
        "authorization_verifier_sha256": value["authorization_verifier_sha256"],
        "authorization_schema_sha256": value["authorization_schema_sha256"],
        "issued_at_utc": value["issued_at_utc"],
        "expires_at_utc": value["expires_at_utc"],
    }
    authorization_id = hashlib.sha256(
        runner._canonical(receipt, newline=False)
    ).hexdigest()
    receipt["authorization_id"] = authorization_id
    if (
        value["authorization_id"] != authorization_id
        or value["receipt_sha256"]
        != hashlib.sha256(runner._canonical(receipt)).hexdigest()
    ):
        raise Denied
    proposal = _proof_proposal(value)
    without_id = dict(proposal)
    without_id.pop("proposal_id")
    if value["proposal_id"] != hashlib.sha256(runner._canonical(without_id)).hexdigest():
        raise Denied
    if require_current_prestart:
        snapshot = runner._default_task_progress_snapshot(repo_root, task)
        if (
            snapshot.sequence != value["progress_sequence"]
            or snapshot.raw_sha256 != value["progress_sha256"]
        ):
            raise Denied
    return {
        "authorization_id": authorization_id,
        "authorized_task": task,
        "status": "PASS",
    }


def validate_proof(path: Path, *, require_current_prestart: bool = False) -> dict[str, Any]:
    value, _raw = _load_json(path)
    return validate_proof_value(
        value,
        Path.cwd().absolute(),
        require_current_prestart=require_current_prestart,
    )


def _prefix_value(value: dict[str, Any], count: int) -> dict[str, Any]:
    states = {task: "PENDING" for task in runner.TASK_IDS}
    for event in value["events"][:count]:
        states[event["task_id"]] = event["to"]
    result = {
        "schema_version": value["schema_version"],
        "baseline_id": value["baseline_id"],
        "baseline_full_digest": value["baseline_full_digest"],
        "tasks_sha256": value["tasks_sha256"],
        "updated_at_utc": value["events"][count - 1]["at_utc"],
        "tasks": states,
        "events": value["events"][:count],
    }
    return result


def _review_progress_context(
    value: Any,
    task: str,
    reviewed_at_utc: str,
) -> tuple[dict[str, Any], bytes]:
    if type(value) is not dict or type(value.get("events")) is not list:
        raise Denied
    events = value["events"]
    completion_indexes = [
        index
        for index, event in enumerate(events)
        if type(event) is dict
        and event.get("task_id") == task
        and event.get("to") == "COMPLETED"
    ]
    if completion_indexes:
        if completion_indexes != [len(events) - 1]:
            raise Denied
        if runner.v1.verifier._timestamp(
            reviewed_at_utc
        ) > runner.v1.verifier._timestamp(events[completion_indexes[0]].get("at_utc")):
            raise Denied
        prefix = _prefix_value(value, completion_indexes[0])
    else:
        prefix = value
    if prefix.get("tasks", {}).get(task) != "IN_PROGRESS":
        raise Denied
    latest = next(
        (
            event
            for event in reversed(prefix["events"])
            if type(event) is dict
            and event.get("task_id") == task
            and event.get("to") == "IN_PROGRESS"
        ),
        None,
    )
    if latest is None or runner.v1.verifier._timestamp(
        reviewed_at_utc
    ) < runner.v1.verifier._timestamp(latest.get("at_utc")):
        raise Denied
    raw = runner._canonical(prefix)
    return prefix, raw


def _expected_start_refs(
    repo_root: Path,
    task: str,
    authorization_id: str,
    proof_path: str,
    *,
    proof_raw: bytes | None = None,
) -> list[dict[str, str]]:
    raw = proof_raw
    if raw is None:
        raw, _identity = runner._read_repo_file(repo_root, proof_path)
    prefix = task.lower().replace("-", "")
    refs = [
        {
            "kind": "opaque",
            "id": f"{prefix}-authorization:{authorization_id}",
        },
        {
            "kind": "repo_file",
            "path": proof_path,
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
    ]
    refs.sort(key=runner._canonical)
    return refs


def validate_start_refs(
    repo_root: Path,
    task: str,
    proof_path: str,
    authorization_id: str,
    refs: list[dict[str, str]],
    *,
    proof_raw: bytes | None = None,
) -> None:
    if refs != _expected_start_refs(
        repo_root,
        task,
        authorization_id,
        proof_path,
        proof_raw=proof_raw,
    ):
        raise Denied


def _review_path(task: str) -> str:
    if task != "T-003":
        raise Denied
    return f"specs/subject-distillation/task-authorizations/{task}.review.json"


def _reviewed_outputs(
    repo_root: Path, descriptor: dict[str, Any]
) -> list[dict[str, str]]:
    policies = {
        item["path"]: item for item in descriptor["writable_path_policies"]
    }
    outputs: list[dict[str, str]] = []
    for path in descriptor["completion_repo_relative_paths"]:
        raw, identity = runner._read_repo_file(repo_root, path, maximum=16_777_216)
        expected_mode = policies[path]["final_mode"]
        mode = 0o755 if expected_mode == "0755" else 0o644
        runner._require_public_identity(identity, mode)
        outputs.append(
            {
                "mode": f"10{expected_mode}",
                "path": path,
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return outputs


def validate_completion_review_value(
    value: Any,
    raw: bytes,
    repo_root: Path,
    task: str,
    *,
    retained: dict[str, bytes] | None = None,
    progress_value: Any | None = None,
) -> dict[str, Any]:
    _require_supported_task(repo_root, task, retained=retained)
    if type(value) is not dict or set(value) != REVIEW_KEYS or raw != runner._canonical(value):
        raise Denied
    if (
        value["schema_version"] != 3
        or value["artifact_kind"] != "subject-task-completion-review-v3"
        or value["status"] != "PASS"
        or value["authorized_task"] != task
        or task != "T-003"
        or value["verdict"] != "PASS"
    ):
        raise Denied
    if retained is None:
        descriptor, descriptor_raw = runner._load_scope_descriptor(repo_root, task)
    else:
        try:
            descriptor_raw = retained[runner._scope_path(task)]
            descriptor_value = runner.v1.verifier._parse(descriptor_raw)
            descriptor = runner._validate_scope_descriptor(
                descriptor_value, descriptor_raw, task
            )
        except (KeyError, runner.v1.verifier.Denied, runner.Denied):
            raise Denied from None
    proof_path = descriptor["proof_repo_relative_path"]
    if retained is None:
        proof_value, proof_raw = _load_json(repo_root / proof_path)
    else:
        try:
            proof_raw = retained[proof_path]
            proof_value = runner.v1.verifier._parse(proof_raw)
            runner._scan_v3(proof_value)
        except (KeyError, runner.v1.verifier.Denied, runner.Denied):
            raise Denied from None
        if proof_raw != runner._canonical(proof_value):
            raise Denied
    proof_result = validate_proof_value(proof_value, repo_root, retained=retained)
    if proof_result["authorized_task"] != task:
        raise Denied
    reviewed_at = runner.v1.verifier._timestamp(value["reviewed_at_utc"])
    recorded_at = runner.v1.verifier._timestamp(proof_value["recorded_at_utc"])
    if reviewed_at < recorded_at:
        raise Denied
    if progress_value is not None:
        progress_raw = runner._canonical(progress_value)
    elif retained is None:
        progress_raw, _progress_identity = runner._read_repo_file(
            repo_root, runner.PROGRESS_PATH
        )
    else:
        try:
            progress_raw = retained[runner.PROGRESS_PATH]
        except KeyError:
            raise Denied from None
    try:
        progress_value = runner.v1.verifier._parse(progress_raw)
        runner._scan_v3(progress_value)
    except (runner.v1.verifier.Denied, runner.Denied):
        raise Denied from None
    if progress_raw != runner._canonical(progress_value):
        raise Denied
    progress_before, progress_before_raw = _review_progress_context(
        progress_value, task, value["reviewed_at_utc"]
    )
    if (
        type(value["progress_before_sequence"]) is not int
        or value["progress_before_sequence"] != len(progress_before["events"])
        or value["progress_before_sha256"]
        != hashlib.sha256(progress_before_raw).hexdigest()
    ):
        raise Denied
    if (
        value["implementation_base_commit"] != proof_value["implementation_base_commit"]
        or value["baseline_id"] != proof_value["baseline_id"]
        or value["baseline_full_digest"] != proof_value["baseline_full_digest"]
        or value["scope_descriptor_sha256"] != hashlib.sha256(descriptor_raw).hexdigest()
        or value["authorization_proof_sha256"] != hashlib.sha256(proof_raw).hexdigest()
        or value["verification_commands"] != descriptor["verification_commands"]
        or value["verification_result"] != {"exit_code": 0, "status": "PASS"}
    ):
        raise Denied
    for principal in (value["builder_principal"], value["reviewer_principal"]):
        if type(principal) is not str or runner.OPAQUE.fullmatch(principal) is None:
            raise Denied
    if value["builder_principal"] == value["reviewer_principal"]:
        raise Denied
    for key in ("p0", "p1", "p2"):
        if type(value[key]) is not int or not 0 <= value[key] <= 65_535:
            raise Denied
    if value["p0"] != 0 or value["p1"] != 0:
        raise Denied
    policies = {
        item["path"]: item for item in descriptor["writable_path_policies"]
    }
    if retained is None:
        outputs = _reviewed_outputs(repo_root, descriptor)
    else:
        try:
            outputs = [
                {
                    "mode": f"10{policies[path]['final_mode']}",
                    "path": path,
                    "sha256": hashlib.sha256(retained[path]).hexdigest(),
                }
                for path in descriptor["completion_repo_relative_paths"]
            ]
        except KeyError:
            raise Denied from None
    review_path = _review_path(task)
    change_paths = sorted(
        descriptor["completion_repo_relative_paths"] + [proof_path]
    )
    changes = value["reviewed_changes"]
    if (
        type(changes) is not list
        or len(changes) != len(change_paths)
        or value["reviewed_outputs"] != outputs
        or value["reviewed_change_paths"] != change_paths
        or [item.get("path") if type(item) is dict else None for item in changes]
        != change_paths
    ):
        raise Denied
    for item in changes:
        if type(item) is not dict or set(item) != {
            "action",
            "mode",
            "path",
            "sha256",
        }:
            raise Denied
        expected_mode = (
            "100644"
            if item["path"] == proof_path
            else f"10{policies.get(item['path'], {}).get('final_mode', '')}"
        )
        if (
            item["action"] not in {"add", "modify"}
            or item["mode"] != expected_mode
            or type(item["sha256"]) is not str
            or HEX64.fullmatch(item["sha256"]) is None
        ):
            raise Denied
        if retained is None:
            change_raw, change_identity = runner._read_repo_file(
                repo_root, item["path"], maximum=16_777_216
            )
            runner._require_public_identity(change_identity, int(expected_mode[-3:], 8))
        else:
            try:
                change_raw = retained[item["path"]]
            except KeyError:
                raise Denied from None
        if item["sha256"] != hashlib.sha256(change_raw).hexdigest():
            raise Denied
    if value["reviewed_change_set_sha256"] != hashlib.sha256(
        runner._canonical(changes, newline=False)
    ).hexdigest():
        raise Denied
    try:
        runner._scan_v3(value)
    except (runner.v1.verifier.Denied, runner.Denied):
        raise Denied from None
    return {
        "authorization_id": proof_result["authorization_id"],
        "review_id": hashlib.sha256(raw).hexdigest(),
        "review_path": review_path,
        "reviewed_at_utc": value["reviewed_at_utc"],
        "status": "PASS",
    }


def validate_completion_review(path: Path, task: str = "T-003") -> dict[str, Any]:
    value, raw = _load_json(path)
    return validate_completion_review_value(value, raw, Path.cwd().absolute(), task)


def _expected_completion_refs(
    repo_root: Path,
    task: str,
    descriptor: dict[str, Any],
    authorization_id: str,
    *,
    review_value: Any | None = None,
    review_raw: bytes | None = None,
    retained: dict[str, bytes] | None = None,
    progress_value: Any | None = None,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    prefix = task.lower().replace("-", "")
    review_path = _review_path(task)
    if review_value is None or review_raw is None:
        review_value, review_raw = _load_json(repo_root / review_path)
    review_result = validate_completion_review_value(
        review_value,
        review_raw,
        repo_root,
        task,
        retained=retained,
        progress_value=progress_value,
    )
    if review_result["authorization_id"] != authorization_id:
        raise Denied
    paths = descriptor["completion_repo_relative_paths"] + [
        descriptor["proof_repo_relative_path"],
        review_path,
    ]
    refs: list[dict[str, str]] = []
    for path in sorted(paths):
        if retained is not None and path in retained:
            raw = retained[path]
        elif path == review_path and review_raw is not None:
            raw = review_raw
        else:
            raw, _identity = runner._read_repo_file(
                repo_root, path, maximum=16_777_216
            )
        refs.append(
            {
                "kind": "repo_file",
                "path": path,
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    refs.extend(
        [
            {
                "kind": "opaque",
                "id": f"{prefix}-authorization:{authorization_id}",
            },
            {
                "kind": "opaque",
                "id": f"{prefix}-review:{review_result['review_id']}",
            },
        ]
    )
    refs.sort(key=runner._canonical)
    return refs, review_result


def _validate_activation_prefix(
    value: dict[str, Any],
    repo_root: Path,
    retained: dict[str, bytes] | None,
) -> None:
    contract = (
        runner._load_contract(repo_root)[0]
        if retained is None
        else runner._validate_contract(
            *_retained_json(retained, runner.CONTRACT_PATH)
        )
    )
    events = value.get("events")
    if type(events) is not list or len(events) < 4:
        raise Denied
    prefix = _prefix_value(value, 4)
    prefix_raw = runner._canonical(prefix)
    t001 = [event for event in prefix["events"] if event["task_id"] == "T-001"]
    t002 = [event for event in prefix["events"] if event["task_id"] == "T-002"]
    activation = contract["activation"]
    if (
        hashlib.sha256(prefix_raw).hexdigest()
        != activation["progress"]["sha256"]
        or hashlib.sha256(runner._canonical(t001, newline=False)).hexdigest()
        != activation["t001_events"]["sha256"]
        or hashlib.sha256(runner._canonical(t001[-1], newline=False)).hexdigest()
        != activation["t001_completion_event"]["sha256"]
        or hashlib.sha256(runner._canonical(t002, newline=False)).hexdigest()
        != activation["t002_events"]["sha256"]
        or hashlib.sha256(runner._canonical(t002[-1], newline=False)).hexdigest()
        != activation["t002_completion_event"]["sha256"]
    ):
        raise Denied


def validate_ledger_value(
    value: Any,
    repo_root: Path,
    *,
    retained: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    _require_supported_task(repo_root, "T-003", retained=retained)
    if type(value) is not dict or type(value.get("events")) is not list:
        raise Denied
    _validate_activation_prefix(value, repo_root, retained)
    proofs = 0
    seen_tasks: set[str] = set()
    proof_context: dict[str, tuple[dict[str, Any], dict[str, Any], bytes]] = {}
    for index, event in enumerate(value["events"]):
        if index < 4:
            continue
        if type(event) is not dict:
            raise Denied
        task = _require_supported_task(
            repo_root, event.get("task_id"), retained=retained
        )
        if event.get("from") == "PENDING" and event.get("to") == "BLOCKED":
            raise Denied
        if event.get("to") == "COMPLETED":
            if task not in proof_context:
                raise Denied
            descriptor, proof_result, _proof_raw = proof_context[task]
            refs = event.get("evidence_refs")
            if type(refs) is not list:
                raise Denied
            expected_refs, _review_result = _expected_completion_refs(
                repo_root,
                task,
                descriptor,
                proof_result["authorization_id"],
                retained=retained,
                progress_value=value,
            )
            if refs != expected_refs:
                raise Denied
            continue
        if event.get("to") != "IN_PROGRESS":
            continue
        if event.get("from") == "PENDING":
            if task in seen_tasks:
                raise Denied
            seen_tasks.add(task)
            if retained is None:
                descriptor, _raw = runner._load_scope_descriptor(repo_root, task)
            else:
                try:
                    descriptor_raw = retained[runner._scope_path(task)]
                    descriptor_value = runner.v1.verifier._parse(descriptor_raw)
                    descriptor = runner._validate_scope_descriptor(
                        descriptor_value, descriptor_raw, task
                    )
                except (KeyError, runner.v1.verifier.Denied, runner.Denied):
                    raise Denied from None
            proof_path = descriptor["proof_repo_relative_path"]
            if retained is None:
                proof_value, proof_raw = _load_json(repo_root / proof_path)
            else:
                try:
                    proof_raw = retained[proof_path]
                    proof_value = runner.v1.verifier._parse(proof_raw)
                    runner._scan_v3(proof_value)
                except (KeyError, runner.v1.verifier.Denied, runner.Denied):
                    raise Denied from None
                if proof_raw != runner._canonical(proof_value):
                    raise Denied
            result = validate_proof_value(
                proof_value, repo_root, retained=retained
            )
            if result["authorized_task"] != task:
                raise Denied
            prefix = _prefix_value(value, index)
            if (
                proof_value["progress_sequence"] != index
                or proof_value["progress_sha256"]
                != hashlib.sha256(runner._canonical(prefix)).hexdigest()
            ):
                raise Denied
            proof_context[task] = (descriptor, result, proof_raw)
            proofs += 1
        elif event.get("from") == "BLOCKED":
            if task not in seen_tasks or task not in proof_context:
                raise Denied
            descriptor, result, proof_raw = proof_context[task]
            proof_path = descriptor["proof_repo_relative_path"]
        else:
            raise Denied
        expected_refs = _expected_start_refs(
            repo_root,
            task,
            result["authorization_id"],
            proof_path,
            proof_raw=proof_raw,
        )
        if event.get("evidence_refs") != expected_refs:
            raise Denied
    state = value.get("tasks", {})
    if state.get("T-003") == "PENDING":
        if proofs != 0:
            raise Denied
    elif state.get("T-003") in {"IN_PROGRESS", "BLOCKED", "COMPLETED"}:
        if proofs != 1:
            raise Denied
    else:
        raise Denied
    if any(state.get(f"T-{number:03d}") != "PENDING" for number in range(4, 34)):
        raise Denied
    return {"proofs": proofs, "sequence": len(value["events"]), "status": "PASS"}


def _retained_baseline(retained: dict[str, bytes]) -> dict[str, str]:
    baseline = progress_v1.baseline
    try:
        raw = retained[baseline.MANIFEST_PATH]
        if len(raw) > baseline.MANIFEST_MAX_BYTES:
            raise Denied
        data = runner.v1.verifier._parse(raw)
    except (KeyError, runner.v1.verifier.Denied):
        raise Denied from None
    try:
        baseline._exact_dict(data, baseline.TOP_KEYS, "manifest_shape_invalid")
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise Denied
        baseline._exact_string(
            data["artifact_kind"],
            "subject-distillation-baseline",
            "artifact_kind_invalid",
        )
        baseline._exact_string(data["baseline_state"], "frozen", "baseline_state_invalid")
        algorithm = baseline._exact_dict(
            data["algorithm"], baseline.ALGORITHM_KEYS, "algorithm_shape_invalid"
        )
        if algorithm != {
            "name": "subject-distillation-baseline-v1",
            "domain_separator_utf8_hex": baseline.DOMAIN_SEPARATOR_UTF8_HEX,
            "digest": "sha256",
            "baseline_id_hex_length": 16,
        }:
            raise Denied
        if type(algorithm["baseline_id_hex_length"]) is not int:
            raise Denied
        scope = baseline._exact_dict(
            data["scope"], baseline.SCOPE_KEYS, "scope_shape_invalid"
        )
        if scope != {
            "generic_subject_core": True,
            "person_v1": True,
            "organization": "contract-only",
        }:
            raise Denied
        if (
            type(scope["generic_subject_core"]) is not bool
            or type(scope["person_v1"]) is not bool
        ):
            raise Denied
        files = data["files"]
        if type(files) is not list or len(files) != len(baseline.CANONICAL_PATHS):
            raise Denied
        payload = bytearray(baseline.EXPECTED_DOMAIN)
        total = 0
        for entry, path in zip(files, baseline.CANONICAL_PATHS, strict=True):
            baseline._exact_dict(entry, baseline.FILE_KEYS, "file_entry_shape_invalid")
            if entry["path"] != path or type(entry["size_bytes"]) is not int:
                raise Denied
            canonical_raw = retained[path]
            size = len(canonical_raw)
            digest = hashlib.sha256(canonical_raw).hexdigest()
            total += size
            if (
                size != entry["size_bytes"]
                or digest != entry["sha256"]
                or size > baseline.CANONICAL_MAX_BYTES
                or total > baseline.CANONICAL_TOTAL_MAX_BYTES
            ):
                raise Denied
            payload.extend(
                path.encode("utf-8")
                + b"\0"
                + digest.encode("ascii")
                + b"\0"
                + str(size).encode("ascii")
                + b"\n"
            )
        closure = baseline._exact_dict(
            data["closure"], baseline.CLOSURE_KEYS, "closure_shape_invalid"
        )
        full_digest = hashlib.sha256(payload).hexdigest()
        if closure != {
            "full_digest": full_digest,
            "baseline_id": full_digest[:16],
        }:
            raise Denied
        return {
            "status": "PASS",
            "baseline_id": full_digest[:16],
            "full_digest": full_digest,
        }
    except (KeyError, TypeError, progress_v1.baseline.ValidationError):
        raise Denied from None


def _validate_retained_progress(
    value: dict[str, Any], repo_root: Path, retained: dict[str, bytes]
) -> dict[str, Any]:
    try:
        schema_raw = retained[runner.PROGRESS_SCHEMA_PATH]
        schema_value = runner.v1.verifier._parse(schema_raw)
        tasks_raw = retained[runner.TASKS_PATH]
    except (KeyError, runner.v1.verifier.Denied):
        raise Denied from None
    expected_schema = progress_v1._expected_schema()
    if (
        schema_value != expected_schema
        or schema_raw != progress_v1.evidence._canonical(expected_schema)
    ):
        raise Denied
    manifest_result = _retained_baseline(retained)
    tasks_sha256 = hashlib.sha256(tasks_raw).hexdigest()
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
    progress_v1.evidence._scan_public(value)
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["baseline_id"] != manifest_result["baseline_id"]
        or value["baseline_full_digest"] != manifest_result["full_digest"]
        or value["tasks_sha256"] != tasks_sha256
        or type(value["tasks"]) is not dict
        or tuple(sorted(value["tasks"])) != progress_v1.TASK_IDS
        or any(
            type(state) is not str or state not in progress_v1.STATES
            for state in value["tasks"].values()
        )
    ):
        raise Denied
    environment_path = (
        "specs/subject-distillation/evidence/"
        f"{manifest_result['baseline_id']}/environment.json"
    )
    try:
        environment_raw = retained[environment_path]
        environment = runner.v1.verifier._parse(environment_raw)
        progress_v1.evidence._scan_public(environment)
        proof = environment["implementation_authorization"]
        recorded_at = progress_v1.evidence._timestamp(proof["recorded_at_utc"])
        authorization_id = proof["authorization_id"]
    except (
        KeyError,
        TypeError,
        runner.v1.verifier.Denied,
        progress_v1.evidence.Denied,
    ):
        raise Denied from None
    if (
        environment_raw != progress_v1.evidence._canonical(environment)
        or type(authorization_id) is not str
        or progress_v1.HEX64.fullmatch(authorization_id) is None
        or environment.get("baseline_id") != manifest_result["baseline_id"]
    ):
        raise Denied
    events = value["events"]
    if type(events) is not list or not events or len(events) > 4_096:
        raise Denied
    states = {task: "PENDING" for task in progress_v1.TASK_IDS}
    previous_time = None
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
        task_id = event["task_id"]
        before = event["from"]
        after = event["to"]
        if (
            type(event["sequence"]) is not int
            or event["sequence"] != sequence
            or task_id not in progress_v1.TASK_IDS
            or states[task_id] != before
            or (before, after) not in progress_v1.TRANSITIONS
            or before == "COMPLETED"
        ):
            raise Denied
        when = progress_v1.evidence._timestamp(event["at_utc"])
        if (
            (sequence == 1 and when < recorded_at)
            or (previous_time is not None and when < previous_time)
        ):
            raise Denied
        previous_time = when
        refs = event["evidence_refs"]
        if type(refs) is not list or len(refs) > 16:
            raise Denied
        canonical_refs = [progress_v1.evidence._canonical(item) for item in refs]
        if (
            canonical_refs != sorted(canonical_refs)
            or len(canonical_refs) != len(set(canonical_refs))
        ):
            raise Denied
        for item in refs:
            if type(item) is not dict:
                raise Denied
            if set(item) == {"kind", "path", "sha256"} and item["kind"] == "repo_file":
                path = item["path"]
                digest = item["sha256"]
                try:
                    ref_raw = retained[path]
                except (KeyError, TypeError):
                    raise Denied from None
                if (
                    type(path) is not str
                    or len(path) > 256
                    or path.startswith("/")
                    or "\\" in path
                    or any(part in {"", ".", ".."} for part in path.split("/"))
                    or type(digest) is not str
                    or progress_v1.HEX64.fullmatch(digest) is None
                    or hashlib.sha256(ref_raw).hexdigest() != digest
                ):
                    raise Denied
            elif set(item) == {"kind", "id"} and item["kind"] == "opaque":
                if (
                    type(item["id"]) is not str
                    or progress_v1.OPAQUE.fullmatch(item["id"]) is None
                ):
                    raise Denied
            else:
                raise Denied
        if task_id == "T-001" and after == "COMPLETED":
            progress_v1._validate_t001_completion_refs(
                refs,
                baseline_id=manifest_result["baseline_id"],
                authorization_id=authorization_id,
            )
        if after == "BLOCKED":
            if (
                type(event["blocker"]) is not str
                or progress_v1.BLOCKER.fullmatch(event["blocker"]) is None
            ):
                raise Denied
        elif event["blocker"] is not None:
            raise Denied
        if after == "COMPLETED" and not refs:
            raise Denied
        if after in {"IN_PROGRESS", "COMPLETED"} and not progress_v1._dependencies_allow(
            task_id, states
        ):
            raise Denied
        states[task_id] = after
        if sum(state == "IN_PROGRESS" for state in states.values()) > 1:
            raise Denied
    if value["tasks"] != states or value["updated_at_utc"] != events[-1]["at_utc"]:
        raise Denied
    if states["T-033"] == "COMPLETED":
        raise Denied
    return {
        "baseline_id": value["baseline_id"],
        "sequence": len(events),
        "status": "PASS",
    }


def validate_ledger(repo_root: Path) -> dict[str, Any]:
    base_guard = runner._open_bridge_guard(
        repo_root, "T-003", include_progress=True, include_proof=False
    )
    state_guard: runner.BridgeGuard | None = None
    try:
        retained = base_guard.snapshot()
        progress_raw = retained[runner.PROGRESS_PATH]
        value = runner.v1.verifier._parse(progress_raw)
        runner._scan_v3(value)
        if progress_raw != runner._canonical(value):
            raise Denied
        names_before = runner._directory_names(
            repo_root, "specs/subject-distillation/task-authorizations"
        )
        started = any(
            event.get("task_id") == "T-003" and event.get("to") == "IN_PROGRESS"
            for event in value["events"]
            if type(event) is dict
        )
        review_name = "T-003.review.json"
        review_present = review_name in names_before
        if started:
            descriptor_raw = retained[runner._scope_path("T-003")]
            descriptor_value = runner.v1.verifier._parse(descriptor_raw)
            descriptor = runner._validate_scope_descriptor(
                descriptor_value, descriptor_raw, "T-003"
            )
            extras: list[str] = []
            if review_present or value["tasks"]["T-003"] == "COMPLETED":
                extras.extend(descriptor["completion_repo_relative_paths"])
            if review_present:
                extras.append(_review_path("T-003"))
            state_guard = runner._open_bridge_guard(
                repo_root,
                "T-003",
                include_proof=True,
                include_progress=False,
                extra_paths=extras,
            )
            retained = _merge_retained_snapshots(retained, state_guard.snapshot())
        base_guard.audit()
        if state_guard is not None:
            state_guard.audit()
        _validate_retained_progress(value, repo_root, retained)
        result = validate_ledger_value(value, repo_root, retained=retained)
        expected = ["README.md", "T-002.json", "T-002.review.json"]
        if started:
            expected.append("T-003.json")
        if review_present:
            expected.append(review_name)
        if value["tasks"]["T-003"] == "COMPLETED" and not review_present:
            raise Denied
        if names_before != sorted(expected):
            raise Denied
        if value["tasks"]["T-003"] == "COMPLETED":
            proof_raw = retained[
                "specs/subject-distillation/task-authorizations/T-003.json"
            ]
            proof_value = runner.v1.verifier._parse(proof_raw)
            review_raw = retained[_review_path("T-003")]
            review_value = runner.v1.verifier._parse(review_raw)
            final_paths = review_value["reviewed_change_paths"] + [
                runner.PROGRESS_PATH,
                _review_path("T-003"),
            ]
            changes = runner._repository_changes(
                repo_root,
                proof_value["implementation_base_commit"],
                final_paths,
                retained,
            )
            review_change = next(
                (item for item in changes if item["path"] == _review_path("T-003")),
                None,
            )
            source_changes = [
                item
                for item in changes
                if item["path"] not in {_review_path("T-003"), runner.PROGRESS_PATH}
            ]
            progress_change = next(
                (item for item in changes if item["path"] == runner.PROGRESS_PATH),
                None,
            )
            if (
                source_changes != review_value["reviewed_changes"]
                or progress_change
                != {
                    "action": "modify",
                    "mode": "100644",
                    "path": runner.PROGRESS_PATH,
                    "sha256": hashlib.sha256(progress_raw).hexdigest(),
                }
                or review_change
                != {
                    "action": "add",
                    "mode": "100644",
                    "path": _review_path("T-003"),
                    "sha256": hashlib.sha256(review_raw).hexdigest(),
                }
            ):
                raise Denied
        base_guard.audit()
        if state_guard is not None:
            state_guard.audit()
        if runner._directory_names(
            repo_root, "specs/subject-distillation/task-authorizations"
        ) != names_before:
            raise Denied
        return result
    except Exception:  # noqa: BLE001 - translate fail-closed boundary
        raise Denied from None
    finally:
        if state_guard is not None:
            state_guard.close()
        base_guard.close()


def main(argv: list[str] | None = None) -> int:
    if _BOOTSTRAP_ERROR:
        sys.stderr.write(ERROR_TEXT)
        return 3
    parser = _Parser(add_help=False, allow_abbrev=False)
    parser.add_argument("--proof")
    parser.add_argument("--require-current-prestart", action="store_true")
    parser.add_argument("--ledger", action="store_true")
    parser.add_argument("--json", action="store_true", required=True)
    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
        if args.ledger == (args.proof is not None):
            raise Denied
        result = (
            validate_ledger(Path.cwd().absolute())
            if args.ledger
            else validate_proof(
                Path(args.proof),
                require_current_prestart=args.require_current_prestart,
            )
        )
    except (Denied, SystemExit, runner.v1.Denied):
        sys.stderr.write(DENY_TEXT)
        return 2
    except Exception:  # noqa: BLE001 - fixed no-echo public boundary
        sys.stderr.write(ERROR_TEXT)
        return 3
    sys.stdout.write(runner._canonical(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
