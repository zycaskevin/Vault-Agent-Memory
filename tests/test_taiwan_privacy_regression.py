"""Regression fixtures proving fake Taiwan-looking PII is detected and cannot
silently auto-promote. All values are obviously synthetic. This is NOT medical
compliance; broader clinic privacy profiles require a separate design discussion
(see issue #394 and docs/privacy_regression_fixtures.md).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vault.automation import automation_run
from vault.db import VaultDB
from vault.memory import create_candidate
from vault.privacy import scan_privacy

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "taiwan_privacy_fixtures.json"
_FIXTURES = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
_DETECTION_CASES = [
    case for case in _FIXTURES["cases"] if case.get("expected_finding_types")
]


@pytest.mark.parametrize("case", _DETECTION_CASES, ids=[c["id"] for c in _DETECTION_CASES])
def test_scan_privacy_detects_fake_taiwan_pii(case):
    result = scan_privacy(case["content"])
    assert result["status"] == case["expected_status"]
    finding_types = {finding["type"] for finding in result["findings"]}
    assert set(case["expected_finding_types"]).issubset(finding_types)


def test_scan_privacy_passes_on_non_phone_like_clinic_record():
    """Locks the documented false-negative boundary as a regression."""
    case = next(
        case for case in _FIXTURES["cases"]
        if case["id"] == "clinic_record_non_phone_like_limitation"
    )
    result = scan_privacy(case["content"])
    assert result["status"] == case["expected_status"]
    assert result["findings"] == []


def _init_project(tmp_path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / "raw").mkdir()
    with VaultDB(project / "vault.db") as db:
        db.set_config("embedding_provider", "hash")
    return project


def _write_auto_promote_policy(project: Path) -> None:
    (project / "automation_policy.yaml").write_text(
        "\n".join(
            [
                "mode: balanced",
                "auto_promote_low_risk_candidates: true",
                "auto_promote_max_per_run: 5",
                "auto_promote_min_trust: 0.65",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_candidate_with_fake_taiwan_pii_does_not_auto_promote(tmp_path):
    project = _init_project(tmp_path)
    _write_auto_promote_policy(project)
    pii_content = "聯絡：0987-654-321，身分證 C234567890。"
    with VaultDB(project / "vault.db") as db:
        result = create_candidate(
            db,
            title="Decision: Taiwan PII regression fixture",
            content=(
                "Decision: never auto-promote Taiwan PII. "
                f"Fixture: {pii_content}"
            ),
            reason="Privacy regression guard for issue #394.",
            source="session_capture",
            source_ref="codex:session:taiwan-pii-fixture#L1",
            memory_type="session_lesson",
            category="decision",
            tags="session-capture,privacy,taiwan",
            trust=0.82,
            scope="project",
            sensitivity="low",
        )
        assert result["status"] == "candidate_created"
        assert result["gates"]["privacy"] == "warn"
        candidate_id = result["candidate_id"]
        before_active = db.conn.execute(
            "SELECT COUNT(*) AS n FROM knowledge WHERE status = 'active'"
        ).fetchone()["n"]

    payload = automation_run(
        project, mode="balanced", apply=True, limit=10, write_reports=False
    )

    assert payload["auto_promote"]["enabled"] is True
    assert payload["auto_promote"]["promoted_count"] == 0
    skipped = next(
        item
        for item in payload["auto_promote"]["items"]
        if item["candidate_id"] == candidate_id
    )
    assert skipped["eligible"] is False
    assert "privacy_gate_not_pass:warn" in skipped["reason"]
    with VaultDB(project / "vault.db") as db:
        assert db.get_memory_candidate(candidate_id)["status"] == "candidate"
        after_active = db.conn.execute(
            "SELECT COUNT(*) AS n FROM knowledge WHERE status = 'active'"
        ).fetchone()["n"]
        assert after_active == before_active
