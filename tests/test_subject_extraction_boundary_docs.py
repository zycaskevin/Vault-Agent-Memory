from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "docs/decision_records/2026-08-21-extract-subject-distillation.md"
STATUS = ROOT / "docs/subject-distillation.md"
DRAFTS = ROOT / "docs/issue_comment_drafts/VAM-001-subject-distillation-extraction.md"
PROGRESS = ROOT / "specs/subject-distillation/implementation-progress.json"


def test_extraction_adr_records_the_complete_boundary_decision() -> None:
    text = ADR.read_text(encoding="utf-8")
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
    assert "Vault imports `digital_life_identity`" in text
    assert "Digital Life Identity reads `vault.db`" in text


def test_subject_status_marks_runtime_as_extracted_without_rewriting_history() -> None:
    text = STATUS.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "preserved origin package" in normalized
    assert "Digital Life Identity Runtime" in normalized
    assert "T-001 through T-004 remain completed" in normalized
    assert "T-005 through T-033 remain pending" in normalized

    progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    assert all(progress["tasks"][f"T-{number:03d}"] == "COMPLETED" for number in range(1, 5))
    assert all(progress["tasks"][f"T-{number:03d}"] == "PENDING" for number in range(5, 34))


def test_issue_comment_drafts_are_bounded_and_not_execution_receipts() -> None:
    text = DRAFTS.read_text(encoding="utf-8")
    for issue in (410, 495, 496, 497):
        assert f"## Issue #{issue}" in text

    assert "Keep open until the DLI Sprint 1 repository is available" in text
    assert "Close as superseded, not completed" in text
    assert "Close as not planned" in text
    assert "Close as superseded by the architecture decision" in text
    assert "DRAFT ONLY — no GitHub mutation performed" in text
