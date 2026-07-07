import json

from vault.cli import main
from vault.daily_loop import build_daily_loop_report, refresh_daily_loop_report, run_daily_loop
from vault.db import VaultDB
from vault.memory import create_candidate


def _read_json(capsys):
    return json.loads(capsys.readouterr().out)


def _project_with_candidate(tmp_path):
    project = tmp_path / "daily-loop-project"
    project.mkdir()
    with VaultDB(project / "vault.db") as db:
        db.add_knowledge(
            "Daily loop active memory",
            "This reviewed memory should stay active during the default daily loop.",
            category="workflow",
            trust=0.8,
        )
        candidate = create_candidate(
            db,
            title="Daily loop candidate",
            content="Decision: the daily loop should keep new memory candidate-first until review.",
            reason="Exercise daily-loop review cards.",
            source="session_capture",
            source_ref="tests/test_daily_loop.py",
            memory_type="session_lesson",
            category="workflow",
            trust=0.7,
        )
    return project, candidate["candidate_id"]


def test_daily_loop_run_writes_reports_and_stays_candidate_first(tmp_path):
    project, candidate_id = _project_with_candidate(tmp_path)

    payload = run_daily_loop(project, write_report=True, limit=5)

    assert payload["ok"] is True
    assert payload["action"] == "daily-loop-run"
    assert payload["apply"] is False
    assert payload["sync"]["dry_run"] is True
    assert payload["sync"]["operations"]["push_read_copy"]["status"] == "dry_run"
    assert payload["safety"]["candidate_first"] is True
    assert payload["safety"]["hard_delete"] is False
    assert payload["safety"]["includes_raw_candidate_content"] is False
    assert payload["summary"]["pending_candidates"] >= 1
    assert any(card["id"] == candidate_id for card in payload["human_review"]["cards"])
    assert payload["paths"]["json"] == "reports/daily-loop/daily-loop-latest.json"
    assert payload["paths"]["markdown"] == "reports/daily-loop/daily-loop-latest.md"
    assert (project / payload["paths"]["json"]).exists()
    assert (project / payload["paths"]["markdown"]).exists()
    with VaultDB(project / "vault.db") as db:
        active_count = db.conn.execute("SELECT count(*) AS count FROM knowledge WHERE status='active'").fetchone()["count"]
        candidates = db.list_memory_candidates(status=None)
    assert active_count == 1
    assert any(item["id"] == candidate_id for item in candidates)


def test_daily_loop_status_and_report_cli(tmp_path, capsys):
    project, _candidate_id = _project_with_candidate(tmp_path)

    main(["daily-loop", "status", "--project-dir", str(project), "--json"])
    status = _read_json(capsys)
    assert status["action"] == "daily-loop-status"
    assert status["latest_report"]["exists"] is False
    assert status["safety"]["writes_candidates"] is False

    main(["daily-loop", "run", "--project-dir", str(project), "--write-report", "--json"])
    run = _read_json(capsys)
    assert run["action"] == "daily-loop-run"
    assert run["paths"]["json"] == "reports/daily-loop/daily-loop-latest.json"

    main(["daily-loop", "report", "--project-dir", str(project), "--write-report", "--json"])
    report = _read_json(capsys)
    assert report["ok"] is True
    assert report["action"] == "daily-loop-report"
    assert report["paths"]["markdown"] == "reports/daily-loop/daily-loop-latest.md"
    assert "Vault Daily Loop" in (project / report["paths"]["markdown"]).read_text(encoding="utf-8")


def test_daily_loop_refresh_writes_report_without_new_candidates(tmp_path):
    project, candidate_id = _project_with_candidate(tmp_path)
    with VaultDB(project / "vault.db") as db:
        before = db.conn.execute("SELECT count(*) AS count FROM memory_candidates").fetchone()["count"]

    payload = refresh_daily_loop_report(project, write_report=True, limit=5)

    assert payload["ok"] is True
    assert payload["action"] == "daily-loop-refresh"
    assert payload["safety"]["writes_candidates"] is False
    assert payload["sync"]["source"] == "remote-status"
    assert payload["sync"]["dry_run"] is False
    assert payload["memory_ingestion"]["pipeline"]["status"] == "skipped"
    assert payload["memory_ingestion"]["reflection"]["write_candidates"] is False
    assert payload["summary"]["pipeline_candidates_written"] == 0
    assert payload["summary"]["reflection_candidates_written"] == 0
    assert payload["summary"]["vector_index_status"] == "empty"
    assert payload["vector_index"]["status"] == "empty"
    assert payload["vector_index"]["remote_read_enabled"] is False
    assert payload["vector_index"]["plan"]["dry_run"] is True
    assert payload["vector_index"]["paths"]["status_json"] == "reports/vector-index/status-latest.json"
    assert payload["vector_index"]["paths"]["plan_json"] == "reports/vector-index/plan-latest.json"
    assert payload["artifacts"]["vector_index_status"] == "reports/vector-index/status-latest.json"
    assert payload["artifacts"]["vector_index_plan"] == "reports/vector-index/plan-latest.json"
    assert any(card["id"] == candidate_id for card in payload["human_review"]["cards"])
    assert payload["paths"]["json"] == "reports/daily-loop/daily-loop-latest.json"
    assert (project / payload["paths"]["json"]).exists()
    assert (project / "reports/vector-index/status-latest.json").exists()
    assert (project / "reports/vector-index/plan-latest.md").exists()
    assert (
        "This reviewed memory should stay active"
        not in (project / "reports/vector-index/plan-latest.json").read_text(encoding="utf-8")
    )
    assert (
        "This reviewed memory should stay active"
        not in (project / payload["paths"]["markdown"]).read_text(encoding="utf-8")
    )
    with VaultDB(project / "vault.db") as db:
        after = db.conn.execute("SELECT count(*) AS count FROM memory_candidates").fetchone()["count"]
    assert after == before


def test_daily_loop_report_refresh_cli_is_read_only(tmp_path, capsys):
    project, _candidate_id = _project_with_candidate(tmp_path)
    with VaultDB(project / "vault.db") as db:
        before = db.conn.execute("SELECT count(*) AS count FROM memory_candidates").fetchone()["count"]

    main(["daily-loop", "report", "--refresh", "--project-dir", str(project), "--write-report", "--json"])
    payload = _read_json(capsys)

    assert payload["action"] == "daily-loop-refresh"
    assert payload["safety"]["writes_candidates"] is False
    assert payload["vector_index"]["paths"]["plan_markdown"] == "reports/vector-index/plan-latest.md"
    assert payload["paths"]["markdown"] == "reports/daily-loop/daily-loop-latest.md"
    with VaultDB(project / "vault.db") as db:
        after = db.conn.execute("SELECT count(*) AS count FROM memory_candidates").fetchone()["count"]
    assert after == before


def test_daily_loop_report_blocks_when_latest_missing(tmp_path):
    project = tmp_path / "empty"
    project.mkdir()

    payload = build_daily_loop_report(project)

    assert payload["ok"] is False
    assert payload["status"] == "missing"
    assert "daily-loop run" in payload["next_action"]
