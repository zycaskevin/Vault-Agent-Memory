from __future__ import annotations

import json
from pathlib import Path
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
