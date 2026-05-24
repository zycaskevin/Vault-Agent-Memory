"""DL-2.5 review decision workflow tests for Dream/Librarian."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrails_lite.dream_queue import create_candidate, decide_candidate, list_candidates
from guardrails_lite.guardrails_db import GuardrailsDB


def _candidate(**overrides):
    candidate = {
        "source_type": "manual",
        "source_agent": "nancy",
        "source_session_id": "session-decision",
        "source_channel": "cli",
        "source_refs": [{"kind": "file", "path": "/tmp/decision.md"}],
        "proposed_title": "Dream Decision Candidate",
        "summary": "A candidate summary",
        "content_draft": "# Dream Decision Candidate\n\nDraft body.",
        "category": "workflow",
        "tags": ["guardrails", "dream"],
        "privacy_status": "clear",
        "dedupe_status": "unique",
        "status": "ready_for_review",
    }
    candidate.update(overrides)
    return candidate


@pytest.mark.parametrize(
    ("decision", "expected_status"),
    [
        ("approved", "approved"),
        ("merge_suggested", "merge_suggested"),
        ("discarded", "discarded"),
        ("blocked", "blocked"),
        ("ask_arthur", "ready_for_review"),
    ],
)
def test_decide_candidate_updates_status_audit_and_never_writes_formal_or_raw(tmp_path, decision, expected_status):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    sentinel = raw_dir / "sentinel.md"
    sentinel.write_text("original raw content", encoding="utf-8")
    db_path = tmp_path / "guardrails.db"

    with GuardrailsDB(db_path) as db:
        db.add_knowledge("Existing Formal", "Formal body", category="workflow")
        formal_count_before = db.conn.execute("SELECT COUNT(*) AS c FROM knowledge").fetchone()["c"]
        candidate_id = create_candidate(
            db.conn,
            _candidate(candidate_id=f"dream_decision_{decision}", recommended_action="review"),
        )

        result = decide_candidate(
            db.conn,
            candidate_id,
            decision=decision,
            reason="reviewed by Arthur and Nancy",
            reviewer="nancy",
        )
        formal_count_after = db.conn.execute("SELECT COUNT(*) AS c FROM knowledge").fetchone()["c"]
        row = list_candidates(db.conn, status=expected_status, limit=10)[0]

    assert result["success"] is True
    assert result["candidate_id"] == candidate_id
    assert result["decision"] == decision
    assert result["status"] == expected_status
    assert result["formal_knowledge_written"] is False
    assert result["raw_written"] is False
    assert result["sync_invoked"] is False
    assert formal_count_after == formal_count_before
    assert sentinel.read_text(encoding="utf-8") == "original raw content"
    assert row["decision_reason"] == "reviewed by Arthur and Nancy"
    assert row["reviewer"] == "nancy"
    assert row["reviewed_at"]
    assert row["audit_log"][-1]["event"] == "review_decision"
    assert row["audit_log"][-1]["decision"] == decision
    assert row["audit_log"][-1]["status"] == expected_status
    if decision == "ask_arthur":
        assert row["recommended_action"] == "ask_arthur"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"decision": "publish", "reason": "valid reason", "reviewer": "nancy"}, "decision"),
        ({"decision": "approved", "reason": "", "reviewer": "nancy"}, "reason is required"),
        ({"decision": "approved", "reason": "valid reason", "reviewer": ""}, "reviewer is required"),
    ],
)
def test_decide_candidate_rejects_invalid_decision_empty_reason_and_empty_reviewer(tmp_path, kwargs, message):
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        candidate_id = create_candidate(db.conn, _candidate(candidate_id="dream_decision_invalid"))
        with pytest.raises(ValueError, match=message):
            decide_candidate(db.conn, candidate_id, **kwargs)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"privacy_status": "unknown"}, "privacy_status=clear"),
        ({"privacy_status": "redact_required"}, "privacy_status=clear"),
        ({"privacy_status": "private_only"}, "privacy_status=clear"),
        ({"privacy_status": "blocked"}, "privacy_status=clear"),
        ({"classification": "private_draft"}, "classification=shared_knowledge"),
        ({"classification": "no_write"}, "classification=shared_knowledge"),
        ({"dedupe_status": "duplicate"}, "dedupe_status=duplicate"),
        ({"dedupe_status": "near_duplicate"}, "dedupe_status=near_duplicate"),
        ({"dedupe_status": "conflict"}, "dedupe_status=conflict"),
        ({"status": "blocked"}, "cannot change terminal status blocked to approved"),
        ({"status": "discarded"}, "cannot change terminal status discarded to approved"),
        ({"status": "promoted"}, "cannot change terminal status promoted to approved"),
    ],
)
def test_decide_candidate_rejects_unsafe_approval_paths(tmp_path, overrides, message):
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        candidate = _candidate(candidate_id="dream_decision_unsafe_approval")
        candidate.update(overrides)
        candidate_id = create_candidate(db.conn, candidate)

        with pytest.raises(ValueError, match=message):
            decide_candidate(
                db.conn,
                candidate_id,
                decision="approved",
                reason="approve unsafe path",
                reviewer="nancy",
            )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"privacy_status": "blocked"}, "privacy_status blocked cannot be merge_suggested"),
        ({"privacy_status": "private_only"}, "privacy_status private_only cannot be merge_suggested"),
        ({"classification": "no_write"}, "classification no_write cannot be merge_suggested"),
        ({"status": "blocked"}, "cannot change terminal status blocked to merge_suggested"),
        ({"status": "discarded"}, "cannot change terminal status discarded to merge_suggested"),
        ({"status": "promoted"}, "cannot change terminal status promoted to merge_suggested"),
    ],
)
def test_decide_candidate_rejects_unsafe_merge_paths(tmp_path, overrides, message):
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        candidate = _candidate(candidate_id="dream_decision_unsafe_merge")
        candidate.update(overrides)
        candidate_id = create_candidate(db.conn, candidate)

        with pytest.raises(ValueError, match=message):
            decide_candidate(
                db.conn,
                candidate_id,
                decision="merge_suggested",
                reason="merge unsafe path",
                reviewer="nancy",
            )


@pytest.mark.parametrize(
    ("decision", "expected_status"),
    [
        ("blocked", "blocked"),
        ("discarded", "discarded"),
        ("ask_arthur", "ready_for_review"),
    ],
)
def test_decide_candidate_allows_safe_resolutions_for_unsafe_or_unknown_candidates(
    tmp_path, decision, expected_status
):
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        candidate_id = create_candidate(
            db.conn,
            _candidate(
                candidate_id=f"dream_decision_safe_resolution_{decision}",
                privacy_status="private_only",
                classification="no_write",
                dedupe_status="conflict",
                recommended_action="ask_arthur",
            ),
        )

        result = decide_candidate(
            db.conn,
            candidate_id,
            decision=decision,
            reason="resolve without promoting or merging",
            reviewer="nancy",
        )
        row = list_candidates(db.conn, status=expected_status, limit=10)[0]

    assert result["status"] == expected_status
    assert row["candidate_id"] == candidate_id


@pytest.mark.parametrize(
    ("status", "decision"),
    [
        ("blocked", "blocked"),
        ("discarded", "discarded"),
    ],
)
def test_decide_candidate_allows_same_terminal_resolution_without_reopening(tmp_path, status, decision):
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        candidate_id = create_candidate(
            db.conn,
            _candidate(
                candidate_id=f"dream_decision_same_terminal_{status}",
                status=status,
                privacy_status="blocked" if status == "blocked" else "private_only",
            ),
        )

        result = decide_candidate(
            db.conn,
            candidate_id,
            decision=decision,
            reason="confirm terminal outcome",
            reviewer="nancy",
        )

    assert result["status"] == status


def test_dream_decide_cli_outputs_safety_flags_and_updates_candidate_only(tmp_path):
    db_path = tmp_path / "guardrails.db"
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    sentinel = raw_dir / "sentinel.md"
    sentinel.write_text("original raw content", encoding="utf-8")

    with GuardrailsDB(db_path) as db:
        db.add_knowledge("Existing Formal", "Formal body", category="workflow")
        formal_count_before = db.conn.execute("SELECT COUNT(*) AS c FROM knowledge").fetchone()["c"]
        create_candidate(
            db.conn,
            _candidate(candidate_id="dream_decision_cli", recommended_action="merge"),
        )

    env = os.environ.copy()
    repo_root = Path(__file__).parent.parent
    env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "guardrails_lite.guardrails_cli",
            "dream",
            "decide",
            "dream_decision_cli",
            "--decision",
            "merge_suggested",
            "--reason",
            "merge with existing item 1",
            "--reviewer",
            "nancy",
            "--db-path",
            str(db_path),
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
    assert payload["status"] == "merge_suggested"
    assert payload["formal_knowledge_written"] is False
    assert payload["raw_written"] is False
    assert payload["sync_invoked"] is False

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        formal_count_after = conn.execute("SELECT COUNT(*) AS c FROM knowledge").fetchone()["c"]
        row = conn.execute(
            "SELECT * FROM knowledge_candidates WHERE candidate_id=?",
            ("dream_decision_cli",),
        ).fetchone()
    finally:
        conn.close()

    assert formal_count_after == formal_count_before
    assert row["status"] == "merge_suggested"
    assert row["decision_reason"] == "merge with existing item 1"
    assert row["reviewer"] == "nancy"
    assert json.loads(row["audit_log_json"])[-1]["event"] == "review_decision"
    assert sentinel.read_text(encoding="utf-8") == "original raw content"


@pytest.mark.parametrize(
    "extra_args, expected_stderr",
    [
        (["--decision", "approved", "--reason", "", "--reviewer", "nancy"], "reason is required"),
        (["--decision", "approved", "--reason", "valid reason", "--reviewer", ""], "reviewer is required"),
        (["--decision", "publish", "--reason", "valid reason", "--reviewer", "nancy"], "invalid choice"),
    ],
)
def test_dream_decide_cli_rejects_invalid_inputs(tmp_path, extra_args, expected_stderr):
    db_path = tmp_path / "guardrails.db"
    with GuardrailsDB(db_path) as db:
        create_candidate(db.conn, _candidate(candidate_id="dream_decision_cli_invalid"))

    env = os.environ.copy()
    repo_root = Path(__file__).parent.parent
    env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "guardrails_lite.guardrails_cli",
            "dream",
            "decide",
            "dream_decision_cli_invalid",
            *extra_args,
            "--db-path",
            str(db_path),
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert expected_stderr in result.stderr
