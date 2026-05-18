"""B7 report-only queue export tests.

These tests intentionally exercise only deterministic local metadata and verify
that B7 never emits raw knowledge content or executable promote/merge actions.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrails_lite.guardrails_db import GuardrailsDB


BANNED_ACTION_TOKENS = ("promote", "merge", "write")


def _actions(report: dict) -> list[str]:
    return [str(item.get("recommended_action", "")) for item in report.get("items", [])]


def _issue_types(report: dict) -> set[str]:
    return {str(item.get("issue_type", "")) for item in report.get("items", [])}


def test_b7_report_detects_duplicates_and_review_only_actions(tmp_path):
    from guardrails_lite.b7_report import build_b7_report

    db_path = tmp_path / "guardrails.db"
    raw_dir = tmp_path / "raw"
    compiled_dir = tmp_path / "compiled"
    raw_dir.mkdir()
    compiled_dir.mkdir()

    with GuardrailsDB(db_path) as db:
        first_id = db.add_knowledge("Duplicate Title", "same duplicate body", source="dup-one.md")
        second_id = db.add_knowledge(" duplicate   title ", "same duplicate body", source="dup-two.md")

    report = build_b7_report(
        db_path=db_path,
        raw_dir=raw_dir,
        compiled_dir=compiled_dir,
    )

    assert report["report_only"] is True
    assert report["auto_promote"] is False
    assert report["destructive_merge"] is False

    issue_types = _issue_types(report)
    assert "duplicate_title" in issue_types
    assert "duplicate_content_hash" in issue_types

    duplicate_items = [
        item for item in report["items"] if item["issue_type"] in {"duplicate_title", "duplicate_content_hash"}
    ]
    assert duplicate_items
    assert all({first_id, second_id}.issubset(set(item["knowledge_ids"])) for item in duplicate_items)
    assert all(item["recommended_action"] == "review_duplicate" for item in duplicate_items)
    assert not any(token in action for action in _actions(report) for token in BANNED_ACTION_TOKENS)


def test_b7_report_detects_convergence_freshness_and_provenance_gaps_without_raw_content(tmp_path):
    from guardrails_lite.b7_report import build_b7_report

    db_path = tmp_path / "guardrails.db"
    raw_dir = tmp_path / "raw"
    compiled_dir = tmp_path / "compiled"
    raw_dir.mkdir()
    compiled_dir.mkdir()
    fake_secret = "sk-test-secret-do-not-export"

    with GuardrailsDB(db_path) as db:
        kid = db.add_knowledge(
            "Needs Review",
            f"Operational note contains {fake_secret}",
            layer="L3",
            category="technique",
            source="missing-source.md",
        )
        db.update_convergence(kid, "partial", 0.2)
        db.update_freshness(kid, 0.1, last_verified="2020-01-01T00:00:00+00:00")

    report = build_b7_report(
        db_path=db_path,
        raw_dir=raw_dir,
        compiled_dir=compiled_dir,
        convergence_threshold=0.8,
        freshness_threshold=0.5,
    )
    serialized = json.dumps(report, ensure_ascii=False)

    assert fake_secret not in serialized
    assert "content_raw" not in serialized
    assert "Operational note" not in serialized

    issue_types = _issue_types(report)
    assert "low_convergence" in issue_types
    assert "stale_freshness" in issue_types
    assert "provenance_gap" in issue_types

    provenance = [item for item in report["items"] if item["issue_type"] == "provenance_gap"]
    assert provenance
    assert provenance[0]["knowledge_id"] == kid
    assert provenance[0]["recommended_action"] == "repair_provenance"
    assert provenance[0]["source_refs"]
    assert not any(token in action for action in _actions(report) for token in BANNED_ACTION_TOKENS)


def test_b7_report_cli_writes_json(tmp_path):
    db_path = tmp_path / "guardrails.db"
    raw_dir = tmp_path / "raw"
    compiled_dir = tmp_path / "compiled"
    output = tmp_path / "report.json"
    raw_dir.mkdir()
    compiled_dir.mkdir()

    with GuardrailsDB(db_path) as db:
        db.add_knowledge("CLI Report Row", "body", source="missing-cli.md")

    env = os.environ.copy()
    repo_root = Path(__file__).parent.parent
    env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "guardrails_lite.guardrails_cli",
            "b7",
            "report",
            "--db-path",
            str(db_path),
            "--raw-dir",
            str(raw_dir),
            "--compiled-dir",
            str(compiled_dir),
            "--output",
            str(output),
        ],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert output.exists()
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["report_only"] is True
    assert report["auto_promote"] is False
    assert report["destructive_merge"] is False
    assert isinstance(report["items"], list)
