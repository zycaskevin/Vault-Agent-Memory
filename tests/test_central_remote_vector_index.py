import json
from pathlib import Path

from vault.central_vector_index import central_remote_vector_index_status
from vault.cli import main


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeRpcQuery:
    def __init__(self, client, name, params):
        self.client = client
        self.name = name
        self.params = params

    def execute(self):
        self.client.rpc_calls.append((self.name, dict(self.params)))
        if self.client.error:
            raise RuntimeError(self.client.error)
        return _FakeResponse(self.client.rows)


class _FakeSupabaseClient:
    def __init__(self, rows=None, error=""):
        self.rows = rows if rows is not None else []
        self.error = error
        self.rpc_calls = []

    def rpc(self, name, params):
        return _FakeRpcQuery(self, name, params)


def test_central_vector_index_migration_defines_pgvector_cache_contract():
    path = Path(__file__).resolve().parents[1] / "supabase/migrations/20260708_central_vector_index.sql"
    sql = path.read_text(encoding="utf-8")

    assert "create extension if not exists vector" in sql
    assert "set search_path = public, extensions" in sql
    assert "create table if not exists public.vault_memory_embeddings" in sql
    assert "embedding vector(1536) not null" in sql
    assert "using hnsw (embedding vector_cosine_ops)" in sql
    assert "alter table public.vault_memory_embeddings enable row level security" in sql
    assert "create or replace function public.vault_central_vector_index_status()" in sql
    assert "grant execute on function public.vault_central_vector_index_status()" in sql
    assert "create or replace function public.vault_match_readable_memory_embeddings" in sql
    assert "p_query_embedding vector(1536)" in sql
    assert "returns table (\n    memory_key text" in sql
    assert "remote_search_text" not in sql.split("create or replace function public.vault_match_readable_memory_embeddings", 1)[1]
    assert "s.content" not in sql
    assert "grant execute on function public.vault_match_readable_memory_embeddings" in sql
    assert "p_project_id is not null" in sql
    assert "lower(e.scope) = 'public'" in sql
    assert "lower(e.scope) in ('shared', 'project')" in sql
    assert "source_table = 'vault_active_memory_snapshots'" in sql
    assert "lower(sensitivity) in ('low', 'medium')" in sql
    assert "create policy agents_rw" not in sql


def test_central_remote_vector_index_status_installed_empty():
    client = _FakeSupabaseClient(
        [
            {
                "installed": True,
                "vector_rows": 0,
                "latest_vector_rows": 0,
                "embedding_models": 0,
                "project_count": 0,
                "oldest_updated_at": None,
                "newest_updated_at": None,
                "remote_read_enabled": True,
                "remote_write_enabled": False,
                "index_role": "derived_remote_read_cache",
                "source_of_truth": "trusted_sync_host_reviewed_snapshots",
            }
        ]
    )

    payload = central_remote_vector_index_status(sb_client=client)

    assert payload["ok"] is True
    assert payload["status"] == "installed_empty"
    assert payload["installed"] is True
    assert payload["counts"]["vector_rows"] == 0
    assert payload["remote_read_enabled"] is True
    assert payload["remote_write_enabled"] is False
    assert payload["safety"]["trusted_sync_host_writes_only"] is True
    assert payload["safety"]["returns_embedding_values"] is False
    assert client.rpc_calls == [("vault_central_vector_index_status", {})]


def test_central_remote_vector_index_status_reports_missing_schema():
    client = _FakeSupabaseClient(error="PGRST202: could not find the function vault_central_vector_index_status")

    payload = central_remote_vector_index_status(sb_client=client)

    assert payload["ok"] is False
    assert payload["status"] == "schema_missing"
    assert payload["installed"] is False
    assert "20260708_central_vector_index.sql" in payload["next_actions"][0]


def test_central_remote_vector_index_status_rows_without_remote_read_requests_latest_migration():
    client = _FakeSupabaseClient(
        [
            {
                "installed": True,
                "vector_rows": 3,
                "latest_vector_rows": 3,
                "embedding_models": 1,
                "project_count": 1,
                "oldest_updated_at": "2026-07-08T00:00:00Z",
                "newest_updated_at": "2026-07-08T01:00:00Z",
                "remote_read_enabled": False,
                "remote_write_enabled": False,
                "index_role": "derived_remote_read_cache",
                "source_of_truth": "trusted_sync_host_reviewed_snapshots",
            }
        ]
    )

    payload = central_remote_vector_index_status(sb_client=client)

    assert payload["ok"] is True
    assert payload["status"] == "installed"
    assert payload["remote_read_enabled"] is False
    assert "Reapply" in payload["next_actions"][0]
    assert "20260708_central_vector_index.sql" in payload["next_actions"][0]


def test_central_remote_vector_index_status_handles_client_import_error(monkeypatch):
    import vault.central_vector_index as central_vector_index

    def fail_client():
        raise ImportError("cannot import name 'create_client' from 'supabase'")

    monkeypatch.setattr(central_vector_index, "_get_remote_vector_client", fail_client)

    payload = central_remote_vector_index_status()

    assert payload["ok"] is False
    assert payload["status"] == "unavailable"
    assert "create_client" in payload["error"]
    assert "Supabase Python client" in payload["next_actions"][0]


def test_vector_index_central_status_cli_json(monkeypatch, tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()
    client = _FakeSupabaseClient(
        [
            {
                "installed": True,
                "vector_rows": 3,
                "latest_vector_rows": 2,
                "embedding_models": 1,
                "project_count": 1,
                "oldest_updated_at": "2026-07-08T00:00:00Z",
                "newest_updated_at": "2026-07-08T01:00:00Z",
                "remote_read_enabled": True,
                "remote_write_enabled": False,
                "index_role": "derived_remote_read_cache",
                "source_of_truth": "trusted_sync_host_reviewed_snapshots",
            }
        ]
    )

    import vault.central_vector_index as central_vector_index

    monkeypatch.setattr(central_vector_index, "_get_remote_vector_client", lambda: client)

    main(["--project-dir", str(project), "vector-index", "central-status", "--write-report", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert payload["artifact_type"] == "central_remote_vector_index_status"
    assert payload["status"] == "installed"
    assert payload["remote_read_enabled"] is True
    assert payload["counts"]["vector_rows"] == 3
    assert payload["paths"]["json"] == "reports/vector-index/central-status-latest.json"
    assert (project / payload["paths"]["json"]).exists()
    assert (project / payload["paths"]["markdown"]).exists()
