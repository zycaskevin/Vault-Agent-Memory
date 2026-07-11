from __future__ import annotations

from vault.db import VaultDB
from vault.memory_provider import (
    MEMORY_PROVIDER_OPERATIONS,
    MemoryProvider,
    SQLiteMemoryProvider,
    memory_provider_contract_payload,
    sqlite_memory_provider,
)


def test_memory_provider_contract_names_governed_backend_boundary():
    payload = memory_provider_contract_payload(provider_id="sqlite")

    assert payload["name"] == "Memory Provider Interface"
    assert payload["provider_id"] == "sqlite"
    assert payload["default_provider"] == "sqlite"
    assert payload["operations"] == MEMORY_PROVIDER_OPERATIONS
    assert payload["semantics"]["candidate_first_remote_writes"] is True
    assert payload["semantics"]["remote_direct_active_memory_writes"] is False
    assert payload["semantics"]["hard_delete_by_remote_agent"] is False
    assert payload["backend_boundary"]["sqlite_is_default_local_provider"] is True
    assert payload["backend_boundary"]["qdrant_is_semantic_index_provider_not_source_of_truth"] is True


def test_sqlite_memory_provider_is_candidate_first_and_metadata_only(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    db_path = project / "vault.db"
    with VaultDB(db_path) as db:
        active_id = db.add_knowledge(
            title="Provider active memory",
            content_raw="Provider search should find this active memory only.",
            tags="provider,active",
            trust=0.9,
        )
        archived_id = db.add_knowledge(
            title="Provider archived memory",
            content_raw="Provider search should not return deleted memory.",
            tags="provider,archived",
            trust=0.9,
        )
        db.update_knowledge(archived_id, status="deleted")

    provider = sqlite_memory_provider(project)
    assert isinstance(provider, MemoryProvider)
    assert isinstance(provider, SQLiteMemoryProvider)

    status = provider.status()
    assert status["provider_id"] == "sqlite"
    assert status["backend_type"] == "local_sqlite"
    assert status["db_exists"] is True
    assert status["capabilities"]["candidate_queue_storage"] is True
    assert status["safety"]["writes_active_knowledge_from_remote"] is False

    rows = provider.search_active("Provider", limit=10)
    assert [row["id"] for row in rows] == [active_id]

    updated = provider.update_memory(active_id, actor_agent="provider-agent", summary="Provider summary")
    assert updated["status"] == "ok"
    assert updated["memory"]["summary"] == "Provider summary"
    assert updated["safety"]["remote_direct_active_memory_writes"] is False
    assert updated["safety"]["audit_recorded"] is True

    candidate = provider.create_candidate(
        title="Provider candidate",
        content="Decision: provider create writes review candidates, not active memory.",
        reason="Exercise the provider candidate-first boundary.",
        tags="provider,candidate",
        source="test",
        source_ref="test:provider",
        owner_agent="provider-agent",
    )
    assert candidate["status"] == "candidate_created"
    assert candidate["safety"]["candidate_first"] is True
    assert candidate["safety"]["writes_active_knowledge"] is False
    assert candidate["candidate"]["status"] == "candidate"

    with VaultDB(db_path) as db:
        active_count = db.conn.execute("SELECT count(*) AS count FROM knowledge").fetchone()["count"]
        candidate_count = db.conn.execute("SELECT count(*) AS count FROM memory_candidates").fetchone()["count"]
    assert active_count == 2
    assert candidate_count == 1

    deleted = provider.soft_delete_memory(active_id, actor_agent="provider-agent", reason="test tombstone")
    assert deleted["status"] == "ok"
    assert deleted["safety"]["hard_delete"] is False
    assert deleted["safety"]["audit_recorded"] is True
    assert deleted["memory"]["status"] == "deleted"

    assert provider.get_memory(active_id)["status"] == "deleted"
    assert provider.search_active("Provider active", limit=10) == []

    audit = provider.list_audit(memory_id=active_id)
    assert audit
    assert audit[0]["action"] == "provider:soft_delete_memory"
    assert {event["action"] for event in audit} >= {"provider:update_memory", "provider:soft_delete_memory"}
    assert "payload_json" not in audit[0]

    timeline = provider.list_timeline(active_id)
    assert timeline["status"] == "ok"
    assert timeline["current"]["id"] == active_id
    assert "content_raw" not in timeline["current"]
    assert timeline["safety"]["returns_raw_memory_content"] is False
    assert timeline["safety"]["returns_raw_audit_payloads"] is False

    sync = provider.sync()
    assert sync["status"] == "unsupported"
    assert sync["provider"] == "sqlite"


def test_sqlite_memory_provider_applies_read_policy_filtering(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    db_path = project / "vault.db"
    with VaultDB(db_path) as db:
        shared_id = db.add_knowledge(
            title="Provider policy shared",
            content_raw="Provider policy smoke shared note.",
            scope="shared",
            sensitivity="low",
            trust=0.9,
        )
        private_id = db.add_knowledge(
            title="Provider policy private",
            content_raw="Provider policy smoke private note.",
            scope="private",
            sensitivity="high",
            owner_agent="profile-agent",
            allowed_agents=["work-agent"],
            trust=0.9,
        )
        restricted_id = db.add_knowledge(
            title="Provider policy restricted",
            content_raw="Provider policy smoke restricted note.",
            scope="shared",
            sensitivity="restricted",
            owner_agent="profile-agent",
            allowed_agents=["work-agent"],
            trust=0.9,
        )

    provider = sqlite_memory_provider(project)

    legacy = provider.search_active("Provider policy smoke", limit=10)
    work_agent = provider.search_active("Provider policy smoke", limit=10, agent_id="work-agent")
    work_agent_private = provider.search_active(
        "Provider policy smoke",
        limit=10,
        agent_id="work-agent",
        include_private=True,
    )
    product_agent = provider.search_active("Provider policy smoke", limit=10, agent_id="product-agent")
    capped = provider.search_active(
        "Provider policy smoke",
        limit=10,
        agent_id="work-agent",
        include_private=True,
        max_sensitivity="medium",
    )

    assert {row["id"] for row in legacy} == {shared_id, private_id, restricted_id}
    assert {row["id"] for row in work_agent} == {shared_id, restricted_id}
    assert {row["id"] for row in work_agent_private} == {shared_id, private_id, restricted_id}
    assert {row["id"] for row in product_agent} == {shared_id}
    assert {row["id"] for row in capped} == {shared_id}

    assert provider.get_memory(private_id, agent_id="work-agent") is None
    assert provider.get_memory(private_id, agent_id="work-agent", include_private=True)["id"] == private_id
    assert provider.get_memory(restricted_id, agent_id="product-agent") is None
    assert provider.get_memory(restricted_id, agent_id="work-agent")["id"] == restricted_id


def test_sqlite_memory_provider_blocks_protected_fields_and_invalid_status_transitions(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    db_path = project / "vault.db"
    with VaultDB(db_path) as db:
        memory_id = db.add_knowledge(
            title="Protected provider memory",
            content_raw="Provider updates must preserve identity fields.",
        )

    provider = sqlite_memory_provider(project)

    protected = provider.update_memory(memory_id, actor_agent="provider-agent", id=999)
    invalid_transition = provider.update_memory(
        memory_id,
        actor_agent="provider-agent",
        status="candidate",
    )

    assert protected["status"] == "blocked"
    assert protected["error"] == "protected_field:id"
    assert invalid_transition["status"] == "blocked"
    assert invalid_transition["error"] == "invalid_status_transition:active->candidate"
    assert provider.get_memory(memory_id)["id"] == memory_id
