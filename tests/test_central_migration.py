import json

from vault.central_candidate_store import list_central_candidate_rows_local, submit_central_candidate_local
from vault.central_migration import (
    export_reviewed_snapshot_bundle,
    import_reviewed_snapshot_bundle,
    migrate_central_candidate_inbox,
    verify_reviewed_snapshot_bundle,
)
from vault.db import VaultDB
from vault.multi_host import record_memory_revision
from vault.remote_candidates import CENTRAL_CANDIDATE_TABLE


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
        self.order_field = ""

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def order(self, field, **_kwargs):
        self.order_field = field
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
        if self.order_field:
            matches.sort(key=lambda row: str(row.get(self.order_field) or ""))
        if self.limit_value is not None:
            matches = matches[: self.limit_value]
        return _FakeResponse(matches)


class _FakeSupabaseClient:
    def __init__(self):
        self.tables = {CENTRAL_CANDIDATE_TABLE: []}
        self.operations = []

    def table(self, name):
        return _FakeTableQuery(self, name)


def test_migrate_supabase_candidates_to_self_host_preview_then_apply(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    fake = _FakeSupabaseClient()
    fake.tables[CENTRAL_CANDIDATE_TABLE].append(
        {
            "id": "remote-1",
            "candidate_key": "candidate-key-1",
            "title": "Remote candidate",
            "content": "Candidate body should migrate only into the central inbox.",
            "reason": "Migration smoke",
            "category": "workflow",
            "tags": ["migration", "self-host"],
            "trust": 0.6,
            "scope": "project",
            "sensitivity": "low",
            "owner_agent": "reviewer",
            "allowed_agents": ["codex"],
            "from_agent": "coze",
            "source_ref": "coze:1",
            "memory_type": "remote_candidate",
            "status": "candidate",
            "idempotency_key": "candidate-key-1",
            "hmac_key_id": "k1",
            "hmac_algorithm": "hmac-sha256",
            "payload_hash": "hash",
            "hmac_signature": "sig",
            "created_at": "2026-07-09T00:00:00+00:00",
        }
    )

    preview = migrate_central_candidate_inbox(
        project,
        direction="supabase-to-self-host",
        apply=False,
        sb_client=fake,
    )

    assert preview["ok"] is True
    assert preview["dry_run"] is True
    assert preview["count"] == 1
    assert preview["inserted_count"] == 0
    assert preview["candidates"][0]["has_content"] is True
    assert "content" not in preview["candidates"][0]
    assert list_central_candidate_rows_local(project) == []

    applied = migrate_central_candidate_inbox(
        project,
        direction="supabase-to-self-host",
        apply=True,
        sb_client=fake,
    )

    assert applied["ok"] is True
    assert applied["inserted_count"] == 1
    assert applied["safety"]["writes_active_memory"] is False
    rows = list_central_candidate_rows_local(project)
    assert len(rows) == 1
    assert rows[0]["candidate_key"] == "candidate-key-1"
    assert rows[0]["from_agent"] == "coze"
    assert rows[0]["hmac_signature"] == "sig"


def test_migrate_self_host_candidates_to_supabase_updates_by_candidate_key(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    submitted = submit_central_candidate_local(
        project,
        title="Self-host candidate",
        content="Self-host central inbox candidate should copy to Supabase.",
        reason="Migration smoke",
        from_agent="phone",
        category="workflow",
        tags=["migration"],
        source_ref="phone:1",
        idempotency_key="self-host-key-1",
    )
    assert submitted["ok"] is True
    fake = _FakeSupabaseClient()

    first = migrate_central_candidate_inbox(
        project,
        direction="self-host-to-supabase",
        apply=True,
        sb_client=fake,
    )

    assert first["ok"] is True
    assert first["inserted_count"] == 1
    assert fake.tables[CENTRAL_CANDIDATE_TABLE][0]["candidate_key"] == "self-host-key-1"
    assert fake.tables[CENTRAL_CANDIDATE_TABLE][0]["content"].startswith("Self-host central")

    second = migrate_central_candidate_inbox(
        project,
        direction="self-host-to-supabase",
        apply=True,
        sb_client=fake,
    )

    assert second["ok"] is True
    assert second["updated_count"] == 1
    assert any(operation[0] == "update" for operation in fake.operations)
    assert second["safety"]["promotes_candidates"] is False


def test_reviewed_snapshot_bundle_export_defaults_to_no_raw_content(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with VaultDB(project / "vault.db") as db:
        db.add_knowledge(
            title="Reviewed deployment lesson",
            content_raw="The real body should stay out of default snapshot bundles.",
            category="workflow",
            tags="deploy,self-host",
            summary="Safe summary",
            trust=0.9,
        )

    bundle_path = project / "snapshots.json"
    payload = export_reviewed_snapshot_bundle(project, bundle_path=bundle_path)

    assert payload["ok"] is True
    assert payload["action"] == "export-snapshots"
    assert payload["count"] == 1
    assert payload["safety"]["includes_raw_memory_content_in_bundle"] is False
    assert payload["snapshots"][0]["has_content"] is False
    assert payload["manifest"]["snapshot_count"] == 1
    assert payload["manifest"]["content_policy"] == "metadata_summary_hash_only"
    assert payload["manifest"]["history"]["memory_revisions"] == 0
    assert payload["manifest"]["history"]["contains_raw_audit_payloads"] is False
    assert "content" not in payload["snapshots"][0]
    bundle = json.loads(bundle_path.read_text())
    assert bundle["snapshots"][0]["content"] == ""
    assert bundle["manifest"]["snapshots_digest"]


def test_reviewed_snapshot_bundle_import_writes_candidates_only_when_applied(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    with VaultDB(source / "vault.db") as db:
        db.add_knowledge(
            title="Reviewed workflow import",
            content_raw="Use candidate-first import because direct active writes are unsafe.",
            category="workflow",
            tags="migration",
            trust=0.9,
            source="source-host",
        )
    with VaultDB(target / "vault.db") as db:
        before_active_count = db.conn.execute("SELECT count(*) AS count FROM knowledge").fetchone()["count"]

    bundle_path = tmp_path / "reviewed-snapshots.json"
    export_reviewed_snapshot_bundle(source, bundle_path=bundle_path, include_content=True)

    preview = import_reviewed_snapshot_bundle(target, bundle_path=bundle_path, apply=False)
    assert preview["ok"] is True
    assert preview["dry_run"] is True
    assert preview["count"] == 1
    assert preview["created_count"] == 0
    assert preview["safety"]["writes_active_memory"] is False
    with VaultDB(target / "vault.db") as db:
        assert db.list_memory_candidates(status=None) == []

    applied = import_reviewed_snapshot_bundle(target, bundle_path=bundle_path, apply=True)
    assert applied["ok"] is True
    assert applied["created_count"] == 1
    assert applied["safety"]["writes_local_review_queue"] is True
    assert applied["safety"]["writes_active_memory"] is False
    assert applied["safety"]["promotes_candidates"] is False
    assert "content" not in applied["snapshots"][0]
    with VaultDB(target / "vault.db") as db:
        rows = db.list_memory_candidates(status=None)
        after_active_count = db.conn.execute("SELECT count(*) AS count FROM knowledge").fetchone()["count"]
    assert len(rows) == 1
    assert rows[0]["source"] == "snapshot_bundle_import"
    assert rows[0]["memory_type"] == "snapshot_import_candidate"
    assert rows[0]["content"].startswith("Use candidate-first import")
    assert after_active_count == before_active_count

    second = import_reviewed_snapshot_bundle(target, bundle_path=bundle_path, apply=True)
    assert second["created_count"] == 0
    assert second["write_items"][0]["status"] == "skipped_existing_source_ref"


def test_snapshot_bundle_verify_checks_manifest_and_content_requirements(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with VaultDB(project / "vault.db") as db:
        knowledge_id = db.add_knowledge(
            title="Verified DR lesson",
            content_raw="Verify snapshot bundles before DR import.",
            category="ops",
            tags="dr,audit",
            trust=0.9,
        )
        record_memory_revision(
            db,
            knowledge_id=knowledge_id,
            title="Verified DR lesson",
            content="Verify snapshot bundles before DR import.",
            operation="snapshot_export_test",
            status="active",
            source_agent="codex",
        )

    metadata_only_bundle = project / "metadata-only.json"
    export_reviewed_snapshot_bundle(project, bundle_path=metadata_only_bundle)
    verified = verify_reviewed_snapshot_bundle(project, bundle_path=metadata_only_bundle)
    assert verified["ok"] is True
    assert verified["missing_content_count"] == 1
    assert verified["manifest"]["history"]["memory_revisions"] == 1
    assert verified["manifest"]["history"]["memory_audit_log"] == 1
    require_content = verify_reviewed_snapshot_bundle(
        project,
        bundle_path=metadata_only_bundle,
        require_content=True,
    )
    assert require_content["ok"] is False
    assert "raw content is required" in require_content["errors"][0]

    content_bundle = project / "content.json"
    export_reviewed_snapshot_bundle(project, bundle_path=content_bundle, include_content=True)
    verified_content = verify_reviewed_snapshot_bundle(
        project,
        bundle_path=content_bundle,
        require_content=True,
    )
    assert verified_content["ok"] is True
    assert verified_content["missing_content_count"] == 0

    tampered = json.loads(content_bundle.read_text())
    tampered["snapshots"][0]["title"] = "Tampered title"
    tampered_bundle = project / "tampered.json"
    tampered_bundle.write_text(json.dumps(tampered), encoding="utf-8")
    tampered_result = verify_reviewed_snapshot_bundle(project, bundle_path=tampered_bundle)
    assert tampered_result["ok"] is False
    assert "snapshot digest mismatch" in tampered_result["errors"]
