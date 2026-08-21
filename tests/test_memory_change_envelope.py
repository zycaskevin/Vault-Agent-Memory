from __future__ import annotations

import hashlib
import json

import vault.memory_provider as memory_provider_module
from vault.db import VaultDB
from vault.memory_change_envelope import MEMORY_CHANGE_SCHEMA_VERSION
from vault.memory_provider import MemoryProvider, sqlite_memory_provider


def _change_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with VaultDB(project / "vault.db") as db:
        first_id = db.add_knowledge(
            title="Readable change one",
            content_raw="line one\nline two\nline three\nline four",
            source="fixture",
            scope="shared",
            sensitivity="low",
            memory_type="event",
            valid_from="2026-08-20T09:00:00+00:00",
        )
        second_id = db.add_knowledge(
            title="Readable change two",
            content_raw="second readable memory",
            scope="shared",
            sensitivity="low",
        )
        private_id = db.add_knowledge(
            title="Hidden private change",
            content_raw="private content must not leak",
            scope="private",
            sensitivity="high",
            owner_agent="private-agent",
        )
    return project, first_id, second_id, private_id


def test_provider_change_page_is_stable_policy_filtered_and_cursor_based(tmp_path):
    project, first_id, second_id, _private_id = _change_project(tmp_path)
    provider = sqlite_memory_provider(project)

    assert isinstance(provider, MemoryProvider)
    provider.update_memory(first_id, actor_agent="review-agent", summary="audited metadata")

    first_page = provider.list_changes(
        agent_id="work-agent",
        max_sensitivity="low",
        limit=1,
    )
    assert first_page["status"] == "ok"
    assert first_page["count"] == 1
    assert first_page["has_more"] is True
    assert first_page["next_cursor"]
    assert "total" not in first_page

    first = first_page["changes"][0]
    assert first["schema_version"] == MEMORY_CHANGE_SCHEMA_VERSION
    assert first["memory_id"] in {str(first_id), str(second_id)}
    assert first["revision_id"].startswith("rev_")
    assert len(first["revision_id"]) == 68
    assert len(first["content_sha256"]) == 64
    assert first["recorded_at"]
    assert first["change_type"] == "upsert"
    assert first["evidence_ref"] == {
        "memory_id": first["memory_id"],
        "revision_id": first["revision_id"],
        "operation": "read_bounded_evidence",
    }
    assert "content" not in first
    assert "content_raw" not in first
    assert "allowed_agents" not in first

    second_page = provider.list_changes(
        cursor=first_page["next_cursor"],
        agent_id="work-agent",
        max_sensitivity="low",
        limit=1,
    )
    assert second_page["status"] == "ok"
    assert second_page["count"] == 1
    assert second_page["has_more"] is False
    assert second_page["changes"][0]["memory_id"] != first["memory_id"]
    combined = first_page["changes"] + second_page["changes"]
    audited = next(change for change in combined if change["memory_id"] == str(first_id))
    assert audited["audit_ref"].startswith("audit:")

    encoded_pages = json.dumps([first_page, second_page], ensure_ascii=False)
    assert "Hidden private change" not in encoded_pages
    assert "private content must not leak" not in encoded_pages

    repeated = provider.list_changes(
        cursor=second_page["next_cursor"],
        agent_id="work-agent",
        max_sensitivity="low",
        limit=10,
    )
    assert repeated["changes"] == []
    assert repeated["next_cursor"] == second_page["next_cursor"]


def test_change_page_uses_bounded_policy_scans_and_selected_row_hydration(tmp_path, monkeypatch):
    project, _first_id, _second_id, _private_id = _change_project(tmp_path)
    with VaultDB(project / "vault.db") as db:
        db.conn.executemany(
            """INSERT INTO knowledge
               (title, content_raw, scope, sensitivity, owner_agent, created_at, updated_at)
               VALUES (?, ?, 'private', 'high', 'private-agent', '', '')""",
            [(f"Hidden {index}", f"private {index}") for index in range(125)],
        )
        db.conn.commit()
    statements: list[str] = []

    class TracedVaultDB(VaultDB):
        def connect(self):
            connected = super().connect()
            connected.conn.set_trace_callback(statements.append)
            return connected

    monkeypatch.setattr(memory_provider_module, "VaultDB", TracedVaultDB)
    page = sqlite_memory_provider(project).list_changes(
        agent_id="work-agent",
        max_sensitivity="low",
        limit=1,
    )

    assert page["status"] == "ok"
    assert page["count"] == 1
    selects = [statement.lower() for statement in statements if statement.lstrip().lower().startswith("select")]
    policy_scans = [statement for statement in selects if "from knowledge" in statement and "order by coalesce" in statement]
    assert len(policy_scans) >= 2
    assert all("select *" not in statement for statement in policy_scans)
    assert all("content_raw" not in statement for statement in policy_scans)
    assert all(" limit " in statement for statement in policy_scans)
    hydrated_rows = [statement for statement in selects if "select * from knowledge" in statement]
    assert hydrated_rows
    assert all("where id in" in statement for statement in hydrated_rows)
    audit_queries = [statement for statement in selects if "from memory_audit_log" in statement]
    assert all("target_id in" in statement for statement in audit_queries)


def test_change_page_scan_and_hydration_share_one_read_snapshot(tmp_path, monkeypatch):
    project, first_id, _second_id, _private_id = _change_project(tmp_path)
    original_content = "line one\nline two\nline three\nline four"

    class MutatingConnection:
        def __init__(self, connection):
            self._connection = connection
            self.mutated = False

        def __getattr__(self, name):
            return getattr(self._connection, name)

        def execute(self, sql, parameters=()):
            cursor = self._connection.execute(sql, parameters)
            normalized = " ".join(str(sql).lower().split())
            if (
                not self.mutated
                and normalized.startswith("select")
                and "from knowledge" in normalized
                and "order by coalesce" in normalized
            ):
                self.mutated = True
                with VaultDB(project / "vault.db") as writer:
                    writer.conn.execute(
                        """UPDATE knowledge
                           SET title=?, content_raw=?, updated_at=?
                           WHERE id=?""",
                        (
                            "Concurrent title",
                            "concurrent content",
                            "2099-01-01T00:00:00+00:00",
                            first_id,
                        ),
                    )
                    writer.conn.commit()
            return cursor

    class SnapshotProbeVaultDB(VaultDB):
        def connect(self):
            connected = super().connect()
            connected.conn = MutatingConnection(connected.conn)
            return connected

    monkeypatch.setattr(memory_provider_module, "VaultDB", SnapshotProbeVaultDB)
    page = sqlite_memory_provider(project).list_changes(
        agent_id="work-agent",
        max_sensitivity="low",
        limit=10,
    )

    assert page["status"] == "ok"
    first = next(change for change in page["changes"] if change["memory_id"] == str(first_id))
    assert first["title"] == "Readable change one"
    assert first["content_sha256"] == hashlib.sha256(original_content.encode()).hexdigest()
    with VaultDB(project / "vault.db") as db:
        assert db.get_knowledge(first_id)["title"] == "Concurrent title"


def test_change_cursor_is_opaque_validated_and_bound_to_read_policy(tmp_path):
    project, _first_id, _second_id, _private_id = _change_project(tmp_path)
    provider = sqlite_memory_provider(project)

    page = provider.list_changes(agent_id="work-agent", max_sensitivity="low", limit=1)

    invalid = provider.list_changes(
        cursor="not-a-valid-cursor",
        agent_id="work-agent",
        max_sensitivity="low",
    )
    assert invalid["status"] == "error"
    assert invalid["error"] == "invalid_cursor"
    assert "changes" not in invalid

    rebound = provider.list_changes(
        cursor=page["next_cursor"],
        agent_id="private-agent",
        include_private=True,
        max_sensitivity="high",
    )
    assert rebound["status"] == "error"
    assert rebound["error"] == "cursor_policy_mismatch"
    assert "changes" not in rebound


def test_revision_bound_bounded_evidence_fails_closed_when_stale(tmp_path):
    project, first_id, _second_id, private_id = _change_project(tmp_path)
    provider = sqlite_memory_provider(project)

    metadata = provider.get_metadata(
        first_id,
        agent_id="work-agent",
        max_sensitivity="low",
    )
    assert metadata is not None
    assert metadata["memory_id"] == str(first_id)
    assert metadata["content_sha256"] == hashlib.sha256(
        b"line one\nline two\nline three\nline four"
    ).hexdigest()
    assert metadata["occurred_at"] == "2026-08-20T09:00:00+00:00"
    assert provider.get_revision(
        first_id,
        metadata["revision_id"],
        agent_id="work-agent",
        max_sensitivity="low",
    ) == metadata

    evidence = provider.read_bounded_evidence(
        first_id,
        metadata["revision_id"],
        line_start=1,
        line_end=2,
        agent_id="work-agent",
        max_sensitivity="low",
    )
    assert evidence["status"] == "ok"
    assert evidence["memory_id"] == str(first_id)
    assert evidence["revision_id"] == metadata["revision_id"]
    assert evidence["content"] == "1|line one\n2|line two"
    assert evidence["safety"]["bounded_read"] is True
    assert evidence["safety"]["max_lines"] == 80

    too_large = provider.read_bounded_evidence(
        first_id,
        metadata["revision_id"],
        line_start=1,
        line_end=81,
        max_lines=2_000,
        agent_id="work-agent",
        max_sensitivity="low",
    )
    assert too_large["status"] == "error"
    assert too_large["error"] == "range_too_large"
    assert too_large["max_lines"] == 80

    denied = provider.read_bounded_evidence(
        private_id,
        "rev_unknown",
        line_start=1,
        line_end=1,
        agent_id="work-agent",
        include_private=True,
        max_sensitivity="high",
    )
    assert denied["status"] == "error"
    assert denied["error"] == "not_found_or_not_readable"
    assert "content" not in denied

    provider.update_memory(
        first_id,
        actor_agent="review-agent",
        content_raw="new line one\nnew line two",
    )
    stale = provider.read_bounded_evidence(
        first_id,
        metadata["revision_id"],
        line_start=1,
        line_end=1,
        agent_id="work-agent",
        max_sensitivity="low",
    )
    assert stale["status"] == "error"
    assert stale["error"] == "revision_mismatch"
    assert "content" not in stale

    current = provider.get_metadata(first_id, agent_id="work-agent", max_sensitivity="low")
    assert current is not None
    assert current["revision_id"] != metadata["revision_id"]
    assert provider.get_revision(
        first_id,
        metadata["revision_id"],
        agent_id="work-agent",
        max_sensitivity="low",
    ) is None


def test_deleted_memory_is_a_tombstone_change_without_readable_evidence(tmp_path):
    project, first_id, _second_id, _private_id = _change_project(tmp_path)
    provider = sqlite_memory_provider(project)

    provider.soft_delete_memory(first_id, actor_agent="review-agent", reason="retired")
    page = provider.list_changes(agent_id="work-agent", max_sensitivity="low", limit=10)
    tombstone = next(change for change in page["changes"] if change["memory_id"] == str(first_id))

    assert tombstone["change_type"] == "delete"
    assert tombstone["lifecycle"]["status"] == "deleted"
    denied = provider.read_bounded_evidence(
        first_id,
        tombstone["revision_id"],
        line_start=1,
        line_end=1,
        agent_id="work-agent",
        max_sensitivity="low",
    )
    assert denied["status"] == "error"
    assert denied["error"] == "not_found_or_not_readable"
    assert "content" not in denied
