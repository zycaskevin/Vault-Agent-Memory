#!/usr/bin/env python3
"""Proof-aware atomic start/completion wrapper for Subject authorization v2."""

from __future__ import annotations

import argparse
import copy
import hashlib
import os
import sys
from pathlib import Path

try:
    import run_subject_task_authorization_v2 as runner
    import update_subject_progress as writer_v1
    import validate_subject_task_authorization_v2 as validator
except ImportError:  # pragma: no cover - import path used by test loaders
    from scripts import run_subject_task_authorization_v2 as runner
    from scripts import update_subject_progress as writer_v1
    from scripts import validate_subject_task_authorization_v2 as validator


DENY_TEXT = "SUBJECT_TASK_PROGRESS_V2_DENY\n"
ERROR_TEXT = "SUBJECT_TASK_PROGRESS_V2_ERROR\n"
Denied = runner.Denied


class _Parser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise Denied


def _merge_snapshots(*guards: runner.BridgeGuard) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for guard in guards:
        for label, raw in guard.snapshot().items():
            if label in result and result[label] != raw:
                raise Denied
            result[label] = raw
    return result


def _audit_all(*guards: runner.BridgeGuard) -> None:
    for guard in guards:
        guard.audit()


def start(
    proof_path: Path,
    *,
    runtime: writer_v1.Runtime | None = None,
    lock_runtime: object | None = None,
) -> dict[str, object]:
    repo_root = Path.cwd().absolute()
    task = "T-002"
    expected_proof = repo_root / f"specs/subject-distillation/task-authorizations/{task}.json"
    if proof_path.absolute() != expected_proof.absolute():
        raise Denied
    paths = writer_v1._paths(repo_root)
    selected_runtime = runtime if runtime is not None else writer_v1.Runtime()
    manifest, _tasks_sha = writer_v1._inputs(paths)
    selected_lock_runtime = (
        lock_runtime if lock_runtime is not None else runner.v1.Runtime()
    )
    with runner.v1._authorization_lock(
        os.fspath(repo_root),
        "subject-progress",
        manifest["baseline_id"],
        selected_lock_runtime,
    ):
        guard = runner._open_bridge_guard(
            repo_root, task, include_proof=True, include_progress=False
        )
        try:
            guard.audit()
            retained = guard.snapshot()
            value_path = (
                f"specs/subject-distillation/task-authorizations/{task}.json"
            )
            try:
                raw = retained[value_path]
            except KeyError:
                raise Denied from None
            try:
                value = runner.v1.verifier._parse(raw)
                runner._scan_v2(value)
            except (runner.v1.verifier.Denied, runner.Denied):
                raise Denied from None
            if raw != runner._canonical(value):
                raise Denied
            result = validator.validate_proof_value(
                value, repo_root, retained=retained
            )
            if result["authorized_task"] != task:
                raise Denied
            proof_digest = hashlib.sha256(raw).hexdigest()
            opaque = (
                f"{task.lower().replace('-', '')}-authorization:"
                f"{result['authorization_id']}"
            )
            refs = writer_v1._parse_refs(
                [f"{value['proof_repo_relative_path']}={proof_digest}"], [opaque]
            )
            validator.validate_start_refs(
                repo_root,
                task,
                value["proof_repo_relative_path"],
                result["authorization_id"],
                refs,
                proof_raw=raw,
            )
            guard.audit()
            current = writer_v1._existing(paths)
            if current["tasks"][task] == "IN_PROGRESS":
                if not writer_v1._event_matches(
                    current["events"][-1],
                    task=task,
                    expected="PENDING",
                    target="IN_PROGRESS",
                    refs=refs,
                    blocker=None,
                ):
                    raise Denied
                validator.validate_ledger(repo_root)
                return {
                    "sequence": len(current["events"]),
                    "status": "RECOVERED_COMMITTED",
                    "task_id": task,
                }
            if current["tasks"][task] != "PENDING":
                raise Denied
            current_raw = writer_v1.evidence._canonical(current)
            if (
                value["progress_sequence"] != len(current["events"])
                or value["progress_sha256"]
                != hashlib.sha256(current_raw).hexdigest()
            ):
                raise Denied
            candidate = copy.deepcopy(current)
            when = writer_v1._time(selected_runtime)
            candidate["tasks"][task] = "IN_PROGRESS"
            candidate["events"].append(
                {
                    "sequence": len(candidate["events"]) + 1,
                    "task_id": task,
                    "from": "PENDING",
                    "to": "IN_PROGRESS",
                    "at_utc": when,
                    "evidence_refs": refs,
                    "blocker": None,
                }
            )
            candidate["updated_at_utc"] = when

            def validate_candidate(_pending_identity=None) -> None:
                guard.audit()
                validator.validate_ledger_value(
                    candidate, repo_root, retained=retained
                )
                guard.audit()

            validate_candidate()
            recovered = writer_v1._publish(
                paths,
                candidate,
                initialize=False,
                runtime=selected_runtime,
                pre_publish=validate_candidate,
                post_publish=lambda: (
                    guard.audit(),
                    validator.validate_ledger(repo_root),
                    guard.audit(),
                ),
            )
            validator.validate_ledger(repo_root)
            return {
                "sequence": len(candidate["events"]),
                "status": "RECOVERED_COMMITTED" if recovered else "PASS",
                "task_id": task,
            }
        finally:
            guard.close()


def complete(
    review_packet_path: Path,
    *,
    runtime: writer_v1.Runtime | None = None,
    lock_runtime: object | None = None,
) -> dict[str, object]:
    repo_root = Path.cwd().absolute()
    task = "T-002"
    paths = writer_v1._paths(repo_root)
    selected_runtime = runtime if runtime is not None else writer_v1.Runtime()
    manifest, _tasks_sha = writer_v1._inputs(paths)
    selected_lock_runtime = (
        lock_runtime if lock_runtime is not None else runner.v1.Runtime()
    )
    external, review_raw = runner._open_external_public_packet(
        review_packet_path.absolute(), repo_root
    )
    trust: runner.BridgeGuard | None = None
    prestate: runner.BridgeGuard | None = None
    source: runner.BridgeGuard | None = None
    review_guard: runner.BridgeGuard | None = None
    try:
        with runner.v1._authorization_lock(
            os.fspath(repo_root),
            "subject-progress",
            manifest["baseline_id"],
            selected_lock_runtime,
        ):
            trust = runner._open_bridge_guard(
                repo_root, task, include_proof=True, include_progress=False
            )
            prestate = runner._open_bridge_guard(
                repo_root, task, include_proof=True, include_progress=True
            )
            trust_snapshot = trust.snapshot()
            descriptor_raw = trust_snapshot[runner._scope_path(task)]
            try:
                descriptor_value = runner.v1.verifier._parse(descriptor_raw)
                descriptor = runner._validate_scope_descriptor(
                    descriptor_value, descriptor_raw, task
                )
            except (runner.v1.verifier.Denied, runner.Denied):
                raise Denied from None
            review_path = validator._review_path(task)
            names = runner._directory_names(
                repo_root, "specs/subject-distillation/task-authorizations"
            )
            if names not in (
                ["README.md", "T-002.json"],
                ["README.md", "T-002.json", "T-002.review.json"],
            ):
                raise Denied
            review_present = "T-002.review.json" in names
            current_raw = prestate.snapshot()[runner.PROGRESS_PATH]
            try:
                current = runner.v1.verifier._parse(current_raw)
                runner._scan_v2(current)
            except (runner.v1.verifier.Denied, runner.Denied):
                raise Denied from None
            if current_raw != runner._canonical(current):
                raise Denied
            existing = writer_v1._existing(paths)
            if writer_v1.evidence._canonical(existing) != current_raw:
                raise Denied
            current = existing
            if current["tasks"][task] not in {"IN_PROGRESS", "COMPLETED"}:
                raise Denied
            source = runner._open_bridge_guard(
                repo_root,
                task,
                include_proof=True,
                include_progress=False,
                extra_paths=descriptor["completion_repo_relative_paths"]
                + ([review_path] if review_present else []),
            )
            retained = _merge_snapshots(trust, prestate, source)
            validator.validate_ledger_value(current, repo_root, retained=retained)
            try:
                review_value = runner.v1.verifier._parse(review_raw)
                runner._scan_v2(review_value)
            except (runner.v1.verifier.Denied, runner.Denied):
                raise Denied from None
            if review_raw != runner._canonical(review_value):
                raise Denied
            review_result = validator.validate_completion_review_value(
                review_value,
                review_raw,
                repo_root,
                task,
                retained=retained,
            )
            if review_present and retained[review_path] != review_raw:
                raise Denied
            expected_before = review_value["reviewed_change_paths"] + [
                runner.PROGRESS_PATH
            ] + ([review_path] if review_present else [])
            changes_before = runner._repository_changes(
                repo_root,
                review_value["implementation_base_commit"],
                expected_before,
                retained,
            )
            source_changes = [
                item
                for item in changes_before
                if item["path"] not in {review_path, runner.PROGRESS_PATH}
            ]
            progress_before_change = next(
                (
                    item
                    for item in changes_before
                    if item["path"] == runner.PROGRESS_PATH
                ),
                None,
            )
            expected_progress_sha256 = (
                hashlib.sha256(current_raw).hexdigest()
                if current["tasks"][task] == "COMPLETED"
                else review_value["progress_before_sha256"]
            )
            if (
                source_changes != review_value["reviewed_changes"]
                or progress_before_change
                != {
                    "action": "modify",
                    "mode": "100644",
                    "path": runner.PROGRESS_PATH,
                    "sha256": expected_progress_sha256,
                }
            ):
                raise Denied
            _audit_all(external, trust, prestate, source)
            if current["tasks"][task] == "COMPLETED":
                if not review_present:
                    raise Denied
                validator.validate_ledger(repo_root)
                _audit_all(external, trust, prestate, source)
                return {
                    "sequence": len(current["events"]),
                    "status": "RECOVERED_COMMITTED",
                    "task_id": task,
                }
            when = writer_v1._time(selected_runtime)
            if runner.v1.verifier._timestamp(when) < runner.v1.verifier._timestamp(
                review_result["reviewed_at_utc"]
            ):
                raise Denied
            runner._publish_proof(
                repo_root,
                review_path,
                review_raw,
                audit=lambda: _audit_all(external, trust, prestate, source),
            )
            review_guard = runner._open_bridge_guard(
                repo_root,
                task,
                include_progress=False,
                extra_paths=(review_path,),
            )
            retained = _merge_snapshots(trust, prestate, source, review_guard)
            _audit_all(external, trust, prestate, source, review_guard)
            changes_after = runner._repository_changes(
                repo_root,
                review_value["implementation_base_commit"],
                review_value["reviewed_change_paths"]
                + [runner.PROGRESS_PATH, review_path],
                retained,
            )
            if [
                item
                for item in changes_after
                if item["path"] not in {review_path, runner.PROGRESS_PATH}
            ] != review_value["reviewed_changes"]:
                raise Denied
            progress_after_change = next(
                (
                    item
                    for item in changes_after
                    if item["path"] == runner.PROGRESS_PATH
                ),
                None,
            )
            if progress_after_change != {
                "action": "modify",
                "mode": "100644",
                "path": runner.PROGRESS_PATH,
                "sha256": review_value["progress_before_sha256"],
            }:
                raise Denied
            review_change = next(
                (item for item in changes_after if item["path"] == review_path), None
            )
            if review_change != {
                "action": "add",
                "mode": "100644",
                "path": review_path,
                "sha256": hashlib.sha256(review_raw).hexdigest(),
            }:
                raise Denied
            refs, current_review = validator._expected_completion_refs(
                repo_root,
                task,
                descriptor,
                review_result["authorization_id"],
                review_value=review_value,
                review_raw=review_raw,
                retained=retained,
            )
            if current_review != review_result:
                raise Denied
            candidate = copy.deepcopy(current)
            candidate["tasks"][task] = "COMPLETED"
            candidate["events"].append(
                {
                    "sequence": len(candidate["events"]) + 1,
                    "task_id": task,
                    "from": "IN_PROGRESS",
                    "to": "COMPLETED",
                    "at_utc": when,
                    "evidence_refs": refs,
                    "blocker": None,
                }
            )
            candidate["updated_at_utc"] = when

            def validate_candidate(_pending_identity=None) -> None:
                _audit_all(external, trust, source, review_guard)
                validator.validate_ledger_value(candidate, repo_root, retained=retained)
                _audit_all(external, trust, source, review_guard)

            validate_candidate()
            prestate.audit()
            prestate.close()
            prestate = None
            recovered = writer_v1._publish(
                paths,
                candidate,
                initialize=False,
                runtime=selected_runtime,
                pre_publish=validate_candidate,
                post_publish=lambda: (
                    _audit_all(external, trust, source, review_guard),
                    validator.validate_ledger(repo_root),
                    _audit_all(external, trust, source, review_guard),
                ),
            )
            validator.validate_ledger(repo_root)
            return {
                "sequence": len(candidate["events"]),
                "status": "RECOVERED_COMMITTED" if recovered else "PASS",
                "task_id": task,
            }
    finally:
        if review_guard is not None:
            review_guard.close()
        if source is not None:
            source.close()
        if prestate is not None:
            prestate.close()
        if trust is not None:
            trust.close()
        external.close()


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(add_help=False)
    parser.add_argument("action", choices=("start", "complete"))
    parser.add_argument("--proof")
    parser.add_argument("--review-packet")
    parser.add_argument("--json", action="store_true", required=True)
    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
        if args.action == "start" and args.proof is not None and args.review_packet is None:
            output = start(Path(args.proof))
        elif args.action == "complete" and args.review_packet is not None and args.proof is None:
            output = complete(Path(args.review_packet))
        else:
            raise Denied
    except (Denied, SystemExit, writer_v1.Denied, runner.v1.Denied):
        sys.stderr.write(DENY_TEXT)
        return 2
    except Exception:  # noqa: BLE001 - fixed no-echo public boundary
        sys.stderr.write(ERROR_TEXT)
        return 3
    sys.stdout.write(runner._canonical(output).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
