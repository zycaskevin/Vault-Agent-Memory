from __future__ import annotations

import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

import pytest

from vault.cli import main
from vault.db import VaultDB
from vault.docmap import build_document_map_for_entry
from vault.gateway import (
    BoundedThreadPoolHTTPServer,
    gateway_health,
    gateway_memory_audit,
    gateway_memory_create,
    gateway_memory_delete_request,
    gateway_memory_get,
    gateway_memory_search,
    gateway_memory_timeline,
    gateway_memory_update_request,
    gateway_read_range,
    gateway_openapi,
    gateway_pull_central_candidates,
    gateway_search,
    gateway_submit_central_candidate,
    gateway_submit_candidate,
    make_gateway_handler,
    run_gateway,
)
from vault.gateway_remote_semantic import gateway_remote_semantic_search, gateway_remote_snapshot_read
from vault.gateway_audit import gateway_audit_report
from vault.gateway_security import GatewaySecurityPolicy
from vault.agent_setup_remote_server import write_remote_server_deploy_templates


def _project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with VaultDB(project / "vault.db") as db:
        public_id = db.add_knowledge(
            "Shared Gateway Runbook",
            "# Shared Gateway Runbook\n\nGateway search should find this shared runbook.\n\n## Evidence\n\nAgents should read bounded ranges.",
            category="runbook",
            tags="gateway,shared",
            scope="shared",
            sensitivity="low",
            trust=0.9,
        )
        build_document_map_for_entry(db, public_id)
        private_id = db.add_knowledge(
            "Private Gateway Note",
            "# Private Gateway Note\n\nOnly the owner should see this private note.",
            category="private",
            tags="gateway,private",
            scope="private",
            sensitivity="high",
            owner_agent="profile-agent",
            trust=0.9,
        )
        build_document_map_for_entry(db, private_id)
    return project, public_id, private_id


def _post_json(host, port, path, payload, *, token="secret"):
    return _request_json("POST", host, port, path, payload, token=token)


def _request_json(method, host, port, path, payload=None, *, token="secret"):
    conn = http.client.HTTPConnection(host, port, timeout=5)
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    conn.request(method, path, body, headers)
    response = conn.getresponse()
    body = response.read()
    conn.close()
    return response.status, json.loads(body.decode("utf-8"))


def _free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_remote_server(url: str, token: str, *, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            conn = http.client.HTTPConnection(url.replace("http://", ""), timeout=1)
            conn.request("GET", "/health", headers={"Authorization": f"Bearer {token}"})
            response = conn.getresponse()
            response.read()
            conn.close()
            if response.status == 200:
                return
        except Exception as exc:
            last_error = exc
        time.sleep(0.1)
    raise AssertionError(f"remote server did not become ready: {last_error}")


class _FakeRemoteSemanticProvider:
    def encode(self, texts):
        assert texts
        return [[0.01] * 1536]


class _FakeRemoteSemanticResponse:
    def __init__(self, data):
        self.data = data


class _FakeRemoteSemanticRpc:
    def __init__(self, client, name, params):
        self.client = client
        self.name = name
        self.params = dict(params)

    def execute(self):
        self.client.rpc_calls.append((self.name, self.params))
        return _FakeRemoteSemanticResponse(self.client.rows_by_rpc.get(self.name, []))


class _FakeRemoteSemanticClient:
    def __init__(self):
        self.rpc_calls = []
        self.rows_by_rpc = {
            "vault_match_readable_memory_embeddings": [
                {
                    "memory_key": "private-memory:a87aa9886d99:knowledge:2",
                    "revision": 1,
                    "similarity": 0.91,
                    "title": "Central semantic read",
                    "summary": "Approved safe summary only.",
                    "scope": "project",
                    "sensitivity": "low",
                    "read_handle": "private-memory:a87aa9886d99:knowledge:2",
                }
            ],
            "vault_get_readable_memory_snapshot": [
                {
                    "memory_key": "private-memory:a87aa9886d99:knowledge:2",
                    "revision": 1,
                    "title": "Central semantic read",
                    "content_preview": "Approved bounded preview.",
                    "content_source": "reviewed_snapshot_summary",
                    "truncated": False,
                    "scope": "project",
                    "sensitivity": "low",
                }
            ],
        }

    def rpc(self, name, params):
        return _FakeRemoteSemanticRpc(self, name, params)


def test_gateway_http_requires_token_and_serves_health(tmp_path):
    project, _public_id, _private_id = _project(tmp_path)
    handler = make_gateway_handler(project, auth_token="secret")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/health")
        denied = conn.getresponse()
        assert denied.status == 401
        denied.read()
        conn.close()

        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/health", headers={"X-Vault-Gateway-Token": "secret"})
        allowed = conn.getresponse()
        assert allowed.status == 200
        assert allowed.getheader("X-Content-Type-Options") == "nosniff"
        assert allowed.getheader("Referrer-Policy") == "no-referrer"
        assert allowed.getheader("Strict-Transport-Security") is None
        payload = json.loads(allowed.read().decode("utf-8"))
        assert payload["status"] == "ok"
        assert payload["gateway"]["candidate_first_writes"] is True
        governance = payload["gateway"]["governance_contract"]
        assert governance["semantics"]["remote_writes_enter_candidates"] is True
        assert governance["write_policy"]["direct_remote_active_memory_writes"] is False
        assert "submit_candidate" in governance["operations"]
        provider = payload["gateway"]["memory_provider"]
        assert provider["provider_id"] == "sqlite"
        assert provider["backend_type"] == "local_sqlite"
        assert provider["provider_contract"]["name"] == "Memory Provider Interface"
        assert provider["provider_contract"]["semantics"]["remote_direct_active_memory_writes"] is False
        assert provider["safety"]["candidate_first_remote_writes"] is True
        assert payload["gateway"]["central_candidate_inbox"] is True
        assert payload["gateway"]["vault_memory_api"]["status"] == "facade"
        assert payload["gateway"]["vault_memory_api"]["legacy_gateway_endpoints_preserved"] is True
        assert payload["gateway"]["vault_memory_api"]["update_writes_active_knowledge"] is False
        assert payload["gateway"]["vault_memory_api"]["delete_hard_deletes"] is False
        assert payload["gateway"]["vault_memory_api"]["delete_submits_review_candidate"] is True
        assert payload["gateway"]["central_semantic_read"]["supported"] is True
        assert payload["gateway"]["central_semantic_read"]["enabled"] is False
        assert payload["gateway"]["central_semantic_read"]["ready"] is False
        assert payload["gateway"]["central_semantic_read"]["token_agent_binding_required"] is True
        assert payload["gateway"]["central_semantic_read"]["returns_embedding_values"] is False
        assert payload["gateway"]["central_semantic_read"]["query_embedding_provider"] == "openai"
        assert payload["gateway"]["central_semantic_read"]["query_embedding_model"] == "text-embedding-3-small"
        assert payload["gateway"]["central_semantic_read"]["privacy_warnings"] == []
        assert "remote_semantic_query_text_sent_to_openai" in payload["gateway"]["central_semantic_read"]["privacy_warnings_if_enabled"]
        assert "/openapi.json" in payload["gateway"]["endpoints"]
        assert "/memory/search" in payload["gateway"]["endpoints"]
        assert "/memory/create" in payload["gateway"]["endpoints"]
        assert "/memory/{id}" in payload["gateway"]["endpoints"]
        assert "/central-candidates/submit" in payload["gateway"]["endpoints"]
        assert "/remote-semantic-search" in payload["gateway"]["endpoints"]
        assert "/remote-snapshot-read" in payload["gateway"]["endpoints"]
        assert payload["gateway"]["graceful_shutdown_supported"] is True
        assert payload["gateway"]["default_shutdown_timeout_seconds"] == 10.0
        assert payload["gateway"]["remote_ready"]["active_multi_master_sync"] is False
        conn.close()

        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/openapi.json", headers={"X-Vault-Gateway-Token": "secret"})
        contract_response = conn.getresponse()
        assert contract_response.status == 200
        contract = json.loads(contract_response.read().decode("utf-8"))
        assert contract["info"]["title"] == "Vault Gateway"
        assert contract["x-vault-safety"]["candidate_first_writes"] is True
        assert contract["x-vault-governance-contract"]["semantics"]["remote_agents_can_promote_active_memory"] is False
        assert contract["x-vault-governance-contract"]["write_policy"]["remote_write_policy"] == "candidate_first_only"
        assert contract["x-vault-safety"]["central_candidate_inbox"] is True
        assert contract["x-vault-safety"]["central_semantic_read"] is True
        assert contract["x-vault-safety"]["remote_semantic_enabled_by_default"] is False
        assert contract["x-vault-safety"]["remote_semantic_requires_token_agent_binding"] is True
        assert contract["x-vault-safety"]["remote_semantic_query_sent_to_embedding_provider"] is True
        assert contract["x-vault-safety"]["remote_semantic_default_query_embedding_provider"] == "openai"
        assert contract["x-vault-safety"]["remote_semantic_query_embedding_provider"] == "openai"
        assert contract["x-vault-safety"]["remote_semantic_query_text_sent_to_openai_by_default"] is True
        assert contract["x-vault-safety"]["remote_semantic_search_returns_raw_content"] is False
        assert contract["x-vault-safety"]["remote_semantic_search_returns_embedding_values"] is False
        assert contract["x-vault-safety"]["remote_snapshot_read_bounded"] is True
        assert contract["x-vault-safety"]["writes_active_knowledge"] is False
        assert contract["x-vault-safety"]["memory_provider_interface"] is True
        assert contract["x-vault-safety"]["default_memory_provider"] == "sqlite"
        assert contract["x-vault-safety"]["remote_direct_active_memory_writes"] is False
        assert contract["x-vault-memory-provider-interface"]["name"] == "Memory Provider Interface"
        assert (
            contract["x-vault-memory-provider-interface"]["semantics"]["remote_direct_active_memory_writes"]
            is False
        )
        provider_read = contract["x-vault-memory-api"]["provider_read_adoption"]
        assert provider_read["paths"] == ["/memory/search", "/memory/{id}"]
        assert provider_read["mode"] == "shadow_metadata_probe"
        assert provider_read["policy_authority"] == "legacy_gateway_policy_gate"
        assert provider_read["search_probes_returned_ids_only"] is True
        assert provider_read["returns_provider_raw_rows"] is False
        assert contract["x-vault-safety"]["max_search_query_chars"] == 1000
        assert contract["components"]["schemas"]["SearchRequest"]["properties"]["query"]["maxLength"] == 1000
        assert "/remote-semantic-search" in contract["paths"]
        assert "/remote-snapshot-read" in contract["paths"]
        conn.close()
    finally:
        server.shutdown()
        server.server_close()


def test_gateway_search_and_read_range_apply_agent_policy(tmp_path):
    project, public_id, private_id = _project(tmp_path)

    missing_agent = gateway_search(project, query="Gateway", agent_id="")
    assert missing_agent["error"] == "agent_id_required"
    assert "next_action" in missing_agent

    search = gateway_search(project, query="Gateway", agent_id="work-agent", max_sensitivity="low")
    assert search["status"] == "ok"
    titles = {row["title"] for row in search["results"]}
    assert "Shared Gateway Runbook" in titles
    assert "Private Gateway Note" not in titles

    denied = gateway_read_range(
        project,
        knowledge_id=private_id,
        agent_id="work-agent",
        include_private=False,
        max_sensitivity="low",
        line_start=1,
        line_end=2,
    )
    assert denied["error"] == "access_denied"

    allowed = gateway_read_range(
        project,
        knowledge_id=public_id,
        agent_id="work-agent",
        include_private=False,
        max_sensitivity="low",
        line_start=1,
        line_end=2,
    )
    assert allowed["status"] == "ok"
    assert allowed["entry_id"] == public_id
    assert "Shared Gateway Runbook" in allowed["title"]


def test_gateway_health_missing_db_suggests_init(tmp_path):
    payload = gateway_health(tmp_path / "empty-project")

    assert payload["status"] == "blocked"
    assert payload["db_exists"] is False
    assert "vault init" in payload["try"][0]
    assert "next_action" in payload


def test_gateway_health_discloses_remote_semantic_provider_and_query_privacy(tmp_path, monkeypatch):
    project, _public_id, _private_id = _project(tmp_path)
    monkeypatch.delenv("VAULT_REMOTE_SEMANTIC_EMBEDDING_PROVIDER", raising=False)
    monkeypatch.delenv("VAULT_REMOTE_SEMANTIC_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_EMBEDDING_MODEL", raising=False)

    payload = gateway_health(
        project,
        remote_semantic_enabled=True,
        token_agent_map={"agent-secret": "remote-agent"},
    )
    semantic = payload["gateway"]["central_semantic_read"]

    assert semantic["enabled"] is True
    assert semantic["ready"] is True
    assert semantic["query_embedding_provider"] == "openai"
    assert semantic["query_embedding_model"] == "text-embedding-3-small"
    assert semantic["query_embedding_provider_defaulted"] is True
    assert semantic["query_text_sent_to_embedding_provider_when_enabled"] is True
    assert semantic["query_text_sent_to_external_provider_when_enabled"] is True
    assert "remote_semantic_query_text_sent_to_openai" in semantic["privacy_warnings"]
    assert "OpenAI" in semantic["privacy_warning"]

    monkeypatch.setenv("VAULT_REMOTE_SEMANTIC_EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("VAULT_REMOTE_SEMANTIC_EMBEDDING_MODEL", "nomic-embed-text")
    local_payload = gateway_health(
        project,
        remote_semantic_enabled=True,
        token_agent_map={"agent-secret": "remote-agent"},
    )
    local_semantic = local_payload["gateway"]["central_semantic_read"]

    assert local_semantic["query_embedding_provider"] == "ollama"
    assert local_semantic["query_embedding_model"] == "nomic-embed-text"
    assert local_semantic["query_text_sent_to_external_provider_when_enabled"] is False
    assert local_semantic["privacy_warnings"] == []


def test_gateway_search_rejects_overlong_query_and_missing_db_has_next_step(tmp_path):
    missing = gateway_search(tmp_path / "missing", query="runbook", agent_id="work-agent")
    assert missing["error"] == "db_not_found"
    assert "vault init" in missing["try"][0]
    assert "next_action" in missing

    project, _public_id, _private_id = _project(tmp_path)
    too_long = gateway_search(project, query="x" * 1001, agent_id="work-agent")
    assert too_long["error"] == "query_too_long"
    assert too_long["max_query_chars"] == 1000
    assert "next_action" in too_long


def test_gateway_http_security_headers_include_hsts_when_tls_mode(tmp_path):
    project, _public_id, _private_id = _project(tmp_path)
    handler = make_gateway_handler(project, auth_token="secret", tls_enabled=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/health", headers={"Authorization": "Bearer secret"})
        response = conn.getresponse()
        response.read()
        conn.close()
        assert response.status == 200
        assert response.getheader("X-Content-Type-Options") == "nosniff"
        assert response.getheader("Referrer-Policy") == "no-referrer"
        assert response.getheader("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
    finally:
        server.shutdown()
        server.server_close()


def test_gateway_submit_candidate_is_candidate_first_and_policy_bound(tmp_path):
    project, _public_id, _private_id = _project(tmp_path)

    blocked = gateway_submit_candidate(
        project,
        title="Shared candidate",
        content="Decision: shared candidates need an explicit gateway launch flag because shared memory affects other agents.",
        agent_id="work-agent",
        scope="shared",
    )
    assert blocked["error"] == "access_denied"

    accepted = gateway_submit_candidate(
        project,
        title="Project candidate",
        content="Decision: project gateway candidates stay in review because Gateway v0 must not write active memory.",
        agent_id="work-agent",
        scope="project",
    )
    assert accepted["status"] == "ok"
    assert accepted["safety"]["writes_active_knowledge"] is False
    assert accepted["safety"]["governance_contract"]["write_policy"]["remote_write_policy"] == "candidate_first_only"
    with VaultDB(project / "vault.db") as db:
        candidates = db.list_memory_candidates(status=None)
        active_count = db.conn.execute("SELECT count(*) AS count FROM knowledge").fetchone()["count"]
    assert len(candidates) == 1
    assert candidates[0]["source"] == "gateway:work-agent"
    assert candidates[0]["status"] == "candidate"
    assert active_count == 2


def test_gateway_central_candidate_inbox_is_pull_into_review(tmp_path):
    project, _public_id, _private_id = _project(tmp_path)

    blocked = gateway_submit_central_candidate(
        project,
        title="Shared central candidate",
        content="Shared central candidates need explicit launch policy.",
        agent_id="phone-agent",
        scope="shared",
    )
    assert blocked["error"] == "access_denied"

    submitted = gateway_submit_central_candidate(
        project,
        title="Central project candidate",
        content="Decision: self-hosted central candidates are pulled into local review before promotion.",
        agent_id="phone-agent",
        scope="project",
    )
    assert submitted["ok"] is True
    assert submitted["status"] == "candidate"
    assert submitted["central_memory_station"] is True
    assert submitted["safety"]["writes_active_knowledge"] is False
    assert submitted["safety"]["governance_contract"]["semantics"]["remote_writes_enter_candidates"] is True

    preview = gateway_pull_central_candidates(project, agent_id="review-agent", apply=False)
    assert preview["ok"] is True
    assert preview["count"] == 1
    assert preview["imported_count"] == 0
    assert preview["requests"][0]["title"] == "Central project candidate"

    applied = gateway_pull_central_candidates(project, agent_id="review-agent", apply=True)
    assert applied["imported_count"] == 1
    assert applied["requests"][-1]["status"] == "imported"
    assert applied["safety"]["apply_writes_local_candidates_only"] is True
    assert applied["safety"]["governance_contract"]["write_policy"]["direct_remote_active_memory_writes"] is False

    with VaultDB(project / "vault.db") as db:
        candidates = db.list_memory_candidates(status=None)
        active_count = db.conn.execute("SELECT count(*) AS count FROM knowledge").fetchone()["count"]
    assert len(candidates) == 1
    assert candidates[0]["source"] == "central_memory_candidate"
    assert candidates[0]["status"] == "candidate"
    assert active_count == 2


def test_gateway_openapi_contract_documents_safe_adapter_boundary():
    contract = gateway_openapi()
    assert contract["openapi"].startswith("3.")
    assert {
        "/health",
        "/openapi.json",
        "/search",
        "/read-range",
        "/submit-candidate",
        "/memory/search",
        "/memory/create",
        "/memory/{id}",
        "/memory/audit",
        "/memory/timeline",
        "/central-candidates/status",
        "/central-candidates/submit",
        "/central-candidates/pull",
        "/remote-semantic-search",
        "/remote-snapshot-read",
    } <= set(contract["paths"])
    assert contract["components"]["securitySchemes"]["bearerAuth"]["scheme"] == "bearer"
    safety = contract["x-vault-safety"]
    assert safety["agent_id_required_for_reads"] is True
    assert safety["private_hidden_by_default"] is True
    assert safety["search_returns_raw_content"] is False
    assert safety["writes_active_knowledge"] is False
    assert safety["candidate_first_writes"] is True
    governance = contract["x-vault-governance-contract"]
    assert governance["semantics"]["remote_writes_enter_candidates"] is True
    assert governance["write_policy"]["direct_remote_active_memory_writes"] is False
    assert safety["central_candidate_inbox"] is True
    assert safety["central_semantic_read"] is True
    assert safety["remote_semantic_enabled_by_default"] is False
    assert safety["remote_semantic_requires_token_agent_binding"] is True
    assert safety["remote_semantic_query_sent_to_embedding_provider"] is True
    assert safety["remote_semantic_default_query_embedding_provider"] == "openai"
    assert safety["remote_semantic_query_text_sent_to_openai_by_default"] is True
    assert safety["remote_semantic_search_returns_raw_content"] is False
    assert safety["remote_semantic_search_returns_embedding_values"] is False
    assert safety["remote_snapshot_read_bounded"] is True
    assert safety["tls_supported"] is True
    assert safety["bounded_worker_pool_supported"] is True
    assert safety["vault_memory_api_additive"] is True
    assert safety["memory_api_update_writes_active_knowledge"] is False
    assert safety["memory_api_delete_hard_deletes"] is False
    assert safety["memory_api_delete_submits_review_candidate"] is True
    memory_api = contract["x-vault-memory-api"]
    assert memory_api["status"] == "facade"
    assert memory_api["legacy_gateway_endpoints_preserved"] is True
    assert memory_api["delete_semantics"] == "soft_delete_review_candidate_in_gateway_facade"
    assert "/memory/promote" in memory_api["planned_paths"]


def test_gateway_memory_api_facade_is_candidate_first_and_metadata_only(tmp_path):
    project, public_id, _private_id = _project(tmp_path)

    search = gateway_memory_search(project, query="Gateway", agent_id="work-agent")
    assert search["status"] == "ok"
    assert search["memory_api"]["legacy_equivalent"] == "/search"
    assert search["memory_api"]["provider_read"]["provider_id"] == "sqlite"
    assert search["memory_api"]["provider_read"]["mode"] == "shadow_metadata_probe"
    assert search["memory_api"]["provider_read"]["policy_authority"] == "legacy_gateway_search"
    assert search["memory_api"]["provider_read"]["results_authority"] == "legacy_gateway_policy_filtered"
    assert search["memory_api"]["provider_read"]["returned_result_count"] == len(search["results"])
    assert search["memory_api"]["provider_read"]["probes_returned_ids_only"] is True
    assert search["memory_api"]["provider_read"]["returns_provider_raw_rows"] is False
    assert "provider_result_count" not in search["memory_api"]["provider_read"]
    assert "rows" not in search["memory_api"]["provider_read"]
    assert any(row["id"] == public_id for row in search["results"])

    private_search = gateway_memory_search(project, query="Only the owner should see", agent_id="work-agent")
    assert private_search["status"] == "ok"
    assert private_search["results"] == []
    assert private_search["memory_api"]["provider_read"]["returned_result_count"] == 0
    assert private_search["memory_api"]["provider_read"]["returned_ids_present_in_provider"] == []
    assert private_search["memory_api"]["provider_read"]["probes_returned_ids_only"] is True
    assert "provider_result_count" not in private_search["memory_api"]["provider_read"]

    read = gateway_memory_get(project, memory_id=public_id, agent_id="work-agent", line_start=1, line_end=2)
    assert read["status"] == "ok"
    assert read["memory_api"]["bounded_read"] is True
    assert read["memory_api"]["provider_read"]["provider_id"] == "sqlite"
    assert read["memory_api"]["provider_read"]["mode"] == "metadata_probe_after_legacy_policy_gate"
    assert read["memory_api"]["provider_read"]["policy_authority"] == "legacy_gateway_read_range"
    assert read["memory_api"]["provider_read"]["metadata_only"] is True
    assert read["memory_api"]["provider_read"]["memory_exists"] is True
    assert read["memory_api"]["provider_read"]["returns_provider_raw_content"] is False
    assert "content_raw" not in read["memory_api"]["provider_read"]
    assert read["entry_id"] == public_id

    created = gateway_memory_create(
        project,
        body={
            "title": "Memory API project candidate",
            "content": "Decision: Vault Memory API create remains candidate-first and does not write active memory.",
            "agent_id": "work-agent",
            "source_app": "test-suite",
            "workspace_id": "workspace-a",
        },
        agent_id="work-agent",
    )
    assert created["status"] == "ok"
    assert created["candidate"]["status"] == "candidate_created"
    assert created["memory_api"]["legacy_equivalent"] == "/submit-candidate"
    assert created["safety"]["writes_active_knowledge"] is False

    updated = gateway_memory_update_request(
        project,
        memory_id=public_id,
        body={
            "agent_id": "work-agent",
            "patch": {"summary": "Use the new bounded Memory API facade."},
            "reason": "Keep the runbook current.",
        },
        agent_id="work-agent",
        allow_shared_candidates=True,
    )
    assert updated["status"] == "ok"
    assert updated["candidate"]["status"] == "candidate_created"
    assert updated["safety"]["update_request"] is True
    assert updated["safety"]["writes_active_knowledge"] is False

    deleted = gateway_memory_delete_request(
        project,
        memory_id=public_id,
        body={"agent_id": "work-agent", "reason": "Test the review candidate path."},
        agent_id="work-agent",
        allow_shared_candidates=True,
    )
    assert deleted["status"] == "ok"
    assert deleted["candidate"]["status"] == "candidate_created"
    assert deleted["safety"]["soft_delete_request"] is True
    assert deleted["safety"]["hard_delete"] is False

    with VaultDB(project / "vault.db") as db:
        active_count = db.conn.execute("SELECT count(*) AS count FROM knowledge").fetchone()["count"]
        public = db.get_knowledge(public_id)
        candidates = db.list_memory_candidates(status=None)

    assert active_count == 2
    assert public["status"] == "active"
    assert {row["memory_type"] for row in candidates} >= {
        "knowledge",
        "memory_update_candidate",
        "memory_delete_candidate",
    }

    audit = gateway_memory_audit(project, agent_id="work-agent", memory_id=public_id)
    assert audit["status"] == "ok"
    assert audit["safety"]["returns_raw_audit_payloads"] is False
    assert {row["action"] for row in audit["events"]} >= {
        "memory_api:update_requested",
        "memory_api:soft_delete_requested",
    }
    assert all("payload_json" not in row for row in audit["events"])

    timeline = gateway_memory_timeline(project, agent_id="work-agent", memory_id=public_id)
    assert timeline["status"] == "ok"
    assert timeline["current"]["id"] == public_id
    assert "content_raw" not in timeline["current"]
    assert timeline["safety"]["returns_raw_memory_content"] is False
    assert all("payload_json" not in row for row in timeline["audit_events"])


def test_gateway_http_memory_api_facade_routes(tmp_path):
    project, public_id, _private_id = _project(tmp_path)
    handler = make_gateway_handler(project, auth_token="secret", allow_shared_candidates=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address

        status, search = _post_json(
            host,
            port,
            "/memory/search",
            {"agent_id": "work-agent", "query": "Gateway", "limit": 5},
        )
        assert status == 200
        assert search["status"] == "ok"
        assert search["memory_api"]["endpoint"] == "/memory/search"
        assert search["memory_api"]["provider_read"]["returns_provider_raw_rows"] is False

        status, created = _post_json(
            host,
            port,
            "/memory/create",
            {
                "agent_id": "work-agent",
                "title": "HTTP Memory API candidate",
                "content": "Decision: HTTP Memory API create writes review candidates instead of active memory.",
            },
        )
        assert status == 200
        assert created["candidate"]["status"] == "candidate_created"
        assert created["safety"]["candidate_first"] is True

        status, read = _request_json(
            "GET",
            host,
            port,
            f"/memory/{public_id}?agent_id=work-agent&line_start=1&line_end=2",
            None,
        )
        assert status == 200
        assert read["status"] == "ok"
        assert read["entry_id"] == public_id

        status, updated = _request_json(
            "PATCH",
            host,
            port,
            f"/memory/{public_id}",
            {"agent_id": "work-agent", "patch": {"summary": "HTTP patch request candidate"}},
        )
        assert status == 200
        assert updated["candidate"]["status"] == "candidate_created"
        assert updated["safety"]["update_request"] is True

        status, deleted = _request_json(
            "DELETE",
            host,
            port,
            f"/memory/{public_id}?agent_id=work-agent",
            None,
        )
        assert status == 200
        assert deleted["candidate"]["status"] == "candidate_created"
        assert deleted["safety"]["soft_delete_request"] is True

        status, audit = _request_json(
            "GET",
            host,
            port,
            f"/memory/audit?agent_id=work-agent&memory_id={public_id}",
            None,
        )
        assert status == 200
        assert audit["status"] == "ok"
        assert audit["safety"]["returns_raw_audit_payloads"] is False

        status, timeline = _request_json(
            "GET",
            host,
            port,
            f"/memory/timeline?agent_id=work-agent&memory_id={public_id}",
            None,
        )
        assert status == 200
        assert timeline["status"] == "ok"
        assert timeline["current"]["id"] == public_id
    finally:
        server.shutdown()
        server.server_close()

    with VaultDB(project / "vault.db") as db:
        assert db.get_knowledge(public_id)["status"] == "active"
        assert db.conn.execute("SELECT count(*) AS count FROM knowledge").fetchone()["count"] == 2


def test_gateway_remote_semantic_helpers_use_safe_central_read_chain(monkeypatch):
    import vault.mcp_remote_semantic as remote_semantic

    client = _FakeRemoteSemanticClient()
    monkeypatch.setattr(remote_semantic, "_get_supabase_client", lambda: client)
    monkeypatch.setattr(remote_semantic, "_create_remote_semantic_query_provider", lambda: _FakeRemoteSemanticProvider())

    search = gateway_remote_semantic_search(
        query="central semantic read",
        agent_id="remote-agent",
        project_id="private-memory:a87aa9886d99",
    )

    assert search["count"] == 1
    assert search["agent_id"] == "remote-agent"
    assert search["safety"]["gateway_adapter"] is True
    assert search["safety"]["returns_raw_memory_content"] is False
    assert search["safety"]["returns_embedding_values"] is False
    assert search["safety"]["query_sent_to_embedding_provider"] is True
    assert search["safety"]["query_embedding_provider"] == "openai"
    assert search["safety"]["query_embedding_model"] == "text-embedding-3-small"
    assert "remote_semantic_query_text_sent_to_openai" in search["safety"]["query_provider_privacy_warnings"]
    assert search["safety"]["writes_active_knowledge"] is False
    result = search["results"][0]
    assert result["read_handle"] == "private-memory:a87aa9886d99:knowledge:2"
    assert result["recommended_next_tool"] == "vault_remote_snapshot_read"
    assert "content_preview" not in result

    read = gateway_remote_snapshot_read(
        read_handle=result["read_handle"],
        agent_id="remote-agent",
        project_id="private-memory:a87aa9886d99",
    )

    assert read["result_type"] == "bounded_central_snapshot_preview"
    assert read["safety"]["gateway_adapter"] is True
    assert read["safety"]["bounded_preview"] is True
    assert read["safety"]["returns_embedding_values"] is False
    assert read["result"]["content_preview"] == "Approved bounded preview."
    assert [call[0] for call in client.rpc_calls] == [
        "vault_match_readable_memory_embeddings",
        "vault_get_readable_memory_snapshot",
    ]


def test_gateway_http_remote_semantic_search_snapshot_read_and_audit(tmp_path, monkeypatch):
    import vault.mcp_remote_semantic as remote_semantic

    project, _public_id, _private_id = _project(tmp_path)
    client = _FakeRemoteSemanticClient()
    monkeypatch.setattr(remote_semantic, "_get_supabase_client", lambda: client)
    monkeypatch.setattr(remote_semantic, "_create_remote_semantic_query_provider", lambda: _FakeRemoteSemanticProvider())

    handler = make_gateway_handler(
        project,
        auth_token="secret",
        token_agent_map={"agent-secret": "remote-agent"},
        remote_semantic_enabled=True,
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        status, search = _post_json(
            host,
            port,
            "/remote-semantic-search",
            {
                "query": "central semantic read",
                "project_id": "private-memory:a87aa9886d99",
            },
            token="agent-secret",
        )
        assert status == 200
        assert search["count"] == 1
        assert search["safety"]["gateway_adapter"] is True
        assert search["safety"]["returns_raw_memory_content"] is False
        assert search["safety"]["query_embedding_provider"] == "openai"
        assert "remote_semantic_query_text_sent_to_openai" in search["safety"]["query_provider_privacy_warnings"]
        assert search["results"][0]["read_handle"] == "private-memory:a87aa9886d99:knowledge:2"

        status, read = _post_json(
            host,
            port,
            "/remote-snapshot-read",
            {
                "read_handle": search["results"][0]["read_handle"],
                "project_id": "private-memory:a87aa9886d99",
            },
            token="agent-secret",
        )
        assert status == 200
        assert read["result_type"] == "bounded_central_snapshot_preview"
        assert read["safety"]["bounded_preview"] is True
        assert read["result"]["content_preview"] == "Approved bounded preview."
    finally:
        server.shutdown()
        server.server_close()

    audit = project / "reports" / "gateway" / "audit.jsonl"
    lines = audit.read_text(encoding="utf-8").splitlines()
    assert any('"event": "remote_semantic_search"' in line for line in lines)
    assert any('"event": "remote_snapshot_read"' in line for line in lines)
    parsed = [json.loads(line) for line in lines]
    semantic_rows = [row for row in parsed if row.get("event") == "remote_semantic_search"]
    assert semantic_rows[-1]["query_chars"] == len("central semantic read")
    assert "query" not in semantic_rows[-1]


def test_gateway_remote_semantic_http_requires_enablement_and_token_agent_binding(tmp_path, monkeypatch):
    import vault.mcp_remote_semantic as remote_semantic

    project, _public_id, _private_id = _project(tmp_path)
    client = _FakeRemoteSemanticClient()
    monkeypatch.setattr(remote_semantic, "_get_supabase_client", lambda: client)
    monkeypatch.setattr(remote_semantic, "_create_remote_semantic_query_provider", lambda: _FakeRemoteSemanticProvider())

    disabled_handler = make_gateway_handler(project, auth_token="secret")
    disabled_server = ThreadingHTTPServer(("127.0.0.1", 0), disabled_handler)
    disabled_thread = threading.Thread(target=disabled_server.serve_forever, daemon=True)
    disabled_thread.start()
    try:
        host, port = disabled_server.server_address
        status, blocked = _post_json(
            host,
            port,
            "/remote-semantic-search",
            {"agent_id": "remote-agent", "query": "central semantic read", "project_id": "private-memory:a87aa9886d99"},
        )
        assert status == 403
        assert blocked["error"] == "remote_semantic_disabled"
        assert blocked["status"] == "blocked"
    finally:
        disabled_server.shutdown()
        disabled_server.server_close()

    bound_handler = make_gateway_handler(
        project,
        auth_token="secret",
        token_agent_map={"agent-secret": "remote-agent"},
        remote_semantic_enabled=True,
    )
    bound_server = ThreadingHTTPServer(("127.0.0.1", 0), bound_handler)
    bound_thread = threading.Thread(target=bound_server.serve_forever, daemon=True)
    bound_thread.start()
    try:
        host, port = bound_server.server_address
        status, unbound = _post_json(
            host,
            port,
            "/remote-semantic-search",
            {"agent_id": "remote-agent", "query": "central semantic read", "project_id": "private-memory:a87aa9886d99"},
            token="secret",
        )
        assert status == 403
        assert unbound["error"] == "agent_token_binding_required"

        status, mismatch = _post_json(
            host,
            port,
            "/remote-semantic-search",
            {"agent_id": "other-agent", "query": "central semantic read", "project_id": "private-memory:a87aa9886d99"},
            token="agent-secret",
        )
        assert status == 403
        assert mismatch["error"] == "agent_token_mismatch"
    finally:
        bound_server.shutdown()
        bound_server.server_close()


def test_gateway_bounded_worker_pool_rejects_excess_requests():
    entered = threading.Event()
    release = threading.Event()

    class BlockingHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/hold":
                entered.set()
                release.wait(timeout=5)
            body = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *args):
            return

    server = BoundedThreadPoolHTTPServer(("127.0.0.1", 0), BlockingHandler, max_workers=1)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    first_thread = None
    first_conn = None
    try:
        host, port = server.server_address
        first_conn = http.client.HTTPConnection(host, port, timeout=5)

        def hold_request():
            assert first_conn is not None
            first_conn.request("GET", "/hold")
            response = first_conn.getresponse()
            response.read()

        first_thread = threading.Thread(target=hold_request)
        first_thread.start()
        assert entered.wait(timeout=5)

        second = http.client.HTTPConnection(host, port, timeout=5)
        second.request("GET", "/health")
        response = second.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        second.close()
        assert response.status == 503
        assert payload["error"] == "gateway_overloaded"
    finally:
        release.set()
        if first_thread is not None:
            first_thread.join(timeout=5)
        if first_conn is not None:
            first_conn.close()
        server.shutdown()
        server.server_close()


def test_gateway_drain_rejects_new_requests_and_waits_for_active_requests():
    entered = threading.Event()
    release = threading.Event()

    class BlockingHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/hold":
                entered.set()
                release.wait(timeout=5)
            body = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *args):
            return

    server = BoundedThreadPoolHTTPServer(
        ("127.0.0.1", 0),
        BlockingHandler,
        max_workers=2,
        shutdown_timeout_seconds=0.1,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    first_thread = None
    first_conn = None
    try:
        host, port = server.server_address
        first_conn = http.client.HTTPConnection(host, port, timeout=5)

        def hold_request():
            assert first_conn is not None
            first_conn.request("GET", "/hold")
            response = first_conn.getresponse()
            response.read()

        first_thread = threading.Thread(target=hold_request)
        first_thread.start()
        assert entered.wait(timeout=5)
        assert server.active_requests == 1

        server.begin_draining()
        assert server.wait_for_active_requests(timeout=0.01) is False

        second = http.client.HTTPConnection(host, port, timeout=5)
        second.request("GET", "/health")
        response = second.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        second.close()
        assert response.status == 503
        assert payload["error"] == "gateway_draining"

        release.set()
        assert server.wait_for_active_requests(timeout=5) is True
    finally:
        release.set()
        if first_thread is not None:
            first_thread.join(timeout=5)
        if first_conn is not None:
            first_conn.close()
        server.shutdown()
        server.server_close()


def test_gateway_http_search_submit_and_audit(tmp_path):
    project, _public_id, _private_id = _project(tmp_path)
    handler = make_gateway_handler(project, auth_token="secret")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        status, search = _post_json(
            host,
            port,
            "/search",
            {"agent_id": "work-agent", "query": "runbook", "max_sensitivity": "low"},
        )
        assert status == 200
        assert search["status"] == "ok"
        assert search["results"]

        status, submitted = _post_json(
            host,
            port,
            "/submit-candidate",
            {
                "agent_id": "work-agent",
                "title": "Gateway candidate",
                "content": "Decision: Gateway HTTP writes should create review candidates because agents need one safe door.",
            },
        )
        assert status == 200
        assert submitted["status"] == "ok"
    finally:
        server.shutdown()
        server.server_close()

    audit = project / "reports" / "gateway" / "audit.jsonl"
    assert audit.exists()
    lines = audit.read_text(encoding="utf-8").splitlines()
    assert any('"event": "search"' in line for line in lines)
    assert any('"event": "submit_candidate"' in line for line in lines)
    parsed = [json.loads(line) for line in lines]
    assert all(row.get("client_ip") == "127.0.0.1" for row in parsed)
    assert all("endpoint" in row for row in parsed)


def test_gateway_http_central_candidate_submit_pull_and_audit(tmp_path):
    project, _public_id, _private_id = _project(tmp_path)
    handler = make_gateway_handler(project, auth_token="secret")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        status, submitted = _post_json(
            host,
            port,
            "/central-candidates/submit",
            {
                "agent_id": "phone-agent",
                "title": "HTTP central candidate",
                "content": "Decision: Gateway central candidates enter the central inbox before local review.",
            },
        )
        assert status == 200
        assert submitted["ok"] is True
        assert submitted["status"] == "candidate"

        status, preview = _post_json(
            host,
            port,
            "/central-candidates/pull",
            {"agent_id": "review-agent", "apply": False},
        )
        assert status == 200
        assert preview["count"] == 1
        assert preview["imported_count"] == 0

        status, applied = _post_json(
            host,
            port,
            "/central-candidates/pull",
            {"agent_id": "review-agent", "apply": True},
        )
        assert status == 200
        assert applied["imported_count"] == 1
    finally:
        server.shutdown()
        server.server_close()

    with VaultDB(project / "vault.db") as db:
        candidates = db.list_memory_candidates(status=None)
        active_count = db.conn.execute("SELECT count(*) AS count FROM knowledge").fetchone()["count"]
    assert len(candidates) == 1
    assert candidates[0]["source"] == "central_memory_candidate"
    assert active_count == 2

    audit = project / "reports" / "gateway" / "audit.jsonl"
    lines = audit.read_text(encoding="utf-8").splitlines()
    assert any('"event": "central_candidate_submit"' in line for line in lines)
    assert any('"event": "central_candidate_pull"' in line for line in lines)


def test_gateway_ip_denylist_blocks_request_and_audits(tmp_path):
    project, _public_id, _private_id = _project(tmp_path)
    handler = make_gateway_handler(
        project,
        auth_token="secret",
        security_policy=GatewaySecurityPolicy(ip_denylist="127.0.0.1"),
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/health", headers={"Authorization": "Bearer secret", "User-Agent": "vault-test"})
        denied = conn.getresponse()
        body = json.loads(denied.read().decode("utf-8"))
        conn.close()
        assert denied.status == 403
        assert body["error"] == "ip_denied"
    finally:
        server.shutdown()
        server.server_close()

    audit = project / "reports" / "gateway" / "audit.jsonl"
    row = json.loads(audit.read_text(encoding="utf-8").splitlines()[-1])
    assert row["event"] == "request_blocked"
    assert row["reason"] == "ip_denied"
    assert row["client_ip"] == "127.0.0.1"
    assert row["user_agent"] == "vault-test"


def test_gateway_rate_limit_blocks_excess_requests(tmp_path):
    project, _public_id, _private_id = _project(tmp_path)
    handler = make_gateway_handler(
        project,
        auth_token="secret",
        security_policy=GatewaySecurityPolicy(rate_limit_per_minute=1, token_rate_limit_per_minute=0),
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/health", headers={"Authorization": "Bearer secret"})
        first = conn.getresponse()
        first.read()
        conn.close()
        assert first.status == 200

        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/health", headers={"Authorization": "Bearer secret"})
        limited = conn.getresponse()
        body = json.loads(limited.read().decode("utf-8"))
        conn.close()
        assert limited.status == 429
        assert body["error"] == "rate_limited"
    finally:
        server.shutdown()
        server.server_close()


def test_gateway_auth_failure_lockout(tmp_path):
    project, _public_id, _private_id = _project(tmp_path)
    handler = make_gateway_handler(
        project,
        auth_token="secret",
        security_policy=GatewaySecurityPolicy(rate_limit_per_minute=0, auth_failure_limit=1, auth_lockout_seconds=60),
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/health", headers={"Authorization": "Bearer wrong"})
        denied = conn.getresponse()
        denied_body = json.loads(denied.read().decode("utf-8"))
        conn.close()
        assert denied.status == 429
        assert denied_body["error"] == "auth_locked"

        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/health", headers={"Authorization": "Bearer secret"})
        locked = conn.getresponse()
        locked_body = json.loads(locked.read().decode("utf-8"))
        conn.close()
        assert locked.status == 429
        assert locked_body["error"] == "auth_locked"
    finally:
        server.shutdown()
        server.server_close()


def test_gateway_audit_report_summarizes_blocked_events(tmp_path):
    project = tmp_path / "project"
    audit = project / "reports" / "gateway" / "audit.jsonl"
    audit.parent.mkdir(parents=True)
    audit.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "created_at": "2026-07-02T00:00:00Z",
                        "event": "health",
                        "status": "ok",
                        "agent_id": "",
                        "client_ip": "127.0.0.1",
                        "endpoint": "/health",
                        "method": "GET",
                    }
                ),
                json.dumps(
                    {
                        "created_at": "2026-07-02T00:01:00Z",
                        "event": "auth_failed",
                        "status": "error",
                        "agent_id": "",
                        "client_ip": "10.0.0.5",
                        "user_agent": "bad-client",
                        "endpoint": "/search",
                        "method": "POST",
                        "reason": "auth_locked",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    payload = gateway_audit_report(project, limit=5)

    assert payload["status"] == "needs_review"
    assert payload["summary"]["total_events"] == 2
    assert payload["summary"]["blocked_or_failed_events"] == 1
    assert payload["summary"]["top_reasons"]["auth_locked"] == 1
    assert payload["recent_events"][-1]["user_agent"] == "bad-client"
    assert "Review auth_failed" in payload["next_action"]


def test_gateway_audit_log_rotates_when_size_limit_is_reached(tmp_path, monkeypatch):
    project, _public_id, _private_id = _project(tmp_path)
    audit = project / "reports" / "gateway" / "audit.jsonl"
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text("x" * 64, encoding="utf-8")
    monkeypatch.setenv("VAULT_GATEWAY_AUDIT_MAX_BYTES", "32")
    monkeypatch.setenv("VAULT_GATEWAY_AUDIT_BACKUPS", "2")
    handler = make_gateway_handler(project, auth_token="secret")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/health", headers={"Authorization": "Bearer secret"})
        response = conn.getresponse()
        response.read()
        conn.close()
        assert response.status == 200
    finally:
        server.shutdown()
        server.server_close()

    rotated = sorted(audit.parent.glob("audit-*.jsonl"))
    assert len(rotated) == 1
    assert rotated[0].read_text(encoding="utf-8") == "x" * 64
    current_rows = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
    assert current_rows[-1]["event"] == "health"
    report = gateway_audit_report(project)
    assert report["rotation"]["rotated_log_count"] == 1


def test_gateway_audit_cli_and_mcp_return_safe_summary(tmp_path, capsys):
    from vault.cli import main
    from vault.mcp import _set_project_dir, handle_tool_call

    project, _public_id, _private_id = _project(tmp_path)
    audit = project / "reports" / "gateway" / "audit.jsonl"
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(
        json.dumps(
            {
                "created_at": "2026-07-02T00:02:00Z",
                "event": "request_blocked",
                "status": "rate_limited",
                "agent_id": "codex",
                "client_ip": "127.0.0.1",
                "user_agent": "vault-test",
                "endpoint": "/search",
                "method": "POST",
                "reason": "rate_limited",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    main(["gateway", "audit", "--project-dir", str(project), "--json"])
    cli_payload = json.loads(capsys.readouterr().out)
    assert cli_payload["summary"]["blocked_or_failed_events"] == 1
    assert cli_payload["recent_events"][0]["reason"] == "rate_limited"

    _set_project_dir(project)
    result = handle_tool_call("vault_gateway_audit", {"limit": 5})
    mcp_payload = json.loads(result["result"])
    assert mcp_payload["ok"] is True
    assert mcp_payload["status"] == "needs_review"
    assert mcp_payload["recent_events"][0]["agent_id"] == "codex"


def test_gateway_http_tolerates_bad_numeric_fields(tmp_path):
    project, _public_id, _private_id = _project(tmp_path)
    handler = make_gateway_handler(project, auth_token="secret")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        status, search = _post_json(
            host,
            port,
            "/search",
            {"agent_id": "work-agent", "query": "runbook", "limit": "not-a-number"},
        )
        assert status == 200
        assert search["status"] == "ok"

        status, read = _post_json(
            host,
            port,
            "/read-range",
            {
                "agent_id": "work-agent",
                "knowledge_id": "not-a-number",
                "line_start": "also-bad",
            },
        )
        assert status == 200
        assert read["status"] == "error"
    finally:
        server.shutdown()
        server.server_close()


def test_gateway_no_auth_requires_localhost(tmp_path):
    with pytest.raises(ValueError):
        run_gateway(tmp_path, host="0.0.0.0", no_auth=True)


def test_gateway_tls_requires_cert_and_key(tmp_path):
    with pytest.raises(ValueError, match="TLS requires both"):
        run_gateway(tmp_path, no_auth=True, tls_cert=tmp_path / "cert.pem")
    with pytest.raises(FileNotFoundError, match="TLS certificate not found"):
        run_gateway(tmp_path, no_auth=True, tls_cert=tmp_path / "missing-cert.pem", tls_key=tmp_path / "missing-key.pem")


def test_gateway_startup_prints_token_and_remote_safety_checklist(tmp_path, monkeypatch, capsys):
    class FakeServer:
        def __init__(self, address, _handler, *, max_workers, shutdown_timeout_seconds):
            self.server_address = address
            self.max_workers = max_workers
            self.shutdown_timeout_seconds = shutdown_timeout_seconds
            self.active_requests = 0

        def serve_forever(self):
            raise KeyboardInterrupt

        def begin_draining(self):
            return None

        def wait_for_active_requests(self, *, timeout):
            return True

        def server_close(self):
            return None

    monkeypatch.setattr("vault.gateway.BoundedThreadPoolHTTPServer", FakeServer)
    run_gateway(
        tmp_path,
        host="0.0.0.0",
        port=8789,
        auth_token="stable-token",
        shutdown_timeout_seconds=2,
    )

    out = capsys.readouterr().out
    assert "Shutdown drain timeout: 2s" in out
    assert "SECURITY: copy this token only into trusted local agent configuration." in out
    assert "Token: stable-token" in out
    assert "REMOTE CHECKLIST: use TLS or a trusted reverse proxy" in out
    assert "Vault Gateway drain complete." in out


def test_remote_server_cli_and_generated_validation_script_end_to_end(tmp_path):
    project, _public_id, _private_id = _project(tmp_path)
    templates = write_remote_server_deploy_templates(output_dir=tmp_path / "templates", project_dir=project)
    validation_script = Path(templates["remote_clients"]["validation_script"])
    port = _free_local_port()
    url = f"http://127.0.0.1:{port}"
    token = "stable-test-token"
    env = os.environ.copy()
    env["VAULT_GATEWAY_TOKEN"] = token
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "vault.cli",
            "remote-server",
            "serve",
            "--project-dir",
            str(project),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        _wait_for_remote_server(url, token)
        read_only = subprocess.run(
            [
                sys.executable,
                str(validation_script),
                "--agent-id",
                "codex",
                "--query",
                "runbook",
            ],
            check=True,
            capture_output=True,
            text=True,
            env={**env, "VAULT_REMOTE_URL": url},
        )
        read_payload = json.loads(read_only.stdout)
        assert read_payload["ok"] is True
        assert read_payload["submitted_candidate"] is False
        assert [item["name"] for item in read_payload["checks"]] == ["health", "openapi", "search"]

        write_smoke = subprocess.run(
            [
                sys.executable,
                str(validation_script),
                "--agent-id",
                "codex",
                "--query",
                "runbook",
                "--submit-candidate",
            ],
            check=True,
            capture_output=True,
            text=True,
            env={**env, "VAULT_REMOTE_URL": url},
        )
        write_payload = json.loads(write_smoke.stdout)
        assert write_payload["ok"] is True
        assert write_payload["submitted_candidate"] is True
        assert [item["name"] for item in write_payload["checks"]] == [
            "health",
            "openapi",
            "search",
            "submit_candidate",
        ]
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    with VaultDB(project / "vault.db") as db:
        candidates = db.list_memory_candidates(status=None)
        active_count = db.conn.execute("SELECT count(*) AS count FROM knowledge").fetchone()["count"]
    assert len(candidates) == 1
    assert candidates[0]["source"] == "gateway:codex"
    assert active_count == 2


def test_remote_server_serve_requires_stable_token(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("VAULT_GATEWAY_TOKEN", raising=False)
    project, _public_id, _private_id = _project(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["remote-server", "serve", "--project-dir", str(project)])
    assert exc.value.code == 2
    output = capsys.readouterr().out
    assert "requires a stable token" in output
