#!/usr/bin/env python3
"""Fail-closed verifier for a Vault benchmark publication bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_INDEX_TYPE = "memory_foundation_publication_bundle_index"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_bundle(bundle_dir: str | Path) -> dict[str, Any]:
    root = Path(bundle_dir).resolve()
    if not root.is_dir():
        raise ValueError(f"bundle directory does not exist: {root}")

    checksum_path = root / "SHA256SUMS"
    index_path = root / "artifact-index.json"
    if not checksum_path.is_file() or not index_path.is_file():
        raise ValueError("bundle requires SHA256SUMS and artifact-index.json")

    expected: dict[Path, str] = {}
    for number, raw_line in enumerate(checksum_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            digest, relative = raw_line.split("  ", maxsplit=1)
        except ValueError as exc:
            raise ValueError(f"invalid SHA256SUMS line {number}") from exc
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError(f"invalid SHA-256 on line {number}")
        relative_path = Path(relative.removeprefix("./"))
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"unsafe checksum path on line {number}: {relative}")
        resolved = (root / relative_path).resolve()
        if root not in resolved.parents:
            raise ValueError(f"checksum path escapes bundle on line {number}")
        if resolved in expected:
            raise ValueError(f"duplicate checksum path: {relative_path}")
        expected[resolved] = digest

    actual = {
        path.resolve()
        for path in root.rglob("*")
        if path.is_file() and path != checksum_path
    }
    if set(expected) != actual:
        missing = sorted(str(path.relative_to(root)) for path in set(expected) - actual)
        unlisted = sorted(str(path.relative_to(root)) for path in actual - set(expected))
        raise ValueError(f"checksum coverage mismatch: missing={missing}, unlisted={unlisted}")

    mismatches = [str(path.relative_to(root)) for path, digest in expected.items() if _sha256(path) != digest]
    if mismatches:
        raise ValueError(f"checksum mismatch: {sorted(mismatches)}")

    index = json.loads(index_path.read_text(encoding="utf-8"))
    if index.get("schema_version") != 1 or index.get("artifact_type") != REQUIRED_INDEX_TYPE:
        raise ValueError("artifact index contract is invalid")
    tracks = index.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        raise ValueError("artifact index must contain tracks")

    verified_tracks = []
    for track in tracks:
        summary_relative = Path(str(track.get("summary") or ""))
        if not summary_relative.name or summary_relative.is_absolute() or ".." in summary_relative.parts:
            raise ValueError("track summary path is invalid")
        summary_path = root / summary_relative
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if track.get("publishable") is not True or summary.get("publishable") is not True:
            raise ValueError(f"track is not publishable: {track.get('system')}")
        if summary.get("release_gate_reasons"):
            raise ValueError(f"track has release-gate reasons: {track.get('system')}")
        if str(summary.get("system") or "") != str(track.get("system") or ""):
            raise ValueError(f"track summary system mismatch: {track.get('system')}")
        if int(summary.get("repeats") or 0) != int(track.get("repeats") or 0):
            raise ValueError(f"track repeat count mismatch: {track.get('system')}")
        verified_tracks.append(
            {
                "system": track.get("system"),
                "system_version": track.get("system_version"),
                "repeats": track.get("repeats"),
                "summary": str(summary_relative),
            }
        )

    return {
        "ok": True,
        "artifact_type": "publication_bundle_verification",
        "benchmark": index.get("benchmark"),
        "evidence_source_revision": index.get("evidence_source_revision"),
        "claim_boundary": index.get("claim_boundary"),
        "files_verified": len(expected),
        "tracks": verified_tracks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", help="Path to an extracted publication bundle")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable verification output")
    args = parser.parse_args()
    result = verify_bundle(args.bundle)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        systems = ", ".join(str(track["system"]) for track in result["tracks"])
        print(f"PASS: {result['files_verified']} files; tracks: {systems}")
        print(f"Claim boundary: {result['claim_boundary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
