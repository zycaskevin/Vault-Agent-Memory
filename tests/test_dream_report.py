"""Dream review-report tests for Guardrails Dream/Librarian DL-2."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrails_lite.dream_queue import create_candidate
from guardrails_lite.dream_report import (
    build_dream_review_report,
    write_dream_review_report_json,
    write_dream_review_report_markdown,
)
from guardrails_lite.guardrails_db import GuardrailsDB


PRIVATE_PAYLOAD = "Alice Chen phone +1 415 555 2671 filler treatment"


def _candidate(**overrides):
    candidate = {
        "source_type": "manual",
        "source_agent": "nancy",
        "source_session_id": "session-report",
        "source_channel": "cli",
        "source_refs": [{"kind": "file", "path": "/tmp/dream-report.md"}],
        "proposed_title": "Dream Report Candidate",
        "summary": "A candidate summary",
        "content_draft": "# Dream Report Candidate\n\nUseful but raw draft body.",
        "category": "workflow",
        "tags": ["guardrails", "dream"],
        "privacy_status": "clear",
        "dedupe_status": "unique",
    }
    candidate.update(overrides)
    return candidate


def test_build_dream_review_report_is_report_only_date_filtered_and_safe(tmp_path):
    db_path = tmp_path / "guardrails.db"
    with GuardrailsDB(db_path) as db:
        create_candidate(
            db.conn,
            _candidate(
                candidate_id="dream_report_clear",
                created_at="2026-05-23T01:00:00+00:00",
                recommended_action="review",
            ),
        )
        create_candidate(
            db.conn,
            _candidate(
                candidate_id="dream_report_private",
                created_at="2026-05-23T02:00:00+00:00",
                proposed_title="Private Candidate Safe Title",
                summary=PRIVATE_PAYLOAD,
                content_draft=f"Raw private body: {PRIVATE_PAYLOAD}",
                privacy_status="private_only",
                dedupe_status="near_duplicate",
                dedupe_candidates=[{"knowledge_id": 7, "title": "Existing Safe Title", "reason": "normalized_title"}],
                recommended_action="ask_arthur",
            ),
        )
        create_candidate(
            db.conn,
            _candidate(candidate_id="dream_report_other_day", created_at="2026-05-22T23:59:00+00:00"),
        )
        before = [dict(row) for row in db.conn.execute("SELECT * FROM knowledge_candidates ORDER BY candidate_id")]

    report = build_dream_review_report(db_path, date="2026-05-23", limit=50)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        after = [dict(row) for row in conn.execute("SELECT * FROM knowledge_candidates ORDER BY candidate_id")]

    serialized = json.dumps(report, ensure_ascii=False, sort_keys=True)
    assert before == after
    assert report["schema"] == "guardrails.dream.review.v1"
    assert report["report_only"] is True
    assert report["auto_promote"] is False
    assert report["formal_knowledge_written"] is False
    assert report["counts"]["candidates"] == 2
    assert report["counts"]["by_privacy_status"] == {"clear": 1, "private_only": 1}
    assert report["counts"]["by_dedupe_status"] == {"near_duplicate": 1, "unique": 1}
    assert [item["candidate_id"] for item in report["candidates"]] == [
        "dream_report_private",
        "dream_report_clear",
    ]
    assert all("content_draft" not in item for item in report["candidates"])
    assert PRIVATE_PAYLOAD not in serialized
    assert "Raw private body" not in serialized


def test_write_dream_review_report_json_and_markdown_are_safe(tmp_path):
    db_path = tmp_path / "guardrails.db"
    json_path = tmp_path / "reports" / "dream" / "2026-05-23-dream-review.json"
    markdown_path = tmp_path / "reports" / "dream" / "2026-05-23-dream-review.md"

    with GuardrailsDB(db_path) as db:
        create_candidate(
            db.conn,
            _candidate(
                candidate_id="dream_report_markdown",
                created_at="2026-05-23T03:00:00+00:00",
                summary=PRIVATE_PAYLOAD,
                content_draft=PRIVATE_PAYLOAD,
                privacy_status="blocked",
                recommended_action="block",
            ),
        )

    report = build_dream_review_report(db_path, date="2026-05-23")
    write_dream_review_report_json(json_path, report)
    write_dream_review_report_markdown(markdown_path, report)

    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")

    assert parsed["schema"] == "guardrails.dream.review.v1"
    assert "dream_report_markdown" in markdown
    assert "report_only=true" in markdown
    assert "auto_promote=false" in markdown
    assert "formal_knowledge_written=false" in markdown
    assert "raw_written=false" in markdown
    assert "sync_invoked=false" in markdown
    assert PRIVATE_PAYLOAD not in json_path.read_text(encoding="utf-8")
    assert PRIVATE_PAYLOAD not in markdown
    assert "content_draft" not in markdown


def test_review_report_sanitizes_private_or_blocked_user_metadata(tmp_path):
    db_path = tmp_path / "guardrails.db"
    json_path = tmp_path / "reports" / "dream" / "metadata.json"
    markdown_path = tmp_path / "reports" / "dream" / "metadata.md"
    raw_token = "sk-proj-reportmetadataabcdefghijklmnopqrstuvwxyz0123456789"
    raw_title_payload = f"Customer Alice Chen phone +1 415 555 2671 token {raw_token}"
    raw_agent = "nancy\n## injected heading"
    raw_channel = "cli`\n# injected"
    raw_tag = "customer Alice Chen +1 415 555 2671"
    raw_dedupe_title = f"Existing customer token {raw_token}"

    with GuardrailsDB(db_path) as db:
        create_candidate(
            db.conn,
            _candidate(
                candidate_id="dream_report_metadata_leak",
                created_at="2026-05-23T05:00:00+00:00",
                proposed_title=raw_title_payload,
                source_agent=raw_agent,
                source_session_id=f"session {raw_token}",
                source_channel=raw_channel,
                tags=[raw_tag, "safe-tag"],
                summary=PRIVATE_PAYLOAD,
                content_draft=f"raw body {PRIVATE_PAYLOAD} {raw_token}",
                privacy_status="blocked",
                dedupe_status="duplicate",
                dedupe_candidates=[{"knowledge_id": 9, "title": raw_dedupe_title, "reason": "exact_title"}],
                recommended_action="block",
            ),
        )

    report = build_dream_review_report(db_path, date="2026-05-23")
    write_dream_review_report_json(json_path, report)
    write_dream_review_report_markdown(markdown_path, report)

    serialized_report = json.dumps(report, ensure_ascii=False, sort_keys=True)
    json_text = json_path.read_text(encoding="utf-8")
    markdown = markdown_path.read_text(encoding="utf-8")
    combined = serialized_report + json_text + markdown

    assert raw_token not in combined
    assert "Alice Chen" not in combined
    assert "+1 415 555 2671" not in combined
    assert "injected heading" not in combined
    assert "# injected" not in combined
    assert "summary" not in serialized_report
    assert "content_draft" not in serialized_report
    assert ("[REDACTED_PRIVATE_CONTEXT]" in combined) or ("[REDACTED_SECRET:" in combined)
    assert report["candidates"][0]["dedupe_candidates"][0]["title"] != raw_dedupe_title


@pytest.mark.parametrize("privacy_status", ["unknown", "redact_required", "private_only", "blocked"])
def test_review_report_redacts_user_metadata_for_nonclear_privacy_statuses(tmp_path, privacy_status):
    db_path = tmp_path / "guardrails.db"
    raw_title = f"Title should not leak for {privacy_status}"
    raw_agent = f"agent-secret-{privacy_status}"
    raw_session = f"session-secret-{privacy_status}"
    raw_channel = f"channel-secret-{privacy_status}"
    raw_tag = f"tag-secret-{privacy_status}"
    raw_dedupe_title = f"dedupe-title-secret-{privacy_status}"

    with GuardrailsDB(db_path) as db:
        create_candidate(
            db.conn,
            _candidate(
                candidate_id=f"dream_report_redact_{privacy_status}",
                created_at="2026-05-23T05:30:00+00:00",
                proposed_title=raw_title,
                source_agent=raw_agent,
                source_session_id=raw_session,
                source_channel=raw_channel,
                tags=[raw_tag],
                privacy_status=privacy_status,
                dedupe_candidates=[{"knowledge_id": 11, "title": raw_dedupe_title, "reason": "title_match"}],
            ),
        )

    report = build_dream_review_report(db_path, date="2026-05-23")
    item = report["candidates"][0]
    serialized = json.dumps(report, ensure_ascii=False, sort_keys=True)

    assert item["candidate_id"] == f"dream_report_redact_{privacy_status}"
    assert item["status"] == "pending"
    assert item["recommended_action"] == "review"
    assert item["privacy_status"] == privacy_status
    assert item["dedupe_status"] == "unique"
    assert raw_title not in serialized
    assert raw_agent not in serialized
    assert raw_session not in serialized
    assert raw_channel not in serialized
    assert raw_tag not in serialized
    assert raw_dedupe_title not in serialized
    assert item["proposed_title"] == "[REDACTED_PRIVATE_CONTEXT]"
    assert item["source_agent"] == "[REDACTED_PRIVATE_CONTEXT]"
    assert item["source_session_id"] == "[REDACTED_PRIVATE_CONTEXT]"
    assert item["source_channel"] == "[REDACTED_PRIVATE_CONTEXT]"
    assert item["tags"] == ["[REDACTED_PRIVATE_CONTEXT]"]
    assert item["dedupe_candidates"][0]["title"] == "[REDACTED_PRIVATE_CONTEXT]"


def test_review_report_keeps_clear_candidate_metadata_readable(tmp_path):
    db_path = tmp_path / "guardrails.db"
    with GuardrailsDB(db_path) as db:
        create_candidate(
            db.conn,
            _candidate(
                candidate_id="dream_report_clear_readable",
                created_at="2026-05-23T05:45:00+00:00",
                proposed_title="Readable Safe Title",
                source_agent="nancy-agent",
                source_session_id="session-readable",
                source_channel="feishu",
                tags=["safe-tag", "workflow"],
                privacy_status="clear",
                dedupe_candidates=[{"knowledge_id": 12, "title": "Readable Existing Title", "reason": "title_match"}],
            ),
        )

    report = build_dream_review_report(db_path, date="2026-05-23")
    item = report["candidates"][0]

    assert item["proposed_title"] == "Readable Safe Title"
    assert item["source_agent"] == "nancy-agent"
    assert item["source_session_id"] == "session-readable"
    assert item["source_channel"] == "feishu"
    assert item["tags"] == ["safe-tag", "workflow"]
    assert item["dedupe_candidates"][0]["title"] == "Readable Existing Title"


def test_review_report_buckets_unsafe_privacy_flag_kind_and_rule_id(tmp_path):
    db_path = tmp_path / "guardrails.db"
    unsafe_kind = "customer Alice Chen +1 415 555 2671"
    unsafe_rule = "secret-token-sk-live-12345678901234567890"

    with GuardrailsDB(db_path) as db:
        create_candidate(
            db.conn,
            _candidate(
                candidate_id="dream_report_unsafe_flags",
                created_at="2026-05-23T05:50:00+00:00",
                privacy_status="redact_required",
                privacy_flags=[
                    {"kind": unsafe_kind, "rule_id": unsafe_rule},
                    {"kind": "pii", "rule_id": "phone_number"},
                ],
            ),
        )

    report = build_dream_review_report(db_path, date="2026-05-23")
    flags = report["candidates"][0]["privacy_flags"]
    serialized = json.dumps(flags, ensure_ascii=False, sort_keys=True)

    assert flags["finding_count"] == 2
    assert flags["by_kind"] == {"other": 1, "pii": 1}
    assert flags["by_rule"] == {"phone_number": 1, "unknown_rule": 1}
    assert unsafe_kind not in serialized
    assert unsafe_rule not in serialized
    assert "Alice Chen" not in serialized
    assert "sk-live" not in serialized


def test_dream_review_markdown_groups_actions_for_feishu_cta_without_private_payloads(tmp_path):
    db_path = tmp_path / "guardrails.db"
    markdown_path = tmp_path / "reports" / "dream" / "grouped.md"
    actions = [
        ("dream_group_promote", "promote", "clear"),
        ("dream_group_merge", "merge", "clear"),
        ("dream_group_discard", "discard", "clear"),
        ("dream_group_block", "block", "blocked"),
        ("dream_group_ask", "ask_arthur", "private_only"),
        ("dream_group_review", "review", "clear"),
    ]

    with GuardrailsDB(db_path) as db:
        for index, (candidate_id, action, privacy_status) in enumerate(actions):
            create_candidate(
                db.conn,
                _candidate(
                    candidate_id=candidate_id,
                    created_at=f"2026-05-23T0{index}:00:00+00:00",
                    proposed_title=f"Title {action} {PRIVATE_PAYLOAD}" if privacy_status != "clear" else f"Title {action}",
                    summary=PRIVATE_PAYLOAD,
                    content_draft=f"raw body {PRIVATE_PAYLOAD}",
                    privacy_status=privacy_status,
                    recommended_action=action,
                ),
            )

    report = build_dream_review_report(db_path, date="2026-05-23", limit=0)
    write_dream_review_report_markdown(markdown_path, report)
    markdown = markdown_path.read_text(encoding="utf-8")

    assert "## Promote / Write" in markdown
    assert "## Merge" in markdown
    assert "## Discard" in markdown
    assert "## Block" in markdown
    assert "## Ask Arthur" in markdown
    assert "## General Review" in markdown
    assert "Feishu CTA:" in markdown
    assert "dream decide dream_group_promote --decision approved" in markdown
    assert "dream decide dream_group_ask --decision ask_arthur" in markdown
    assert PRIVATE_PAYLOAD not in markdown
    assert "summary" not in markdown
    assert "content_draft" not in markdown
    assert "[REDACTED_PRIVATE_CONTEXT]" in markdown


def test_review_report_includes_reviewer_ux_summary_action_items_and_feishu_quick_replies(tmp_path):
    db_path = tmp_path / "guardrails.db"
    markdown_path = tmp_path / "reports" / "dream" / "reviewer-ux.md"
    cases = [
        ("dream_ux_promote", "promote", "clear", "Title promote"),
        ("dream_ux_merge", "merge", "clear", "Title merge"),
        ("dream_ux_discard", "discard", "clear", "Title discard"),
        ("dream_ux_block", "block", "blocked", f"Blocked {PRIVATE_PAYLOAD}"),
        ("dream_ux_ask", "ask_arthur", "private_only", f"Ask {PRIVATE_PAYLOAD}"),
    ]

    with GuardrailsDB(db_path) as db:
        before = [dict(row) for row in db.conn.execute("SELECT * FROM knowledge_candidates ORDER BY candidate_id")]
        for index, (candidate_id, action, privacy_status, title) in enumerate(cases):
            create_candidate(
                db.conn,
                _candidate(
                    candidate_id=candidate_id,
                    created_at=f"2026-05-23T0{index}:00:00+00:00",
                    proposed_title=title,
                    summary=PRIVATE_PAYLOAD,
                    content_draft=f"raw body {PRIVATE_PAYLOAD}",
                    privacy_status=privacy_status,
                    recommended_action=action,
                ),
            )

    report = build_dream_review_report(db_path, date="2026-05-23", limit=0)
    write_dream_review_report_markdown(markdown_path, report)
    markdown = markdown_path.read_text(encoding="utf-8")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        after = [dict(row) for row in conn.execute("SELECT * FROM knowledge_candidates ORDER BY candidate_id")]

    ux = report["reviewer_ux"]
    serialized = json.dumps(ux, ensure_ascii=False, sort_keys=True)
    assert len(after) == len(before) + len(cases)
    assert report["report_only"] is True
    assert report["auto_promote"] is False
    assert report["formal_knowledge_written"] is False
    assert report["raw_written"] is False
    assert report["sync_invoked"] is False
    assert ux["conclusion"]["total_candidates"] == 5
    assert ux["conclusion"]["suggest_promote"] == 1
    assert ux["conclusion"]["suggest_merge"] == 1
    assert ux["conclusion"]["suggest_discard"] == 1
    assert ux["conclusion"]["need_arthur"] == 1
    assert ux["conclusion"]["blocked"] == 1
    assert [item["number"] for item in ux["action_items"]] == [1, 2, 3, 4, 5]
    assert all("content_draft" not in item for item in ux["action_items"])
    assert all("summary" not in item for item in ux["action_items"])
    assert any("dream decide dream_ux_promote --decision approved" in item["decide_command"] for item in ux["action_items"])
    assert any("dream decide dream_ux_block --decision blocked" in item["decide_command"] for item in ux["action_items"])
    assert "寫入全部" in ux["quick_replies"]
    assert "只寫 1" in ux["quick_replies"]
    assert "合併 2" in ux["quick_replies"]
    assert "丟棄 3" in ux["quick_replies"]
    assert "封鎖 4" in ux["quick_replies"]
    assert "先不用" in ux["quick_replies"]
    assert "## 結論" in markdown
    assert "## Feishu 快速回覆" in markdown
    assert "## 編號審核清單" in markdown
    assert "1. [promote]" in markdown
    assert "dream decide dream_ux_promote --decision approved" in markdown
    assert PRIVATE_PAYLOAD not in serialized
    assert PRIVATE_PAYLOAD not in markdown
    assert "Blocked Alice" not in markdown
    assert "Ask Alice" not in markdown


def test_reviewer_ux_decide_commands_shell_quote_candidate_ids(tmp_path):
    db_path = tmp_path / "guardrails.db"
    markdown_path = tmp_path / "reports" / "dream" / "quoted.md"
    malicious_id = "dream_ux_bad; touch /tmp/pwned"

    with GuardrailsDB(db_path) as db:
        create_candidate(
            db.conn,
            _candidate(
                candidate_id=malicious_id,
                created_at="2026-05-23T07:00:00+00:00",
                proposed_title="Safe title",
                privacy_status="clear",
                recommended_action="promote",
            ),
        )

    report = build_dream_review_report(db_path, date="2026-05-23", limit=0)
    write_dream_review_report_markdown(markdown_path, report)
    command = report["reviewer_ux"]["action_items"][0]["decide_command"]
    markdown = markdown_path.read_text(encoding="utf-8")

    assert "dream decide 'dream_ux_bad; touch /tmp/pwned' --decision approved" in command
    assert "dream decide dream_ux_bad; touch /tmp/pwned --decision approved" not in command
    assert "dream decide 'dream_ux_bad; touch /tmp/pwned' --decision approved" in markdown
    assert "Feishu CTA: dream decide 'dream_ux_bad; touch /tmp/pwned' --decision approved" in markdown
    assert "Feishu CTA: dream decide `dream_ux_bad; touch /tmp/pwned` --decision approved" not in markdown


def test_build_dream_review_report_restores_row_factory_and_rejects_bad_date(tmp_path):
    db_path = tmp_path / "guardrails.db"
    with GuardrailsDB(db_path) as db:
        create_candidate(
            db.conn,
            _candidate(candidate_id="dream_report_row_factory", created_at="2026-05-23T06:00:00+00:00"),
        )

    conn = sqlite3.connect(db_path)
    try:
        assert conn.row_factory is None
        report = build_dream_review_report(conn, date="2026-05-23")
        assert report["counts"]["candidates"] == 1
        assert conn.row_factory is None
    finally:
        conn.close()

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        build_dream_review_report(db_path, date="2026-5-23")

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        build_dream_review_report(db_path, date="2026-13-99")


def test_dream_review_report_cli_writes_json_and_markdown(tmp_path):
    db_path = tmp_path / "guardrails.db"
    output = tmp_path / "reports" / "dream" / "2026-05-23-dream-review.json"
    markdown = tmp_path / "reports" / "dream" / "2026-05-23-dream-review.md"

    with GuardrailsDB(db_path) as db:
        create_candidate(
            db.conn,
            _candidate(candidate_id="dream_report_cli", created_at="2026-05-23T04:00:00+00:00"),
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
            "review-report",
            "--date",
            "2026-05-23",
            "--db-path",
            str(db_path),
            "--output",
            str(output),
            "--markdown",
            str(markdown),
        ],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert output.exists()
    assert markdown.exists()
    parsed = json.loads(output.read_text(encoding="utf-8"))
    assert parsed["report_only"] is True
    assert parsed["auto_promote"] is False
    assert parsed["formal_knowledge_written"] is False
    assert parsed["counts"]["candidates"] == 1


@pytest.mark.parametrize(
    ("path_arg", "relative_path"),
    [
        ("--output", Path("raw") / "dream-review.json"),
        ("--output", Path("compiled") / "dream-review.json"),
        ("--markdown", Path("raw") / "dream-review.md"),
        ("--markdown", Path("compiled") / "dream-review.md"),
    ],
)
def test_dream_review_report_cli_rejects_outputs_inside_raw_or_compiled(tmp_path, path_arg, relative_path):
    db_path = tmp_path / "guardrails.db"
    (tmp_path / "raw").mkdir()
    (tmp_path / "compiled").mkdir()
    safe_output = tmp_path / "reports" / "dream-review.json"
    safe_markdown = tmp_path / "reports" / "dream-review.md"
    forbidden_path = tmp_path / relative_path
    output = forbidden_path if path_arg == "--output" else safe_output
    markdown = forbidden_path if path_arg == "--markdown" else safe_markdown

    with GuardrailsDB(db_path) as db:
        create_candidate(db.conn, _candidate(candidate_id="dream_report_cli_forbidden_path"))

    env = os.environ.copy()
    repo_root = Path(__file__).parent.parent
    env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "guardrails_lite.guardrails_cli",
            "dream",
            "review-report",
            "--db-path",
            str(db_path),
            "--output",
            str(output),
            "--markdown",
            str(markdown),
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 2
    assert "Dream review reports cannot be written inside raw/ or compiled/" in result.stderr
    assert not forbidden_path.exists()


def test_dream_review_report_cli_rejects_negative_limit(tmp_path):
    db_path = tmp_path / "guardrails.db"
    output = tmp_path / "reports" / "dream-review.json"
    with GuardrailsDB(db_path) as db:
        create_candidate(db.conn, _candidate(candidate_id="dream_report_cli_negative_limit"))

    env = os.environ.copy()
    repo_root = Path(__file__).parent.parent
    env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "guardrails_lite.guardrails_cli",
            "dream",
            "review-report",
            "--db-path",
            str(db_path),
            "--output",
            str(output),
            "--limit",
            "-1",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 2
    assert "must be a non-negative integer" in result.stderr
    assert not output.exists()
