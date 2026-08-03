#!/usr/bin/env python3
"""Validate the repository's Human-on-the-loop governance control plane."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "AGENTS.md",
    "agent_manifest.json",
    "AGENT_OPERATING_CONTRACT.md",
    "docs/governance/PROJECT_GOVERNANCE_PROFILE.yaml",
    "docs/governance/CURRENT_STATE.md",
    "docs/governance/SDD_TRACEABILITY.md",
    "docs/governance/PROGRESS_LEDGER.md",
    "docs/governance/DECISION_LOG.md",
    "docs/governance/DEVIATION_LOG.md",
    "docs/governance/WORK_CLAIMS.md",
    "docs/governance/CAPABILITY_MAP.md",
    "docs/governance/DEPENDENCY_GRAPH.md",
    "docs/governance/BOOTSTRAP_REPORT_2026-08-03.md",
    "docs/governance/evidence/BOOTSTRAP-2026-08-03.md",
    "docs/governance/work-claims/WP-GOV-001.yaml",
    "docs/governance/templates/work-package.md",
    "docs/governance/templates/checkpoint.md",
    "docs/governance/templates/decision-package.md",
    "docs/governance/templates/operational-action-package.md",
    "docs/governance/templates/l3-approval.md",
    "docs/governance/templates/milestone-uat.md",
    "docs/adr/README.md",
    "docs/adr/0000-template.md",
    ".github/ISSUE_TEMPLATE/work_package.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/pages.yml",
)
EXPECTED_PROFILE_KEYS = {
    "schema_version",
    "profile",
    "repository",
    "operating_mode",
    "main_branch",
    "source_of_truth",
    "risk_authority",
    "risk_namespace",
    "memory_namespace",
    "preauthorized_actions",
    "approval_budget_per_milestone",
    "checkpoint",
    "merge_gate",
    "production_boundary",
    "staging_boundary",
    "subject_authorization_boundary",
}
EXPECTED_SOURCE_OF_TRUTH = {
    "product": [
        "docs/vision.md",
        "docs/strategy/product-architecture.md",
        "docs/strategy/positioning.md",
    ],
    "repository_governance": [
        "AGENTS.md",
        "AGENT_OPERATING_CONTRACT.md",
        "docs/repo_governance.md",
    ],
    "active_sdd": [
        "specs/subject-distillation/requirements.md",
        "specs/subject-distillation/design.md",
        "specs/subject-distillation/tasks.md",
        "specs/subject-distillation/traceability.md",
        "specs/subject-distillation/schema.v15.sql",
        "specs/subject-distillation/baseline-manifest.json",
        "specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json",
    ],
}
EXPECTED_RISK_AUTHORITY = {
    "risk:L0": "autonomous",
    "risk:L1": "autonomous_within_approved_sdd_or_mission",
    "risk:L2": "owner_decision_package_required",
    "risk:L3": "operation_specific_owner_approval_required",
}
EXPECTED_ACTIONS = [
    "issue_lifecycle",
    "feature_branch",
    "work_claim",
    "repo_code_test_docs_ci_changes",
    "reversible_dependency_updates",
    "targeted_and_regression_verification",
    "commit",
    "feature_branch_push",
    "pull_request",
    "review_and_ci_repair",
    "l0_l1_merge",
    "development_test_staging_deploy",
    "reversible_agent_change_rollback",
]
EXPECTED_APPROVAL_BUDGET = {
    "risk:L0": 0,
    "risk:L1": 0,
    "risk:L2_per_decision": 1,
    "risk:L3_per_operation": 1,
    "milestone_uat": 1,
}
WAITING_TITLES = [
    "ACTION REQUIRED — Decision Package",
    "ACTION REQUIRED — Operational Action Package",
    "ACTION REQUIRED — L3 Approval",
    "ACTION REQUIRED — Milestone UAT",
]
EXPECTED_CHECKPOINT = {
    "default": "informational",
    "waiting_titles": WAITING_TITLES,
}
EXPECTED_MERGE_GATE = {
    "require_exact_scope": True,
    "require_required_ci": True,
    "require_independent_review": True,
    "require_sdd_traceability": True,
    "require_rollback_readiness": True,
    "require_post_merge_workflow_side_effect_review": True,
    "forbid_acceptance_criteria_reduction": True,
    "forbid_safety_check_removal": True,
}
EXPECTED_PRODUCTION_BOUNDARY = {
    "production_deploy": "risk:L3",
    "public_site_deploy": "risk:L3",
    "package_publish_or_release": "risk:L3",
    "store_publish": "risk:L3",
    "destructive_migration": "risk:L3",
    "production_data_mutation": "risk:L3",
    "production_secret_access_or_rotation": "risk:L3",
    "payment_or_subscription_activation": "risk:L3",
    "dns_or_public_domain_change": "risk:L3",
    "protected_branch_force_push": "risk:L3",
    "external_customer_communication": "risk:L3",
}
EXPECTED_STAGING_BOUNDARY = {
    "environment": "pre_existing_approved_non_production",
    "data": "synthetic_or_sanitized_only",
    "live_private_customer_data": "forbidden",
    "new_login_mfa_account_or_credential": "operational_action",
    "new_spend_or_public_exposure": "risk:L2_or_risk:L3",
    "external_customer_communication": "risk:L3",
    "require_verified_rollback": True,
}
EXPECTED_SUBJECT_AUTHORIZATION = {
    "b001_owner_lane_and_exact_base": "required_while_normative",
    "t_task_owner_confirmed_exact_proposal_and_digest": "required_while_normative",
    "agent_hash_review_or_ci_is_authority": False,
}
ISSUE_FIELDS = {
    "why": "Why",
    "product-impact": "Product Impact",
    "sdd": "SDD References",
    "outcome": "Capability Outcome",
    "scope": "Scope",
    "nonscope": "Non-scope",
    "acceptance": "Acceptance Criteria",
    "risk": "Risk Level",
    "verification": "Verification Plan",
    "dependencies": "Dependencies",
    "rollback": "Rollback",
    "done": "Definition of Done",
}
RISK_OPTIONS = ["risk:L0", "risk:L1", "risk:L2", "risk:L3"]
RISK_OUTPUT_FILES = (
    ".github/ISSUE_TEMPLATE/work_package.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "docs/adr/README.md",
    "docs/adr/0000-template.md",
    "docs/governance/BOOTSTRAP_REPORT_2026-08-03.md",
    "docs/governance/CAPABILITY_MAP.md",
    "docs/governance/CURRENT_STATE.md",
    "docs/governance/DECISION_LOG.md",
    "docs/governance/DEVIATION_LOG.md",
    "docs/governance/PROGRESS_LEDGER.md",
    "docs/governance/SDD_TRACEABILITY.md",
    "docs/governance/WORK_CLAIMS.md",
    "docs/governance/templates/decision-package.md",
)
BARE_RISK = re.compile(r"(?<!risk:)\bL[0-3]\b")
EXPECTED_MANIFEST_GOVERNANCE = {
    "mode": "human-on-the-loop",
    "operating_contract": "AGENT_OPERATING_CONTRACT.md",
    "profile": "docs/governance/PROJECT_GOVERNANCE_PROFILE.yaml",
    "risk_namespace": "risk:",
    "memory_namespace": "memory:",
}
EXPECTED_GOVERNANCE_CLAIM_PATHS = [
    ".github/ISSUE_TEMPLATE/work_package.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "AGENTS.md",
    "AGENT_OPERATING_CONTRACT.md",
    "agent_manifest.json",
    "docs/adr/0000-template.md",
    "docs/adr/README.md",
    "docs/governance/BOOTSTRAP_REPORT_2026-08-03.md",
    "docs/governance/CAPABILITY_MAP.md",
    "docs/governance/CURRENT_STATE.md",
    "docs/governance/DECISION_LOG.md",
    "docs/governance/DEPENDENCY_GRAPH.md",
    "docs/governance/DEVIATION_LOG.md",
    "docs/governance/PROGRESS_LEDGER.md",
    "docs/governance/PROJECT_GOVERNANCE_PROFILE.yaml",
    "docs/governance/SDD_TRACEABILITY.md",
    "docs/governance/WORK_CLAIMS.md",
    "docs/governance/evidence/BOOTSTRAP-2026-08-03.md",
    "docs/governance/templates/checkpoint.md",
    "docs/governance/templates/decision-package.md",
    "docs/governance/templates/l3-approval.md",
    "docs/governance/templates/milestone-uat.md",
    "docs/governance/templates/operational-action-package.md",
    "docs/governance/templates/work-package.md",
    "docs/governance/work-claims/WP-GOV-001.yaml",
    "docs/plans/SUBJECT_DISTILLATION_PROGRESS.md",
    "scripts/validate_agent_governance.py",
    "tests/test_agent_governance_bootstrap.py",
]


def _load_yaml(path: Path, kind: str, errors: list[str]) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors.append(f"invalid-{kind}:{type(exc).__name__}")
        return None


def _validate_profile(root: Path, errors: list[str]) -> None:
    path = root / "docs/governance/PROJECT_GOVERNANCE_PROFILE.yaml"
    if not path.is_file():
        return
    profile = _load_yaml(path, "profile", errors)
    if not isinstance(profile, dict):
        errors.append("invalid-profile:root")
        return
    if set(profile) != EXPECTED_PROFILE_KEYS:
        errors.append("invalid-profile:closed-schema")
    scalar_expectations = {
        "schema_version": 1,
        "profile": "sdd-governed-autonomous-agent-development-v1.1",
        "repository": "zycaskevin/Vault-Agent-Memory",
        "operating_mode": "human-on-the-loop",
        "main_branch": "main",
        "risk_namespace": "risk:",
        "memory_namespace": "memory:",
    }
    for key, expected in scalar_expectations.items():
        if profile.get(key) != expected:
            errors.append(f"invalid-profile:{key.replace('_', '-')}")
    exact_sections = {
        "source_of_truth": (EXPECTED_SOURCE_OF_TRUTH, "source-of-truth"),
        "risk_authority": (EXPECTED_RISK_AUTHORITY, "risk-authority"),
        "preauthorized_actions": (EXPECTED_ACTIONS, "preauthorized-actions"),
        "approval_budget_per_milestone": (
            EXPECTED_APPROVAL_BUDGET,
            "approval-budget",
        ),
        "checkpoint": (EXPECTED_CHECKPOINT, "checkpoint"),
        "merge_gate": (EXPECTED_MERGE_GATE, "merge-gate"),
        "production_boundary": (
            EXPECTED_PRODUCTION_BOUNDARY,
            "production-boundary",
        ),
        "staging_boundary": (EXPECTED_STAGING_BOUNDARY, "staging-boundary"),
        "subject_authorization_boundary": (
            EXPECTED_SUBJECT_AUTHORIZATION,
            "subject-authorization-boundary",
        ),
    }
    for key, (expected, error_name) in exact_sections.items():
        if profile.get(key) != expected:
            errors.append(f"invalid-profile:{error_name}")
    for paths in EXPECTED_SOURCE_OF_TRUTH.values():
        for relative in paths:
            if not (root / relative).is_file():
                errors.append(f"invalid-profile:missing-source:{relative}")


def _validate_bootstrap_routing(root: Path, errors: list[str]) -> None:
    agents_path = root / "AGENTS.md"
    if agents_path.is_file():
        text = agents_path.read_text(encoding="utf-8")
        for pointer in (
            "AGENT_OPERATING_CONTRACT.md",
            "docs/governance/PROJECT_GOVERNANCE_PROFILE.yaml",
            "read the operating contract and governance",
        ):
            if pointer not in text:
                errors.append(f"invalid-agent-bootstrap:missing:{pointer}")

    manifest_path = root / "agent_manifest.json"
    if not manifest_path.is_file():
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"invalid-agent-manifest:{type(exc).__name__}")
        return
    if not isinstance(manifest, dict):
        errors.append("invalid-agent-manifest:root")
        return
    if manifest.get("governance") != EXPECTED_MANIFEST_GOVERNANCE:
        errors.append("invalid-agent-manifest:governance")
    sources = manifest.get("agent_sources_of_truth")
    expected_prefix = [
        "AGENTS.md",
        "AGENT_OPERATING_CONTRACT.md",
        "docs/governance/PROJECT_GOVERNANCE_PROFILE.yaml",
    ]
    if not isinstance(sources, list) or sources[:3] != expected_prefix:
        errors.append("invalid-agent-manifest:sources-of-truth")


def _validate_issue_template(root: Path, errors: list[str]) -> None:
    path = root / ".github/ISSUE_TEMPLATE/work_package.yml"
    if not path.is_file():
        return
    issue = _load_yaml(path, "issue-template", errors)
    if not isinstance(issue, dict) or set(issue) != {
        "name",
        "description",
        "title",
        "body",
    }:
        errors.append("invalid-issue-template:closed-schema")
        return
    body = issue.get("body")
    if not isinstance(body, list) or len(body) != len(ISSUE_FIELDS):
        errors.append("invalid-issue-template:body")
        return
    actual: dict[str, dict[str, Any]] = {}
    for item in body:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            errors.append("invalid-issue-template:item")
            continue
        actual[item["id"]] = item
    if set(actual) != set(ISSUE_FIELDS):
        errors.append("invalid-issue-template:fields")
    for field_id, label in ISSUE_FIELDS.items():
        item = actual.get(field_id)
        if not isinstance(item, dict):
            continue
        attributes = item.get("attributes")
        validations = item.get("validations")
        if not isinstance(attributes, dict) or attributes.get("label") != label:
            errors.append(f"invalid-issue-template:label:{field_id}")
        if not isinstance(validations, dict) or validations.get("required") is not True:
            errors.append(f"invalid-issue-template:required:{field_id}")
    risk = actual.get("risk", {}).get("attributes", {})
    if not isinstance(risk, dict) or risk.get("options") != RISK_OPTIONS:
        errors.append("invalid-issue-template:risk-options")


def _validate_governance_claim(root: Path, errors: list[str]) -> None:
    path = root / "docs/governance/work-claims/WP-GOV-001.yaml"
    if not path.is_file():
        return
    claim = _load_yaml(path, "governance-claim", errors)
    expected_scalars = {
        "schema_version": 1,
        "work_package": "WP-GOV-001",
        "issue": 427,
        "owner": "Main Engineering Agent",
        "risk": "risk:L0",
        "base_commit": "cfee9429c64a1dfa86bc14b126666979a6ce2611",
        "state": "CLAIMED",
    }
    if not isinstance(claim, dict) or set(claim) != {
        *expected_scalars,
        "capability_outcome",
        "owned_paths",
    }:
        errors.append("invalid-governance-claim:closed-schema")
        return
    for key, expected in expected_scalars.items():
        if claim.get(key) != expected:
            errors.append(f"invalid-governance-claim:{key.replace('_', '-')}")
    if claim.get("capability_outcome") != (
        "Repository can run auditable Human-on-the-loop delivery without "
        "per-step owner prompts"
    ):
        errors.append("invalid-governance-claim:capability-outcome")
    if claim.get("owned_paths") != EXPECTED_GOVERNANCE_CLAIM_PATHS:
        errors.append("invalid-governance-claim:owned-paths")


def _validate_contract_and_pr(root: Path, errors: list[str]) -> None:
    contract_path = root / "AGENT_OPERATING_CONTRACT.md"
    if contract_path.is_file():
        text = contract_path.read_text(encoding="utf-8")
        required_phrases = (
            "safety, privacy, legal and production protections",
            "the latest explicit repository-owner instruction",
            "approved product contracts and normative SDD",
            "Subject Distillation's exact owner instruction",
            "an Agent-created proposal, hash",
            "Informational checkpoints never require a reply",
            "risk:L0 through risk:L3",
            "memory:L0 through memory:L3",
            "pre-existing approved",
            "synthetic or sanitized data",
            "every post-merge workflow side effect",
            "Completing one Work Package is not a wait state",
        )
        positions: list[int] = []
        for phrase in required_phrases:
            position = text.find(phrase)
            if position < 0:
                errors.append(f"invalid-contract:missing:{phrase}")
            positions.append(position)
        precedence = positions[:3]
        if all(position >= 0 for position in precedence) and precedence != sorted(
            precedence
        ):
            errors.append("invalid-contract:precedence")

    pr_path = root / ".github/PULL_REQUEST_TEMPLATE.md"
    if pr_path.is_file():
        text = pr_path.read_text(encoding="utf-8")
        for phrase in (
            "Capability outcome:",
            "SDD / ADR references:",
            "risk:L0 / risk:L1 / risk:L2 / risk:L3",
            "Non-scope:",
            "Rollback:",
            "Acceptance criteria and security checks were not reduced",
            "Required CI and independent review are green",
        ):
            if phrase not in text:
                errors.append(f"invalid-pr-template:missing:{phrase}")


def _validate_risk_namespace(root: Path, errors: list[str]) -> None:
    for relative in RISK_OUTPUT_FILES:
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        sanitized = text.replace("ACTION REQUIRED — L3 Approval", "")
        match = BARE_RISK.search(sanitized)
        if match:
            errors.append(f"invalid-risk-namespace:{relative}:{match.group(0)}")


def _validate_pages_classification(root: Path, errors: list[str]) -> None:
    path = root / ".github/workflows/pages.yml"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    auto_public = "\n  push:\n" in text or "\n  schedule:\n" in text
    if auto_public:
        profile_path = root / "docs/governance/PROJECT_GOVERNANCE_PROFILE.yaml"
        profile = _load_yaml(profile_path, "profile", errors)
        if (
            not isinstance(profile, dict)
            or profile.get("production_boundary", {}).get("public_site_deploy")
            != "risk:L3"
            or profile.get("merge_gate", {}).get(
                "require_post_merge_workflow_side_effect_review"
            )
            is not True
        ):
            errors.append("invalid-pages:auto-publication-unclassified")


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            errors.append(f"missing-or-unsafe:{relative}")
    _validate_profile(root, errors)
    _validate_bootstrap_routing(root, errors)
    _validate_issue_template(root, errors)
    _validate_governance_claim(root, errors)
    _validate_contract_and_pr(root, errors)
    _validate_risk_namespace(root, errors)
    _validate_pages_classification(root, errors)
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("agent-governance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
