from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import run_external_reproduction as runner
from scripts import preflight_external_reproduction as preflight
from scripts.validate_external_reproduction import validate_submission


ROOT = Path(__file__).resolve().parents[1]


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
    monkeypatch.setattr(runner, "run_preflight", lambda **kwargs: {"ok": True, "blocked_checks": []})
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


def test_reproduction_docs_keep_environment_outside_clean_checkout():
    guide = (ROOT / "benchmarks/external_reproduction/README.md").read_text(encoding="utf-8")
    assert "python3.13 -m venv ../vault-repro-venv" in guide
    assert ">=3.10,<3.14" in guide
    assert "../vault-repro-venv/bin/python scripts/run_external_reproduction.py" in guide
    assert "python -m venv .repro-venv" not in guide
    assert ".repro-venv/bin/python" not in guide
    assert "huggingface.co" in guide
    assert "Environment blocked" in guide
    assert "--preflight-only --json" in guide
    assert "environment readiness only" in guide


def test_blocked_attempt_has_separate_non_submission_issue_form():
    form = (ROOT / ".github/ISSUE_TEMPLATE/external_reproduction_blocked.yml").read_text(encoding="utf-8")
    assert "External reproduction blocked attempt" in form
    assert "FastEmbed model prewarm" in form
    assert "No complete five-repeat bundle or Contract validated claim" in form


def test_model_prewarm_failure_explains_environment_blocked_state(tmp_path, monkeypatch):
    def fake_git(*args):
        return {("rev-parse", "HEAD"): "b" * 40, ("status", "--porcelain"): ""}[args]

    def fake_run(command, *, env=None, capture=False):
        if command[1:4] == ["-m", "pip", "freeze"]:
            return "mem0ai==2.0.12\n"
        if "export-provider-input" in command:
            output = Path(command[command.index("--output") + 1])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("{}", encoding="utf-8")
            return ""
        if command[1:2] == ["-c"]:
            raise runner.subprocess.CalledProcessError(1, command)
        return ""

    monkeypatch.setattr(runner, "_git", fake_git)
    monkeypatch.setattr(runner, "_run", fake_run)
    monkeypatch.setattr(runner, "run_preflight", lambda **kwargs: {"ok": True, "blocked_checks": []})
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
    with pytest.raises(RuntimeError, match="Environment blocked"):
        runner.run(args)


def _preflight_kwargs(tmp_path):
    return {
        "output_dir": tmp_path / "output",
        "model_cache_dir": tmp_path / "cache",
        "root": tmp_path / "repo",
        "prefix": tmp_path / "venv",
        "base_prefix": tmp_path / "system-python",
        "package_versions": dict(preflight.PINNED_PACKAGES),
        "disk_free_bytes": 20 * preflight.GIB,
        "memory_bytes": 16 * preflight.GIB,
        "git_revision": "c" * 40,
        "git_dirty": False,
        "network_probe": lambda url, timeout: (True, "HTTP 200"),
        "python_version": (3, 13),
    }


def test_preflight_passes_with_cold_cache_and_reachable_model_host(tmp_path):
    result = preflight.run_preflight(**_preflight_kwargs(tmp_path))
    assert result["ok"] is True
    assert result["status"] == "pass"
    assert "pinned_model_cache" in result["warnings"]
    assert "not a benchmark run" in result["claim_boundary"]


@pytest.mark.parametrize("change,blocked", [
    ({"git_dirty": True}, "clean_worktree"),
    ({"disk_free_bytes": preflight.GIB}, "free_disk"),
    ({"memory_bytes": preflight.GIB}, "system_memory"),
])
def test_preflight_blocks_invalid_environment(tmp_path, change, blocked):
    kwargs = _preflight_kwargs(tmp_path)
    kwargs.update(change)
    result = preflight.run_preflight(**kwargs)
    assert result["ok"] is False
    assert blocked in result["blocked_checks"]


def test_preflight_blocks_python_314_before_dependency_install(tmp_path):
    kwargs = _preflight_kwargs(tmp_path)
    kwargs["python_version"] = (3, 14)
    result = preflight.run_preflight(**kwargs)
    assert "python_version" in result["blocked_checks"]


def test_preflight_blocks_environment_inside_repo_and_package_drift(tmp_path):
    kwargs = _preflight_kwargs(tmp_path)
    repo = kwargs["root"]
    kwargs["prefix"] = repo / "venv"
    kwargs["output_dir"] = repo / "output"
    kwargs["package_versions"] = {**preflight.PINNED_PACKAGES, "mem0ai": "2.0.13"}
    result = preflight.run_preflight(**kwargs)
    assert {"isolated_environment", "output_location", "pinned_dependencies"} <= set(result["blocked_checks"])


def test_preflight_blocks_cold_cache_when_hugging_face_is_unreachable(tmp_path):
    kwargs = _preflight_kwargs(tmp_path)
    kwargs["network_probe"] = lambda url, timeout: (False, "Host not in allowlist")
    result = preflight.run_preflight(**kwargs)
    assert result["status"] == "environment_blocked"
    assert "hugging_face_access" in result["blocked_checks"]


def test_preflight_allows_complete_cache_when_hugging_face_is_unreachable(tmp_path):
    kwargs = _preflight_kwargs(tmp_path)
    cache = kwargs["model_cache_dir"]
    for marker in preflight.REQUIRED_CACHE_MARKERS:
        (cache / marker).mkdir(parents=True)
    kwargs["network_probe"] = lambda url, timeout: (False, "offline")
    result = preflight.run_preflight(**kwargs)
    assert result["ok"] is True
    assert "hugging_face_access" in result["warnings"]


def test_owner_smoke_bundle_cannot_be_mistaken_for_external_submission(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "run_preflight", lambda **kwargs: {"ok": True, "blocked_checks": []})
    monkeypatch.setattr(runner, "_git", lambda *args: {("rev-parse", "HEAD"): "d" * 40, ("status", "--porcelain"): "", ("remote", "get-url", "origin"): "local"}[args])
    monkeypatch.setattr(runner.importlib.metadata, "version", lambda name: "2.0.12")

    def fake_run(command, *, env=None, capture=False):
        if command[1:4] == ["-m", "pip", "freeze"]:
            return "mem0ai==2.0.12\n"
        if "--output" in command:
            path = Path(command[command.index("--output") + 1])
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"publishable": True, "release_gate_reasons": []} if "summarize-repeats" in command else {}
            path.write_text(json.dumps(payload), encoding="utf-8")
        return ""

    monkeypatch.setattr(runner, "_run", fake_run)
    args = type("Args", (), {"output_dir": str(tmp_path / "owner"), "github_handle": "project-owner", "affiliation": "owner", "conflicts": "maintainer", "operator_mode": "owner-smoke"})()
    bundle = runner.run(args)
    manifest = json.loads((bundle / "submission.json").read_text())
    assert manifest["artifact_type"] == "owner_operated_reproduction_smoke"
    assert manifest["attestation"]["independent_operator"] is False
    with pytest.raises(ValueError):
        validate_submission(bundle)
