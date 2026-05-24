"""DL-3 safe explicit local-only promotion tests for Dream/Librarian."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrails_lite.dream_promote import promote_candidate
from guardrails_lite.dream_queue import create_candidate, list_candidates
from guardrails_lite.guardrails_db import GuardrailsDB


def _candidate(**overrides):
    candidate = {
        "candidate_id": "dream_20260523_promote",
        "source_type": "manual",
        "source_agent": "nancy",
        "source_session_id": "session-promote",
        "source_channel": "cli",
        "source_refs": [{"kind": "file", "path": "/tmp/promote.md"}],
        "proposed_title": "Dream Promote Candidate",
        "summary": "Promotion summary",
        "content_draft": "# Dream Promote Candidate\n\n- Promotion body with durable shared knowledge.",
        "category": "workflow",
        "tags": ["guardrails", "dream", "promote"],
        "classification": "shared_knowledge",
        "privacy_status": "clear",
        "dedupe_status": "unique",
        "status": "approved",
        "recommended_action": "promote",
        "trust_initial": 0.62,
    }
    candidate.update(overrides)
    return candidate


def _knowledge_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) AS c FROM knowledge").fetchone()["c"]


def _raw_snapshot(raw_dir: Path) -> dict[str, str]:
    if not raw_dir.exists():
        return {}
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(raw_dir.glob("*.md"))}


def _frontmatter(raw_text: str) -> dict:
    assert raw_text.startswith("---\n")
    end = raw_text.index("\n---", 4)
    return json.loads(raw_text[4:end])


def test_promote_candidate_success_writes_formal_raw_readback_and_audit(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    sentinel = raw_dir / "sentinel.md"
    sentinel.write_text("original raw content", encoding="utf-8")
    before_raw = _raw_snapshot(raw_dir)

    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        db.add_knowledge("Existing Formal", "Formal body", category="workflow")
        before_count = _knowledge_count(db.conn)
        candidate_id = create_candidate(db.conn, _candidate())

        result = promote_candidate(
            db,
            candidate_id,
            project_dir=tmp_path,
            reviewer="nancy",
            no_sync=True,
            run_compile=False,
            run_map=False,
        )

        after_count = _knowledge_count(db.conn)
        knowledge = db.get_knowledge(result["knowledge_id"])
        promoted = list_candidates(db.conn, status="promoted", limit=10)[0]

    assert result["success"] is True
    assert result["candidate_id"] == candidate_id
    assert result["knowledge_id"] == knowledge["id"]
    assert result["formal_knowledge_written"] is True
    assert result["raw_written"] is True
    assert result["sync_invoked"] is False
    assert result["auto_promote"] is False
    assert result["no_sync"] is True
    assert result["compile_invoked"] is False
    assert result["map_invoked"] is False
    assert result["readback_verified"] is True

    assert after_count == before_count + 1
    assert knowledge["title"] == "Dream Promote Candidate"
    assert knowledge["summary"] == "Promotion summary"
    assert knowledge["content_raw"] == "# Dream Promote Candidate\n\n- Promotion body with durable shared knowledge."
    assert knowledge["category"] == "workflow"
    assert knowledge["tags"] == "guardrails,dream,promote"
    assert knowledge["trust"] == pytest.approx(0.62)
    assert knowledge["source"] == result["raw_path"]

    raw_path = tmp_path / result["raw_path"]
    assert raw_path.exists()
    assert raw_path.parent == raw_dir
    assert "/" not in raw_path.name
    assert ".." not in raw_path.name
    assert sentinel.read_text(encoding="utf-8") == before_raw["sentinel.md"]
    raw_text = raw_path.read_text(encoding="utf-8")
    metadata = _frontmatter(raw_text)
    assert metadata["title"] == "Dream Promote Candidate"
    assert metadata["layer"] == "L3"
    assert metadata["category"] == "workflow"
    assert metadata["tags"] == ["guardrails", "dream", "promote"]
    assert metadata["trust"] == pytest.approx(0.62)
    assert metadata["summary"] == "Promotion summary"
    assert metadata["source_candidate_id"] == candidate_id
    assert metadata["source_agent"] == "nancy"
    assert metadata["source_type"] == "manual"
    assert metadata["created"]
    assert raw_text.endswith("\n")

    assert promoted["candidate_id"] == candidate_id
    assert promoted["reviewer"] == "nancy"
    assert promoted["reviewed_at"]
    assert promoted["decision_reason"] == "promoted to formal knowledge"
    assert promoted["audit_log"][-1]["event"] == "promoted"
    assert promoted["audit_log"][-1]["knowledge_id"] == result["knowledge_id"]
    assert promoted["audit_log"][-1]["raw_path"] == result["raw_path"]
    assert promoted["audit_log"][-1]["reviewer"] == "nancy"
    assert promoted["audit_log"][-1]["no_sync"] is True


@pytest.mark.parametrize(
    ("overrides", "kwargs", "message"),
    [
        ({"status": "ready_for_review"}, {}, "status=approved"),
        ({"privacy_status": "unknown"}, {}, "privacy_status=clear"),
        ({"classification": "private_draft"}, {}, "classification=shared_knowledge"),
        ({"dedupe_status": "duplicate"}, {}, "dedupe_status=duplicate"),
        ({"dedupe_status": "near_duplicate"}, {}, "dedupe_status=near_duplicate"),
        ({"dedupe_status": "conflict"}, {}, "dedupe_status=conflict"),
        ({"content_draft": "# Secret\n\nsk-proj-abcdefghijklmnopqrstuvwxyz1234567890"}, {}, "final privacy scan"),
        ({}, {"reviewer": ""}, "reviewer is required"),
        ({}, {"no_sync": False}, "sync is not supported"),
    ],
)
def test_promote_candidate_safety_failures_leave_formal_raw_and_status_unchanged(
    tmp_path, overrides, kwargs, message
):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    sentinel = raw_dir / "sentinel.md"
    sentinel.write_text("original raw content", encoding="utf-8")
    before_raw = _raw_snapshot(raw_dir)

    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        db.add_knowledge("Existing Formal", "Formal body", category="workflow")
        before_count = _knowledge_count(db.conn)
        candidate_id = create_candidate(db.conn, _candidate(**overrides))
        before_status = db.conn.execute(
            "SELECT status FROM knowledge_candidates WHERE candidate_id=?", (candidate_id,)
        ).fetchone()["status"]

        call_kwargs = {
            "project_dir": tmp_path,
            "reviewer": "nancy",
            "no_sync": True,
            "run_compile": False,
            "run_map": False,
        }
        call_kwargs.update(kwargs)
        with pytest.raises(ValueError, match=message):
            promote_candidate(db, candidate_id, **call_kwargs)

        after_count = _knowledge_count(db.conn)
        after_status = db.conn.execute(
            "SELECT status FROM knowledge_candidates WHERE candidate_id=?", (candidate_id,)
        ).fetchone()["status"]

    assert after_count == before_count
    assert _raw_snapshot(raw_dir) == before_raw
    assert after_status == before_status


def test_promote_default_compile_map_handles_trailing_newline_without_partial_failure(tmp_path):
    """Default promote must not fail after writing raw/formal/status when compile normalizes body."""
    (tmp_path / "raw").mkdir()
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        candidate_id = create_candidate(
            db.conn,
            _candidate(
                candidate_id="dream_20260523_promote_compile",
                content_draft="# Dream Promote Candidate\n\n- Body keeps trailing newline.\n",
            ),
        )

        result = promote_candidate(
            db,
            candidate_id,
            project_dir=tmp_path,
            reviewer="nancy",
            no_sync=True,
            run_compile=True,
            run_map=True,
        )

        knowledge = db.get_knowledge(result["knowledge_id"])
        status = db.conn.execute(
            "SELECT status FROM knowledge_candidates WHERE candidate_id=?", (candidate_id,)
        ).fetchone()["status"]
        node_count = db.conn.execute(
            "SELECT COUNT(*) AS c FROM knowledge_nodes WHERE knowledge_id=?",
            (result["knowledge_id"],),
        ).fetchone()["c"]

    assert result["success"] is True
    assert result["compile_invoked"] is True
    assert result["map_invoked"] is True
    assert result["readback_verified"] is True
    assert result["sync_invoked"] is False
    assert status == "promoted"
    assert knowledge["source"] == result["raw_path"]
    assert result["raw_path"].startswith("raw/")
    assert node_count >= 1


def test_promote_default_compile_does_not_stage_or_commit_unrelated_tracked_changes(tmp_path):
    """Dream promote must not let compile's auto-git path stage/commit unrelated files."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, check=True, capture_output=True, text=True)
    before_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    tracked.write_text("after\n", encoding="utf-8")

    (tmp_path / "raw").mkdir()
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        candidate_id = create_candidate(
            db.conn,
            _candidate(
                candidate_id="dream_20260523_promote_no_git_side_effect",
                content_draft="# Dream Promote Candidate\n\n- Body forces compile update and must not touch git.\n",
            ),
        )
        result = promote_candidate(
            db,
            candidate_id,
            project_dir=tmp_path,
            reviewer="nancy",
            no_sync=True,
            run_compile=True,
            run_map=True,
        )

    after_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    tracked_status = subprocess.check_output(
        ["git", "status", "--short", "tracked.txt"], cwd=tmp_path, text=True
    ).rstrip()

    assert result["success"] is True
    assert result["compile_invoked"] is True
    assert result["sync_invoked"] is False
    assert after_head == before_head
    assert tracked_status == " M tracked.txt"


def test_promote_blocks_existing_formal_title_before_raw_or_status_side_effects(tmp_path):
    """A stale/incorrect unique dedupe status must not let compile title-dedupe delete the promoted row."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    sentinel = raw_dir / "sentinel.md"
    sentinel.write_text("original raw content", encoding="utf-8")
    before_raw = _raw_snapshot(raw_dir)

    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        db.add_knowledge("Dream Promote Candidate", "Existing formal body", category="workflow")
        before_count = _knowledge_count(db.conn)
        candidate_id = create_candidate(db.conn, _candidate())

        with pytest.raises(ValueError, match="existing formal knowledge title"):
            promote_candidate(
                db,
                candidate_id,
                project_dir=tmp_path,
                reviewer="nancy",
                no_sync=True,
                run_compile=True,
                run_map=True,
            )

        after_count = _knowledge_count(db.conn)
        after_status = db.conn.execute(
            "SELECT status FROM knowledge_candidates WHERE candidate_id=?", (candidate_id,)
        ).fetchone()["status"]

    assert after_count == before_count
    assert _raw_snapshot(raw_dir) == before_raw
    assert after_status == "approved"


def test_promote_default_compile_ignores_unrelated_raw_with_same_title(tmp_path):
    """Default compile verification must not let an older raw title overwrite the promoted row."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    old_raw = raw_dir / "zzzz.md"
    old_raw.write_text(
        '---\n{"title":"Dream Promote Candidate","category":"workflow","layer":"L3","tags":[],"trust":0.4,"source":"raw/zzzz.md"}\n---\n\n# Old raw\n',
        encoding="utf-8",
    )

    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        candidate_id = create_candidate(db.conn, _candidate())

        result = promote_candidate(
            db,
            candidate_id,
            project_dir=tmp_path,
            reviewer="nancy",
            no_sync=True,
            run_compile=True,
            run_map=True,
        )

        knowledge = db.get_knowledge(result["knowledge_id"])
        count = _knowledge_count(db.conn)
        status = db.conn.execute(
            "SELECT status FROM knowledge_candidates WHERE candidate_id=?", (candidate_id,)
        ).fetchone()["status"]

    assert result["success"] is True
    assert result["readback_verified"] is True
    assert count == 1
    assert status == "promoted"
    assert knowledge["source"] == result["raw_path"]
    assert knowledge["source"] != "raw/zzzz.md"
    assert old_raw.exists()


def test_promote_single_file_compile_does_not_hijack_like_wildcard_source_match(tmp_path):
    """Compiler source lookup must not treat promoted raw filename underscores as SQL LIKE wildcards."""
    (tmp_path / "raw").mkdir()
    candidate_id = "dream_20260523_promote_like"
    promoted_source_file = f"{candidate_id}_Dream_Promote_Candidate.md"
    wildcard_matching_source = f"raw/{promoted_source_file.replace('_', 'X')}"

    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        unrelated_id = db.add_knowledge(
            "Unrelated Formal",
            "Unrelated body must not be overwritten",
            category="workflow",
            source=wildcard_matching_source,
        )
        create_candidate(db.conn, _candidate(candidate_id=candidate_id))

        result = promote_candidate(
            db,
            candidate_id,
            project_dir=tmp_path,
            reviewer="nancy",
            no_sync=True,
            run_compile=True,
            run_map=True,
        )

        unrelated = db.get_knowledge(unrelated_id)
        promoted = db.get_knowledge(result["knowledge_id"])
        count = _knowledge_count(db.conn)

    assert result["success"] is True
    assert count == 2
    assert unrelated["title"] == "Unrelated Formal"
    assert unrelated["source"] == wildcard_matching_source
    assert unrelated["content_raw"] == "Unrelated body must not be overwritten"
    assert promoted["title"] == "Dream Promote Candidate"
    assert promoted["source"] == result["raw_path"]


def test_promote_blocks_existing_formal_source_before_raw_or_status_side_effects(tmp_path):
    """A stale DB source collision must not let single-file compile overwrite another row."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    before_raw = _raw_snapshot(raw_dir)
    candidate_id = "dream_20260523_promote_source"
    source_file = f"{candidate_id}_Dream_Promote_Candidate.md"

    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        unrelated_id = db.add_knowledge(
            "Unrelated Formal",
            "Unrelated body must not be overwritten",
            category="workflow",
            source=source_file,
        )
        before_count = _knowledge_count(db.conn)
        create_candidate(db.conn, _candidate(candidate_id=candidate_id))

        with pytest.raises(ValueError, match="existing formal knowledge source"):
            promote_candidate(
                db,
                candidate_id,
                project_dir=tmp_path,
                reviewer="nancy",
                no_sync=True,
                run_compile=True,
                run_map=True,
            )

        unrelated = db.get_knowledge(unrelated_id)
        after_count = _knowledge_count(db.conn)
        after_status = db.conn.execute(
            "SELECT status FROM knowledge_candidates WHERE candidate_id=?", (candidate_id,)
        ).fetchone()["status"]

    assert after_count == before_count
    assert _raw_snapshot(raw_dir) == before_raw
    assert after_status == "approved"
    assert unrelated["title"] == "Unrelated Formal"
    assert unrelated["source"] == source_file
    assert unrelated["content_raw"] == "Unrelated body must not be overwritten"


def test_dream_promote_cli_outputs_json_safety_flags_and_local_only(tmp_path):
    db_path = tmp_path / "guardrails.db"
    (tmp_path / "raw").mkdir()
    with GuardrailsDB(db_path) as db:
        before_count = _knowledge_count(db.conn)
        create_candidate(db.conn, _candidate(candidate_id="dream_20260523_promote_cli"))

    env = os.environ.copy()
    repo_root = Path(__file__).parent.parent
    env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "guardrails_lite.guardrails_cli",
            "dream",
            "promote",
            "dream_20260523_promote_cli",
            "--reviewer",
            "nancy",
            "--no-sync",
            "--db-path",
            str(db_path),
            "--skip-compile",
            "--skip-map",
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
    assert payload["candidate_id"] == "dream_20260523_promote_cli"
    assert payload["formal_knowledge_written"] is True
    assert payload["raw_written"] is True
    assert payload["sync_invoked"] is False
    assert payload["auto_promote"] is False
    assert payload["no_sync"] is True
    assert payload["compile_invoked"] is False
    assert payload["map_invoked"] is False
    assert payload["readback_verified"] is True

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        assert conn.execute("SELECT COUNT(*) AS c FROM knowledge").fetchone()["c"] == before_count + 1
        row = conn.execute(
            "SELECT * FROM knowledge_candidates WHERE candidate_id=?",
            ("dream_20260523_promote_cli",),
        ).fetchone()
        knowledge = conn.execute("SELECT * FROM knowledge WHERE id=?", (payload["knowledge_id"],)).fetchone()
    finally:
        conn.close()

    assert row["status"] == "promoted"
    assert json.loads(row["audit_log_json"])[-1]["event"] == "promoted"
    assert knowledge["title"] == "Dream Promote Candidate"
    assert knowledge["summary"] == "Promotion summary"
    assert knowledge["source"] == payload["raw_path"]
    assert (tmp_path / payload["raw_path"]).exists()
