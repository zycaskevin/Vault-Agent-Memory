from vault.central_store import (
    ACTIVE_SNAPSHOT_TABLE,
    EVENT_TABLE,
    REVISION_TABLE,
    SYNC_CURSOR_TABLE,
    build_active_memory_snapshot,
    sync_active_memory_snapshots,
)
from vault.central_vector_store import CENTRAL_VECTOR_TABLE, sync_memory_embeddings
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


class _FakeEmbeddingProvider:
    provider_id = "test-openai-compatible:d1536"
    dim = 1536
    is_semantic = True

    def __init__(self):
        self.calls = []

    def encode(self, texts):
        text_list = [texts] if isinstance(texts, str) else list(texts)
        self.calls.extend(text_list)
        return [[1.0, *([0.0] * 1535)] for _ in text_list]


def test_build_active_memory_snapshot_hides_content_by_default():
    snapshot = build_active_memory_snapshot(
        {
            "id": 7,
            "title": "Central memory",
            "content_raw": "Raw local body",
            "summary": "Short summary",
            "tags": "sync,central",
            "allowed_agents": '["codex", "reviewer"]',
        },
        project_key="project:abc",
    )

    assert snapshot["memory_key"] == "project:abc:knowledge:7"
    assert snapshot["content"] == ""
    assert snapshot["tags"] == ["sync", "central"]
    assert snapshot["allowed_agents"] == ["codex", "reviewer"]
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


def test_sync_memory_embeddings_writes_safe_summary_vectors_only(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with VaultDB(project / "vault.db") as db:
        shared_id = db.add_knowledge(
            "Central vector rule",
            "Raw body should not be embedded into the central vector index.",
            summary="Reviewed safe summary for remote semantic lookup.",
            tags="central,vector",
            scope="project",
            sensitivity="low",
            allowed_agents=["remote-agent"],
        )
        db.add_knowledge(
            "Private vector rule",
            "Private body should never be indexed centrally.",
            summary="Private summary should be skipped.",
            scope="private",
            sensitivity="low",
        )
        db.add_knowledge(
            "Restricted vector rule",
            "Restricted body should never be indexed centrally.",
            summary="Restricted summary should be skipped.",
            scope="project",
            sensitivity="restricted",
        )

    fake = _FakeSupabaseClient()
    sync_active_memory_snapshots(project, sb_client=fake, agent_id="sync-agent")
    provider = _FakeEmbeddingProvider()

    first = sync_memory_embeddings(project, sb_client=fake, provider=provider, agent_id="sync-agent")

    assert first["ok"] is True
    assert first["inserted_count"] == 1
    assert first["skipped_count"] == 2
    assert len(provider.calls) == 1
    assert "Reviewed safe summary" in provider.calls[0]
    assert "Raw body should not be embedded" not in provider.calls[0]

    vector = fake.tables[CENTRAL_VECTOR_TABLE][0]
    assert vector["memory_key"].endswith(f":knowledge:{shared_id}")
    assert vector["revision"] == 1
    assert vector["embedding_dimension"] == 1536
    assert vector["vector_kind"] == "safe_summary"
    assert vector["source_table"] == ACTIVE_SNAPSHOT_TABLE
    assert vector["is_latest"] is True
    assert vector["scope"] == "project"
    assert vector["sensitivity"] == "low"
    assert vector["allowed_agents"] == ["remote-agent"]
    assert vector["remote_search_text_hash"]
    assert vector["embedding_hash"]
    assert "Raw body should not be embedded" not in vector["remote_search_text"]
    assert "Private summary" not in vector["remote_search_text"]

    second = sync_memory_embeddings(project, sb_client=fake, provider=provider, agent_id="sync-agent")
    assert second["unchanged_count"] == 1


def test_sync_memory_embeddings_requires_trusted_marker_for_env_client(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    with VaultDB(project / "vault.db") as db:
        db.add_knowledge(
            "Central vector trusted marker",
            "Raw body.",
            summary="Safe summary.",
        )

    monkeypatch.delenv("VAULT_SUPABASE_TRUSTED_SYNC_HOST", raising=False)
    payload = sync_memory_embeddings(project, provider=_FakeEmbeddingProvider())

    assert payload["ok"] is False
    assert payload["error"] == "trusted_sync_host_marker_missing"


def test_sync_memory_embeddings_preflights_openai_credentials(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    with VaultDB(project / "vault.db") as db:
        db.add_knowledge(
            "Central vector OpenAI key",
            "Raw body.",
            summary="Safe summary.",
        )

    fake = _FakeSupabaseClient()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    payload = sync_memory_embeddings(project, sb_client=fake)

    assert payload["ok"] is False
    assert payload["error"] == "embedding_provider_credentials_missing"
    assert payload["required_env_var"] == "OPENAI_API_KEY"
    assert fake.operations == []


def test_sync_memory_embeddings_supersedes_old_revision(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with VaultDB(project / "vault.db") as db:
        kid = db.add_knowledge(
            "Central vector revision",
            "Initial raw body.",
            summary="Initial safe summary.",
            scope="shared",
            sensitivity="medium",
        )

    fake = _FakeSupabaseClient()
    provider = _FakeEmbeddingProvider()
    sync_active_memory_snapshots(project, sb_client=fake, agent_id="sync-agent")
    first = sync_memory_embeddings(project, sb_client=fake, provider=provider, agent_id="sync-agent")
    assert first["inserted_count"] == 1

    with VaultDB(project / "vault.db") as db:
        db.conn.execute(
            "UPDATE knowledge SET summary=?, content_hash=? WHERE id=?",
            ("Updated safe summary.", "updated-content-hash", kid),
        )
        db.conn.commit()

    sync_active_memory_snapshots(project, sb_client=fake, agent_id="sync-agent")
    second = sync_memory_embeddings(project, sb_client=fake, provider=provider, agent_id="sync-agent")

    assert second["inserted_count"] == 1
    vectors = sorted(fake.tables[CENTRAL_VECTOR_TABLE], key=lambda row: row["revision"])
    assert [row["revision"] for row in vectors] == [1, 2]
    assert vectors[0]["is_latest"] is False
    assert vectors[0]["superseded_at"]
    assert vectors[1]["is_latest"] is True
