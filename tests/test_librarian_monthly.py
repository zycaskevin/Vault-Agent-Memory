"""DL-8 monthly deep cleanup report-only tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrails_lite.guardrails_db import GuardrailsDB
from guardrails_lite.librarian_monthly import build_monthly_deep_cleanup_report, write_monthly_deep_cleanup_markdown, write_monthly_deep_cleanup_report


def test_monthly_deep_cleanup_report_is_report_only_and_prioritizes_cleanup(tmp_path):
    db_path = tmp_path / "guardrails.db"
    raw_dir = tmp_path / "raw"
    compiled_dir = tmp_path / "compiled"
    raw_dir.mkdir()
    compiled_dir.mkdir()
    secret = "sk-test-should-not-leak"

    with GuardrailsDB(db_path) as db:
        first = db.add_knowledge("Duplicate Monthly", f"body {secret}", source="missing-one.md")
        second = db.add_knowledge(" duplicate monthly ", f"body {secret}", source="missing-two.md")
        db.update_convergence(first, "partial", 0.2)
        db.update_freshness(second, 0.1, last_verified="2020-01-01T00:00:00+00:00")

    report = build_monthly_deep_cleanup_report(
        db_path=db_path,
        raw_dir=raw_dir,
        compiled_dir=compiled_dir,
        month="2026-05",
        generated_at="2026-05-24T09:00:00+08:00",
        top_n=3,
    )
    serialized = json.dumps(report, ensure_ascii=False)

    assert report["schema"] == "guardrails.librarian.monthly.v1"
    assert report["report_only"] is True
    assert report["destructive_merge"] is False
    assert report["remote_overwrite"] is False
    assert report["auto_promote"] is False
    assert report["month"] == "2026-05"
    assert report["counts"]["knowledge_rows"] == 2
    assert report["counts"]["review_items"] >= 4
    assert len(report["top_cleanup_priorities"]) == 3
    assert report["top_cleanup_priorities"][0]["recommended_action"].startswith("review_") or report["top_cleanup_priorities"][0]["recommended_action"] == "repair_provenance"
    assert "trend_metrics" in report
    assert report["trend_metrics"]["mode"] == "baseline_current_snapshot"
    assert secret not in serialized
    assert "content_raw" not in serialized
    assert not any("delete" in item["recommended_action"] or "merge_now" in item["recommended_action"] for item in report["top_cleanup_priorities"])


def test_monthly_deep_cleanup_cli_writes_json_and_markdown(tmp_path):
    db_path = tmp_path / "guardrails.db"
    raw_dir = tmp_path / "raw"
    compiled_dir = tmp_path / "compiled"
    output = tmp_path / "monthly.json"
    markdown = tmp_path / "monthly.md"
    raw_dir.mkdir()
    compiled_dir.mkdir()
    with GuardrailsDB(db_path) as db:
        db.add_knowledge("Monthly CLI Row", "body", source="missing-cli.md")

    env = os.environ.copy()
    repo_root = Path(__file__).parent.parent
    env["PYTHONPATH"] = str(repo_root) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "guardrails_lite.guardrails_cli",
            "librarian",
            "monthly",
            "--db-path",
            str(db_path),
            "--raw-dir",
            str(raw_dir),
            "--compiled-dir",
            str(compiled_dir),
            "--month",
            "2026-05",
            "--output",
            str(output),
            "--markdown",
            str(markdown),
        ],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "report_only=true" in result.stdout
    assert output.exists()
    assert markdown.exists()
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["schema"] == "guardrails.librarian.monthly.v1"
    assert report["report_only"] is True
    assert "# Guardrails Librarian Monthly Deep Cleanup" in markdown.read_text(encoding="utf-8")


def test_monthly_deep_cleanup_writers_round_trip(tmp_path):
    report = {
        "schema": "guardrails.librarian.monthly.v1",
        "report_only": True,
        "auto_promote": False,
        "destructive_merge": False,
        "remote_overwrite": False,
        "month": "2026-05",
        "generated_at": "2026-05-24T09:00:00+08:00",
        "counts": {"knowledge_rows": 0, "review_items": 0, "by_issue_type": {}},
        "trend_metrics": {"mode": "baseline_current_snapshot"},
        "top_cleanup_priorities": [],
        "operating_manual": ["Review only."],
    }
    json_path = tmp_path / "monthly.json"
    md_path = tmp_path / "monthly.md"

    write_monthly_deep_cleanup_report(json_path, report)
    write_monthly_deep_cleanup_markdown(md_path, report)

    assert json.loads(json_path.read_text(encoding="utf-8"))["report_only"] is True
    assert "Review only." in md_path.read_text(encoding="utf-8")
