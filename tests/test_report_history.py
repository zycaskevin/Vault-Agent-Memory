"""DL-9 runtime-only historical trend store tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from guardrails_lite.report_history import (
    append_trend_snapshot,
    build_trend_snapshot,
    build_trend_summary,
    validate_history_path,
)


def _aggregate(**overrides):
    aggregate = {
        "schema": "guardrails.dashboard.aggregate.v1",
        "count_only": True,
        "report_only": True,
        "contains_private_payload": False,
        "generated_at": "2026-05-24T00:00:00+00:00",
        "dream_candidates_total": 3,
        "dream_candidates_ready_for_review": 2,
        "dream_candidates_blocked": 1,
        "dream_candidates_need_arthur": 1,
        "last_dream_review_at": "2026-05-24",
        "librarian_open_duplicates": 4,
        "librarian_open_stale": 5,
        "librarian_open_low_convergence": 6,
        "librarian_open_provenance_gaps": 7,
        "librarian_review_items_total": 22,
        "last_librarian_review_at": "2026-05-24T00:00:00+00:00",
    }
    aggregate.update(overrides)
    return aggregate


def test_build_trend_snapshot_is_count_only_and_rejects_payload_fields():
    snapshot = build_trend_snapshot(
        _aggregate(),
        snapshot_date="2026-05-24",
        generated_at="2026-05-24T01:00:00+00:00",
    )

    serialized = json.dumps(snapshot, ensure_ascii=False)
    assert snapshot["schema"] == "guardrails.report_history.snapshot.v1"
    assert snapshot["snapshot_date"] == "2026-05-24"
    assert snapshot["count_only"] is True
    assert snapshot["report_only"] is True
    assert snapshot["contains_private_payload"] is False
    assert snapshot["metrics"]["dream_candidates_total"] == 3
    assert snapshot["metrics"]["librarian_open_provenance_gaps"] == 7
    assert "dream_secret" not in serialized
    assert "Should not leak" not in serialized
    assert "private body" not in serialized
    assert "candidate_id" not in serialized
    assert "content_draft" not in serialized


def test_build_trend_snapshot_fails_closed_for_unsafe_or_unknown_aggregate():
    with pytest.raises(ValueError, match="count-only"):
        build_trend_snapshot(_aggregate(count_only=False), snapshot_date="2026-05-24")
    with pytest.raises(ValueError, match="private payload"):
        build_trend_snapshot(_aggregate(contains_private_payload=True), snapshot_date="2026-05-24")
    with pytest.raises(ValueError, match="forbidden payload field"):
        build_trend_snapshot(_aggregate(candidate_id="dream_secret"), snapshot_date="2026-05-24")
    with pytest.raises(ValueError, match="forbidden payload field"):
        build_trend_snapshot(_aggregate(title="Should not leak"), snapshot_date="2026-05-24")
    with pytest.raises(ValueError, match="forbidden payload field"):
        build_trend_snapshot(_aggregate(content_draft="private body"), snapshot_date="2026-05-24")
    with pytest.raises(ValueError, match="unknown dashboard aggregate metric"):
        build_trend_snapshot(_aggregate(customer_name="Arthur"), snapshot_date="2026-05-24")
    with pytest.raises(ValueError, match="metric must be an integer count"):
        build_trend_snapshot(_aggregate(dream_candidates_total="PRIVATE_SECRET_PAYLOAD"), snapshot_date="2026-05-24")
    with pytest.raises(ValueError, match="generated_at must be ISO timestamp"):
        build_trend_snapshot(_aggregate(generated_at="Arthur private context"), snapshot_date="2026-05-24")
    with pytest.raises(ValueError, match="last_dream_review_at must be YYYY-MM-DD"):
        build_trend_snapshot(_aggregate(last_dream_review_at="Arthur private context"), snapshot_date="2026-05-24")
    with pytest.raises(ValueError, match="last_librarian_review_at must be ISO timestamp"):
        build_trend_snapshot(_aggregate(last_librarian_review_at="Arthur private context"), snapshot_date="2026-05-24")
    with pytest.raises(ValueError, match="generated_at must be ISO timestamp"):
        build_trend_snapshot(_aggregate(), snapshot_date="2026-05-24", generated_at="Arthur private context")
    with pytest.raises(ValueError, match="snapshot_date must be YYYY-MM-DD"):
        build_trend_snapshot(_aggregate(), snapshot_date="2026-5-24")


def test_append_trend_snapshot_is_idempotent_jsonl_and_summary_computes_deltas(tmp_path):
    history_path = tmp_path / "runtime" / "dream-review" / "history" / "dashboard_history.jsonl"
    first = build_trend_snapshot(
        _aggregate(dream_candidates_total=3, librarian_open_stale=5),
        snapshot_date="2026-05-23",
        generated_at="2026-05-23T01:00:00+00:00",
    )
    second = build_trend_snapshot(
        _aggregate(dream_candidates_total=7, librarian_open_stale=2),
        snapshot_date="2026-05-24",
        generated_at="2026-05-24T01:00:00+00:00",
    )

    append_trend_snapshot(history_path, first)
    append_trend_snapshot(history_path, second)
    append_trend_snapshot(history_path, second)

    lines = history_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    summary = build_trend_summary(history_path)
    assert summary["schema"] == "guardrails.report_history.summary.v1"
    assert summary["count_only"] is True
    assert summary["history_records"] == 2
    assert summary["latest"]["snapshot_date"] == "2026-05-24"
    assert summary["previous"]["snapshot_date"] == "2026-05-23"
    assert summary["deltas"]["dream_candidates_total"] == 4
    assert summary["deltas"]["librarian_open_stale"] == -3
    serialized = json.dumps(summary, ensure_ascii=False)
    assert "title" not in serialized
    assert "content_draft" not in serialized
    assert "candidate_id" not in serialized


def test_append_trend_snapshot_rejects_top_level_payload_fields(tmp_path):
    history_path = tmp_path / "history.jsonl"
    snapshot = build_trend_snapshot(_aggregate(), snapshot_date="2026-05-24")
    snapshot["candidate_id"] = "dream_secret"
    snapshot["content_draft"] = "private body"

    with pytest.raises(ValueError, match="forbidden payload field"):
        append_trend_snapshot(history_path, snapshot)

    assert not history_path.exists()


def test_append_trend_snapshot_rejects_payload_values_inside_allowed_fields(tmp_path):
    history_path = tmp_path / "history.jsonl"
    snapshot = build_trend_snapshot(_aggregate(), snapshot_date="2026-05-24")
    snapshot["metrics"]["dream_candidates_total"] = "PRIVATE_SECRET_PAYLOAD"

    with pytest.raises(ValueError, match="metric must be an integer count"):
        append_trend_snapshot(history_path, snapshot)

    assert not history_path.exists()


def test_append_trend_snapshot_rejects_metadata_payload_values(tmp_path):
    history_path = tmp_path / "history.jsonl"
    for field in [
        "generated_at",
        "source_generated_at",
        "last_librarian_review_at",
    ]:
        snapshot = build_trend_snapshot(_aggregate(), snapshot_date="2026-05-24")
        snapshot[field] = "Arthur private context"
        with pytest.raises(ValueError, match=f"{field} must be ISO timestamp"):
            append_trend_snapshot(history_path, snapshot)
    snapshot = build_trend_snapshot(_aggregate(), snapshot_date="2026-05-24")
    snapshot["last_dream_review_at"] = "Arthur private context"
    with pytest.raises(ValueError, match="last_dream_review_at must be YYYY-MM-DD"):
        append_trend_snapshot(history_path, snapshot)

    assert not history_path.exists()


def test_validate_history_path_rejects_raw_or_compiled(tmp_path):
    project = tmp_path / "project"
    (project / "raw").mkdir(parents=True)
    (project / "compiled").mkdir()
    runtime_path = tmp_path / "runtime" / "history.jsonl"

    assert validate_history_path(project, runtime_path) == runtime_path.resolve()
    with pytest.raises(ValueError, match="history path must not be under project raw/ or compiled/"):
        validate_history_path(project, project / "raw" / "history.jsonl")
    with pytest.raises(ValueError, match="history path must not be under project raw/ or compiled/"):
        validate_history_path(project, project / "compiled" / "history.jsonl")
