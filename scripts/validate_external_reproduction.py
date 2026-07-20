#!/usr/bin/env python3
"""Fail-closed validation for an external reproduction submission directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


EXPECTED_BENCHMARK = "vaultgovbench-retrieval-v0.1"
EXPECTED_CLAIM_BOUNDARY = "public synthetic controlled retrieval-only governance contract"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_file(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
        raise ValueError(f"unsafe artifact path: {relative}")
    resolved = (root / candidate).resolve()
    if root not in resolved.parents or not resolved.is_file():
        raise ValueError(f"artifact is missing or escapes submission: {relative}")
    return resolved


def validate_submission(directory: str | Path) -> dict[str, Any]:
    root = Path(directory).resolve()
    manifest_path = root / "submission.json"
    checksums_path = root / "SHA256SUMS"
    if not root.is_dir() or not manifest_path.is_file() or not checksums_path.is_file():
        raise ValueError("submission requires submission.json and SHA256SUMS")

    expected: dict[Path, str] = {}
    for number, line in enumerate(checksums_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            digest, relative = line.split("  ", 1)
        except ValueError as exc:
            raise ValueError(f"invalid SHA256SUMS line {number}") from exc
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError(f"invalid SHA-256 on line {number}")
        path = _safe_file(root, relative.removeprefix("./"))
        if path in expected:
            raise ValueError(f"duplicate checksum path: {relative}")
        expected[path] = digest

    actual = {path.resolve() for path in root.rglob("*") if path.is_file() and path != checksums_path}
    if set(expected) != actual:
        raise ValueError("checksum coverage mismatch")
    mismatches = [str(path.relative_to(root)) for path, digest in expected.items() if _digest(path) != digest]
    if mismatches:
        raise ValueError(f"checksum mismatch: {sorted(mismatches)}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("artifact_type") != "external_reproduction_submission":
        raise ValueError("submission manifest contract is invalid")
    if manifest.get("benchmark") != EXPECTED_BENCHMARK:
        raise ValueError("benchmark identity is invalid")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{7,79}", str(manifest.get("reproduction_id") or "")):
        raise ValueError("reproduction_id is invalid")
    operator_handle = str((manifest.get("operator") or {}).get("github_handle") or "")
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", operator_handle):
        raise ValueError("operator GitHub handle is invalid")
    provider = manifest.get("provider") or {}
    if provider.get("name") != "mem0" or provider.get("version") != "2.0.12":
        raise ValueError("v1 kit accepts only the pinned mem0 2.0.12 track")
    source = manifest.get("source") or {}
    if source.get("git_dirty") is not False or not re.fullmatch(r"[0-9a-f]{40}", str(source.get("revision") or "")):
        raise ValueError("source revision must be a clean 40-character commit")
    protocol = manifest.get("protocol") or {}
    required_protocol = {"repeats": 5, "blinded_provider_input": True, "top_k": 1, "candidate_pool_k": 4}
    if any(protocol.get(key) != value for key, value in required_protocol.items()):
        raise ValueError("protocol does not match the frozen v1 reproduction contract")
    attestation = manifest.get("attestation") or {}
    required_attestations = (
        "independent_operator",
        "provider_never_received_gold_labels",
        "fresh_store_each_repeat",
        "no_secrets_or_private_data",
        "public_review_consent",
    )
    if any(attestation.get(key) is not True for key in required_attestations):
        raise ValueError("all external-reproduction attestations must be true")
    if EXPECTED_CLAIM_BOUNDARY not in str(manifest.get("claim_boundary") or "").lower():
        raise ValueError("claim boundary is missing or too broad")

    artifacts = manifest.get("artifacts") or {}
    summary_path = _safe_file(root, str(artifacts.get("repeat_summary") or ""))
    _safe_file(root, str(artifacts.get("provider_input") or ""))
    _safe_file(root, str(artifacts.get("environment_freeze") or ""))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("artifact_type") != "memory_foundation_repeat_summary":
        raise ValueError("repeat summary artifact type is invalid")
    if summary.get("benchmark") != EXPECTED_BENCHMARK or summary.get("system") != "mem0":
        raise ValueError("repeat summary identity is invalid")
    if summary.get("repeats") != 5 or summary.get("publishable") is not True:
        raise ValueError("repeat summary did not pass the publication contract")
    if summary.get("release_gate_reasons"):
        raise ValueError("repeat summary contains release-gate reasons")

    return {
        "ok": True,
        "artifact_type": "external_reproduction_validation",
        "reproduction_id": manifest.get("reproduction_id"),
        "operator": operator_handle,
        "benchmark": manifest.get("benchmark"),
        "provider": provider,
        "files_verified": len(expected),
        "summary_publishable": True,
        "review_state": "contract_valid_not_maintainer_endorsed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission", help="Path to the external reproduction directory")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate_submission(args.submission)
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"PASS: {result['reproduction_id']} ({result['files_verified']} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
