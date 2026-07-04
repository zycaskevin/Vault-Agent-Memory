from vault.central_store import (
    ACTIVE_SNAPSHOT_TABLE,
    EVENT_TABLE,
    REVISION_TABLE,
    SYNC_CURSOR_TABLE,
    build_active_memory_snapshot,
    sync_active_memory_snapshots,
)
from vault.db import VaultDB


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeTableQuery:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self.filters = []
        self.insert_payload = None
        self.update_payload = None
        self.limit_value = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def insert(self, payload):
        self.insert_payload = dict(payload)
        return self

    def update(self, payload):
        self.update_payload = dict(payload)
        return self

    def execute(self):
        rows = self.client.tables.setdefault(self.table_name, [])
        if self.insert_payload is not None:
            payload = dict(self.insert_payload)
            payload.setdefault("id", f"{self.table_name}-{len(rows) + 1}")
            rows.append(payload)
            self.client.operations.append(("insert", self.table_name, payload))
            return _FakeResponse([payload])
        if self.update_payload is not None:
            updated = []
            for row in rows:
                if all(row.get(field) == value for field, value in self.filters):
                    row.update(self.update_payload)
                    updated.append(dict(row))
                    self.client.operations.append(("update", self.table_name, dict(row)))
            return _FakeResponse(updated)
        matches = [
            dict(row)
            for row in rows
            if all(row.get(field) == value for field, value in self.filters)
        ]
        if self.limit_value is not None:
            matches = matches[: self.limit_value]
        return _FakeResponse(matches)


class _FakeSupabaseClient:
    def __init__(self):
        self.tables = {}
        self.operations = []

    def table(self, name):
        return _FakeTableQuery(self, name)


def test_build_active_memory_snapshot_hides_content_by_default():
    snapshot = build_active_memory_snapshot(
        {
            "id": 7,
            "title": "Central memory",
            "content_raw": "Raw local body",
            "summary": "Short summary",
            "tags": "sync,central",
        },
        project_key="project:abc",
    )

    assert snapshot["memory_key"] == "project:abc:knowledge:7"
    assert snapshot["content"] == ""
    assert snapshot["tags"] == ["sync", "central"]
    assert snapshot["content_hash"]


def test_sync_active_memory_snapshots_writes_snapshot_revision_event_and_cursor(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with VaultDB(project / "vault.db") as db:
        kid = db.add_knowledge("Central snapshot rule", "Reviewed memory should sync as a central snapshot.")

    fake = _FakeSupabaseClient()
    first = sync_active_memory_snapshots(project, sb_client=fake, agent_id="sync-agent")

    assert first["ok"] is True
    assert first["inserted_count"] == 1
    snapshot = fake.tables[ACTIVE_SNAPSHOT_TABLE][0]
    assert snapshot["local_knowledge_id"] == kid
    assert snapshot["revision"] == 1
    assert snapshot["content"] == ""
    assert fake.tables[REVISION_TABLE][0]["operation"] == "snapshot_inserted"
    assert fake.tables[EVENT_TABLE][0]["event_type"] == "active_snapshots_synced"
    assert fake.tables[SYNC_CURSOR_TABLE][0]["agent_id"] == "sync-agent"

    second = sync_active_memory_snapshots(project, sb_client=fake, agent_id="sync-agent")
    assert second["unchanged_count"] == 1
    assert fake.tables[ACTIVE_SNAPSHOT_TABLE][0]["revision"] == 1

    with VaultDB(project / "vault.db") as db:
        db.conn.execute(
            "UPDATE knowledge SET content_raw=?, content_hash=? WHERE id=?",
            ("Reviewed memory changed.", "changed-hash", kid),
        )
        db.conn.commit()

    third = sync_active_memory_snapshots(project, sb_client=fake, agent_id="sync-agent")
    assert third["updated_count"] == 1
    assert fake.tables[ACTIVE_SNAPSHOT_TABLE][0]["revision"] == 2
    revisions = fake.tables[REVISION_TABLE]
    assert any(row["operation"] == "snapshot_updated" and row["revision"] == 2 for row in revisions)
