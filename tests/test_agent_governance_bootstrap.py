from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.validate_agent_governance import REQUIRED_FILES, validate

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "docs/governance/PROJECT_GOVERNANCE_PROFILE.yaml"


def _copy_control_plane(destination: Path) -> Path:
    for relative in REQUIRED_FILES:
        source = ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for relative in (
        "AGENTS.md",
        "docs/repo_governance.md",
        "docs/vision.md",
        "docs/strategy/product-architecture.md",
        "docs/strategy/positioning.md",
        "specs/subject-distillation/requirements.md",
        "specs/subject-distillation/design.md",
        "specs/subject-distillation/tasks.md",
        "specs/subject-distillation/traceability.md",
        "specs/subject-distillation/schema.v15.sql",
        "specs/subject-distillation/baseline-manifest.json",
        "specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json",
    ):
        source = ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return destination


def _profile(root: Path) -> dict[str, Any]:
    value = yaml.safe_load((root / PROFILE).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write_profile(root: Path, value: dict[str, Any]) -> None:
    (root / PROFILE).write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _set_nested(value: dict[str, Any], path: tuple[str, str], replacement: Any) -> None:
    section = value[path[0]]
    assert isinstance(section, dict)
    section[path[1]] = replacement


def test_repository_governance_control_plane_is_complete() -> None:
    assert validate() == []


def test_validator_fails_closed_when_contract_is_missing(tmp_path: Path) -> None:
    root = _copy_control_plane(tmp_path)
    (root / "AGENT_OPERATING_CONTRACT.md").unlink()
    errors = validate(root)
    assert "missing-or-unsafe:AGENT_OPERATING_CONTRACT.md" in errors
    assert "invalid-profile:missing-source:AGENT_OPERATING_CONTRACT.md" in errors


def test_agent_bootstrap_rejects_missing_contract_pointer(tmp_path: Path) -> None:
    root = _copy_control_plane(tmp_path)
    path = root / "AGENTS.md"
    text = path.read_text(encoding="utf-8").replace(
        "AGENT_OPERATING_CONTRACT.md",
        "missing-operating-contract.md",
    )
    path.write_text(text, encoding="utf-8")
    assert (
        "invalid-agent-bootstrap:missing:AGENT_OPERATING_CONTRACT.md"
        in validate(root)
    )


def test_agent_manifest_rejects_governance_pointer_drift(tmp_path: Path) -> None:
    root = _copy_control_plane(tmp_path)
    path = root / "agent_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["governance"]["profile"] = "docs/governance/missing.yaml"
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    errors = validate(root)
    assert "invalid-agent-manifest:governance" in errors
    assert "invalid-agent-manifest:sources-of-truth" not in errors


def test_governance_claim_rejects_owned_path_drift(tmp_path: Path) -> None:
    root = _copy_control_plane(tmp_path)
    path = root / "docs/governance/work-claims/WP-GOV-001.yaml"
    claim = yaml.safe_load(path.read_text(encoding="utf-8"))
    claim["owned_paths"].remove("tests/test_agent_governance_bootstrap.py")
    path.write_text(
        yaml.safe_dump(claim, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    assert "invalid-governance-claim:owned-paths" in validate(root)


def test_profile_keeps_namespaced_risk_and_memory_layers_distinct() -> None:
    profile = _profile(ROOT)
    assert profile["risk_namespace"] == "risk:"
    assert profile["memory_namespace"] == "memory:"
    assert profile["risk_authority"] == {
        "risk:L0": "autonomous",
        "risk:L1": "autonomous_within_approved_sdd_or_mission",
        "risk:L2": "owner_decision_package_required",
        "risk:L3": "operation_specific_owner_approval_required",
    }


@pytest.mark.parametrize(
    ("path", "replacement", "expected_error"),
    [
        (
            ("risk_authority", "risk:L2"),
            "autonomous",
            "invalid-profile:risk-authority",
        ),
        (
            ("risk_authority", "risk:L3"),
            "autonomous",
            "invalid-profile:risk-authority",
        ),
        (
            ("approval_budget_per_milestone", "risk:L0"),
            1,
            "invalid-profile:approval-budget",
        ),
        (
            ("merge_gate", "require_independent_review"),
            False,
            "invalid-profile:merge-gate",
        ),
        (
            ("merge_gate", "require_post_merge_workflow_side_effect_review"),
            False,
            "invalid-profile:merge-gate",
        ),
        (
            ("production_boundary", "public_site_deploy"),
            "risk:L1",
            "invalid-profile:production-boundary",
        ),
        (
            ("staging_boundary", "live_private_customer_data"),
            "allowed",
            "invalid-profile:staging-boundary",
        ),
        (
            ("staging_boundary", "require_verified_rollback"),
            False,
            "invalid-profile:staging-boundary",
        ),
        (
            (
                "subject_authorization_boundary",
                "agent_hash_review_or_ci_is_authority",
            ),
            True,
            "invalid-profile:subject-authorization-boundary",
        ),
    ],
)
def test_security_and_authority_profile_mutations_fail_closed(
    tmp_path: Path,
    path: tuple[str, str],
    replacement: Any,
    expected_error: str,
) -> None:
    root = _copy_control_plane(tmp_path)
    profile = _profile(root)
    _set_nested(profile, path, replacement)
    _write_profile(root, profile)
    assert expected_error in validate(root)


def test_auto_pages_trigger_requires_explicit_l3_classification(
    tmp_path: Path,
) -> None:
    root = _copy_control_plane(tmp_path)
    profile = _profile(root)
    profile["production_boundary"]["public_site_deploy"] = "risk:L1"
    _write_profile(root, profile)
    assert "invalid-pages:auto-publication-unclassified" in validate(root)


def test_issue_template_rejects_ambiguous_bare_risk_options(tmp_path: Path) -> None:
    root = _copy_control_plane(tmp_path)
    path = root / ".github/ISSUE_TEMPLATE/work_package.yml"
    issue = yaml.safe_load(path.read_text(encoding="utf-8"))
    risk = next(item for item in issue["body"] if item["id"] == "risk")
    risk["attributes"]["options"] = ["L0", "L1", "L2", "L3"]
    path.write_text(
        yaml.safe_dump(issue, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    errors = validate(root)
    assert "invalid-issue-template:risk-options" in errors
    assert any(error.startswith("invalid-risk-namespace:") for error in errors)


def test_work_claim_rejects_ambiguous_bare_risk_label(tmp_path: Path) -> None:
    root = _copy_control_plane(tmp_path)
    path = root / "docs/governance/WORK_CLAIMS.md"
    text = path.read_text(encoding="utf-8").replace("risk:L0", "L0", 1)
    path.write_text(text, encoding="utf-8")
    assert any(
        error.startswith("invalid-risk-namespace:docs/governance/WORK_CLAIMS.md")
        for error in validate(root)
    )


def test_contract_rejects_removal_of_subject_human_trust_root(
    tmp_path: Path,
) -> None:
    root = _copy_control_plane(tmp_path)
    path = root / "AGENT_OPERATING_CONTRACT.md"
    text = path.read_text(encoding="utf-8").replace(
        "Subject Distillation's exact owner instruction",
        "Subject Distillation internal instruction",
    )
    path.write_text(text, encoding="utf-8")
    assert any(
        error.startswith("invalid-contract:missing:Subject Distillation")
        for error in validate(root)
    )


def test_pr_template_rejects_safety_gate_removal(tmp_path: Path) -> None:
    root = _copy_control_plane(tmp_path)
    path = root / ".github/PULL_REQUEST_TEMPLATE.md"
    text = path.read_text(encoding="utf-8").replace(
        "Acceptance criteria and security checks were not reduced",
        "Checks passed",
    )
    path.write_text(text, encoding="utf-8")
    assert any(
        error.startswith("invalid-pr-template:missing:Acceptance criteria")
        for error in validate(root)
    )
