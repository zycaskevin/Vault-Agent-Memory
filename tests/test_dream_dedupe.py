"""Candidate dedupe tests for Guardrails Dream/Librarian DL-2."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrails_lite.dream_dedupe import apply_candidate_dedupe, check_candidate_dedupe
from guardrails_lite.dream_queue import create_candidate, list_candidates
from guardrails_lite.guardrails_db import GuardrailsDB


def _candidate(**overrides):
    candidate = {
        "source_type": "manual",
        "source_agent": "nancy",
        "source_session_id": "session-dedupe",
        "source_channel": "cli",
        "source_refs": [{"kind": "file", "path": "/tmp/dream-dedupe.md"}],
        "proposed_title": "Dream Dedupe Candidate",
        "summary": "A dedupe candidate summary",
        "content_draft": "# Dream Dedupe Candidate\n\nA reusable workflow body.",
        "category": "workflow",
        "tags": ["guardrails", "dream"],
    }
    candidate.update(overrides)
    return candidate


def test_check_candidate_dedupe_detects_normalized_title_and_omits_raw_content(tmp_path):
    raw_body = "This body contains operational detail that must not be emitted in dedupe reports."
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        knowledge_id = db.add_knowledge("dream    dedupe candidate", "different formal body")
        result = check_candidate_dedupe(
            db.conn,
            _candidate(proposed_title=" Dream Dedupe   Candidate ", content_draft=raw_body),
        )

    serialized = json.dumps(result, ensure_ascii=False, sort_keys=True)

    assert result["dedupe_status"] in {"duplicate", "near_duplicate"}
    assert {
        "knowledge_id": knowledge_id,
        "title": "dream    dedupe candidate",
        "reason": "normalized_title",
    } in result["dedupe_candidates"]
    assert raw_body not in serialized
    assert "content_draft" not in serialized
    assert "formal body" not in serialized


def test_check_candidate_dedupe_detects_content_hash_and_keyword_title_search(tmp_path):
    shared_body = "Exactly matching reusable content for hash detection."
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        content_hash_id = db.add_knowledge("Hash Match Knowledge", shared_body)
        keyword_id = db.add_knowledge("Guardrails Review Workflow", "Different content")

        hash_result = check_candidate_dedupe(db.conn, _candidate(proposed_title="Different", content_draft=shared_body))
        keyword_result = check_candidate_dedupe(
            db.conn,
            _candidate(proposed_title="Guardrails review workflow checklist", content_draft="new draft"),
        )

    expected_hash = hashlib.sha256(shared_body.encode()).hexdigest()[:16]

    assert hash_result["content_hash"] == expected_hash
    assert any(
        candidate["knowledge_id"] == content_hash_id and candidate["reason"] == "content_hash"
        for candidate in hash_result["dedupe_candidates"]
    )
    assert hash_result["dedupe_status"] == "duplicate"
    assert any(
        candidate["knowledge_id"] == keyword_id and candidate["reason"] == "title_keyword"
        for candidate in keyword_result["dedupe_candidates"]
    )
    assert keyword_result["dedupe_status"] == "near_duplicate"


def test_apply_candidate_dedupe_updates_candidate_safely_and_appends_audit(tmp_path):
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        knowledge_id = db.add_knowledge("Existing Dedupe Target", "Formal body")
        candidate_id = create_candidate(
            db.conn,
            _candidate(proposed_title=" existing   dedupe target ", content_draft="Draft private-ish body"),
        )

        result = apply_candidate_dedupe(db.conn, candidate_id)
        [row] = list_candidates(db.conn)

    assert result["dedupe_status"] in {"duplicate", "near_duplicate"}
    assert row["dedupe_status"] == result["dedupe_status"]
    assert row["recommended_action"] == "merge"
    assert row["dedupe_candidates"] == result["dedupe_candidates"]
    assert any(candidate["knowledge_id"] == knowledge_id for candidate in row["dedupe_candidates"])
    assert any(event["event"] == "dedupe_check" for event in row["audit_log"])
    assert "Draft private-ish body" not in json.dumps(row["audit_log"], ensure_ascii=False)


def test_apply_candidate_dedupe_preserves_stronger_privacy_recommendation(tmp_path):
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        candidate_id = create_candidate(
            db.conn,
            _candidate(
                proposed_title="Unique privacy blocked candidate",
                content_draft="Unique body",
                privacy_status="blocked",
                recommended_action="block",
                status="blocked",
            ),
        )

        result = apply_candidate_dedupe(db.conn, candidate_id)
        [row] = list_candidates(db.conn)

    assert result["dedupe_status"] == "unique"
    assert row["dedupe_status"] == "unique"
    assert row["privacy_status"] == "blocked"
    assert row["recommended_action"] == "block"
    assert row["status"] == "blocked"
