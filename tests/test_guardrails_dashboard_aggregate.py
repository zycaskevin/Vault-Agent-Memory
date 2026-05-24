"""DL-7 count-only Dashboard aggregate tests."""

from __future__ import annotations

import json

import pytest

from guardrails_lite.dashboard_aggregate import build_guardrails_dashboard_aggregate, write_guardrails_dashboard_aggregate


def _dream_report() -> dict:
    return {
        "schema": "guardrails.dream.review.v1",
        "report_only": True,
        "auto_promote": False,
        "formal_knowledge_written": False,
        "raw_written": False,
        "sync_invoked": False,
        "date": "2026-05-24",
        "counts": {
            "candidates": 4,
            "by_status": {"ready_for_review": 2, "blocked": 1, "promoted": 1},
            "by_recommended_action": {"promote": 1, "ask_arthur": 1, "block": 1, "discard": 1},
        },
        "candidates": [{"candidate_id": "dream_secret", "proposed_title": "Do not leak this title"}],
    }


def _b7_report() -> dict:
    return {
        "schema": "guardrails.b7.report.v1",
        "report_only": True,
        "auto_promote": False,
        "destructive_merge": False,
        "private_public_sync": False,
        "remote_overwrite": False,
        "counts": {
            "knowledge_rows": 10,
            "items": 5,
            "by_issue_type": {
                "duplicate_title": 2,
                "duplicate_content_hash": 1,
                "stale_freshness": 1,
                "low_convergence": 1,
                "provenance_gap": 1,
            },
        },
        "items": [{"title": "Do not leak formal title", "knowledge_id": 1}],
    }


def test_dashboard_aggregate_is_count_only_and_safe():
    aggregate = build_guardrails_dashboard_aggregate(_dream_report(), _b7_report(), generated_at="2026-05-24T08:10:00+08:00")
    serialized = json.dumps(aggregate, ensure_ascii=False)

    assert aggregate["schema"] == "guardrails.dashboard.aggregate.v1"
    assert aggregate["count_only"] is True
    assert aggregate["report_only"] is True
    assert aggregate["generated_at"] == "2026-05-24T08:10:00+08:00"
    assert aggregate["dream_candidates_total"] == 4
    assert aggregate["dream_candidates_ready_for_review"] == 2
    assert aggregate["dream_candidates_blocked"] == 1
    assert aggregate["dream_candidates_need_arthur"] == 1
    assert aggregate["librarian_open_duplicates"] == 3
    assert aggregate["librarian_open_stale"] == 1
    assert aggregate["librarian_open_low_convergence"] == 1
    assert aggregate["librarian_open_provenance_gaps"] == 1
    assert "Do not leak" not in serialized
    assert "candidate_id" not in serialized
    assert "title" not in serialized
    assert "knowledge_id" not in serialized


def test_dashboard_aggregate_fail_closed_for_unsafe_reports():
    dream = _dream_report()
    dream["sync_invoked"] = True

    with pytest.raises(ValueError, match="unsafe Dream report"):
        build_guardrails_dashboard_aggregate(dream, _b7_report())

    b7 = _b7_report()
    b7["counts"]["by_issue_type"]["destructive_merge_now"] = 1
    with pytest.raises(ValueError, match="unknown B7 issue_type"):
        build_guardrails_dashboard_aggregate(_dream_report(), b7)


def test_write_dashboard_aggregate_round_trips_json(tmp_path):
    aggregate = build_guardrails_dashboard_aggregate(_dream_report(), _b7_report())
    output = tmp_path / "dashboard" / "aggregate.json"

    write_guardrails_dashboard_aggregate(output, aggregate)

    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["count_only"] is True
    assert loaded["librarian_open_duplicates"] == 3
