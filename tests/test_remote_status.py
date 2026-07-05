import json
from datetime import datetime, timezone


def test_remote_status_reports_local_source_of_truth(tmp_path, capsys, monkeypatch):
    from vault.cli import main

    registry_dir = tmp_path / "registry"
    monkeypatch.setenv("VAULT_AGENT_REGISTRY_DIR", str(registry_dir))
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("VAULT_SUPABASE_TRUSTED_SYNC_HOST", raising=False)

    project = tmp_path / "vault-project"
    main(["init", "--project-dir", str(project)])
    capsys.readouterr()

    main(["remote", "status", "--project-dir", str(project), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["source_of_truth"] == "local_sqlite"
    assert payload["remote_model"]["mode"] == "supabase_reviewed_read_copy_with_candidate_inbox"
    assert payload["remote_model"]["bidirectional"] is False
    assert payload["remote_model"]["candidate_requests"] is True
    assert payload["remote_model"]["realtime"] is False
    assert payload["remote_model"]["realtime_kind"] == "scheduled_or_manual"
    assert payload["local"]["db_exists"] is True
    assert payload["remote_reader"]["targets"]["shell"] is False
    assert any("setup-agent" in item for item in payload["next_actions"])


def test_remote_status_detects_templates_roster_and_sync_report(tmp_path, monkeypatch):
    from vault.cli import main
    from vault.remote_status import build_remote_status

    registry_dir = tmp_path / "registry"
    monkeypatch.setenv("VAULT_AGENT_REGISTRY_DIR", str(registry_dir))
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-test-key")

    project = tmp_path / "vault-project"
    main(["init", "--project-dir", str(project)])

    install = project / "agent-install"
    install.mkdir()
    (install / "remote-reader-smoke.sh").write_text("#!/usr/bin/env sh\n", encoding="utf-8")
    (install / "supabase-sync.cron").write_text("* * * * * vault sync\n", encoding="utf-8")
    (install / "supabase-realtime-sync.sh").write_text("#!/usr/bin/env sh\n", encoding="utf-8")
    (install / "agent-roster.json").write_text(
        json.dumps(
            {
                "agents": [
                    {
                        "agent_id": "coze",
                        "remote_reader": True,
                        "can_write_shared": False,
                        "can_promote": False,
                    },
                    {
                        "agent_id": "codex",
                        "remote_reader": False,
                        "can_write_shared": True,
                        "can_promote": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    reports = project / "reports"
    reports.mkdir()
    (reports / "supabase-sync-latest.json").write_text(
        json.dumps({"status": "ok", "last_synced_at": datetime.now(timezone.utc).isoformat(), "processed": 7}),
        encoding="utf-8",
    )

    payload = build_remote_status(project)

    assert payload["ok"] is True
    assert payload["supabase"]["url_configured"] is True
    assert payload["supabase"]["anon_key_configured"] is True
    assert payload["remote_reader"]["targets"]["shell"] is True
    assert payload["sync"]["templates"]["targets"]["cron"] is True
    assert payload["sync"]["templates"]["targets"]["realtime"] is True
    assert payload["remote_model"]["realtime"] is True
    assert payload["remote_model"]["realtime_kind"] == "near_realtime_push"
    assert payload["sync"]["last_report"]["exists"] is True
    assert payload["sync"]["last_report"]["stale"] is False
    assert payload["agent_access"]["remote_readers"] == ["coze"]
    assert payload["agent_access"]["shared_writers"] == ["codex"]
    assert not any(item["code"] == "sync_report_missing" for item in payload["warnings"])


def test_remote_status_warns_when_service_role_is_not_on_trusted_host(tmp_path, monkeypatch):
    from vault.cli import main
    from vault.remote_status import build_remote_status

    monkeypatch.setenv("VAULT_AGENT_REGISTRY_DIR", str(tmp_path / "registry"))
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-test-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-test-key")
    monkeypatch.delenv("VAULT_SUPABASE_TRUSTED_SYNC_HOST", raising=False)
    monkeypatch.delenv("VAULT_TRUSTED_SYNC_HOST", raising=False)
    project = tmp_path / "vault-project"
    main(["init", "--project-dir", str(project)])

    payload = build_remote_status(project)

    assert payload["supabase"]["service_role_key_present"] is True
    assert payload["supabase"]["trusted_sync_host"] is False
    assert payload["supabase"]["service_role_policy"] == "remote_readers_must_not_receive_service_role"
    assert any(item["code"] == "service_role_key_present" for item in payload["warnings"])


def test_remote_status_allows_service_role_on_declared_trusted_sync_host(tmp_path, monkeypatch):
    from vault.cli import main
    from vault.remote_status import build_remote_status

    monkeypatch.setenv("VAULT_AGENT_REGISTRY_DIR", str(tmp_path / "registry"))
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-test-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-test-key")
    monkeypatch.setenv("VAULT_SUPABASE_TRUSTED_SYNC_HOST", "1")
    project = tmp_path / "vault-project"
    main(["init", "--project-dir", str(project)])

    payload = build_remote_status(project)

    assert payload["supabase"]["service_role_key_present"] is True
    assert payload["supabase"]["trusted_sync_host"] is True
    assert payload["supabase"]["service_role_policy"] == "allowed_on_trusted_sync_host"
    assert not any(item["code"] == "service_role_key_present" for item in payload["warnings"])


def test_remote_status_prefers_central_memory_sync_report(tmp_path, monkeypatch):
    from vault.cli import main
    from vault.remote_status import build_remote_status

    monkeypatch.setenv("VAULT_AGENT_REGISTRY_DIR", str(tmp_path / "registry"))
    project = tmp_path / "vault-project"
    main(["init", "--project-dir", str(project)])

    reports = project / "reports"
    reports.mkdir()
    central = reports / "central-memory-sync-latest.json"
    central.write_text(
        json.dumps(
            {
                "status": "ok",
                "mode": "central_memory_station_sync",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    (reports / "supabase-sync-latest.json").write_text(
        json.dumps({"status": "older", "completed_at": "2026-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )

    payload = build_remote_status(project)

    assert payload["sync"]["last_report"]["path"] == str(central)
    assert payload["sync"]["last_report"]["status"] == "ok"


def test_remote_status_reports_self_host_central_candidate_inbox(tmp_path, monkeypatch):
    from vault.central_candidate_store import submit_central_candidate_local
    from vault.cli import main
    from vault.remote_status import build_remote_status

    monkeypatch.setenv("VAULT_AGENT_REGISTRY_DIR", str(tmp_path / "registry"))
    project = tmp_path / "vault-project"
    main(["init", "--project-dir", str(project)])

    submitted = submit_central_candidate_local(
        project,
        title="Self-host status candidate",
        content="Remote status should report self-host central candidate inbox counts.",
        from_agent="phone-agent",
    )
    assert submitted["ok"] is True

    payload = build_remote_status(project)

    assert payload["remote_model"]["self_hosted_candidate_inbox"] is True
    assert payload["self_host"]["db_exists"] is True
    assert payload["self_host"]["table"] == "vault_memory_candidates_central"
    assert payload["self_host"]["candidate_count"] == 1
    assert payload["self_host"]["pending_count"] == 1


def test_remote_status_human_output(tmp_path, capsys, monkeypatch):
    from vault.cli import main

    monkeypatch.setenv("VAULT_AGENT_REGISTRY_DIR", str(tmp_path / "registry"))
    project = tmp_path / "vault-project"
    main(["init", "--project-dir", str(project)])
    capsys.readouterr()

    main(["remote", "status", "--project-dir", str(project)])
    output = capsys.readouterr().out

    assert "Vault remote status" in output
    assert "Source of truth: local vault.db" in output
    assert "candidate request inbox" in output
