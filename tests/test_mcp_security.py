from vault import mcp_security
from vault.security import security_doctor


def test_mcp_security_rate_limit_can_be_disabled(monkeypatch):
    mcp_security.reset_rate_limiter()
    monkeypatch.setenv("VAULT_MCP_RATE_LIMIT_PER_MINUTE", "0")

    assert mcp_security.check_mcp_rate_limit("vault_stats", {"agent_id": "agent-a"}) is None
    assert mcp_security.check_mcp_rate_limit("vault_stats", {"agent_id": "agent-a"}) is None


def test_mcp_security_rate_limit_invalid_env_falls_back(monkeypatch):
    mcp_security.reset_rate_limiter()
    monkeypatch.setenv("VAULT_MCP_RATE_LIMIT_PER_MINUTE", "not-an-int")
    monkeypatch.setenv("VAULT_MCP_RATE_LIMIT_BURST", "not-an-int")

    assert mcp_security.check_mcp_rate_limit("vault_stats", {"agent_id": "agent-a"}) is None


def test_mcp_security_write_gate_requires_explicit_shared_grant():
    denied = mcp_security.check_write_allowed(
        "vault_add",
        {"agent_id": "agent-a"},
        {"scope": "shared", "sensitivity": "low"},
    )
    allowed = mcp_security.check_write_allowed(
        "vault_add",
        {"agent_id": "agent-a", "allow_shared": True},
        {"scope": "shared", "sensitivity": "low"},
    )

    assert denied is not None
    assert denied["error"] == "write_access_denied"
    assert "allow_shared" in denied["message"]
    assert allowed is None


def test_mcp_agent_signature_optional_without_signature(monkeypatch):
    monkeypatch.delenv("VAULT_MCP_REQUIRE_AGENT_SIGNATURE", raising=False)
    monkeypatch.delenv("VAULT_MCP_AGENT_SECRET", raising=False)

    assert mcp_security.check_agent_signature("vault_stats", {"agent_id": "agent-a"}) is None


def test_mcp_agent_signature_required_rejects_missing_signature(monkeypatch):
    monkeypatch.setenv("VAULT_MCP_REQUIRE_AGENT_SIGNATURE", "1")
    monkeypatch.setenv("VAULT_MCP_AGENT_SECRET", "local-secret")

    denied = mcp_security.check_agent_signature("vault_stats", {"agent_id": "agent-a"})

    assert denied is not None
    assert denied["error"] == "agent_signature_required"
    assert "invalid" in denied["message"] or "require" in denied["message"]


def test_mcp_agent_signature_required_accepts_valid_hmac(monkeypatch):
    monkeypatch.setenv("VAULT_MCP_REQUIRE_AGENT_SIGNATURE", "1")
    monkeypatch.setenv("VAULT_MCP_AGENT_SECRET_AGENT_A", "scoped-secret")
    args = {"agent_id": "agent-a", "query": "deployment"}
    args["agent_signature"] = mcp_security.sign_agent_request("vault_search", args, "scoped-secret")

    assert mcp_security.check_agent_signature("vault_search", args) is None


def test_mcp_agent_signature_optional_rejects_bad_signature(monkeypatch):
    monkeypatch.delenv("VAULT_MCP_REQUIRE_AGENT_SIGNATURE", raising=False)
    monkeypatch.setenv("VAULT_MCP_AGENT_SECRET", "local-secret")

    denied = mcp_security.check_agent_signature(
        "vault_stats",
        {"agent_id": "agent-a", "agent_signature": "bad"},
    )

    assert denied is not None
    assert denied["failure_mode"] == "agent_signature_required"


def test_security_doctor_reports_hmac_posture():
    loose = security_doctor({})
    assert loose["ok"] is False
    assert loose["warning_count"] == 2
    assert any(check["id"] == "mcp_hmac_required" and not check["ok"] for check in loose["checks"])

    strict = security_doctor(
        {
            "VAULT_MCP_REQUIRE_AGENT_SIGNATURE": "1",
            "VAULT_MCP_AGENT_SECRET_CODEX": "secret",
            "VAULT_GUI_TOKEN": "gui-token",
        }
    )
    assert strict["ok"] is True
    assert strict["warning_count"] == 0
    assert strict["governance_contract"]["semantics"]["remote_writes_enter_candidates"] is True
    assert strict["governance_contract"]["write_policy"]["direct_remote_active_memory_writes"] is False


def _doctor_check(payload, check_id):
    return next(check for check in payload["checks"] if check["id"] == check_id)


def test_security_doctor_warns_when_service_role_is_not_on_trusted_host():
    payload = security_doctor({"SUPABASE_SERVICE_ROLE_KEY": "service-role-secret"})

    check = _doctor_check(payload, "supabase_service_role_trusted_host")
    assert check["ok"] is False
    assert payload["supabase"]["service_role_key_present"] is True
    assert payload["supabase"]["trusted_sync_host"] is False
    assert payload["supabase"]["service_role_policy"] == "remote_readers_must_not_receive_service_role"
    assert "service-role-secret" not in str(payload)

    trusted = security_doctor(
        {
            "SUPABASE_SERVICE_ROLE_KEY": "service-role-secret",
            "VAULT_SUPABASE_TRUSTED_SYNC_HOST": "1",
        }
    )
    trusted_check = _doctor_check(trusted, "supabase_service_role_trusted_host")
    assert trusted_check["ok"] is True
    assert trusted["supabase"]["service_role_policy"] == "allowed_on_trusted_sync_host"


def test_security_doctor_checks_self_host_remote_server_boundaries(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "vault.db").write_bytes(b"sqlite placeholder")
    semantic_binding_env = "VAULT_GATEWAY_" + "TOKEN_AGENT_MAP"

    risky = security_doctor(
        {
            "VAULT_REMOTE_SERVER_BIND": "0.0.0.0",
            "VAULT_GATEWAY_REMOTE_SEMANTIC_ENABLED": "1",
        },
        project_dir=project,
    )

    assert _doctor_check(risky, "remote_server_stable_token")["ok"] is False
    assert _doctor_check(risky, "remote_server_transport_boundary")["ok"] is False
    assert _doctor_check(risky, "remote_semantic_token_agent_binding")["ok"] is False
    assert _doctor_check(risky, "remote_server_backup_plan")["ok"] is False
    assert risky["self_host"]["signals_detected"] is True
    assert risky["self_host"]["public_bind"] is True

    backup_dir = project / "backups"
    backup_dir.mkdir()
    (backup_dir / "vault-test.db").write_bytes(b"backup placeholder")
    hardened = security_doctor(
        {
            "VAULT_REMOTE_SERVER_BIND": "0.0.0.0",
            "VAULT_GATEWAY_TOKEN": "stable-token",
            "VAULT_GATEWAY_REMOTE_SEMANTIC_ENABLED": "1",
            semantic_binding_env: "agent-auth=remote-agent",
            "VAULT_REMOTE_SERVER_BEHIND_VPN": "1",
        },
        project_dir=project,
    )

    assert _doctor_check(hardened, "remote_server_stable_token")["ok"] is True
    assert _doctor_check(hardened, "remote_server_transport_boundary")["ok"] is True
    assert _doctor_check(hardened, "remote_semantic_token_agent_binding")["ok"] is True
    assert _doctor_check(hardened, "remote_server_backup_plan")["ok"] is True
    assert hardened["self_host"]["backup"]["latest_backup"].endswith("vault-test.db")
