"""Cron-ready daily Dream review script tests for DL-5."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrails_lite.dream_queue import create_candidate
from guardrails_lite.guardrails_db import GuardrailsDB

SCRIPT = Path(__file__).parent.parent / "scripts" / "dream_daily_review.py"


def _candidate(**overrides):
    candidate = {
        "source_type": "manual",
        "source_agent": "nancy",
        "source_session_id": "session-daily-review",
        "source_channel": "cli",
        "source_refs": [{"kind": "file", "path": "/tmp/daily-review.md"}],
        "proposed_title": "Daily Review Candidate",
        "summary": "A safe summary that must not appear in cron stdout.",
        "content_draft": "# Daily Review Candidate\n\nUseful but raw draft body.",
        "category": "workflow",
        "tags": ["guardrails", "dream"],
        "privacy_status": "clear",
        "dedupe_status": "unique",
        "recommended_action": "promote",
    }
    candidate.update(overrides)
    return candidate


def _run_script(project_dir: Path, runtime_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--project-dir",
            str(project_dir),
            "--runtime-dir",
            str(runtime_dir),
            *extra,
        ],
        cwd=project_dir,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )


def test_daily_review_script_writes_local_artifacts_and_no_agent_stdout(tmp_path):
    project_dir = tmp_path / "project"
    runtime_dir = tmp_path / "runtime"
    project_dir.mkdir()
    (project_dir / "raw").mkdir()
    (project_dir / "compiled").mkdir()
    db_path = project_dir / "guardrails.db"
    with GuardrailsDB(db_path) as db:
        assert db.conn is not None
        create_candidate(
            db.conn,
            _candidate(
                candidate_id="dream_daily_promote",
                created_at="2026-05-24T01:00:00+00:00",
                proposed_title="Safe Daily Candidate",
            ),
        )
        before = [dict(row) for row in db.conn.execute("SELECT * FROM knowledge_candidates ORDER BY candidate_id")]

    result = _run_script(project_dir, runtime_dir, "--date", "2026-05-24", "--limit", "0")

    assert result.returncode == 0, result.stderr
    assert "Guardrails Dream Curator — Daily Review" in result.stdout
    assert "Candidates: 1" in result.stdout
    assert "report_only=true" in result.stdout
    assert "auto_promote=false" in result.stdout
    assert "formal_knowledge_written=false" in result.stdout
    assert "raw_written=false" in result.stdout
    assert "sync_invoked=false" in result.stdout
    assert "MEDIA:" in result.stdout
    assert "safe summary" not in result.stdout.lower()
    assert result.stderr == ""

    json_path = runtime_dir / "dream-review" / "2026-05-24" / "dream_review_2026-05-24.json"
    markdown_path = runtime_dir / "dream-review" / "2026-05-24" / "dream_review_2026-05-24.md"
    triage_path = runtime_dir / "dream-review" / "2026-05-24" / "dream_triage_packet_2026-05-24.json"
    dashboard_path = runtime_dir / "dream-review" / "2026-05-24" / "dashboard_aggregate_2026-05-24.json"
    history_path = runtime_dir / "dream-review" / "history" / "dashboard_history.jsonl"
    latest_path = runtime_dir / "dream-review" / "latest.json"
    assert json_path.exists()
    assert markdown_path.exists()
    assert triage_path.exists()
    assert dashboard_path.exists()
    assert history_path.exists()
    assert latest_path.exists()
    assert f"MEDIA:{markdown_path.resolve()}" in result.stdout

    report = json.loads(json_path.read_text(encoding="utf-8"))
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    assert report["report_only"] is True
    assert report["auto_promote"] is False
    assert report["formal_knowledge_written"] is False
    assert report["raw_written"] is False
    assert report["sync_invoked"] is False
    assert report["counts"]["candidates"] == 1
    assert latest["date"] == "2026-05-24"
    assert latest["json_path"] == str(json_path.resolve())
    assert latest["markdown_path"] == str(markdown_path.resolve())
    assert latest["triage_packet_path"] == str(triage_path.resolve())
    assert latest["dashboard_aggregate_path"] == str(dashboard_path.resolve())
    assert latest["history_path"] == str(history_path.resolve())
    assert latest["report_only"] is True
    triage_packet = json.loads(triage_path.read_text(encoding="utf-8"))
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    assert triage_packet["schema"] == "guardrails.dream.local_model_triage.v1"
    assert triage_packet["prompt_only"] is True
    assert triage_packet["network_invoked"] is False
    assert dashboard["schema"] == "guardrails.dashboard.aggregate.v1"
    assert dashboard["count_only"] is True
    history_records = [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines()]
    assert len(history_records) == 1
    assert history_records[0]["schema"] == "guardrails.report_history.snapshot.v1"
    assert history_records[0]["snapshot_date"] == "2026-05-24"
    assert history_records[0]["count_only"] is True

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        after = [dict(row) for row in conn.execute("SELECT * FROM knowledge_candidates ORDER BY candidate_id")]
        formal_count = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
    assert after == before
    assert formal_count == 0
    assert list((project_dir / "raw").iterdir()) == []


def test_daily_review_script_is_silent_when_no_candidates_but_keeps_local_artifacts(tmp_path):
    project_dir = tmp_path / "project"
    runtime_dir = tmp_path / "runtime"
    project_dir.mkdir()
    (project_dir / "raw").mkdir()
    (project_dir / "compiled").mkdir()
    with GuardrailsDB(project_dir / "guardrails.db"):
        pass

    result = _run_script(project_dir, runtime_dir, "--date", "2026-05-24", "--limit", "0")

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert result.stderr == ""
    json_path = runtime_dir / "dream-review" / "2026-05-24" / "dream_review_2026-05-24.json"
    markdown_path = runtime_dir / "dream-review" / "2026-05-24" / "dream_review_2026-05-24.md"
    triage_path = runtime_dir / "dream-review" / "2026-05-24" / "dream_triage_packet_2026-05-24.json"
    dashboard_path = runtime_dir / "dream-review" / "2026-05-24" / "dashboard_aggregate_2026-05-24.json"
    assert json_path.exists()
    assert markdown_path.exists()
    assert triage_path.exists()
    assert dashboard_path.exists()
    assert json.loads(json_path.read_text(encoding="utf-8"))["counts"]["candidates"] == 0


def test_daily_review_script_rejects_runtime_under_raw_or_compiled(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "raw").mkdir()
    (project_dir / "compiled").mkdir()
    with GuardrailsDB(project_dir / "guardrails.db"):
        pass

    result = _run_script(project_dir, project_dir / "raw" / "reports", "--date", "2026-05-24")

    assert result.returncode == 2
    assert "runtime-dir must not be under project raw/ or compiled/" in result.stderr
    assert result.stdout == ""
