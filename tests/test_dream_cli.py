"""CLI tests for Guardrails Dream DL-1 submit."""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrails_lite.guardrails_db import GuardrailsDB


def test_dream_submit_writes_candidate_only_and_keeps_raw_unchanged(tmp_path):
    db_path = tmp_path / "guardrails.db"
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    sentinel = raw_dir / "sentinel.md"
    sentinel.write_text("original raw content", encoding="utf-8")
    content_file = tmp_path / "candidate.md"
    content_file.write_text("# Candidate\n\nDraft body.", encoding="utf-8")

    with GuardrailsDB(db_path) as db:
        db.add_knowledge("Existing Formal", "Formal body", category="technique")
        formal_count_before = db.conn.execute("SELECT COUNT(*) AS c FROM knowledge").fetchone()["c"]

    raw_before = {p.name: p.read_text(encoding="utf-8") for p in raw_dir.iterdir()}

    env = os.environ.copy()
    repo_root = Path(__file__).parent.parent
    env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "guardrails_lite.guardrails_cli",
            "dream",
            "submit",
            "--title",
            "CLI Dream Candidate",
            "--summary",
            "Candidate summary",
            "--content-file",
            str(content_file),
            "--category",
            "technique",
            "--tags",
            "guardrails,dream",
            "--source-agent",
            "nancy",
            "--source-type",
            "manual",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["candidate_id"].startswith("dream_")
    assert payload["formal_knowledge_written"] is False

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        formal_count_after = conn.execute("SELECT COUNT(*) AS c FROM knowledge").fetchone()["c"]
        candidate = conn.execute(
            "SELECT * FROM knowledge_candidates WHERE candidate_id=?",
            (payload["candidate_id"],),
        ).fetchone()
    finally:
        conn.close()

    assert formal_count_after == formal_count_before
    assert candidate is not None
    assert candidate["proposed_title"] == "CLI Dream Candidate"
    assert json.loads(candidate["tags_json"]) == ["guardrails", "dream"]
    assert candidate["content_draft"] == "# Candidate\n\nDraft body."
    assert {p.name: p.read_text(encoding="utf-8") for p in raw_dir.iterdir()} == raw_before


def test_dream_submit_rejects_invalid_category_choice(tmp_path):
    content_file = tmp_path / "candidate.md"
    content_file.write_text("# Candidate\n\nDraft body.", encoding="utf-8")

    env = os.environ.copy()
    repo_root = Path(__file__).parent.parent
    env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "guardrails_lite.guardrails_cli",
            "dream",
            "submit",
            "--title",
            "CLI Dream Candidate",
            "--summary",
            "Candidate summary",
            "--content-file",
            str(content_file),
            "--category",
            "concept",
            "--tags",
            "guardrails,dream",
            "--source-agent",
            "nancy",
            "--source-type",
            "manual",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 2
    assert "invalid choice" in result.stderr
    assert "concept" in result.stderr


def test_dream_submit_requires_tags(tmp_path):
    content_file = tmp_path / "candidate.md"
    content_file.write_text("# Candidate\n\nDraft body.", encoding="utf-8")

    env = os.environ.copy()
    repo_root = Path(__file__).parent.parent
    env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "guardrails_lite.guardrails_cli",
            "dream",
            "submit",
            "--title",
            "CLI Dream Candidate",
            "--summary",
            "Candidate summary",
            "--content-file",
            str(content_file),
            "--category",
            "technique",
            "--source-agent",
            "nancy",
            "--source-type",
            "manual",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 2
    assert "--tags" in result.stderr
