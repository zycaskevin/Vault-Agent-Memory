from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
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


def test_vam002_rollback_is_executable_and_fail_closed_under_optimized_python() -> None:
    rollback = (
        ROOT / "DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION" / "rollback.md"
    ).read_text(encoding="utf-8")
    fields = dict(
        re.findall(
            r"^(rollback_version|target|command|verify):[ \t]*(.+)$",
            rollback,
            flags=re.MULTILINE,
        )
    )
    assert fields["rollback_version"] == "1.0"
    assert all(fields[name].strip() for name in ("target", "command", "verify"))

    guarded_block = rollback.split("## Guarded preparation command", 1)[1].split(
        "## Reversible steps", 1
    )[0]
    assert "assert " not in guarded_block
    for required in (
        "sddgov evidence verify \"$VAM002_ROLLBACK_DEP\" --strict",
        "gh pr view 500",
        "git rev-list --parents",
        "git ls-remote --exit-code origin refs/heads/main",
        "git fetch --no-tags origin +refs/heads/main:refs/remotes/origin/main",
        "git rev-parse origin/main",
        "sddgov merge digest",
        "sddgov merge gate-digest",
        "approval_consumed",
        "git revert --no-commit -m 1",
        "DEP-VAM-002-BUILDER-LOCAL-GREEN-PATH",
        "DEP-VAM-002-CODERABBIT-CURRENT-HEAD-REMEDIATION",
        "DEP-VAM-002-CODERABBIT-FINAL-REMEDIATION",
        "DEP-VAM-002-FULL-SUITE-COMPATIBILITY",
        "DEP-VAM-002-INDEPENDENT-REVIEW-REMEDIATION",
        "DEP-VAM-002-PUBLIC-READ-SENSITIVITY",
        "DEP-VAM-002-AUDIT-DESCENDANT-ROLLBACK-GUARD",
        "DEP-VAM-002-CODERABBIT-REPLACEMENT-REVIEW-REMEDIATION",
        "DEP-VAM-002-CODERABBIT-FINAL14-REMEDIATION",
        "evidence/DEP-VAM-002-CODERABBIT-THREAD-CLOSURE",
        "tests/test_access_policy.py",
        "vault/governance_read_guard.py",
    ):
        assert required in guarded_block
    assert rollback.count("git status --porcelain=v1 --untracked-files=all") >= 3

    snippets = re.findall(r"python -c '([^']+)'", guarded_block)
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
    assert all("VAM-001" not in path and "VAM-003" not in path for path in expected_paths)
    assert "tests/test_vault_boundary_freeze.py" in expected_paths
    invalid_paths = subprocess.run(
        [sys.executable, "-O", "-c", allowlist_snippet],
        input=b"docs/issues/VAM-003-l0-bootstrap-boundary.md\0",
        check=False,
        capture_output=True,
    )
    valid_paths = subprocess.run(
        [sys.executable, "-O", "-c", allowlist_snippet],
        input=("\0".join(expected_paths) + "\0").encode(),
        check=False,
        capture_output=True,
    )
    assert invalid_paths.returncode != 0
    assert valid_paths.returncode == 0


def test_vam002_review_rollback_keeps_pr_number_as_plain_text() -> None:
    rollback = (
        ROOT / "DEP-VAM-002-INDEPENDENT-REVIEW-REMEDIATION" / "rollback.md"
    ).read_text(encoding="utf-8")
    assert not any(line.startswith("#500") for line in rollback.splitlines())
    assert "PR #500 procedure" in " ".join(rollback.split())


def test_vam002_replacement_review_findings_have_current_reproducible_records() -> None:
    initial_reproduction = (
        ROOT / "evidence/DEP-VAM-002-MEMORY-CHANGE-ENVELOPE/reproduction.md"
    ).read_text(encoding="utf-8")
    final_dep = ROOT / "DEP-VAM-002-CODERABBIT-FINAL-REMEDIATION"
    final_root_cause = (final_dep / "root-cause-hypothesis.md").read_text(
        encoding="utf-8"
    )
    final_green = (
        final_dep / "shareable/artifacts/terminal--final-review-green.txt"
    ).read_text(encoding="utf-8")
    final_rollback = (final_dep / "rollback.md").read_text(encoding="utf-8")
    normalized_final_rollback = " ".join(final_rollback.split())
    public_dep = ROOT / "DEP-VAM-002-PUBLIC-READ-SENSITIVITY"
    public_reproduction = (public_dep / "reproduction.md").read_text(encoding="utf-8")
    public_rollback = (public_dep / "rollback.md").read_text(encoding="utf-8")
    independent_reproduction = (
        ROOT / "DEP-VAM-002-INDEPENDENT-REVIEW-REMEDIATION/reproduction.md"
    ).read_text(encoding="utf-8")
    builder_verification = (
        ROOT / "DEP-VAM-002-BUILDER-LOCAL-GREEN-PATH/verification.md"
    ).read_text(encoding="utf-8")
    historical_dep = ROOT / "evidence/DEP-VAM-002-CODERABBIT-REMEDIATION"
    historical_manifest = json.loads(
        (historical_dep / "manifest.json").read_text(encoding="utf-8")
    )
    historical_report = json.loads(
        (historical_dep / "redaction-report.json").read_text(encoding="utf-8")
    )
    historical_verification = (historical_dep / "verification.md").read_text(
        encoding="utf-8"
    )
    sequential_rollback = (
        ROOT / "DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md"
    ).read_text(encoding="utf-8")
    closure_rollback = (
        ROOT / "evidence/DEP-VAM-002-CODERABBIT-THREAD-CLOSURE/rollback.md"
    ).read_text(encoding="utf-8")
    normalized_closure_rollback = " ".join(closure_rollback.split())
    spec = (ROOT / "docs/specs/vam-002-memory-change-envelope.md").read_text(
        encoding="utf-8"
    )

    failures: list[str] = []
    if "proves only that `vault.memory_change_envelope` was absent" not in initial_reproduction:
        failures.append("F01_initial_red_scope")
    if "does not independently prove the provider contract" not in initial_reproduction:
        failures.append("F01_provider_claim_disposition")
    if "has not completed" in final_root_cause:
        failures.append("F02_stale_local_green_claim")
    for required in (
        "c004c04cd1c1ed471ba39d6d4ad0f5e565dfea5a",
        "446 identity-isolated Subject nodes",
        "2970 passed, 10 skipped, 1 warning",
    ):
        if required not in final_root_cause:
            failures.append(f"F02_missing_{required[:12]}")

    focused_line = next(
        (line for line in final_green.splitlines() if line.startswith("focused_command=")),
        "",
    )
    if not focused_line or " plus " in focused_line:
        failures.append("F03_non_executable_focused_command")
    for node in (
        "test_memory_change_http_errors_use_non_success_status_and_openapi_contract",
        "test_memory_api_all_read_facades_reject_invalid_sensitivity_before_dispatch",
        "test_gateway_preserves_opaque_memory_reference_for_provider_validation",
        "test_gateway_memory_api_facade_is_candidate_first_and_metadata_only",
        "test_vam002_rollback_is_executable_and_fail_closed_under_optimized_python",
        "test_vam002_final_review_records_keep_red_and_green_semantics_distinct",
    ):
        if node not in focused_line:
            failures.append(f"F03_missing_{node}")

    if "remediation-only commit" not in normalized_final_rollback:
        failures.append("F04_remediation_rollback_scope")
    if "does not remove the VAM-002 implementation" not in normalized_final_rollback:
        failures.append("F04_product_preservation")
    if "/tmp/" in public_reproduction or "python -m pytest -q" not in public_reproduction:
        failures.append("F05_nonportable_python")
    if "sole executable implementation rollback" not in public_rollback:
        failures.append("F06_rollback_authority")
    if "DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md" not in public_rollback:
        failures.append("F06_rollback_link")

    for node in (
        "test_invalid_max_sensitivity_fails_closed_for_changes_and_revision_reads",
        "test_audit_reference_is_advisory_and_not_part_of_the_row_revision_contract",
        "test_memory_change_http_errors_use_non_success_status_and_openapi_contract",
    ):
        if node not in independent_reproduction:
            failures.append(f"F07_missing_{node}")
    if "Minimal RED patch" not in independent_reproduction:
        failures.append("F07_missing_patch_description")

    for required in (
        "Authoritative final proof candidate",
        "1a346913563f5437b7815f655393f0eee5a0da52",
        "1429",
        "2967 passed, 10 skipped, and one existing warning",
    ):
        if required not in builder_verification:
            failures.append(f"F08_missing_{required[:12]}")
    if "1,407" in builder_verification:
        failures.append("F08_stale_mode_count")

    follow_up_path = "shareable/artifacts/terminal--follow-up-green.txt"
    follow_up_entries = [
        item for item in historical_manifest["shareable"]
        if item["path"] == follow_up_path
    ]
    if len(follow_up_entries) != 1:
        failures.append("F09_follow_up_manifest")
    else:
        artifact = historical_dep / follow_up_path
        if not artifact.is_file():
            failures.append("F09_follow_up_artifact")
        elif hashlib.sha256(artifact.read_bytes()).hexdigest() != follow_up_entries[0]["sha256"]:
            failures.append("F09_follow_up_hash")
    if not any(item.get("output") == "terminal--follow-up-green.txt" for item in historical_report["files"]):
        failures.append("F09_follow_up_redaction_provenance")
    if (
        "sddgov evidence verify evidence/DEP-VAM-002-CODERABBIT-REMEDIATION --strict"
        not in historical_verification
        or "Strict result: PASS" not in historical_verification
    ):
        failures.append("F10_strict_final_head_proof")

    if 'git merge-base --is-ancestor "$reviewed_head" "$merge_oid^2"' not in sequential_rollback:
        failures.append("F11_reviewed_head_ancestry")
    if 'git diff --name-only "$reviewed_head" "$merge_oid^2"' not in sequential_rollback:
        failures.append("F11_missing_audit_only_diff")
    for audit_path in (
        ":(exclude).sddgov/merge-gate.json",
        ":(exclude).sddgov/reviews/REV-VAM-002.json",
    ):
        if audit_path not in sequential_rollback:
            failures.append(f"F11_missing_{audit_path.rsplit('/', 1)[-1]}")
    if 'test "$reviewed_head" = "$(git rev-parse "$merge_oid^2")"' in sequential_rollback:
        failures.append("F11_exact_parent_rejects_audit_descendants")
    if "fresh exact owner authorization" not in normalized_closure_rollback:
        failures.append("F12_missing_rerun_authorization")
    if "DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md" not in closure_rollback:
        failures.append("F12_missing_authoritative_rollback")
    if "`agent_id_required`" not in spec.split("## HTTP mapping", 1)[1]:
        failures.append("F13_agent_http_mapping")

    assert not failures, "unclosed replacement-review findings: " + ", ".join(failures)


def test_vam002_current_head_coderabbit_findings_have_current_records() -> None:
    """Keep current-head review corrections executable without rewriting raw evidence."""
    remediation = ROOT / "DEP-VAM-002-CODERABBIT-2026-08-26-REMEDIATION"
    canonical = (
        ROOT / "DEP-VAM-002-CODERABBIT-FINAL14-REMEDIATION/finding-dispositions.md"
    ).read_text(encoding="utf-8")
    final_summary = json.loads(
        (
            ROOT / "DEP-VAM-002-CODERABBIT-FINAL14-REMEDIATION/summary.yaml"
        ).read_text(encoding="utf-8")
    )
    final_scope = (
        ROOT / "DEP-VAM-002-CODERABBIT-FINAL14-REMEDIATION/fix-scope.md"
    ).read_text(encoding="utf-8")
    final_rollback = (
        ROOT / "DEP-VAM-002-CODERABBIT-FINAL14-REMEDIATION/rollback.md"
    ).read_text(encoding="utf-8")
    compatibility_rollback = (
        ROOT / "DEP-VAM-002-FULL-SUITE-COMPATIBILITY/rollback.md"
    ).read_text(encoding="utf-8")
    compatibility_reproduction = (
        ROOT / "DEP-VAM-002-FULL-SUITE-COMPATIBILITY/reproduction.md"
    ).read_text(encoding="utf-8")
    replacement_reproduction = (
        ROOT / "DEP-VAM-002-CODERABBIT-REPLACEMENT-REVIEW-REMEDIATION/reproduction.md"
    ).read_text(encoding="utf-8")
    builder_regression = (
        ROOT / "DEP-VAM-002-BUILDER-LOCAL-GREEN-PATH/regression-evidence.md"
    ).read_text(encoding="utf-8")
    sequential_rollback = (
        ROOT / "DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md"
    ).read_text(encoding="utf-8")
    remediation_scope = (remediation / "fix-scope.md").read_text(encoding="utf-8")

    for item in range(1, 15):
        assert f"{item}." in canonical
    assert "finding-dispositions.md" in final_summary["actual_behavior"]
    assert "f0a8273`" not in final_scope
    assert "1a346913..." not in final_scope
    assert "git diff --cached --check" in final_rollback
    assert "git status --ignored=matching --porcelain=v1" in final_rollback
    for node in (
        "test_strict_guard_fails_closed_for_unknown_scope_and_sensitivity",
        "test_gateway_memory_api_facade_is_candidate_first_and_metadata_only",
    ):
        assert node in compatibility_rollback
    assert "7a64938bdc1e5aa483db013e4de4c8e78952fa20" in compatibility_reproduction
    assert "1a346913563f5437b7815f655393f0eee5a0da52" in compatibility_reproduction
    assert "$PROJECT_VENV/bin/python" in replacement_reproduction
    assert 'pytest.__version__ == "9.1.1"' in builder_regression
    assert '"$SDDGOV_RUNTIME/bin/sddgov" ci local-gate .' in builder_regression
    assert builder_regression.count("ci local-gate .") == 1
    assert "git diff --cached --check" in sequential_rollback
    assert "git status --ignored=matching --porcelain=v1" in sequential_rollback
    assert "Historical evidence must not be rewritten without its raw source." in remediation_scope


def test_vam002_final_review_records_keep_red_and_green_semantics_distinct() -> None:
    current_head_dep = ROOT / "DEP-VAM-002-CODERABBIT-CURRENT-HEAD-REMEDIATION"
    fix_scope = (current_head_dep / "fix-scope.md").read_text(encoding="utf-8")
    rollback = (current_head_dep / "rollback.md").read_text(encoding="utf-8")
    compatibility = (
        ROOT / "DEP-VAM-002-FULL-SUITE-COMPATIBILITY" / "regression-evidence.md"
    ).read_text(encoding="utf-8")
    normalized_fix_scope = " ".join(fix_scope.split())
    normalized_rollback = " ".join(rollback.split())
    normalized_compatibility = " ".join(compatibility.split())

    assert "two implementation defects" in normalized_fix_scope
    assert "six test, evidence, or documentation defects" in normalized_fix_scope
    assert "expected RED" in normalized_rollback
    assert "expected to exit nonzero" in normalized_rollback
    assert "Every Green command must exit zero" in normalized_rollback
    assert "full column-projected snapshot" in normalized_compatibility
    assert "final active-row count" not in normalized_compatibility


def test_vam002_final14_review_dispositions_are_executable_and_truthful() -> None:
    independent = ROOT / "DEP-VAM-002-INDEPENDENT-REVIEW-REMEDIATION"
    historical = ROOT / "evidence/DEP-VAM-002-CODERABBIT-REMEDIATION"
    replacement = ROOT / "DEP-VAM-002-CODERABBIT-REPLACEMENT-REVIEW-REMEDIATION"
    compatibility = ROOT / "DEP-VAM-002-FULL-SUITE-COMPATIBILITY"
    builder_path = ROOT / "DEP-VAM-002-BUILDER-LOCAL-GREEN-PATH"
    final = ROOT / "DEP-VAM-002-CODERABBIT-FINAL-REMEDIATION"
    sequential = ROOT / "DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION"
    closure = ROOT / "evidence/DEP-VAM-002-CODERABBIT-THREAD-CLOSURE"

    closure_verification = (closure / "verification.md").read_text(encoding="utf-8")
    assert "preflight subset" in closure_verification
    assert "must not be added to the full-suite total" in closure_verification

    independent_verification = (independent / "verification.md").read_text(
        encoding="utf-8"
    )
    assert "not an instruction to bind today's gate back" in " ".join(
        independent_verification.split()
    )
    independent_reproduction = (independent / "reproduction.md").read_text(
        encoding="utf-8"
    )
    assert 'env PYTHONPATH=. "$VAULT_TEST_PYTHON" -m pytest -q' in independent_reproduction
    assert "focused three-node RED selection" in independent_reproduction

    historical_verification = (historical / "verification.md").read_text(
        encoding="utf-8"
    )
    normalized_historical = " ".join(historical_verification.split())
    assert "not authoritative chronological evidence" in normalized_historical
    assert "no timestamp is retroactively invented" in normalized_historical

    replacement_rollback = (replacement / "rollback.md").read_text(encoding="utf-8")
    normalized_replacement = " ".join(replacement_rollback.split())
    assert "run the two successor regressions" in normalized_replacement
    assert "do not name or execute removed nodes afterward" in normalized_replacement

    compatibility_rollback = (compatibility / "rollback.md").read_text(
        encoding="utf-8"
    )
    assert "rollback_ref: 1a346913563f5437b7815f655393f0eee5a0da52" in (
        compatibility_rollback
    )
    assert "git revert --no-commit 1a346913563f5437b7815f655393f0eee5a0da52" in (
        compatibility_rollback
    )
    compatibility_reproduction = (compatibility / "reproduction.md").read_text(
        encoding="utf-8"
    )
    assert 'env PYTHONPATH=. "$VAULT_TEST_PYTHON" -m pytest -q' in (
        compatibility_reproduction
    )

    builder_verification = (builder_path / "verification.md").read_text(
        encoding="utf-8"
    )
    for stage in ("983c4803", "7a64938b", "1a346913"):
        assert stage in builder_verification
    assert "not to an overall Local Green PASS" in " ".join(
        builder_verification.split()
    )
    builder_regression = (builder_path / "regression-evidence.md").read_text(
        encoding="utf-8"
    )
    assert 'VAM002_PINNED_PATH="$VAULT_PYTHON_SHIM:$SDDGOV_RUNTIME/bin:' in (
        builder_regression
    )
    assert "..." not in builder_regression

    current_rollback = (
        ROOT / "DEP-VAM-002-CODERABBIT-CURRENT-HEAD-REMEDIATION/rollback.md"
    ).read_text(encoding="utf-8")
    assert "expected RED" in current_rollback
    assert "Separately run these rollback-safe Green commands" in current_rollback

    final_verification = (final / "verification.md").read_text(encoding="utf-8")
    normalized_final = " ".join(final_verification.split())
    assert "missing or empty `agent_id`" in normalized_final
    assert "HTTP 400 rather than HTTP 200" in normalized_final

    sequential_rollback = (sequential / "rollback.md").read_text(encoding="utf-8")
    assert "git ls-remote --exit-code origin refs/heads/main" in sequential_rollback
    assert (
        "git fetch --no-tags origin +refs/heads/main:refs/remotes/origin/main"
        in sequential_rollback
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


def test_vam003_redaction_reports_bind_manifest_and_shareable_bytes() -> None:
    reports = sorted(ROOT.glob("DEP-VAM-003-*/redaction-report.json"))

    assert reports
    for report_path in reports:
        dep = report_path.parent
        manifest = json.loads((dep / "manifest.json").read_text(encoding="utf-8"))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        raw_hashes = {record["sha256"] for record in manifest["raw"]}
        shareable_by_name = {
            Path(record["path"]).name: record for record in manifest["shareable"]
        }

        for record in report["files"]:
            output = shareable_by_name[record["output"]]
            artifact = dep / output["path"]

            assert record["source_sha256"] in raw_hashes, report_path
            assert record["output_sha256"] == output["sha256"], report_path
            assert record["output_sha256"] == hashlib.sha256(
                artifact.read_bytes()
            ).hexdigest(), artifact


def test_shareable_redaction_proof_does_not_claim_its_green_is_pending() -> None:
    dep = ROOT / "DEP-VAM-003-SHAREABLE-PATH-REDACTION"
    summary = json.loads((dep / "summary.yaml").read_text(encoding="utf-8"))
    verification = (dep / "verification.md").read_text(encoding="utf-8")

    assert summary["workflow"]["phase"] == "proof"
    assert "still requires complete Builder Local Green" not in verification
    assert "Local Green is enforced separately by the merge gate" in verification
