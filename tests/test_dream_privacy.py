"""Privacy preflight tests for Guardrails Dream/Librarian DL-2."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrails_lite.dream_queue import create_candidate, list_candidates, run_candidate_privacy_preflight
from guardrails_lite.guardrails_db import GuardrailsDB
from guardrails_lite.privacy_scanner import scan_entry


def _candidate(**overrides):
    candidate = {
        "source_type": "manual",
        "source_agent": "nancy",
        "source_session_id": "session-privacy",
        "source_channel": "cli",
        "source_refs": [{"kind": "file", "path": "/tmp/dream.md"}],
        "proposed_title": "Dream Privacy Candidate",
        "summary": "Reusable workflow note for Guardrails review.",
        "content_draft": "# Workflow\n\nKeep reports review-only and deterministic.",
        "category": "workflow",
        "tags": ["guardrails", "dream"],
    }
    candidate.update(overrides)
    return candidate


def _serialized(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def test_scan_entry_normal_workflow_content_is_clear():
    result = scan_entry(
        _candidate(),
        context={"entry_point": "dream", "intended_visibility": "shared"},
    ).to_dict()

    assert result["outcome"] == "clear"
    assert result["findings"] == []
    assert result["can_store_draft"] is True
    assert result["can_promote_shared"] is True
    assert result["can_sync_remote"] is True


def test_scan_entry_detects_nested_api_token_without_storing_raw_secret():
    raw_token = "sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCDE"
    result = scan_entry(
        _candidate(
            source_refs=[{"kind": "url", "url": f"https://example.invalid/hook?token={raw_token}"}],
            audit_log=[{"event": "note", "message": "nested source ref has token"}],
        ),
        context={"entry_point": "dream", "intended_visibility": "shared"},
    ).to_dict()
    serialized = _serialized(result)

    assert result["outcome"] in {"blocked", "redact_required"}
    assert result["findings"]
    assert any(finding["kind"] == "secret" for finding in result["findings"])
    assert any("[0]" in finding["field_path"] for finding in result["findings"])
    assert raw_token not in serialized
    assert "abcdefghijklmnopqrstuvwxyz0123456789" not in serialized


def test_scan_entry_finding_paths_do_not_echo_sensitive_dict_keys():
    raw_token = "sk-proj-sensitivekeyabcdefghijklmnopqrstuvwxyz0123456789"
    raw_email = "alice.chen@client.invalid"
    sensitive_key = f"customer.{raw_email}.{raw_token}[payload]"
    result = scan_entry(
        {
            "outer.with[odd].chars": {
                sensitive_key: "Bearer abcdefghijklmnopqrstuvwxyz0123456789ABCDE",
            }
        },
        context={"entry_point": "dream", "intended_visibility": "shared"},
    ).to_dict()
    serialized_safe_outputs = _serialized(
        {
            "findings": result["findings"],
            "audit_summary": result["audit_summary"],
            "redacted_text": result["redacted_text"],
        }
    )

    assert result["outcome"] == "blocked"
    assert result["findings"]
    assert "field:" in result["findings"][0]["field_path"]
    assert sensitive_key not in serialized_safe_outputs
    assert raw_email not in serialized_safe_outputs
    assert raw_token not in serialized_safe_outputs


def test_scan_entry_detects_secret_in_dict_key_even_when_value_is_clean():
    raw_token = "sk-proj-keyonlyabcdefghijklmnopqrstuvwxyz0123456789"
    result = scan_entry(
        {f"metadata-{raw_token}": "clean value"},
        context={"entry_point": "dream", "intended_visibility": "shared"},
    ).to_dict()
    serialized = _serialized(result)

    assert result["outcome"] == "blocked"
    assert any(finding["kind"] == "secret" for finding in result["findings"])
    assert raw_token not in serialized


def test_run_candidate_privacy_preflight_normal_candidate_is_clear(tmp_path):
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        candidate_id = create_candidate(db.conn, _candidate())

        result = run_candidate_privacy_preflight(db.conn, candidate_id)
        [row] = list_candidates(db.conn)

    assert result["privacy_status"] == "clear"
    assert row["privacy_status"] == "clear"
    assert row["recommended_action"] == "review"


def test_run_candidate_privacy_preflight_updates_private_only_and_safe_audit(tmp_path):
    private_payload = "Customer Alice Chen, phone +1 415 555 2671, scheduled filler treatment."
    with GuardrailsDB(tmp_path / "guardrails.db") as db:
        candidate_id = create_candidate(
            db.conn,
            _candidate(summary=private_payload, content_draft="Generalized CRM workflow draft."),
        )

        result = run_candidate_privacy_preflight(db.conn, candidate_id)
        [row] = list_candidates(db.conn)

    serialized_result = _serialized(result)
    serialized_flags = _serialized(row["privacy_flags"])
    serialized_audit = _serialized(row["audit_log"])

    assert result["privacy_status"] == "private_only"
    assert row["privacy_status"] == "private_only"
    assert row["recommended_action"] == "ask_arthur"
    assert row["status"] == "pending"
    assert any(event["event"] == "privacy_preflight" for event in row["audit_log"])
    assert "Alice Chen" not in serialized_result + serialized_flags + serialized_audit
    assert "+1 415 555 2671" not in serialized_result + serialized_flags + serialized_audit


def test_scanner_allows_documented_placeholder_secret_patterns():
    docs_text = """
    Scanner docs examples only: use OPENAI_API_KEY=<TOKEN> or Authorization: Bearer <TOKEN>.
    Pattern examples include sk-... and ghp_<TOKEN_PLACEHOLDER>; do not paste a real token.
    """

    result = scan_entry(
        _candidate(content_draft=docs_text),
        context={"entry_point": "docs", "intended_visibility": "shared"},
    ).to_dict()

    assert result["outcome"] == "clear"
    assert result["findings"] == []
