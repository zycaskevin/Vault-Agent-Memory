import json

from vault.central_sync import run_central_memory_sync
from vault.cli import main
from vault.central_candidate_store import submit_central_candidate_local
from vault.db import VaultDB


def _init_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    VaultDB(project / "vault.db").connect().close()
    return project


def _memory_counts(project):
    with VaultDB(project / "vault.db") as db:
        active_count = db.conn.execute("SELECT count(*) AS count FROM knowledge").fetchone()["count"]
        candidate_count = len(db.list_memory_candidates(status=None))
    return active_count, candidate_count


def test_central_memory_sync_dry_run_writes_report_without_remote_calls(tmp_path):
    project = _init_project(tmp_path)
    report = tmp_path / "central-report.json"

    def fail_sync(*_args, **_kwargs):
        raise AssertionError("dry run should not call remote sync")

    payload = run_central_memory_sync(
        project,
        push_read_copy=True,
        push_central_store=True,
        push_central_vectors=True,
        pull_candidates=True,
        apply=True,
        dry_run=True,
        report_path=report,
        sync_knowledge=fail_sync,
        sync_document_map=fail_sync,
        sync_health=fail_sync,
        sync_central_store=fail_sync,
        sync_central_vectors=fail_sync,
        pull_remote_candidates=fail_sync,
    )

    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["operations"]["push_read_copy"]["status"] == "dry_run"
    assert payload["operations"]["push_central_store"]["status"] == "dry_run"
    assert payload["operations"]["push_central_vectors"]["status"] == "dry_run"
    assert payload["operations"]["pull_candidates"]["status"] == "dry_run"
    assert payload["safety"]["multi_master_active_memory"] is False
    assert payload["safety"]["remote_candidates_require_review"] is True
    assert payload["safety"]["active_memory_writes"] is False
    assert payload["operations"]["pull_candidates"]["safety"]["dry_run_read_only"] is True
    saved = json.loads(report.read_text(encoding="utf-8"))
    assert saved["mode"] == "central_memory_station_sync"
    assert saved["bidirectional_active_memory"] is False
    assert saved["safety"]["service_role_scope"] == "trusted_sync_host_only"


def test_central_memory_sync_runs_injected_push_and_pull(tmp_path):
    project = _init_project(tmp_path)
    calls = []

    def sync_knowledge(db_path, *, include_content=False):
        calls.append(("knowledge", db_path, include_content))

    def sync_document_map(db_path):
        calls.append(("document_map", db_path))
        return {"nodes_inserted": 1}

    def sync_health(db_path):
        calls.append(("health", db_path))
        return {"action": "inserted"}

    def sync_central_store(project_dir, **kwargs):
        calls.append(("central_store", str(project_dir), kwargs))
        return {"ok": True, "count": 1, "inserted_count": 1}

    def sync_central_vectors(project_dir, **kwargs):
        calls.append(("central_vectors", str(project_dir), kwargs))
        return {"ok": True, "count": 1, "inserted_count": 1, "table": "vault_memory_embeddings"}

    def pull_candidates(project_dir, **kwargs):
        calls.append(("pull", str(project_dir), kwargs))
        return {"ok": True, "count": 1, "imported_count": 1, "requests": []}

    payload = run_central_memory_sync(
        project,
        agent_id="sync-agent",
        push_read_copy=True,
        push_central_store=True,
        push_central_vectors=True,
        pull_candidates=True,
        candidate_limit=7,
        apply=True,
        include_content=True,
        sync_knowledge=sync_knowledge,
        sync_document_map=sync_document_map,
        sync_health=sync_health,
        sync_central_store=sync_central_store,
        sync_central_vectors=sync_central_vectors,
        pull_remote_candidates=pull_candidates,
    )

    assert payload["ok"] is True
    assert payload["operations"]["push_read_copy"]["status"] == "ok"
    assert payload["operations"]["push_central_store"]["status"] == "ok"
    assert payload["operations"]["push_central_vectors"]["status"] == "ok"
    assert payload["operations"]["pull_candidates"]["status"] == "ok"
    assert payload["safety"]["pull_candidates_apply_writes_local_candidates_only"] is True
    assert payload["safety"]["active_memory_writes"] is False
    assert payload["safety"]["central_vector_writes"] is True
    assert payload["safety"]["central_vectors_index_candidates"] is False
    assert calls[0][0] == "knowledge"
    assert calls[0][2] is True
    assert any(call[0] == "central_store" and call[2]["agent_id"] == "sync-agent" for call in calls)
    assert any(call[0] == "central_vectors" and call[2]["agent_id"] == "sync-agent" for call in calls)
    pull = calls[-1]
    assert pull[0] == "pull"
    assert pull[2]["agent_id"] == "sync-agent"
    assert pull[2]["limit"] == 7
    assert pull[2]["apply"] is True


def test_central_memory_sync_can_pull_self_host_candidates(tmp_path):
    project = _init_project(tmp_path)
    submitted = submit_central_candidate_local(
        project,
        title="Worker self-host candidate",
        content="Scheduled sync should import self-host central candidates into local review.",
        from_agent="phone-agent",
    )
    assert submitted["ok"] is True

    payload = run_central_memory_sync(
        project,
        agent_id="sync-agent",
        pull_candidates=True,
        central_backend="self-host",
        apply=True,
    )

    assert payload["ok"] is True
    assert payload["central_backend"] == "self-host"
    pull = payload["operations"]["pull_candidates"]
    assert pull["status"] == "ok"
    assert pull["central_backend"] == "self-host"
    assert pull["imported_count"] == 1
    with VaultDB(project / "vault.db") as db:
        rows = db.list_memory_candidates(status=None)
    assert len(rows) == 1
    assert rows[0]["source"] == "central_memory_candidate"


def test_multi_host_governed_sync_keeps_remote_submissions_candidate_first(tmp_path):
    project = _init_project(tmp_path)

    submitted = submit_central_candidate_local(
        project,
        title="Remote host candidate",
        content=(
            "Decision: remote hosts should submit candidates because official "
            "shared memory is promoted only by the trusted sync host."
        ),
        from_agent="coze-remote",
        trust=0.8,
        source_ref="remote://coze/session/1",
    )
    assert submitted["ok"] is True
    assert submitted["status"] == "candidate"
    assert _memory_counts(project) == (0, 0)

    preview = run_central_memory_sync(
        project,
        agent_id="sync-agent",
        pull_candidates=True,
        central_backend="self-host",
        apply=False,
    )
    assert preview["ok"] is True
    assert preview["bidirectional_active_memory"] is False
    assert preview["safety"]["multi_master_active_memory"] is False
    assert preview["safety"]["pull_candidates_preview_read_only"] is True
    assert preview["safety"]["pull_candidates_apply_writes_local_candidates_only"] is False
    preview_pull = preview["operations"]["pull_candidates"]
    assert preview_pull["safety"]["preview_read_only"] is True
    assert preview_pull["safety"]["writes_local_candidates"] is False
    assert preview_pull["safety"]["writes_active_memory"] is False
    assert preview_pull["count"] == 1
    assert preview_pull["imported_count"] == 0
    assert preview_pull["requests"][0]["from_agent"] == "coze-remote"
    assert _memory_counts(project) == (0, 0)

    applied = run_central_memory_sync(
        project,
        agent_id="sync-agent",
        pull_candidates=True,
        central_backend="self-host",
        apply=True,
        auto_promote_low_risk=False,
    )
    assert applied["ok"] is True
    assert applied["bidirectional_active_memory"] is False
    assert applied["safety"]["pull_candidates_apply_writes_local_candidates_only"] is True
    assert applied["safety"]["active_memory_writes"] is False
    applied_pull = applied["operations"]["pull_candidates"]
    assert applied_pull["safety"]["writes_local_candidates"] is True
    assert applied_pull["safety"]["writes_active_memory"] is False
    assert applied_pull["imported_count"] == 1
    assert applied_pull["requests"][0]["status"] == "imported"
    assert applied_pull["auto_promote"]["enabled"] is False

    with VaultDB(project / "vault.db") as db:
        candidates = db.list_memory_candidates(status=None)
        active_count = db.conn.execute("SELECT count(*) AS count FROM knowledge").fetchone()["count"]

    assert active_count == 0
    assert len(candidates) == 1
    assert candidates[0]["source"] == "central_memory_candidate"
    assert candidates[0]["status"] == "candidate"
    assert candidates[0]["memory_type"] == "remote_candidate"


def test_memory_sync_run_once_cli_dry_run_writes_central_report(tmp_path, capsys):
    project = _init_project(tmp_path)
    report = tmp_path / "cli-central-report.json"

    main(
        [
            "memory-sync",
            "run-once",
            "--project-dir",
            str(project),
            "--push-read-copy",
            "--push-central-store",
            "--push-central-vectors",
            "--pull-candidates",
            "--apply",
            "--dry-run",
            "--report",
            str(report),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["central_memory_station"] is True
    assert payload["operations"]["push_read_copy"]["status"] == "dry_run"
    assert payload["operations"]["push_central_store"]["status"] == "dry_run"
    assert payload["operations"]["push_central_vectors"]["status"] == "dry_run"
    assert payload["operations"]["pull_candidates"]["effective_apply"] is False
    assert report.exists()
