from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "docs/decision_records/2026-08-21-extract-subject-distillation.md"
STATUS = ROOT / "docs/subject-distillation.md"
DRAFTS = ROOT / "docs/issue_comment_drafts/VAM-001-subject-distillation-extraction.md"
PROGRESS = ROOT / "specs/subject-distillation/implementation-progress.json"
DELIVERY_ROLLBACK = ROOT / "DEP-VAM-001-DELIVERY-GATE/rollback.md"


def _h2_section(text: str, heading: str) -> str:
    """Return one real, non-fenced Markdown H2 section."""
    headings: list[tuple[str, int]] = []
    fence_character: str | None = None
    fence_length = 0
    offset = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if fence_character is None:
            opening = re.match(r" {0,3}(`{3,}|~{3,})", content)
            if opening:
                token = opening.group(1)
                fence_character = token[0]
                fence_length = len(token)
            elif content.startswith("## "):
                headings.append((content.removeprefix("## "), offset))
        elif re.fullmatch(
            rf" {{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*",
            content,
        ):
            fence_character = None
            fence_length = 0
        offset += len(line)

    matches = [index for index, (name, _offset) in enumerate(headings) if name == heading]
    assert len(matches) == 1
    index = matches[0]
    start = headings[index][1]
    end = headings[index + 1][1] if index + 1 < len(headings) else len(text)
    return text[start:end]


def test_h2_section_ignores_prose_and_fenced_examples() -> None:
    sample = "Prose mentions ## Target\n```md\n## Target\n```\n## Target\nbody\n## Next\n"
    assert _h2_section(sample, "Target") == "## Target\nbody\n"


def test_extraction_adr_records_the_complete_boundary_decision() -> None:
    text = ADR.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    for heading in (
        "## Context",
        "## Decision",
        "## Why Subject crossed the Memory boundary",
        "## What Vault retains",
        "## What Digital Life Identity owns",
        "## Preserved T-001 through T-004 origin",
        "## Why T-005 through T-033 are not continued",
        "## Issue disposition",
        "## Origin",
        "## Compatibility",
        "## Rollback",
        "## Future integration contract",
    ):
        assert heading in text

    assert "291d5595c9cb2208a6b74206acbba35a883eb918" in text
    assert "PR #494" in text
    dli_ownership = " ".join(_h2_section(text, "What Digital Life Identity owns").split())
    assert "Digital Life Identity owns Subject Core application semantics" in dli_ownership
    assert "purpose-scoped Context Packs" in dli_ownership

    integration = " ".join(_h2_section(text, "Future integration contract").split())
    assert "The following are forbidden boundaries:" in integration
    assert "Vault imports `digital_life_identity`." in integration
    assert "Digital Life Identity reads `vault.db` or imports VaultDB internals." in integration
    assert "Either repository creates cross-database foreign keys." in integration
    assert (
        "Vault adds identity-, personality-, or subject-model-specific endpoints."
        in integration
    )
    assert "The Vault adapter lives in the Digital Life Identity repository" in normalized
    assert "Vault treats DLI payload semantics as opaque application data" in normalized
    assert "action ID `VAM-001-ISSUE-DISPOSITION`" in normalized
    assert "Authorization came from the controlling owner instruction" in normalized
    assert "No signed L3 receipt is reusable" in normalized


def test_subject_status_marks_runtime_as_extracted_without_rewriting_history() -> None:
    text = STATUS.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "preserved origin package" in normalized
    assert "Digital Life Identity Runtime" in normalized
    assert "Runtime is not implemented" in text
    assert "T-001 through T-004 remain completed" in normalized
    assert "T-005 through T-033 remain pending" in normalized

    progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    assert all(progress["tasks"][f"T-{number:03d}"] == "COMPLETED" for number in range(1, 5))
    assert all(progress["tasks"][f"T-{number:03d}"] == "PENDING" for number in range(5, 34))


def test_issue_disposition_record_is_bounded_and_exact() -> None:
    text = DRAFTS.read_text(encoding="utf-8")
    introduction = text[: text.index("## Issue #410")]
    sections = {
        issue: _h2_section(text, f"Issue #{issue}")
        for issue in (410, 495, 496, 497)
    }
    expected_states = {
        410: "Keep open until the DLI Sprint 1 repository is available",
        495: "Close as superseded, not completed",
        496: "Close as not planned",
        497: "Close as superseded by the architecture decision",
    }
    for issue, expected_state in expected_states.items():
        assert expected_state in sections[issue]
        assert all(
            expected_state not in section
            for other_issue, section in sections.items()
            if other_issue != issue
        )

    assert "Draft comment for use after the repository has a stable public location" in sections[410]
    assert "Do not post this draft until `<DLI_REPOSITORY_URL>` is real" in sections[410]
    assert "DISPOSITION RECORD — bounded GitHub mutation completed" in introduction
    assert "#495, #496, and #497 were posted and those issues were closed" in introduction
    assert "Issue #410 remains open and its text below remains an unposted future draft" in introduction
    assert "No additional Issue mutation is authorized" in introduction


def test_delivery_rollback_binds_local_main_head_before_revert() -> None:
    text = DELIVERY_ROLLBACK.read_text(encoding="utf-8")
    command = next(
        line.removeprefix("command: ")
        for line in text.splitlines()
        if line.startswith("command: ")
    )
    ordered_guards = (
        'merge_oid="$(gh pr view 498',
        "test \"$(git rev-list --parents -n 1 \"$merge_oid\" | awk '{print NF - 1}')\" -eq 2",
        'git merge-base --is-ancestor ec107d134fc491cc48d44f5a01b919da30c2f913 "$merge_oid^2"',
        '! git merge-base --is-ancestor ec107d134fc491cc48d44f5a01b919da30c2f913 "$merge_oid^1"',
        'test "$(git branch --show-current)" = main',
        'test "$(git rev-parse HEAD)" = "$merge_oid"',
        'approval_json="$(sddgov autonomy evaluate "$VAM001_ROLLBACK_REQUEST" --path .)"',
        "printf '%s\\n' \"$approval_json\" | python -c",
        "git revert --no-commit ec107d134fc491cc48d44f5a01b919da30c2f913",
        "git restore --source=HEAD --staged --worktree -- DEP-VAM-001-DELIVERY-GATE",
        'test "$(git diff --cached --name-only)" = docs/subject-distillation.md',
        'test -z "$(git diff --name-only)"',
    )
    assert all(command.count(fragment) == 1 for fragment in ordered_guards)
    assert [command.index(fragment) for fragment in ordered_guards] == sorted(
        command.index(fragment) for fragment in ordered_guards
    )
