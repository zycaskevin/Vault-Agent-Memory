"""Candidate queue helper tests for Guardrails Dream DL-1."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrails_lite.guardrails_db import GuardrailsDB
from guardrails_lite.dream_queue import (  # noqa: E402
    append_candidate_audit,
    create_candidate,
    list_candidates,
    update_candidate_status,
)


def _candidate(**overrides):
    candidate = {
        "source_type": "manual",
        "source_agent": "nancy",
        "source_session_id": "session-1",
        "source_channel": "cli",
        "source_refs": [{"kind": "file", "path": "/tmp/candidate.md"}],
        "proposed_title": "Dream Candidate",
        "summary": "A short summary",
        "content_draft": "# Dream Candidate\n\nUseful details.",
        "category": "technique",
        "tags": ["guardrails", "dream"],
        "dedupe_candidates": [{"knowledge_id": 1, "score": 0.2}],
    }
    candidate.update(overrides)
    return candidate


def test_create_list_update_and_append_candidate_audit_roundtrips_json(tmp_path):
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        candidate_id = create_candidate(db.conn, _candidate())
        assert candidate_id.startswith("dream_")

        rows = list_candidates(db.conn)
        assert len(rows) == 1
        row = rows[0]
        assert row["candidate_id"] == candidate_id
        assert row["classification"] == "shared_knowledge"
        assert row["privacy_status"] == "unknown"
        assert row["dedupe_status"] == "unknown"
        assert row["status"] == "pending"
        assert row["recommended_action"] == "review"
        assert row["trust_initial"] == 0.4
        assert row["freshness_initial"] == 1.0
        assert row["convergence_status_initial"] == "unknown"
        assert row["tags"] == ["guardrails", "dream"]
        assert row["source_refs"] == [{"kind": "file", "path": "/tmp/candidate.md"}]
        assert row["dedupe_candidates"] == [{"knowledge_id": 1, "score": 0.2}]
        assert row["audit_log"] == []

        update_candidate_status(
            db.conn,
            candidate_id,
            "ready_for_review",
            "ready after initial triage",
            reviewer="nancy",
        )
        append_candidate_audit(db.conn, candidate_id, {"event": "note", "message": "queued"})

        ready_rows = list_candidates(db.conn, status="ready_for_review")
        assert len(ready_rows) == 1
        updated = ready_rows[0]
        assert updated["status"] == "ready_for_review"
        assert updated["decision_reason"] == "ready after initial triage"
        assert updated["reviewer"] == "nancy"
        assert updated["reviewed_at"]
        assert [event["event"] for event in updated["audit_log"]] == [
            "status_updated",
            "note",
        ]


def test_create_candidate_preserves_explicit_candidate_id_and_filters_status(tmp_path):
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        first_id = create_candidate(db.conn, _candidate(candidate_id="dream_custom_1"))
        second_id = create_candidate(
            db.conn,
            _candidate(proposed_title="Blocked", candidate_id="dream_custom_2", status="blocked"),
        )

        assert first_id == "dream_custom_1"
        assert second_id == "dream_custom_2"
        assert [row["candidate_id"] for row in list_candidates(db.conn, status="pending")] == [
            "dream_custom_1"
        ]
        assert [row["candidate_id"] for row in list_candidates(db.conn, limit=1)] == [
            "dream_custom_2"
        ]


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("source_type", "email"),
        ("category", "concept"),
        ("classification", "public"),
        ("privacy_status", "secret"),
        ("dedupe_status", "same"),
        ("status", "done"),
        ("recommended_action", "publish"),
    ],
)
def test_create_candidate_validates_enums(tmp_path, field, bad_value):
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        with pytest.raises(ValueError, match=field):
            create_candidate(db.conn, _candidate(**{field: bad_value}))


def test_update_and_list_validate_status_enum(tmp_path):
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        candidate_id = create_candidate(db.conn, _candidate())
        with pytest.raises(ValueError, match="status"):
            update_candidate_status(db.conn, candidate_id, "done", "bad")
        with pytest.raises(ValueError, match="status"):
            list_candidates(db.conn, status="done")


def test_json_fields_must_be_lists_or_dicts(tmp_path):
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        with pytest.raises(ValueError, match="tags"):
            create_candidate(db.conn, _candidate(tags="guardrails,dream"))
        with pytest.raises(ValueError, match="event"):
            append_candidate_audit(db.conn, "missing", ["not", "a", "dict"])
