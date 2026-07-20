from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import run_external_reproduction as runner
from scripts.validate_external_reproduction import validate_submission


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_submission(root: Path) -> Path:
    root.mkdir()
    summary = {
        "artifact_type": "memory_foundation_repeat_summary",
        "benchmark": "vaultgovbench-retrieval-v0.1",
        "system": "mem0",
        "repeats": 5,
        "publishable": True,
        "release_gate_reasons": [],
    }
    manifest = {
        "schema_version": 1,
        "artifact_type": "external_reproduction_submission",
        "reproduction_id": "tester-20260720-120000",
        "benchmark": "vaultgovbench-retrieval-v0.1",
        "provider": {"name": "mem0", "version": "2.0.12"},
        "operator": {"github_handle": "external-tester"},
        "source": {"revision": "a" * 40, "git_dirty": False},
        "protocol": {"repeats": 5, "blinded_provider_input": True, "top_k": 1, "candidate_pool_k": 4},
        "artifacts": {"repeat_summary": "repeat-summary.json", "provider_input": "provider-input.json", "environment_freeze": "environment.freeze.txt"},
        "attestation": {
            "independent_operator": True,
            "provider_never_received_gold_labels": True,
            "fresh_store_each_repeat": True,
            "no_secrets_or_private_data": True,
            "public_review_consent": True,
        },
        "claim_boundary": "Six-case public synthetic controlled retrieval-only governance contract; not end-to-end QA.",
    }
    files = {
        "submission.json": json.dumps(manifest, indent=2) + "\n",
        "repeat-summary.json": json.dumps(summary, indent=2) + "\n",
        "provider-input.json": "{}\n",
        "environment.freeze.txt": "mem0ai==2.0.12\n",
    }
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8")
    checksums = "".join(f"{_sha(root / name)}  {name}\n" for name in sorted(files))
    (root / "SHA256SUMS").write_text(checksums, encoding="utf-8")
    return root


def test_valid_external_reproduction_contract_passes(tmp_path):
    result = validate_submission(_make_submission(tmp_path / "submission"))
    assert result["ok"] is True
    assert result["files_verified"] == 4
    assert result["review_state"] == "contract_valid_not_maintainer_endorsed"


def test_modified_artifact_fails_closed(tmp_path):
    root = _make_submission(tmp_path / "submission")
    (root / "repeat-summary.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        validate_submission(root)


def test_unlisted_artifact_fails_closed(tmp_path):
    root = _make_submission(tmp_path / "submission")
    (root / "unlisted.txt").write_text("surprise", encoding="utf-8")
    with pytest.raises(ValueError, match="coverage mismatch"):
        validate_submission(root)


def test_false_independence_attestation_is_rejected(tmp_path):
    root = _make_submission(tmp_path / "submission")
    manifest_path = root / "submission.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["attestation"]["independent_operator"] = False
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    lines = []
    for name in ("environment.freeze.txt", "provider-input.json", "repeat-summary.json", "submission.json"):
        lines.append(f"{_sha(root / name)}  {name}\n")
    (root / "SHA256SUMS").write_text("".join(lines), encoding="utf-8")
    with pytest.raises(ValueError, match="attestations"):
        validate_submission(root)


def test_invalid_operator_identity_is_rejected(tmp_path):
    root = _make_submission(tmp_path / "submission")
    manifest_path = root / "submission.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["operator"]["github_handle"] = "not/a/handle"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    lines = []
    for name in ("environment.freeze.txt", "provider-input.json", "repeat-summary.json", "submission.json"):
        lines.append(f"{_sha(root / name)}  {name}\n")
    (root / "SHA256SUMS").write_text("".join(lines), encoding="utf-8")
    with pytest.raises(ValueError, match="GitHub handle"):
        validate_submission(root)


def test_non_publishable_summary_is_rejected(tmp_path):
    root = _make_submission(tmp_path / "submission")
    summary_path = root / "repeat-summary.json"
    summary = json.loads(summary_path.read_text())
    summary["publishable"] = False
    summary["release_gate_reasons"] = ["provider_index_failures"]
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    lines = []
    for name in ("environment.freeze.txt", "provider-input.json", "repeat-summary.json", "submission.json"):
        lines.append(f"{_sha(root / name)}  {name}\n")
    (root / "SHA256SUMS").write_text("".join(lines), encoding="utf-8")
    with pytest.raises(ValueError, match="publication contract"):
        validate_submission(root)


def test_runner_orchestrates_five_fresh_repeats_and_emits_valid_bundle(tmp_path, monkeypatch):
    commands: list[list[str]] = []

    def fake_git(*args):
        if args == ("rev-parse", "HEAD"):
            return "b" * 40
        if args == ("status", "--porcelain"):
            return ""
        if args == ("remote", "get-url", "origin"):
            return "https://example.test/operator/fork.git"
        raise AssertionError(args)

    def fake_run(command, *, env=None, capture=False):
        commands.append(command)
        if command[1:4] == ["-m", "pip", "freeze"]:
            return "mem0ai==2.0.12\n"
        if "--output" in command:
            output = Path(command[command.index("--output") + 1])
            output.parent.mkdir(parents=True, exist_ok=True)
            if "summarize-repeats" in command:
                payload = {
                    "artifact_type": "memory_foundation_repeat_summary",
                    "benchmark": "vaultgovbench-retrieval-v0.1",
                    "system": "mem0",
                    "repeats": 5,
                    "publishable": True,
                    "release_gate_reasons": [],
                }
            else:
                payload = {"artifact": output.name}
            output.write_text(json.dumps(payload), encoding="utf-8")
        return ""

    monkeypatch.setattr(runner, "_git", fake_git)
    monkeypatch.setattr(runner, "_run", fake_run)
    monkeypatch.setattr(runner.importlib.metadata, "version", lambda name: "2.0.12")
    args = type(
        "Args",
        (),
        {
            "output_dir": str(tmp_path / "bundle"),
            "github_handle": "external-tester",
            "affiliation": "independent",
            "conflicts": "none disclosed",
        },
    )()
    bundle = runner.run(args)
    mem0_commands = [command for command in commands if "mem0-run" in command]
    assert len(mem0_commands) == 5
    assert len({command[command.index("--vector-store-path") + 1] for command in mem0_commands}) == 5
    assert validate_submission(bundle)["ok"] is True
