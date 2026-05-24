"""DL-6 local-model-assisted Dream triage packet tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from guardrails_lite.dream_triage import build_local_model_triage_packet, write_local_model_triage_packet


def _review_report() -> dict:
    return {
        "schema": "guardrails.dream.review.v1",
        "report_only": True,
        "auto_promote": False,
        "formal_knowledge_written": False,
        "raw_written": False,
        "sync_invoked": False,
        "date": "2026-05-24",
        "counts": {"candidates": 2},
        "reviewer_ux": {
            "action_items": [
                {
                    "number": 1,
                    "candidate_id": "dream_safe",
                    "title": "Safe reusable workflow",
                    "recommended_action": "promote",
                    "suggested_decision": "approved",
                    "privacy_status": "clear",
                    "dedupe_status": "unique",
                    "decide_command": "dream decide dream_safe --decision approved --reason \"<safe reason>\" --reviewer nancy",
                },
                {
                    "number": 2,
                    "candidate_id": "dream_private",
                    "title": "[REDACTED_PRIVATE_CONTEXT]",
                    "recommended_action": "ask_arthur",
                    "suggested_decision": "ask_arthur",
                    "privacy_status": "private_only",
                    "dedupe_status": "near_duplicate",
                    "decide_command": "dream decide dream_private --decision ask_arthur --reason \"<safe reason>\" --reviewer nancy",
                },
            ]
        },
        "candidates": [
            {
                "candidate_id": "dream_safe",
                "proposed_title": "Safe reusable workflow",
                "privacy_status": "clear",
                "dedupe_status": "unique",
                "recommended_action": "promote",
                "summary": "PRIVATE-SUMMARY-SHOULD-NOT-LEAK",
                "content_draft": "PRIVATE-DRAFT-SHOULD-NOT-LEAK",
            }
        ],
    }


def test_local_model_triage_packet_is_prompt_only_safe_metadata():
    packet = build_local_model_triage_packet(_review_report(), model="qwen3.6:35b", max_items=10)
    serialized = json.dumps(packet, ensure_ascii=False)

    assert packet["schema"] == "guardrails.dream.local_model_triage.v1"
    assert packet["report_only"] is True
    assert packet["prompt_only"] is True
    assert packet["network_invoked"] is False
    assert packet["model"] == "qwen3.6:35b"
    assert packet["formal_knowledge_written"] is False
    assert packet["raw_written"] is False
    assert packet["sync_invoked"] is False
    assert packet["date"] == "2026-05-24"
    assert packet["counts"] == {"items": 2, "clear_items": 1, "blocked_or_private_items": 1}
    assert len(packet["items"]) == 2
    assert packet["items"][0]["candidate_id"] == "dream_safe"
    assert packet["items"][0]["allowed_decisions"] == ["approved", "merge_suggested", "discarded", "blocked", "ask_arthur"]
    assert "PRIVATE-SUMMARY-SHOULD-NOT-LEAK" not in serialized
    assert "PRIVATE-DRAFT-SHOULD-NOT-LEAK" not in serialized
    assert "content_draft" not in serialized
    assert "summary" not in serialized
    assert "promote candidate" not in serialized.lower()
    assert "do not promote" in serialized.lower()


def test_local_model_triage_packet_rejects_non_report_only_input():
    report = _review_report()
    report["auto_promote"] = True

    with pytest.raises(ValueError, match="report-only"):
        build_local_model_triage_packet(report)


def test_write_local_model_triage_packet_round_trips_json(tmp_path):
    packet = build_local_model_triage_packet(_review_report(), model="qwen3.6:35b", max_items=1)
    output = tmp_path / "triage" / "packet.json"

    write_local_model_triage_packet(output, packet)

    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["counts"]["items"] == 1
    assert loaded["items"][0]["candidate_id"] == "dream_safe"
