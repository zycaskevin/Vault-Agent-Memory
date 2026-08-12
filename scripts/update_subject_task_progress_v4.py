#!/usr/bin/env python3
"""Mission-bound atomic start, block and completion for Subject T-004..T-033."""

from __future__ import annotations

import argparse
import copy
import hashlib
import os
import stat
import sys
from pathlib import Path
from typing import Any

try:
    from scripts import run_subject_development_mission_v4 as mission
    from scripts import update_subject_progress as writer
    from scripts import validate_subject_development_mission_v4 as validator
except ImportError:  # pragma: no cover - direct script execution
    try:
        import run_subject_development_mission_v4 as mission
        import update_subject_progress as writer
        import validate_subject_development_mission_v4 as validator
    except Exception:
        if __name__ == "__main__":
            sys.stderr.write("SUBJECT_TASK_PROGRESS_V4_ERROR\n")
            raise SystemExit(3) from None
        raise
except Exception:
    if __name__ == "__main__":
        sys.stderr.write("SUBJECT_TASK_PROGRESS_V4_ERROR\n")
        raise SystemExit(3) from None
    raise


Denied = mission.Denied
DENY_TEXT = "SUBJECT_TASK_PROGRESS_V4_DENY\n"
ERROR_TEXT = "SUBJECT_TASK_PROGRESS_V4_ERROR\n"
PROGRESS_PENDING_PATH = (
    "specs/subject-distillation/" + writer.PENDING_NAME
)


class _Parser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise Denied


def _mission(repo_root: Path, now: str) -> tuple[dict[str, Any], bytes]:
    proof, raw = validator._load_mission_proof(repo_root)
    validator.validate_mission_proof_value(proof, raw, repo_root, now_utc=now)
    if validator._entry_exists(repo_root, mission.REVOCATION_PATH):
        raise Denied
    return proof, raw


def _fresh_active_mission(
    repo_root: Path,
    runtime: writer.Runtime,
    *,
    expected_raw: bytes | None = None,
    previous_utc: str | None = None,
) -> tuple[dict[str, Any], bytes, str]:
    """Recheck authority using a fresh monotonic wall-clock sample."""
    now = writer._time(runtime)
    if previous_utc is not None and mission._timestamp(now) < mission._timestamp(previous_utc):
        raise Denied
    proof, raw = _mission(repo_root, now)
    if expected_raw is not None and raw != expected_raw:
        raise Denied
    return proof, raw, now


def _status(repo_root: Path) -> dict[str, str]:
    return mission.legacy._parse_status_z(
        mission.legacy.v1._git(["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    )


def _require_status(
    repo_root: Path,
    expected: dict[str, str],
    *,
    progress_pending: bool | None,
) -> bool:
    """Validate Git dirt while treating only the writer-owned pending path specially."""
    status = _status(repo_root)
    pending_present = status.pop(PROGRESS_PENDING_PATH, None)
    if pending_present is not None and pending_present != "add":
        raise Denied
    if status != expected:
        raise Denied
    present = pending_present is not None
    if progress_pending is not None and present is not progress_pending:
        raise Denied
    return present


def _task_proof_path(task: str) -> str:
    if mission.TASK.fullmatch(task) is None:
        raise Denied
    return f"specs/subject-distillation/task-authorizations/{task}.json"


def _review_path(task: str) -> str:
    if mission.TASK.fullmatch(task) is None:
        raise Denied
    return f"specs/subject-distillation/task-authorizations/{task}.review.json"


def _validated_task_proof(
    repo_root: Path,
    task: str,
) -> tuple[dict[str, Any], bytes]:
    raw = mission._read(repo_root, _task_proof_path(task))
    value = mission._parse(raw)
    validator.validate_task_authorization_value(
        value,
        raw,
        repo_root,
        historical=True,
    )
    if value["authorized_task"] != task:
        raise Denied
    return value, raw


def _recoverable_publication_raw(
    repo_root: Path,
    final_path: str,
    validate_raw: Any,
    *,
    allowed_extra_paths: set[str] | None = None,
) -> bytes | None:
    """Return exact bytes only for the publisher's pending/final recovery states."""
    pending_path = mission.PENDING_PATH
    present = {
        path for path in (pending_path, final_path) if validator._entry_exists(repo_root, path)
    }
    if not present:
        return None
    status = _status(repo_root)
    extras = set() if allowed_extra_paths is None else allowed_extra_paths
    if set(status) != present | extras or any(status[path] != "add" for path in present):
        raise Denied
    if any(status[path] != "add" for path in extras):
        raise Denied
    raws: dict[str, bytes] = {}
    identities: dict[str, tuple[int, int, int, int, int, int, int]] = {}
    for path in present:
        raw, identity = mission.legacy._read_repo_file(repo_root, path)
        mode = stat.S_IMODE(identity[2])
        if path == pending_path:
            if mode not in {0o600, 0o644} or identity[3] not in {1, 2}:
                raise Denied
        elif mode != 0o644 or identity[3] not in {1, 2}:
            raise Denied
        raws[path] = raw
        identities[path] = identity
    if len(set(raws.values())) != 1:
        raise Denied
    if present == {pending_path, final_path}:
        pending_identity = identities[pending_path]
        final_identity = identities[final_path]
        if (
            pending_identity[:2] != final_identity[:2]
            or pending_identity[3] != 2
            or final_identity[3] != 2
        ):
            raise Denied
    elif present == {pending_path}:
        if identities[pending_path][3] != 1:
            raise Denied
    elif present == {final_path}:
        if identities[final_path][3] != 1:
            raise Denied
    else:
        raise Denied
    raw = next(iter(raws.values()))
    validate_raw(raw)
    return raw


def _current(repo_root: Path) -> dict[str, Any]:
    value, raw = mission._load_progress(repo_root)
    validator.validate_ledger_value(value, repo_root) if len(value["events"]) > 6 else None
    if raw != mission.canonical(value):
        raise Denied
    return value


def _pending_transition_candidate(
    paths: writer.Paths,
    current: dict[str, Any],
    *,
    task: str,
    target: str,
    refs: list[dict[str, str]],
    blocker: str | None = None,
) -> dict[str, Any] | None:
    """Recover only the writer's exact one-event pending candidate."""
    pending = writer._pending_value(paths)
    if pending is None:
        return None
    if len(pending["events"]) != len(current["events"]) + 1:
        raise Denied
    prior = copy.deepcopy(pending)
    pending_event = prior["events"].pop()
    prior["tasks"][task] = current["tasks"][task]
    prior["updated_at_utc"] = current["updated_at_utc"]
    if (
        prior != current
        or not writer._event_matches(
            pending_event,
            task=task,
            expected=current["tasks"][task],
            target=target,
            refs=refs,
            blocker=blocker,
        )
    ):
        raise Denied
    return pending


def _exact_repo_file(
    repo_root: Path,
    path: str,
    expected_raw: bytes,
    *,
    discard: bool,
) -> None:
    """Audit, and optionally unlink, one exact uncommitted public artifact."""
    if mission.legacy._path(path) != path or type(expected_raw) is not bytes:
        raise Denied
    owned: list[int] = []
    try:
        root_fd = os.open("/", mission.legacy.v1.verifier._flags(directory=True))
        owned.append(root_fd)
        discovered, repo = mission.legacy.v1.verifier._repo_root(root_fd, owned)
        if discovered != os.fspath(repo_root):
            raise Denied
        parts = tuple(path.split("/"))
        parent = mission.legacy.v1.verifier._open_chain(
            repo.fd,
            parts[:-1],
            owned,
            final_directory=True,
        )
        fd = os.open(
            parts[-1],
            mission.legacy.v1.verifier._flags(directory=False),
            dir_fd=parent.fd,
        )
        owned.append(fd)
        before = os.fstat(fd)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o644
            or before.st_nlink != 1
            or mission.legacy._read_fd(fd) != expected_raw
        ):
            raise Denied
        current = os.stat(parts[-1], dir_fd=parent.fd, follow_symlinks=False)
        if mission.legacy.v1.verifier._identity(current) != mission.legacy.v1.verifier._identity(
            before
        ):
            raise Denied
        if discard:
            os.unlink(parts[-1], dir_fd=parent.fd)
            os.fsync(parent.fd)
    except (OSError, mission.legacy.v1.verifier.Denied):
        raise Denied from None
    finally:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass


def _audit_exact_repo_file(
    repo_root: Path,
    path: str,
    expected_raw: bytes,
) -> None:
    _exact_repo_file(repo_root, path, expected_raw, discard=False)


def _discard_exact_repo_file(
    repo_root: Path,
    path: str,
    expected_raw: bytes,
) -> None:
    _exact_repo_file(repo_root, path, expected_raw, discard=True)


def _allowed_status_guard(
    repo_root: Path,
    allowed_status: dict[str, str],
    expected_revocation_raw: bytes | None,
) -> mission.legacy.BridgeGuard | None:
    if not allowed_status:
        if expected_revocation_raw is not None:
            raise Denied
        return None
    if (
        allowed_status != {mission.REVOCATION_PATH: "add"}
        or type(expected_revocation_raw) is not bytes
    ):
        raise Denied
    guard = mission.open_paths_guard(repo_root, [mission.REVOCATION_PATH])
    try:
        if guard.snapshot()[mission.REVOCATION_PATH] != expected_revocation_raw:
            raise Denied
        return guard
    except Exception:
        guard.close()
        raise


def _discard_invalidated_active_pending(
    paths: writer.Paths,
    current: dict[str, Any],
    *,
    task: str,
    runtime: writer.Runtime,
    allowed_status: dict[str, str] | None = None,
    expected_revocation_raw: bytes | None = None,
) -> bool:
    """Abort an exact uncommitted start/completion after authority closes."""
    pending = writer._pending_value(paths)
    if pending is None:
        return False
    if len(pending["events"]) != len(current["events"]) + 1:
        raise Denied
    event = pending["events"][-1]
    if event["task_id"] != task or event["from"] != current["tasks"][task]:
        raise Denied
    proof_path = _task_proof_path(task)
    proof_raw = mission._read(paths.repo_root, proof_path)
    proof = mission._parse(proof_raw)
    validator.validate_task_authorization_value(
        proof,
        proof_raw,
        paths.repo_root,
        historical=False,
    )
    if event["to"] == "IN_PROGRESS" and current["tasks"][task] == "PENDING":
        refs = validator._start_refs(task, proof, proof_raw)
        artifact_path = proof_path
        artifact_raw = proof_raw
    elif event["to"] == "COMPLETED" and current["tasks"][task] == "IN_PROGRESS":
        review_path = _review_path(task)
        review_raw = mission._read(paths.repo_root, review_path)
        review = mission._parse(review_raw)
        validator.validate_completion_review_value(
            review,
            review_raw,
            paths.repo_root,
            task,
            proof=proof,
            proof_raw=proof_raw,
        )
        refs = validator._completion_refs(task, proof, proof_raw, review, review_raw)
        artifact_path = review_path
        artifact_raw = review_raw
    else:
        raise Denied
    if not writer._event_matches(
        event,
        task=task,
        expected=current["tasks"][task],
        target=event["to"],
        refs=refs,
        blocker=None,
    ):
        raise Denied
    prior = copy.deepcopy(pending)
    prior["events"].pop()
    prior["tasks"][task] = current["tasks"][task]
    prior["updated_at_utc"] = current["updated_at_utc"]
    if prior != current:
        raise Denied
    allowed = {} if allowed_status is None else dict(allowed_status)
    if artifact_path in allowed or PROGRESS_PENDING_PATH in allowed:
        raise Denied
    expected_status = {**allowed, artifact_path: "add"}
    allowed_guard: mission.legacy.BridgeGuard | None = None
    try:
        _require_status(
            paths.repo_root,
            expected_status,
            progress_pending=True,
        )
        allowed_guard = _allowed_status_guard(
            paths.repo_root,
            allowed,
            expected_revocation_raw,
        )
        if allowed_guard is not None:
            allowed_guard.audit()
        _audit_exact_repo_file(paths.repo_root, artifact_path, artifact_raw)
        _require_status(
            paths.repo_root,
            expected_status,
            progress_pending=True,
        )
        if allowed_guard is not None:
            allowed_guard.audit()
        writer._discard_matching_pending(paths, mission.canonical(pending), runtime)
        _require_status(
            paths.repo_root,
            expected_status,
            progress_pending=False,
        )
        if allowed_guard is not None:
            allowed_guard.audit()
        _discard_exact_repo_file(paths.repo_root, artifact_path, artifact_raw)
        _require_status(
            paths.repo_root,
            allowed,
            progress_pending=False,
        )
        if allowed_guard is not None:
            allowed_guard.audit()
        return True
    finally:
        if allowed_guard is not None:
            allowed_guard.close()


def _discard_orphaned_active_artifact(
    repo_root: Path,
    current: dict[str, Any],
    *,
    task: str,
    allowed_status: dict[str, str],
    expected_revocation_raw: bytes | None = None,
) -> bool:
    """Finish cleanup if a crash occurred after pending unlink."""
    proof_path = _task_proof_path(task)
    allowed_guard: mission.legacy.BridgeGuard | None = None
    if current["tasks"][task] == "PENDING":
        artifact_path = proof_path
        if _status(repo_root) != {**allowed_status, artifact_path: "add"}:
            return False
        proof_raw = mission._read(repo_root, proof_path)
        proof = mission._parse(proof_raw)
        validator.validate_task_authorization_value(
            proof,
            proof_raw,
            repo_root,
            historical=False,
        )
        if (
            proof["progress_sequence"] != len(current["events"])
            or proof["progress_sha256"]
            != hashlib.sha256(mission.canonical(current)).hexdigest()
        ):
            raise Denied
        artifact_raw = proof_raw
    elif current["tasks"][task] == "IN_PROGRESS":
        artifact_path = _review_path(task)
        if _status(repo_root) != {**allowed_status, artifact_path: "add"}:
            return False
        proof_raw = mission._read(repo_root, proof_path)
        proof = mission._parse(proof_raw)
        review_raw = mission._read(repo_root, artifact_path)
        review = mission._parse(review_raw)
        validator.validate_completion_review_value(
            review,
            review_raw,
            repo_root,
            task,
            proof=proof,
            proof_raw=proof_raw,
        )
        validator._validate_review_progress_prefix(
            review["source_review"],
            current,
            len(current["events"]),
        )
        artifact_raw = review_raw
    else:
        return False
    expected_status = {**allowed_status, artifact_path: "add"}
    try:
        _require_status(repo_root, expected_status, progress_pending=False)
        allowed_guard = _allowed_status_guard(
            repo_root,
            allowed_status,
            expected_revocation_raw,
        )
        if allowed_guard is not None:
            allowed_guard.audit()
        _audit_exact_repo_file(repo_root, artifact_path, artifact_raw)
        _require_status(repo_root, expected_status, progress_pending=False)
        if allowed_guard is not None:
            allowed_guard.audit()
        _discard_exact_repo_file(repo_root, artifact_path, artifact_raw)
        _require_status(repo_root, allowed_status, progress_pending=False)
        if allowed_guard is not None:
            allowed_guard.audit()
        return True
    finally:
        if allowed_guard is not None:
            allowed_guard.close()


def _terminal_block_prefix(
    current: dict[str, Any],
    *,
    task: str,
    expected_from: str,
    blocker: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reconstruct the exact ledger prefix before one terminal block event."""
    if current["tasks"].get(task) != "BLOCKED" or not current["events"]:
        raise Denied
    event = current["events"][-1]
    if not writer._event_matches(
        event,
        task=task,
        expected=expected_from,
        target="BLOCKED",
        refs=[],
        blocker=blocker,
    ):
        raise Denied
    prior = copy.deepcopy(current)
    prior["events"].pop()
    if not prior["events"]:
        raise Denied
    prior["tasks"][task] = expected_from
    prior["updated_at_utc"] = prior["events"][-1]["at_utc"]
    return prior, event


def _recover_t032_block(repo_root: Path, current: dict[str, Any]) -> dict[str, Any]:
    prior, _event = _terminal_block_prefix(
        current,
        task="T-032",
        expected_from="PENDING",
        blocker="OPERATIONAL_ACTION_REQUIRED",
    )
    prior_result = validator.validate_ledger_value(
        prior,
        repo_root,
        include_delivery_anchor=True,
    )
    anchor = prior_result.get("delivery_anchor")
    if type(anchor) is not str or mission.COMMIT.fullmatch(anchor) is None:
        raise Denied
    delivery = mission.validate_progress_only_delivery(
        repo_root,
        parent_commit=anchor,
        progress_raw=mission.canonical(current),
    )
    head = mission._git(repo_root, "rev-parse", "HEAD").strip().decode()
    origin = mission._git(repo_root, "rev-parse", "origin/main").strip().decode()
    if delivery == "WORKTREE":
        if head != anchor or origin != anchor:
            raise Denied
        _require_status(
            repo_root,
            {mission.PROGRESS_PATH: "modify"},
            progress_pending=False,
        )
    elif delivery == head == origin:
        _require_status(repo_root, {}, progress_pending=False)
    else:
        raise Denied
    result = validator.validate_ledger_value(
        current,
        repo_root,
        include_delivery_anchor=True,
    )
    if result.get("delivery_anchor") != delivery:
        raise Denied
    return {
        "sequence": len(current["events"]),
        "status": "RECOVERED_COMMITTED",
        "task_id": "T-032",
    }


def _recover_authority_block(
    repo_root: Path,
    current: dict[str, Any],
    *,
    task: str,
    blocker: str,
    lower_utc: str,
    now_utc: str,
    allowed_status: dict[str, str],
    revocation: dict[str, Any] | None,
    revocation_raw: bytes | None,
) -> dict[str, Any]:
    prior, event = _terminal_block_prefix(
        current,
        task=task,
        expected_from="IN_PROGRESS",
        blocker=blocker,
    )
    if not (
        mission._timestamp(lower_utc)
        <= mission._timestamp(event["at_utc"])
        <= mission._timestamp(now_utc)
    ):
        raise Denied
    if revocation is not None:
        if blocker != "MISSION_REVOKED":
            raise Denied
        if validator.validate_revocation_progress(revocation, current) != prior:
            raise Denied
    elif blocker != "MISSION_EXPIRED":
        raise Denied
    validator.validate_ledger_value(prior, repo_root)
    validator.validate_ledger_value(current, repo_root)
    if (revocation is None) is not (revocation_raw is None):
        raise Denied
    task_proof, task_proof_raw = _validated_task_proof(repo_root, task)
    delivery = mission.validate_authority_block_delivery(
        repo_root,
        proof=task_proof,
        proof_raw=task_proof_raw,
        progress_before_raw=mission.canonical(prior),
        progress_after_raw=mission.canonical(current),
        revocation_raw=revocation_raw,
    )
    status = _status(repo_root)
    if delivery == "WORKTREE":
        expected = {**allowed_status, mission.PROGRESS_PATH: "modify"}
        if status != expected:
            raise Denied
    elif status:
        raise Denied
    return {
        "sequence": len(current["events"]),
        "status": "RECOVERED_COMMITTED",
        "task_id": task,
    }


def start(
    task: str,
    base: str,
    *,
    runtime: writer.Runtime | None = None,
    lock_runtime: Any | None = None,
) -> dict[str, Any]:
    if task == "T-032" or mission.TASK.fullmatch(task) is None:
        raise Denied
    repo_root = Path.cwd().absolute()
    selected = runtime if runtime is not None else writer.Runtime()
    paths = writer._paths(repo_root)
    manifest, _tasks_sha = writer._inputs(paths)
    lock = lock_runtime if lock_runtime is not None else mission.legacy.v1.Runtime()
    proof_path = _task_proof_path(task)
    source_guard: mission.legacy.BridgeGuard | None = None
    proof_guard: mission.legacy.BridgeGuard | None = None
    progress_guard: mission.legacy.BridgeGuard | None = None
    with mission.legacy.v1._authorization_lock(
        os.fspath(repo_root), "subject-progress-v4", manifest["baseline_id"], lock
    ):
        try:
            mission_proof, mission_raw, authority_time = _fresh_active_mission(
                repo_root, selected
            )
            contract, _contract_raw = mission.load_contract(repo_root)
            registry, _registry_raw = mission.load_registry(repo_root, contract)
            descriptor = registry["tasks"][int(task[2:]) - 4]
            source_guard = mission.open_paths_guard(
                repo_root,
                sorted(
                    {
                        mission.MISSION_PROOF_PATH,
                        *descriptor["required_read_paths"],
                        *mission.RETAINED_AUTHORITY_PATHS,
                        *contract["trust_root_paths"],
                    }
                ),
            )
            progress_guard = mission.open_paths_guard(repo_root, [mission.PROGRESS_PATH])
            retained_source = source_guard.snapshot()
            if retained_source[mission.MISSION_PROOF_PATH] != mission_raw:
                raise Denied
            reviewed_head = mission._git(repo_root, "rev-parse", "HEAD").strip()
            current = _current(repo_root)
            if progress_guard.snapshot()[mission.PROGRESS_PATH] != mission.canonical(current):
                raise Denied
            if current["tasks"][task] == "IN_PROGRESS":
                proof_guard = mission.open_paths_guard(repo_root, [proof_path])
                proof_raw = proof_guard.snapshot()[proof_path]
                proof = mission._parse(proof_raw)
                validator.validate_task_authorization_value(
                    proof,
                    proof_raw,
                    repo_root,
                    mission_proof=mission_proof,
                    mission_raw=mission_raw,
                    retained=retained_source,
                )
                if current["events"][-1]["evidence_refs"] != validator._start_refs(
                    task, proof, proof_raw
                ):
                    raise Denied
                source_guard.audit()
                proof_guard.audit()
                progress_guard.audit()
                validator.validate_ledger_value(current, repo_root)
                progress_guard.audit()
                proof_guard.audit()
                source_guard.audit()
                return {
                    "sequence": len(current["events"]),
                    "status": "RECOVERED_COMMITTED",
                    "task_id": task,
                }
            if current["tasks"][task] != "PENDING":
                raise Denied

            def audit_proof() -> None:
                nonlocal authority_time
                source_guard.audit()
                _proof_check, _raw_check, authority_time = _fresh_active_mission(
                    repo_root,
                    selected,
                    expected_raw=mission_raw,
                    previous_utc=authority_time,
                )
                status = _status(repo_root)
                if (
                    not status
                    or not set(status)
                    <= {
                        mission.PENDING_PATH,
                        proof_path,
                        PROGRESS_PENDING_PATH,
                    }
                    or any(status[path] != "add" for path in status)
                    or mission._git(repo_root, "rev-parse", "HEAD").strip()
                    != reviewed_head
                ):
                    raise Denied
                source_guard.audit()

            def validate_recovery(raw: bytes) -> None:
                recovered_proof = mission._parse(raw)
                validator.validate_task_authorization_value(
                    recovered_proof,
                    raw,
                    repo_root,
                    mission_proof=mission_proof,
                    mission_raw=mission_raw,
                    retained=retained_source,
                )
                if recovered_proof["implementation_base_commit"] != "git:" + base:
                    raise Denied

            recovery_raw = _recoverable_publication_raw(
                repo_root,
                proof_path,
                validate_recovery,
                allowed_extra_paths=(
                    {PROGRESS_PENDING_PATH}
                    if PROGRESS_PENDING_PATH in _status(repo_root)
                    else set()
                ),
            )
            if recovery_raw is not None:
                proof_raw = recovery_raw
                proof = mission._parse(proof_raw)
                mission.check_task_base(repo_root, base, mission_proof, require_clean=False)
            else:
                if _status(repo_root):
                    raise Denied
                proof = mission.derive_task_authorization(
                    repo_root, mission_proof, task, base, now_utc=authority_time
                )
                if proof["required_read_files"] != mission.required_read_files(
                    repo_root, descriptor, retained=retained_source
                ):
                    raise Denied
                proof_raw = mission.canonical(proof)

                mission.legacy._publish_proof(
                    repo_root, proof_path, proof_raw, audit=audit_proof
                )
            if recovery_raw is not None:
                mission.legacy._publish_proof(
                    repo_root, proof_path, proof_raw, audit=audit_proof
                )
            _require_status(
                repo_root,
                {proof_path: "add"},
                progress_pending=None,
            )
            proof_guard = mission.open_paths_guard(repo_root, [proof_path])
            if proof_guard.snapshot()[proof_path] != proof_raw:
                raise Denied
            if (
                proof["progress_sequence"] != len(current["events"])
                or proof["progress_sha256"]
                != hashlib.sha256(mission.canonical(current)).hexdigest()
            ):
                raise Denied
            refs = validator._start_refs(task, proof, proof_raw)
            _proof_check, _raw_check, start_time = _fresh_active_mission(
                repo_root,
                selected,
                expected_raw=mission_raw,
                previous_utc=authority_time,
            )
            authority_time = start_time
            candidate = _pending_transition_candidate(
                paths,
                current,
                task=task,
                target="IN_PROGRESS",
                refs=refs,
            )
            if candidate is None:
                candidate = copy.deepcopy(current)
                candidate["tasks"][task] = "IN_PROGRESS"
                candidate["events"].append(
                    {
                        "sequence": len(candidate["events"]) + 1,
                        "task_id": task,
                        "from": "PENDING",
                        "to": "IN_PROGRESS",
                        "at_utc": start_time,
                        "evidence_refs": refs,
                        "blocker": None,
                    }
                )
                candidate["updated_at_utc"] = start_time
            else:
                start_time = candidate["events"][-1]["at_utc"]
                if not (
                    mission._timestamp(proof["derived_at_utc"])
                    <= mission._timestamp(start_time)
                    <= mission._timestamp(authority_time)
                ):
                    raise Denied

            def check(_identity=None) -> None:
                nonlocal progress_guard
                if progress_guard is None:
                    raise Denied
                source_guard.audit()
                proof_guard.audit()
                progress_guard.audit()
                _proof_check, _raw_check, _fresh = _fresh_active_mission(
                    repo_root,
                    selected,
                    expected_raw=mission_raw,
                    previous_utc=authority_time,
                )
                if mission._git(repo_root, "rev-parse", "HEAD").strip() != reviewed_head:
                    raise Denied
                _require_status(
                    repo_root,
                    {proof_path: "add"},
                    progress_pending=True,
                )
                validator.validate_ledger_value(candidate, repo_root)
                progress_guard.audit()
                proof_guard.audit()
                source_guard.audit()
                progress_guard.close()
                progress_guard = None

            def post_publish() -> None:
                nonlocal authority_time
                _proof_check, _raw_check, authority_time = _fresh_active_mission(
                    repo_root,
                    selected,
                    expected_raw=mission_raw,
                    previous_utc=authority_time,
                )
                source_guard.audit()
                if (
                    mission._git(repo_root, "rev-parse", "HEAD").strip()
                    != reviewed_head
                ):
                    raise Denied
                _require_status(
                    repo_root,
                    {proof_path: "add", mission.PROGRESS_PATH: "modify"},
                    progress_pending=False,
                )
                proof_guard.audit()
                validator.validate(repo_root, now_utc=authority_time)
                proof_guard.audit()
                source_guard.audit()

            recovered = writer._publish(
                paths,
                candidate,
                initialize=False,
                runtime=selected,
                pre_publish=check,
                post_publish=post_publish,
            )
            validator.validate(repo_root, now_utc=authority_time)
            proof_guard.audit()
            source_guard.audit()
            return {
                "sequence": len(candidate["events"]),
                "status": "RECOVERED_COMMITTED" if recovered else "PASS",
                "task_id": task,
            }
        finally:
            if progress_guard is not None:
                progress_guard.close()
            if proof_guard is not None:
                proof_guard.close()
            if source_guard is not None:
                source_guard.close()


def block_t032(
    *, runtime: writer.Runtime | None = None, lock_runtime: Any | None = None
) -> dict[str, Any]:
    repo_root = Path.cwd().absolute()
    selected = runtime if runtime is not None else writer.Runtime()
    paths = writer._paths(repo_root)
    manifest, _tasks_sha = writer._inputs(paths)
    lock = lock_runtime if lock_runtime is not None else mission.legacy.v1.Runtime()
    with mission.legacy.v1._authorization_lock(
        os.fspath(repo_root), "subject-progress-v4", manifest["baseline_id"], lock
    ):
        when = writer._time(selected)
        mission_proof, mission_raw = _mission(repo_root, when)
        current = _current(repo_root)
        if current["tasks"]["T-032"] == "BLOCKED":
            return _recover_t032_block(repo_root, current)
        if current["tasks"]["T-032"] != "PENDING" or any(
            current["tasks"][f"T-{number:03d}"] != "COMPLETED" for number in range(1, 32)
        ):
            raise Denied
        history = validator.validate_ledger_value(
            current,
            repo_root,
            include_delivery_anchor=True,
        )
        anchor = history["delivery_anchor"]
        if type(anchor) is not str or mission.COMMIT.fullmatch(anchor) is None:
            raise Denied

        def audit_base(*, pending: bool | None, published: bool) -> None:
            proof_check, raw_check = _mission(repo_root, writer._time(selected))
            if proof_check["mission_id"] != mission_proof["mission_id"] or raw_check != mission_raw:
                raise Denied
            if (
                mission._git(repo_root, "rev-parse", "HEAD").strip().decode() != anchor
                or mission._git(repo_root, "rev-parse", "origin/main").strip().decode()
                != anchor
            ):
                raise Denied
            _require_status(
                repo_root,
                {mission.PROGRESS_PATH: "modify"} if published else {},
                progress_pending=pending,
            )

        audit_base(pending=None, published=False)
        candidate = _pending_transition_candidate(
            paths,
            current,
            task="T-032",
            target="BLOCKED",
            refs=[],
            blocker="OPERATIONAL_ACTION_REQUIRED",
        )
        if candidate is None:
            candidate = copy.deepcopy(current)
            candidate["tasks"]["T-032"] = "BLOCKED"
            candidate["events"].append(
                {
                    "sequence": len(candidate["events"]) + 1,
                    "task_id": "T-032",
                    "from": "PENDING",
                    "to": "BLOCKED",
                    "at_utc": when,
                    "evidence_refs": [],
                    "blocker": "OPERATIONAL_ACTION_REQUIRED",
                }
            )
            candidate["updated_at_utc"] = when
        elif not (
            mission._timestamp(current["updated_at_utc"])
            <= mission._timestamp(candidate["events"][-1]["at_utc"])
            <= mission._timestamp(when)
        ):
            raise Denied
        validator.validate_ledger_value(
            candidate,
            repo_root,
            pending_progress_only_task="T-032",
        )
        recovered = writer._publish(
            paths,
            candidate,
            initialize=False,
            runtime=selected,
            pre_publish=lambda _identity=None: (
                audit_base(pending=True, published=False),
                validator.validate_ledger_value(
                    candidate,
                    repo_root,
                    pending_progress_only_task="T-032",
                ),
            ),
            post_publish=lambda: (
                audit_base(pending=False, published=True),
                validator.validate(repo_root, now_utc=writer._time(selected)),
                audit_base(pending=False, published=True),
            ),
        )
        return {
            "sequence": len(candidate["events"]),
            "status": "RECOVERED_COMMITTED" if recovered else "PASS",
            "task_id": "T-032",
        }


def block_authority(
    task: str,
    *,
    runtime: writer.Runtime | None = None,
    lock_runtime: Any | None = None,
) -> dict[str, Any]:
    """Fail closed after mission expiry or an owner-delivered revocation."""
    if task == "T-032" or mission.TASK.fullmatch(task) is None:
        raise Denied
    repo_root = Path.cwd().absolute()
    selected = runtime if runtime is not None else writer.Runtime()
    paths = writer._paths(repo_root)
    manifest, _tasks_sha = writer._inputs(paths)
    lock = lock_runtime if lock_runtime is not None else mission.legacy.v1.Runtime()
    with mission.legacy.v1._authorization_lock(
        os.fspath(repo_root), "subject-progress-v4", manifest["baseline_id"], lock
    ):
        proof, proof_raw = validator._load_mission_proof(repo_root)
        validator.validate_mission_proof_value(
            proof, proof_raw, repo_root, now_utc=proof["active_from_utc"]
        )
        current = _current(repo_root)
        when = writer._time(selected)
        revocation_raw: bytes | None = None
        if validator._entry_exists(repo_root, mission.REVOCATION_PATH):
            revocation_raw = mission._read(repo_root, mission.REVOCATION_PATH)
            revocation = mission._parse(revocation_raw)
            validator.validate_revocation_value(revocation, revocation_raw, proof)
            validator.validate_revocation_progress(revocation, current)
            blocker = "MISSION_REVOKED"
        elif mission._timestamp(when) >= mission._timestamp(
            proof["mission_not_after_utc"]
        ):
            blocker = "MISSION_EXPIRED"
        else:
            raise Denied
        allowed_status = (
            {mission.REVOCATION_PATH: "add"}
            if blocker == "MISSION_REVOKED"
            and _status(repo_root).get(mission.REVOCATION_PATH) == "add"
            else {}
        )
        if current["tasks"][task] == "BLOCKED":
            lower = (
                revocation["revoked_at_utc"]
                if blocker == "MISSION_REVOKED"
                else proof["mission_not_after_utc"]
            )
            return _recover_authority_block(
                repo_root,
                current,
                task=task,
                blocker=blocker,
                lower_utc=lower,
                now_utc=when,
                allowed_status=allowed_status,
                revocation=revocation if blocker == "MISSION_REVOKED" else None,
                revocation_raw=revocation_raw,
            )
        pending = writer._pending_value(paths)
        if pending is not None and pending["events"][-1]["to"] in {
            "IN_PROGRESS",
            "COMPLETED",
        }:
            _discard_invalidated_active_pending(
                paths,
                current,
                task=task,
                runtime=selected,
                allowed_status=allowed_status,
                expected_revocation_raw=revocation_raw,
            )
            pending = None
        _discard_orphaned_active_artifact(
            repo_root,
            current,
            task=task,
            allowed_status=allowed_status,
            expected_revocation_raw=revocation_raw,
        )
        _require_status(
            repo_root,
            allowed_status,
            progress_pending=False,
        )
        if current["tasks"][task] == "PENDING":
            if pending is not None:
                raise Denied
            return {
                "sequence": len(current["events"]),
                "status": "RECOVERED_ABORTED",
                "task_id": task,
            }
        if current["tasks"][task] != "IN_PROGRESS":
            raise Denied
        task_proof, task_proof_raw = _validated_task_proof(repo_root, task)
        mission.validate_active_task_anchor(
            repo_root,
            proof=task_proof,
            proof_raw=task_proof_raw,
            progress_raw=mission.canonical(current),
            allowed_status=allowed_status,
        )
        candidate = _pending_transition_candidate(
            paths,
            current,
            task=task,
            target="BLOCKED",
            refs=[],
            blocker=blocker,
        )
        if candidate is None:
            candidate = copy.deepcopy(current)
            candidate["tasks"][task] = "BLOCKED"
            candidate["events"].append(
                {
                    "sequence": len(candidate["events"]) + 1,
                    "task_id": task,
                    "from": "IN_PROGRESS",
                    "to": "BLOCKED",
                    "at_utc": when,
                    "evidence_refs": [],
                    "blocker": blocker,
                }
            )
            candidate["updated_at_utc"] = when
        else:
            block_at = mission._timestamp(candidate["events"][-1]["at_utc"])
            lower = (
                mission._timestamp(revocation["revoked_at_utc"])
                if blocker == "MISSION_REVOKED"
                else mission._timestamp(proof["mission_not_after_utc"])
            )
            if not lower <= block_at <= mission._timestamp(when):
                raise Denied
        validator.validate_ledger_value(candidate, repo_root)

        def check(_identity=None) -> None:
            now = writer._time(selected)
            if mission._timestamp(now) < mission._timestamp(when):
                raise Denied
            proof_check, proof_raw_check = validator._load_mission_proof(repo_root)
            if proof_raw_check != proof_raw:
                raise Denied
            validator.validate_mission_proof_value(
                proof_check,
                proof_raw_check,
                repo_root,
                now_utc=proof_check["active_from_utc"],
            )
            if blocker == "MISSION_REVOKED":
                if not validator._entry_exists(repo_root, mission.REVOCATION_PATH):
                    raise Denied
                current_revocation_raw = mission._read(
                    repo_root, mission.REVOCATION_PATH
                )
                if current_revocation_raw != revocation_raw:
                    raise Denied
            elif (
                validator._entry_exists(repo_root, mission.REVOCATION_PATH)
                or mission._timestamp(now)
                < mission._timestamp(proof_check["mission_not_after_utc"])
            ):
                raise Denied
            mission.validate_active_task_anchor(
                repo_root,
                proof=task_proof,
                proof_raw=task_proof_raw,
                progress_raw=mission.canonical(current),
                allowed_status={**allowed_status, PROGRESS_PENDING_PATH: "add"},
            )
            validator.validate_ledger_value(candidate, repo_root)

        def post_publish() -> None:
            validator.validate(repo_root, now_utc=writer._time(selected))
            delivery = mission.validate_authority_block_delivery(
                repo_root,
                proof=task_proof,
                proof_raw=task_proof_raw,
                progress_before_raw=mission.canonical(current),
                progress_after_raw=mission.canonical(candidate),
                revocation_raw=revocation_raw,
            )
            if delivery != "WORKTREE":
                raise Denied

        recovered = writer._publish(
            paths,
            candidate,
            initialize=False,
            runtime=selected,
            pre_publish=check,
            post_publish=post_publish,
        )
        return {
            "sequence": len(candidate["events"]),
            "status": "RECOVERED_COMMITTED" if recovered else "PASS",
            "task_id": task,
        }


def revoke(
    revocation_packet_path: Path,
    expected_revocation_id: str,
    *,
    runtime: writer.Runtime | None = None,
    lock_runtime: Any | None = None,
) -> dict[str, Any]:
    """Publish owner revocation and recover the only legal task block."""
    if mission.HEX64.fullmatch(expected_revocation_id) is None:
        raise Denied
    repo_root = Path.cwd().absolute()
    selected = runtime if runtime is not None else writer.Runtime()
    external, raw = mission.legacy._open_external_public_packet(
        revocation_packet_path.absolute(), repo_root
    )
    guard: mission.legacy.BridgeGuard | None = None
    paths = writer._paths(repo_root)
    manifest, _tasks_sha = writer._inputs(paths)
    lock = lock_runtime if lock_runtime is not None else mission.legacy.v1.Runtime()
    try:
        value = mission._parse(raw)
        with mission.legacy.v1._authorization_lock(
            os.fspath(repo_root), "subject-progress-v4", manifest["baseline_id"], lock
        ):
            proof, proof_raw = validator._load_mission_proof(repo_root)
            validator.validate_mission_proof_value(
                proof, proof_raw, repo_root, now_utc=proof["active_from_utc"]
            )
            validator.validate_revocation_value(value, raw, proof)
            if value["revocation_id"] != expected_revocation_id:
                raise Denied
            contract, _contract_raw = mission.load_contract(repo_root)
            guard = mission.open_paths_guard(
                repo_root,
                sorted(
                    {
                        mission.MISSION_PROOF_PATH,
                        *mission.RETAINED_AUTHORITY_PATHS,
                        *contract["trust_root_paths"],
                    }
                ),
            )
            if guard.snapshot()[mission.MISSION_PROOF_PATH] != proof_raw:
                raise Denied
            current = _current(repo_root)
            pending = writer._pending_value(paths)
            revocation_status = (
                {mission.REVOCATION_PATH: "add"}
                if _status(repo_root).get(mission.REVOCATION_PATH) == "add"
                else {}
            )
            if pending is not None and pending["events"][-1]["to"] in {
                "IN_PROGRESS",
                "COMPLETED",
            }:
                pending_task = pending["events"][-1]["task_id"]
                _discard_invalidated_active_pending(
                    paths,
                    current,
                    task=pending_task,
                    runtime=selected,
                    allowed_status=revocation_status,
                    expected_revocation_raw=raw,
                )
                pending = None
            pending_task = (
                next(
                    (
                        task
                        for task, state in current["tasks"].items()
                        if state in {"PENDING", "IN_PROGRESS"}
                        and _status(repo_root).get(
                            _task_proof_path(task)
                            if state == "PENDING"
                            else _review_path(task)
                        )
                        == "add"
                    ),
                    None,
                )
                if pending is None
                else None
            )
            if pending_task is not None:
                _discard_orphaned_active_artifact(
                    repo_root,
                    current,
                    task=pending_task,
                    allowed_status=revocation_status,
                    expected_revocation_raw=raw,
                )
            _require_status(
                repo_root,
                revocation_status,
                progress_pending=pending is not None,
            )
            previous = validator.validate_revocation_progress(value, current)
            if mission._timestamp(value["revoked_at_utc"]) < mission._timestamp(
                previous["events"][-1]["at_utc"]
            ):
                raise Denied
            authority_time = writer._time(selected)
            if mission._timestamp(authority_time) < mission._timestamp(value["revoked_at_utc"]):
                raise Denied
            if not validator._entry_exists(repo_root, mission.REVOCATION_PATH):
                _mission(repo_root, authority_time)
            in_progress = [
                task for task, state in current["tasks"].items() if state == "IN_PROGRESS"
            ]
            active_task_proof: dict[str, Any] | None = None
            active_task_proof_raw: bytes | None = None
            if len(in_progress) > 1:
                raise Denied
            if in_progress:
                active_task_proof, active_task_proof_raw = _validated_task_proof(
                    repo_root, in_progress[0]
                )
                mission.validate_active_task_anchor(
                    repo_root,
                    proof=active_task_proof,
                    proof_raw=active_task_proof_raw,
                    progress_raw=mission.canonical(current),
                    allowed_status=revocation_status,
                )

            def audit_revocation() -> None:
                external.audit()
                guard.audit()
                now = writer._time(selected)
                if mission._timestamp(now) < mission._timestamp(authority_time):
                    raise Denied
                if validator._entry_exists(repo_root, mission.REVOCATION_PATH):
                    current_raw = mission._read(repo_root, mission.REVOCATION_PATH)
                    if current_raw != raw:
                        raise Denied
                    validator.validate_revocation_value(value, current_raw, proof)
                    validator.validate_revocation_progress(value, _current(repo_root))
                else:
                    _mission(repo_root, now)
                guard.audit()

            recovered_record = mission.publish_revocation_record(
                repo_root, raw, audit=audit_revocation
            )
            if not in_progress:
                if current["events"][-1].get("blocker") == "MISSION_REVOKED":
                    blocked_task = current["events"][-1]["task_id"]
                    blocked_proof, blocked_proof_raw = _validated_task_proof(
                        repo_root, blocked_task
                    )
                    mission.validate_authority_block_delivery(
                        repo_root,
                        proof=blocked_proof,
                        proof_raw=blocked_proof_raw,
                        progress_before_raw=mission.canonical(previous),
                        progress_after_raw=mission.canonical(current),
                        revocation_raw=raw,
                    )
                validator.validate(repo_root, now_utc=authority_time)
                return {
                    "mission_state": "REVOKED",
                    "revocation_id": expected_revocation_id,
                    "sequence": len(current["events"]),
                    "status": "RECOVERED_COMMITTED" if recovered_record else "PASS",
                }
            if (
                len(in_progress) != 1
                or active_task_proof is None
                or active_task_proof_raw is None
            ):
                raise Denied
            task = in_progress[0]
            block_time = writer._time(selected)
            if mission._timestamp(block_time) < mission._timestamp(value["revoked_at_utc"]):
                raise Denied
            candidate = _pending_transition_candidate(
                paths,
                current,
                task=task,
                target="BLOCKED",
                refs=[],
                blocker="MISSION_REVOKED",
            )
            if candidate is None:
                candidate = copy.deepcopy(current)
                candidate["tasks"][task] = "BLOCKED"
                candidate["events"].append(
                    {
                        "sequence": len(candidate["events"]) + 1,
                        "task_id": task,
                        "from": "IN_PROGRESS",
                        "to": "BLOCKED",
                        "at_utc": block_time,
                        "evidence_refs": [],
                        "blocker": "MISSION_REVOKED",
                    }
                )
                candidate["updated_at_utc"] = block_time
            elif not (
                mission._timestamp(value["revoked_at_utc"])
                <= mission._timestamp(candidate["events"][-1]["at_utc"])
                <= mission._timestamp(block_time)
            ):
                raise Denied
            validator.validate_ledger_value(candidate, repo_root)
            recovered_ledger = writer._publish(
                paths,
                candidate,
                initialize=False,
                runtime=selected,
                pre_publish=lambda _identity=None: (
                    audit_revocation(),
                    mission.validate_active_task_anchor(
                        repo_root,
                        proof=active_task_proof,
                        proof_raw=active_task_proof_raw,
                        progress_raw=mission.canonical(current),
                        allowed_status={
                            mission.REVOCATION_PATH: "add",
                            PROGRESS_PENDING_PATH: "add",
                        },
                    ),
                    validator.validate_ledger_value(candidate, repo_root),
                ),
                post_publish=lambda: (
                    audit_revocation(),
                    validator.validate(repo_root, now_utc=writer._time(selected)),
                    mission.validate_authority_block_delivery(
                        repo_root,
                        proof=active_task_proof,
                        proof_raw=active_task_proof_raw,
                        progress_before_raw=mission.canonical(current),
                        progress_after_raw=mission.canonical(candidate),
                        revocation_raw=raw,
                    ),
                ),
            )
            return {
                "mission_state": "REVOKED",
                "revocation_id": expected_revocation_id,
                "sequence": len(candidate["events"]),
                "status": (
                    "RECOVERED_COMMITTED"
                    if recovered_record or recovered_ledger
                    else "PASS"
                ),
            }
    finally:
        if guard is not None:
            guard.close()
        external.close()


def complete(
    task: str,
    source_review_packet_path: Path,
    preliminary_delivery_packet_path: Path,
    *,
    runtime: writer.Runtime | None = None,
    lock_runtime: Any | None = None,
) -> dict[str, Any]:
    if task in {"T-032", "T-033"} or mission.TASK.fullmatch(task) is None:
        raise Denied
    repo_root = Path.cwd().absolute()
    selected = runtime if runtime is not None else writer.Runtime()
    source_external, source_review_raw = mission.legacy._open_external_public_packet(
        source_review_packet_path.absolute(), repo_root
    )
    delivery_external, delivery_raw = mission.legacy._open_external_public_packet(
        preliminary_delivery_packet_path.absolute(), repo_root
    )
    guard: mission.legacy.BridgeGuard | None = None
    progress_guard: mission.legacy.BridgeGuard | None = None
    review_guard: mission.legacy.BridgeGuard | None = None
    paths = writer._paths(repo_root)
    manifest, _tasks_sha = writer._inputs(paths)
    lock = lock_runtime if lock_runtime is not None else mission.legacy.v1.Runtime()
    try:
        with mission.legacy.v1._authorization_lock(
            os.fspath(repo_root), "subject-progress-v4", manifest["baseline_id"], lock
        ):
            mission_proof, mission_raw, authority_time = _fresh_active_mission(
                repo_root, selected
            )
            current = _current(repo_root)
            if current["tasks"][task] not in {"IN_PROGRESS", "COMPLETED"}:
                raise Denied
            proof_path = _task_proof_path(task)
            proof_raw = mission._read(repo_root, proof_path)
            proof = mission._parse(proof_raw)
            proof_result = validator.validate_task_authorization_value(
                proof,
                proof_raw,
                repo_root,
                mission_proof=mission_proof,
                mission_raw=mission_raw,
            )
            descriptor = proof_result["descriptor"]
            contract, contract_raw = mission.load_contract(repo_root)
            _registry, registry_raw = mission.load_registry(repo_root, contract)
            guarded_paths = sorted(
                {
                    mission.MISSION_PROOF_PATH,
                    proof_path,
                    *descriptor["completion_repo_relative_paths"],
                    *descriptor["required_read_paths"],
                    *mission.RETAINED_AUTHORITY_PATHS,
                    *contract["trust_root_paths"],
                }
            )
            guard = mission.open_paths_guard(repo_root, guarded_paths)
            progress_guard = mission.open_paths_guard(repo_root, [mission.PROGRESS_PATH])
            retained = guard.snapshot()
            if (
                retained[mission.MISSION_PROOF_PATH] != mission_raw
                or retained[mission.CONTRACT_PATH] != contract_raw
                or retained[mission.SCOPE_REGISTRY_PATH] != registry_raw
                or retained[proof_path] != proof_raw
            ):
                raise Denied
            current_raw = progress_guard.snapshot()[mission.PROGRESS_PATH]
            retained[mission.PROGRESS_PATH] = current_raw
            source_review = mission._parse(source_review_raw)
            validator.validate_source_review_value(
                source_review,
                source_review_raw,
                repo_root,
                task,
                proof=proof,
                proof_raw=proof_raw,
                retained=retained,
            )
            delivery = mission._parse(delivery_raw)
            validator.validate_preliminary_delivery_value(
                delivery,
                delivery_raw,
                repo_root,
                task,
                proof=proof,
                proof_raw=proof_raw,
                source_review=source_review,
                source_review_raw=source_review_raw,
                retained=retained,
            )
            review = validator.build_completion_review(
                source_review, source_review_raw, delivery, delivery_raw
            )
            review_raw = mission.canonical(review)
            review_result = validator.validate_completion_review_value(
                review,
                review_raw,
                repo_root,
                task,
                proof=proof,
                proof_raw=proof_raw,
                retained=retained,
            )
            _proof_check, _raw_check, completion_time = _fresh_active_mission(
                repo_root,
                selected,
                expected_raw=mission_raw,
                previous_utc=authority_time,
            )
            if mission._timestamp(completion_time) < mission._timestamp(
                review_result["reviewed_at_utc"]
            ):
                raise Denied
            progress_before = current
            progress_before_raw = current_raw
            if current["tasks"][task] == "COMPLETED":
                if (
                    not current["events"]
                    or current["events"][-1]["task_id"] != task
                    or current["events"][-1]["to"] != "COMPLETED"
                ):
                    raise Denied
                progress_before = copy.deepcopy(current)
                progress_before["events"].pop()
                progress_before["tasks"][task] = "IN_PROGRESS"
                progress_before["updated_at_utc"] = progress_before["events"][-1]["at_utc"]
                progress_before_raw = mission.canonical(progress_before)
            if (
                source_review["progress_before_sequence"] != len(progress_before["events"])
                or source_review["progress_before_sha256"]
                != hashlib.sha256(progress_before_raw).hexdigest()
            ):
                raise Denied
            review_path = _review_path(task)
            source_paths = sorted([proof_path, *descriptor["completion_repo_relative_paths"]])
            expected_before_paths = sorted([*source_paths, mission.PROGRESS_PATH])
            reviewed_head = delivery["preliminary_head_commit"][4:].encode()
            if mission._git(repo_root, "rev-parse", "HEAD").strip() != reviewed_head:
                raise Denied

            def validate_review_recovery(raw: bytes) -> None:
                if raw != review_raw:
                    raise Denied

            review_recovery = _recoverable_publication_raw(
                repo_root,
                review_path,
                validate_review_recovery,
                allowed_extra_paths=(
                    (
                        {mission.PROGRESS_PATH}
                        if current["tasks"][task] == "COMPLETED"
                        else set()
                    )
                    | (
                        {PROGRESS_PENDING_PATH}
                        if PROGRESS_PENDING_PATH in _status(repo_root)
                        else set()
                    )
                ),
            )
            if review_recovery is None and _status(repo_root):
                raise Denied

            def audit_review() -> None:
                nonlocal authority_time
                _proof_check, _raw_check, authority_time = _fresh_active_mission(
                    repo_root,
                    selected,
                    expected_raw=mission_raw,
                    previous_utc=authority_time,
                )
                source_external.audit()
                delivery_external.audit()
                guard.audit()
                progress_guard.audit()
                if mission._git(repo_root, "rev-parse", "HEAD").strip() != reviewed_head:
                    raise Denied
                if not set(_status(repo_root)) <= {
                    *expected_before_paths,
                    mission.PENDING_PATH,
                    PROGRESS_PENDING_PATH,
                    review_path,
                }:
                    raise Denied

            mission.legacy._publish_proof(repo_root, review_path, review_raw, audit=audit_review)
            review_guard = mission.open_paths_guard(repo_root, [review_path])
            review_guard.audit()
            retained[review_path] = review_guard.snapshot()[review_path]
            expected_after_status = {review_path: "add"}
            if current["tasks"][task] == "COMPLETED":
                expected_after_status[mission.PROGRESS_PATH] = "modify"
            _require_status(
                repo_root,
                expected_after_status,
                progress_pending=(
                    False if current["tasks"][task] == "COMPLETED" else None
                ),
            )
            validator.validate_ledger_value(current, repo_root)
            if current["tasks"][task] == "COMPLETED":
                validator.validate(repo_root, now_utc=authority_time)
                return {
                    "review_id": review_result["review_id"],
                    "sequence": len(current["events"]),
                    "status": "RECOVERED_COMMITTED",
                    "task_id": task,
                }
            refs = validator._completion_refs(task, proof, proof_raw, review, review_raw)
            candidate = _pending_transition_candidate(
                paths,
                current,
                task=task,
                target="COMPLETED",
                refs=refs,
            )
            if candidate is None:
                candidate = copy.deepcopy(current)
                candidate["tasks"][task] = "COMPLETED"
                candidate["events"].append(
                    {
                        "sequence": len(candidate["events"]) + 1,
                        "task_id": task,
                        "from": "IN_PROGRESS",
                        "to": "COMPLETED",
                        "at_utc": completion_time,
                        "evidence_refs": refs,
                        "blocker": None,
                    }
                )
                candidate["updated_at_utc"] = completion_time
            else:
                completion_time = candidate["events"][-1]["at_utc"]
                if not (
                    mission._timestamp(review_result["reviewed_at_utc"])
                    <= mission._timestamp(completion_time)
                    <= mission._timestamp(authority_time)
                ):
                    raise Denied

            def audit_completed_source(*, published: bool) -> None:
                nonlocal authority_time
                _proof_check, _raw_check, authority_time = _fresh_active_mission(
                    repo_root,
                    selected,
                    expected_raw=mission_raw,
                    previous_utc=authority_time,
                )
                source_external.audit()
                delivery_external.audit()
                guard.audit()
                review_guard.audit()
                if mission._git(repo_root, "rev-parse", "HEAD").strip() != reviewed_head:
                    raise Denied
                expected = {review_path: "add"}
                if published:
                    expected[mission.PROGRESS_PATH] = "modify"
                _require_status(
                    repo_root,
                    expected,
                    progress_pending=False if published else None,
                )

            def check(_identity=None) -> None:
                audit_completed_source(published=False)
                validator.validate_ledger_value(
                    candidate,
                    repo_root,
                    pending_final_delivery_task=task,
                )
                audit_completed_source(published=False)

            check()
            progress_guard.audit()
            progress_guard.close()
            progress_guard = None
            recovered = writer._publish(
                paths,
                candidate,
                initialize=False,
                runtime=selected,
                pre_publish=check,
                post_publish=lambda: (
                    audit_completed_source(published=True),
                    validator.validate(repo_root, now_utc=authority_time),
                    audit_completed_source(published=True),
                ),
            )
            _proof_check, _raw_check, authority_time = _fresh_active_mission(
                repo_root,
                selected,
                expected_raw=mission_raw,
                previous_utc=authority_time,
            )
            validator.validate(repo_root, now_utc=authority_time)
            return {
                "review_id": review_result["review_id"],
                "sequence": len(candidate["events"]),
                "status": "RECOVERED_COMMITTED" if recovered else "PASS",
                "task_id": task,
            }
    finally:
        if review_guard is not None:
            review_guard.close()
        if progress_guard is not None:
            progress_guard.close()
        if guard is not None:
            guard.close()
        delivery_external.close()
        source_external.close()


def main(argv: list[str] | None = None) -> int:
    try:
        parser = _Parser(add_help=False, allow_abbrev=False)
        parser.add_argument(
            "action",
            choices=("start", "complete", "block-t032", "block-authority", "revoke"),
        )
        parser.add_argument("--task")
        parser.add_argument("--implementation-base-commit")
        parser.add_argument("--source-review-packet")
        parser.add_argument("--preliminary-delivery-packet")
        parser.add_argument("--revocation-packet")
        parser.add_argument("--expected-revocation-id")
        parser.add_argument("--json", action="store_true")
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
        if not args.json:
            raise Denied
        if (
            args.action == "start"
            and args.task
            and args.implementation_base_commit
            and not args.source_review_packet
            and not args.preliminary_delivery_packet
            and not args.revocation_packet
            and not args.expected_revocation_id
        ):
            result = start(args.task, args.implementation_base_commit)
        elif (
            args.action == "complete"
            and args.task
            and args.source_review_packet
            and args.preliminary_delivery_packet
            and not args.implementation_base_commit
            and not args.revocation_packet
            and not args.expected_revocation_id
        ):
            result = complete(
                args.task,
                Path(args.source_review_packet),
                Path(args.preliminary_delivery_packet),
            )
        elif args.action == "block-t032" and not any(
            (
                args.task,
                args.implementation_base_commit,
                args.source_review_packet,
                args.preliminary_delivery_packet,
                args.revocation_packet,
                args.expected_revocation_id,
            )
        ):
            result = block_t032()
        elif (
            args.action == "block-authority"
            and args.task
            and not args.implementation_base_commit
            and not args.source_review_packet
            and not args.preliminary_delivery_packet
            and not args.revocation_packet
            and not args.expected_revocation_id
        ):
            result = block_authority(args.task)
        elif (
            args.action == "revoke"
            and args.revocation_packet
            and args.expected_revocation_id
            and not any(
                (
                    args.task,
                    args.implementation_base_commit,
                    args.source_review_packet,
                    args.preliminary_delivery_packet,
                )
            )
        ):
            result = revoke(
                Path(args.revocation_packet), args.expected_revocation_id
            )
        else:
            raise Denied
        sys.stdout.buffer.write(mission.canonical(result))
        return 0
    except (Denied, writer.Denied, mission.legacy.v1.Denied, SystemExit):
        sys.stderr.write(DENY_TEXT)
        return 2
    except Exception:  # noqa: BLE001 - fixed no-echo boundary
        sys.stderr.write(ERROR_TEXT)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
