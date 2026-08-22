from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_new_cli_project_uses_l0_bootstrap_without_legacy_identity(tmp_path: Path) -> None:
    from vault.cli_core import cmd_init

    project = tmp_path / "cli-project"
    cmd_init(SimpleNamespace(project_dir=str(project), pretty=False, json=False))

    assert (project / "L0-bootstrap").is_dir()
    assert not (project / "L0-identity").exists()


def test_new_agent_setup_project_uses_l0_bootstrap_without_legacy_identity(
    tmp_path: Path,
) -> None:
    from vault.agent_setup import ensure_project

    project = ensure_project(tmp_path / "agent-project")

    assert (project / "L0-bootstrap").is_dir()
    assert not (project / "L0-identity").exists()


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("L0-bootstrap/project.md", "L0"),
        ("L0-identity/about.md", "L0"),
    ],
)
def test_l0_source_inference_supports_canonical_and_legacy_paths(
    source: str,
    expected: str,
) -> None:
    from vault.compiler import assign_layer

    assert assign_layer({"source": source}) == expected


@pytest.mark.parametrize("language", ["en", "zh-Hant", "zh-CN"])
def test_generated_maintenance_guide_does_not_teach_human_modeling(
    language: str,
) -> None:
    from vault.agent_setup_memory import render_memory_agents_guide

    guide = render_memory_agents_guide(
        project_dir="/tmp/synthetic-vault-project",
        agent="maintenance-agent",
        language=language,
    )
    lowered = guide.casefold()
    forbidden = (
        "profile agents produce",
        "profile candidate",
        "user_profile",
        "care_summary",
        "shared user profiles",
        "人格側寫",
        "人格侧写",
        "側寫候選",
        "侧写候选",
    )
    assert not any(term.casefold() in lowered for term in forbidden)
    assert "candidate" in lowered or "候選" in guide or "候选" in guide
    assert "archive" in lowered


def test_agent_manifest_declares_neutral_bootstrap_boundary() -> None:
    manifest = json.loads((ROOT / "agent_manifest.json").read_text(encoding="utf-8"))
    governance = manifest["memory_governance"]

    assert governance["L0_boundary"]["canonical_directory"] == "L0-bootstrap"
    assert governance["L0_boundary"]["legacy_read_alias"] == "L0-identity"
    assert governance["L0_boundary"]["owns_identity_modeling"] is False
    assert governance["L0_boundary"]["migrates_legacy_data"] is False


@pytest.mark.parametrize(
    "relative",
    ["README.md", "README.zh-Hant.md", "README.zh-CN.md", "docs/core-concepts.md"],
)
def test_primary_public_docs_name_l0_bootstrap_not_l0_identity(relative: str) -> None:
    text = (ROOT / relative).read_text(encoding="utf-8")

    assert "L0-bootstrap" in text
    assert "L0 Identity" not in text
    assert "L0 身份" not in text


@pytest.mark.parametrize(
    ("relative", "stale_phrases", "required_phrase"),
    [
        (
            "docs/memory_governance.md",
            (
                "Minimal identity for the user, agent, project, or workspace.",
                "owner_agent: profile-agent",
                "memory_type: care_summary",
                "Keep each agent's persona, private profile notes",
                "Let care or companion agents publish short `L2` summaries",
            ),
            "Stable bootstrap context for the project or workspace",
        ),
        (
            "docs/agent_install.md",
            (
                "The user wants profile summaries, dream reports, forgetting, or periodic curation.",
            ),
            "memory curation, lifecycle reports, TTL review, or reversible archive previews",
        ),
        (
            "docs/vision.md",
            ("reviewed profile summaries",),
            "reviewed, sourced memory summaries",
        ),
    ],
)
def test_active_public_guidance_respects_frozen_memory_boundary(
    relative: str,
    stale_phrases: tuple[str, ...],
    required_phrase: str,
) -> None:
    text = (ROOT / relative).read_text(encoding="utf-8")

    for stale_phrase in stale_phrases:
        assert stale_phrase not in text
    assert required_phrase in text


def test_vam003_rollback_approval_and_cleanliness_guards_fail_closed() -> None:
    rollback = (
        ROOT / "DEP-VAM-003-L0-BOOTSTRAP-BOUNDARY" / "rollback.md"
    ).read_text(encoding="utf-8")

    guarded_block = rollback.split("## Guarded preparation command", 1)[1].split(
        "## Reversible steps", 1
    )[0]
    assert "assert " not in guarded_block
    assert "raise SystemExit" in rollback
    assert rollback.count("git status --porcelain=v1 --untracked-files=all") >= 2
    assert "DEP-VAM-003-INDEPENDENT-REVIEW-REMEDIATION" in guarded_block
    assert "DEP-VAM-003-SHAREABLE-PATH-REDACTION" in guarded_block

    snippets = re.findall(r"python -c '([^']+)'", rollback)
    approval_snippet = next(
        snippet for snippet in snippets if "approval_consumed" in snippet
    )
    invalid = subprocess.run(
        [sys.executable, "-O", "-c", approval_snippet],
        input='{"state":"CONTINUE","approval_consumed":false}\n',
        text=True,
        check=False,
        capture_output=True,
    )
    valid = subprocess.run(
        [sys.executable, "-O", "-c", approval_snippet],
        input='{"state":"CONTINUE","approval_consumed":true}\n',
        text=True,
        check=False,
        capture_output=True,
    )

    assert invalid.returncode != 0
    assert valid.returncode == 0

    allowlist_snippet = next(
        snippet for snippet in snippets if "actual=set" in snippet
    )
    expected_match = re.search(
        r'expected=set\("""(.*?)"""\.splitlines\(\)\)',
        allowlist_snippet,
        flags=re.DOTALL,
    )
    assert expected_match is not None
    expected_paths = expected_match.group(1).splitlines()
    invalid_allowlist = subprocess.run(
        [sys.executable, "-O", "-c", allowlist_snippet],
        input=b"unexpected-path\0",
        check=False,
        capture_output=True,
    )
    valid_allowlist = subprocess.run(
        [sys.executable, "-O", "-c", allowlist_snippet],
        input=("\0".join(expected_paths) + "\0").encode(),
        check=False,
        capture_output=True,
    )

    assert invalid_allowlist.returncode != 0
    assert valid_allowlist.returncode == 0


def test_vam003_rollback_exposes_merge_verifier_contract() -> None:
    rollback = (
        ROOT / "DEP-VAM-003-L0-BOOTSTRAP-BOUNDARY" / "rollback.md"
    ).read_text(encoding="utf-8")
    fields = dict(
        re.findall(
            r"^(rollback_version|target|command|verify):[ \t]*(.+)$",
            rollback,
            flags=re.MULTILINE,
        )
    )

    assert fields["rollback_version"] == "1.0"
    for name in ("target", "command", "verify"):
        value = fields[name].strip()
        assert value
        lowered = value.casefold()
        assert not any(
            placeholder in lowered
            for placeholder in ("todo", "replace", "unavailable", "<", ">")
        )


def test_exact_head_builder_proof_redacts_workstation_path_and_binds_hashes() -> None:
    dep = ROOT / "DEP-VAM-003-IDENTITY-ISOLATION-RECHECK"
    relative = "shareable/artifacts/exact-head-builder-local-green.txt"
    artifact = dep / relative
    content = artifact.read_text(encoding="utf-8")

    assert "/home/" not in content
    assert "$BUILDER_WORKTREE" in content

    output_sha256 = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest = json.loads((dep / "manifest.json").read_text(encoding="utf-8"))
    manifest_record = next(
        record for record in manifest["shareable"] if record["path"] == relative
    )
    assert manifest_record["sha256"] == output_sha256
    raw_record = next(
        record
        for record in manifest["raw"]
        if record["path"] == "private/raw/exact-head-builder-local-green.txt"
    )
    assert raw_record["sha256"] == (
        "8078c2cca9c7449ef50e17631d6041829866c01e26cf270c08b9d9c1c778b6a8"
    )

    report = json.loads(
        (dep / "redaction-report.json").read_text(encoding="utf-8")
    )
    report_record = next(
        record
        for record in report["files"]
        if record["output"] == "exact-head-builder-local-green.txt"
    )
    assert report_record["source_sha256"] == (
        "8078c2cca9c7449ef50e17631d6041829866c01e26cf270c08b9d9c1c778b6a8"
    )
    assert report_record["output_sha256"] == output_sha256
    assert report_record["redactions"] == {"workstation_path": 1}


def test_all_vam003_shareable_evidence_omits_owner_home_paths() -> None:
    artifacts = sorted(ROOT.glob("DEP-VAM-003-*/shareable/artifacts/*"))

    assert artifacts
    for artifact in artifacts:
        if artifact.is_file():
            assert b"/home/" not in artifact.read_bytes(), artifact
