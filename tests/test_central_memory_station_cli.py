import json
from datetime import datetime, timedelta, timezone

from vault.cli import main
from vault.db import VaultDB


def _read_json(capsys):
    return json.loads(capsys.readouterr().out)


def _init_project(tmp_path, capsys):
    project = tmp_path / "central-memory-project"
    main(["init", "--project-dir", str(project), "--json"])
    payload = _read_json(capsys)
    assert payload["ok"] is True
    return project


def test_start_lists_central_memory_station_surface(capsys):
    main(["start", "--json"])
    payload = _read_json(capsys)

    assert payload["ok"] is True
    assert payload["surface"] == "central_memory_station"
    assert "vault memory-sync status" in payload["commands"]
    assert "vault memory-lifecycle status" in payload["commands"]


def test_memory_sync_status_wraps_remote_status(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("VAULT_AGENT_REGISTRY_DIR", str(tmp_path / "registry"))
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    project = _init_project(tmp_path, capsys)

    main(["memory-sync", "status", "--project-dir", str(project), "--json"])
    payload = _read_json(capsys)

    assert payload["ok"] is True
    assert payload["action"] == "status"
    assert payload["central_memory_station"] is True
    assert payload["status"]["source_of_truth"] == "local_sqlite"
    assert payload["status"]["remote_model"]["candidate_requests"] is True


def test_memory_sync_push_can_submit_to_central_store(capsys, monkeypatch):
    import vault.remote_candidates as remote_candidates

    def fake_submit(**kwargs):
        return {
            "ok": True,
            "id": "central-cli",
            "status": "candidate",
            "central_candidate_table": "vault_memory_candidates_central",
            "title": kwargs["title"],
        }

    monkeypatch.setattr(
        remote_candidates,
        "submit_central_candidate_request",
        fake_submit,
    )

    main(
        [
            "memory-sync",
            "push",
            "--central-store",
            "--title",
            "CLI central candidate",
            "--content",
            "Central Memory Station push should target the central candidate table.",
            "--json",
        ]
    )
    payload = _read_json(capsys)

    assert payload["ok"] is True
    assert payload["id"] == "central-cli"
    assert payload["status"] == "candidate"
    assert payload["central_memory_station"] is True
    assert payload["central_candidate_table"] == "vault_memory_candidates_central"


def test_memory_sync_self_host_push_and_pull_round_trip(tmp_path, capsys):
    project = _init_project(tmp_path, capsys)

    main(
        [
            "memory-sync",
            "push",
            "--central-backend",
            "self-host",
            "--project-dir",
            str(project),
            "--from-agent",
            "phone-agent",
            "--title",
            "Self-host central candidate",
            "--content",
            "Self-host central candidates should land in vault-central.db before local review.",
            "--json",
        ]
    )
    pushed = _read_json(capsys)
    assert pushed["ok"] is True
    assert pushed["central_backend"] == "self-host"
    assert pushed["central_candidate_db"].endswith("vault-central.db")

    main(
        [
            "memory-sync",
            "pull",
            "--central-backend",
            "self-host",
            "--project-dir",
            str(project),
            "--agent-id",
            "review-agent",
            "--json",
        ]
    )
    preview = _read_json(capsys)
    assert preview["ok"] is True
    assert preview["count"] == 1
    assert preview["imported_count"] == 0

    main(
        [
            "memory-sync",
            "pull",
            "--central-backend",
            "self-host",
            "--project-dir",
            str(project),
            "--agent-id",
            "review-agent",
            "--apply",
            "--json",
        ]
    )
    pulled = _read_json(capsys)
    assert pulled["ok"] is True
    assert pulled["central_backend"] == "self-host"
    assert pulled["imported_count"] == 1
    with VaultDB(project / "vault.db") as db:
        candidates = db.list_memory_candidates(status=None)
        active_count = db.conn.execute("SELECT count(*) AS count FROM knowledge").fetchone()["count"]
    assert len(candidates) == 1
    assert candidates[0]["source"] == "central_memory_candidate"
    assert active_count == 0


def test_memory_review_inbox_lists_candidates_without_raw_content(tmp_path, capsys):
    project = _init_project(tmp_path, capsys)
    main(
        [
            "remember",
            "Central inbox candidate",
            "--content",
            "This raw candidate body should be hidden in the default central inbox.",
            "--reason",
            "Regression test for the review inbox",
            "--project-dir",
            str(project),
            "--json",
        ]
    )
    remembered = _read_json(capsys)
    assert remembered["ok"] is True

    main(["memory-review", "inbox", "--project-dir", str(project), "--json"])
    payload = _read_json(capsys)

    assert payload["ok"] is True
    assert payload["central_memory_station"] is True
    assert payload["candidate_count"] == 1
    candidate = payload["candidates"][0]
    assert candidate["id"] == remembered["candidate_id"]
    assert "content" not in candidate
    assert "content_preview" in candidate


def test_memory_lifecycle_status_and_archive_preview(tmp_path, capsys):
    project = _init_project(tmp_path, capsys)

    main(["memory-lifecycle", "status", "--project-dir", str(project), "--json"])
    status = _read_json(capsys)
    assert status["ok"] is True
    assert status["central_memory_station"] is True
    assert status["action"] == "status"

    main(["memory-lifecycle", "archive", "--project-dir", str(project), "--json"])
    archive = _read_json(capsys)
    assert archive["central_memory_station"] is True
    assert archive["dry_run"] is True
    assert archive["archived_count"] == 0


def test_memory_lifecycle_forget_writes_review_candidates_only(tmp_path, capsys):
    project = _init_project(tmp_path, capsys)
    expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    with VaultDB(project / "vault.db") as db:
        protected_id = db.add_knowledge(
            "Private expired central memory",
            "Private expired memory should become a forgetting review candidate.",
            expires_at=expired,
            scope="private",
        )

    main(["memory-lifecycle", "forget", "--write-candidates", "--project-dir", str(project), "--json"])
    payload = _read_json(capsys)

    assert payload["ok"] is True
    assert payload["hard_delete"] is False
    assert payload["candidate_suggestions"] == 1
    with VaultDB(project / "vault.db") as db:
        assert db.get_knowledge(protected_id)["status"] == "active"
        candidates = [
            item for item in db.list_memory_candidates(limit=10)
            if item["memory_type"] == "forgetting_suggestion"
        ]
    assert len(candidates) == 1


def test_ops_security_uses_existing_security_doctor(capsys):
    main(["ops", "security", "--json"])
    payload = _read_json(capsys)

    assert "ok" in payload
    assert "checks" in payload
    assert any(check["id"] == "mcp_hmac_required" for check in payload["checks"])
