from __future__ import annotations

from vault.db import VaultDB
from vault.gateway_memory_api import gateway_memory_create
from vault.gateway_openapi import gateway_openapi
from vault.memory_change_envelope import memory_change_envelope
from vault.memory_object import (
    MEMORY_LAYER_CAPABILITIES,
    MEMORY_LAYER_NON_RESPONSIBILITIES,
    MEMORY_OBJECT_KINDS,
    MemoryObject,
    memory_layer_contract_payload,
)
from vault.memory_provider import memory_provider_contract_payload, sqlite_memory_provider


def test_memory_layer_contract_freezes_exact_generic_boundary():
    contract = memory_layer_contract_payload()

    assert contract["mission"] == "Governed Memory Infrastructure for AI Agents"
    assert contract["memory_object"]["envelope"] == "MemoryObject"
    assert contract["memory_object"]["kinds"] == list(MEMORY_OBJECT_KINDS)
    assert list(MEMORY_OBJECT_KINDS) == [
        "event",
        "experience",
        "decision",
        "knowledge",
        "interaction",
    ]
    assert list(MEMORY_LAYER_CAPABILITIES) == [
        "storage",
        "retrieval",
        "provenance",
        "confidence",
        "lifecycle",
        "governance",
    ]
    assert list(MEMORY_LAYER_NON_RESPONSIBILITIES) == [
        "personality",
        "identity",
        "relationship",
        "life_phase",
        "human_modeling",
    ]
    assert contract["integration_boundary"]["vault_role"] == "memory_provider"
    assert contract["integration_boundary"]["application_semantics_are_opaque"] is True


def test_memory_object_maps_legacy_rows_without_reinterpreting_them():
    obj = MemoryObject.from_record(
        {
            "id": 7,
            "title": "Legacy application record",
            "content_raw": "Opaque application-owned payload.",
            "memory_type": "profile_summary",
            "source": "external-runtime",
            "source_ref": "record:7",
            "trust": 0.75,
            "scope": "private",
            "sensitivity": "high",
            "status": "active",
        }
    ).as_dict()

    assert obj["kind"] == "knowledge"
    assert obj["confidence"] == 0.75
    assert obj["provenance"]["source_ref"] == "record:7"
    assert obj["governance"]["scope"] == "private"
    assert obj["application_metadata"]["legacy_memory_type"] == "profile_summary"


def test_provider_exposes_candidate_first_memory_object_adapter(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with VaultDB(project / "vault.db") as db:
        memory_id = db.add_knowledge(
            title="Provider event",
            content_raw="A source-backed event in the compatibility schema.",
            memory_type="event",
            trust=0.91,
            source="external-runtime",
        )

    provider = sqlite_memory_provider(project)
    candidate = provider.create_memory_object_candidate(
        {
            "kind": "decision",
            "title": "Provider decision",
            "content": "Use Vault only as the governed memory provider.",
            "confidence": 0.88,
            "provenance": {"source": "external-runtime", "source_ref": "decision:1"},
            "governance": {"scope": "project", "sensitivity": "low"},
        },
        reason="Preserve the integration boundary.",
        actor_agent="external-runtime",
    )

    assert candidate["memory_object"]["kind"] == "decision"
    assert candidate["memory_object"]["confidence"] == 0.88
    assert candidate["memory_layer"]["vault_role"] == "memory_provider"
    assert candidate["safety"]["writes_active_knowledge"] is False
    assert provider.get_memory_object(memory_id)["kind"] == "event"
    assert provider.search_memory_objects("source-backed event")[0]["id"] == str(memory_id)

    with VaultDB(project / "vault.db") as db:
        assert db.conn.execute("SELECT count(*) FROM knowledge").fetchone()[0] == 1
        assert db.conn.execute("SELECT count(*) FROM memory_candidates").fetchone()[0] == 1


def test_gateway_create_accepts_additive_kind_and_confidence_aliases(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with VaultDB(project / "vault.db"):
        pass

    created = gateway_memory_create(
        project,
        body={
            "title": "Runtime interaction",
            "content": "An interaction submitted as governed memory.",
            "reason": "Preserve source-backed history.",
            "memory_kind": "interaction",
            "confidence": 0.82,
        },
        agent_id="external-runtime",
    )
    assert created["status"] == "ok"
    assert created["memory_api"]["memory_kind"] == "interaction"
    assert created["memory_api"]["memory_object_schema_version"] == "1.0"
    with VaultDB(project / "vault.db") as db:
        candidate = db.get_memory_candidate(created["candidate"]["candidate_id"])
        before_rejected = db.conn.execute("SELECT count(*) FROM memory_candidates").fetchone()[0]
    assert candidate["memory_type"] == "interaction"
    assert candidate["trust"] == 0.82

    rejected = gateway_memory_create(
        project,
        body={"title": "Invalid", "content": "Invalid kind", "memory_kind": "identity"},
        agent_id="external-runtime",
    )
    assert rejected["status"] == "error"
    assert rejected["error"] == "unsupported_memory_kind"
    with VaultDB(project / "vault.db") as db:
        assert db.conn.execute("SELECT count(*) FROM memory_candidates").fetchone()[0] == before_rejected


def test_provider_openapi_and_change_envelope_publish_one_kind_contract():
    provider_contract = memory_provider_contract_payload()
    openapi = gateway_openapi()

    assert provider_contract["memory_layer"]["version"] == "1.0"
    assert openapi["x-vault-memory-layer"] == provider_contract["memory_layer"]
    create_schema = openapi["components"]["schemas"]["MemoryCreateRequest"]
    aliases = create_schema["allOf"][1]["properties"]
    assert aliases["memory_kind"]["enum"] == list(MEMORY_OBJECT_KINDS)
    assert aliases["confidence"]["minimum"] == 0
    assert aliases["confidence"]["maximum"] == 1

    legacy_change = memory_change_envelope(
        {
            "id": 9,
            "title": "Opaque legacy record",
            "content_raw": "opaque",
            "memory_type": "profile_summary",
            "created_at": "2026-08-21T00:00:00+00:00",
            "updated_at": "2026-08-21T00:00:00+00:00",
        }
    )
    assert legacy_change["kind"] == "knowledge"
    assert legacy_change["application_metadata"]["legacy_memory_type"] == "profile_summary"
