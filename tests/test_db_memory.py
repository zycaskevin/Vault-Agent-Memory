import pytest

from vault.db import VaultDB
from vault.db_memory import memory_feedback_summary, record_memory_feedback


def _candidate(candidate_id: str = "cand_1") -> dict:
    return {
        "id": candidate_id,
        "title": "Candidate title",
        "content": "A project lesson with source evidence.",
        "layer": "L2",
        "category": "workflow",
        "tags": "automation",
        "trust": 0.72,
        "source": "session_capture",
        "source_ref": "session://local#1",
        "reason": "Useful project lesson",
        "status": "candidate",
        "privacy_status": "pass",
        "duplicate_status": "pass",
        "quality_status": "pass",
        "gate_payload_json": "{}",
        "scope": "shared",
        "sensitivity": "low",
        "owner_agent": "codex",
        "allowed_agents": ["codex", "reviewer"],
        "memory_type": "session_lesson",
    }


def test_memory_candidate_helper_normalizes_governance_metadata(tmp_path):
    db = VaultDB(tmp_path / "vault.db").connect()
    try:
        candidate_id = db.add_memory_candidate(_candidate())

        row = db.get_memory_candidate(candidate_id)
        assert row["scope"] == "shared"
        assert row["sensitivity"] == "low"
        assert row["owner_agent"] == "codex"
        assert row["allowed_agents"] == '["codex", "reviewer"]'
        assert row["memory_type"] == "session_lesson"
    finally:
        db.close()


def test_memory_candidate_helper_rejects_unknown_update_columns(tmp_path):
    db = VaultDB(tmp_path / "vault.db").connect()
    try:
        db.add_memory_candidate(_candidate("cand_bad_update"))

        with pytest.raises(ValueError, match="invalid memory candidate update field"):
            db.update_memory_candidate("cand_bad_update", **{"status = 'promoted' --": "bad"})
    finally:
        db.close()


def test_memory_feedback_helper_serializes_payload_and_summarizes(tmp_path):
    db = VaultDB(tmp_path / "vault.db").connect()
    try:
        event_id = record_memory_feedback(
            db.conn,
            {
                "candidate_id": "cand_payload",
                "source": "review-summary",
                "memory_type": "session_lesson",
                "category": "workflow",
                "outcome": "accepted",
                "score": 0.8,
                "payload_json": {"note": "ok"},
            },
        )
        assert event_id > 0

        events = db.list_memory_feedback(source="review-summary", limit=10)
        assert events[0]["payload_json"] == '{"note": "ok"}'

        summary = memory_feedback_summary(db.conn, limit=10)
        assert summary["event_count"] == 1
        assert summary["outcome_counts"] == {"accepted": 1}
        assert summary["groups"][0]["positive_outcomes"] == 1
        assert summary["groups"][0]["acceptance_rate"] == 1.0
    finally:
        db.close()
