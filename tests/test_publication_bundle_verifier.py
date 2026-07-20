from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts.verify_publication_bundle import verify_bundle


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "benchmarks/results/vaultgovbench-retrieval-v0.1/89b9156"


def test_checked_in_bundle_passes_standalone_verification():
    result = verify_bundle(BUNDLE)
    assert result["ok"] is True
    assert result["files_verified"] == 36
    assert [track["system"] for track in result["tracks"]] == ["vault", "mem0"]
    assert "retrieval-only" in result["claim_boundary"]


def test_verifier_rejects_modified_artifact(tmp_path):
    target = tmp_path / "bundle"
    shutil.copytree(BUNDLE, target)
    (target / "mem0-r1/run.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_bundle(target)


def test_verifier_rejects_unlisted_artifact(tmp_path):
    target = tmp_path / "bundle"
    shutil.copytree(BUNDLE, target)
    (target / "extra.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="coverage mismatch"):
        verify_bundle(target)


def test_verifier_rejects_unsafe_checksum_path(tmp_path):
    target = tmp_path / "bundle"
    shutil.copytree(BUNDLE, target)
    with (target / "SHA256SUMS").open("a", encoding="utf-8") as handle:
        handle.write(f"{'0' * 64}  ../escape.json\n")
    with pytest.raises(ValueError, match="unsafe checksum path"):
        verify_bundle(target)
