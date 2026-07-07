import json
import sqlite3

from vault.cli import main
from vault.db import VaultDB


def _init_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with VaultDB(project / "vault.db") as db:
        db.add_knowledge(
            title="Shared fact",
            content_raw="Shared reviewed memory.",
            scope="project",
            sensitivity="low",
        )
    return project


def test_vector_index_status_empty_is_local_only(tmp_path, capsys):
    project = _init_project(tmp_path)

    main(["--project-dir", str(project), "vector-index", "status", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert payload["artifact_type"] == "central_derived_vector_index_status"
    assert payload["status"] == "empty"
    assert payload["index_role"] == "derived_rebuildable_cache"
    assert payload["source_of_truth"] == "local_sqlite_markdown"
    assert payload["remote_read_enabled"] is False
    assert payload["remote_writes_policy"] == "candidate_first_only"
    assert payload["readiness"]["local_vector_search"] is False
    assert payload["policy"]["index_candidates"] is False
    assert payload["counts"]["default_indexable_active_rows"] == 1
    assert payload["counts"]["semantic_vector_rows"] == 0


def test_vector_index_status_reports_stale_and_shared_read_risk(tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()
    db_path = project / "vault.db"
    with VaultDB(db_path) as db:
        shared_id = db.add_knowledge(
            title="Shared fact",
            content_raw="Shared reviewed memory.",
            scope="project",
            sensitivity="low",
        )
        private_id = db.add_knowledge(
            title="Private fact",
            content_raw="Private memory.",
            scope="private",
            sensitivity="low",
        )
        high_id = db.add_knowledge(
            title="High fact",
            content_raw="High sensitivity memory.",
            scope="project",
            sensitivity="high",
        )
        archived_id = db.add_knowledge(
            title="Archived fact",
            content_raw="Archived memory.",
            scope="project",
            sensitivity="low",
        )
        for knowledge_id, content_hash in [
            (shared_id, "shared-current"),
            (private_id, "private-current"),
            (high_id, "high-current"),
            (archived_id, "archived-current"),
        ]:
            db.conn.execute("UPDATE knowledge SET content_hash=? WHERE id=?", (content_hash, knowledge_id))
        db.conn.execute("UPDATE knowledge SET status='archived' WHERE id=?", (archived_id,))
        for knowledge_id, content_hash in [
            (shared_id, "shared-old"),
            (private_id, "private-current"),
            (high_id, "high-current"),
            (archived_id, "archived-current"),
        ]:
            db.conn.execute(
                """INSERT INTO semantic_vectors
                   (knowledge_id, vector_kind, item_uid, provider_id, dimension, vector,
                    source_text, content_hash, updated_at)
                   VALUES (?, 'claim', ?, 'hash-deterministic-v1', 8,
                           '[0,0,0,0,0,0,0,1]', 'text', ?, '2026-07-07T00:00:00Z')""",
                (knowledge_id, f"claim-{knowledge_id}", content_hash),
            )
        db.conn.commit()

    main(["--project-dir", str(project), "vector-index", "doctor", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert payload["action"] == "doctor"
    assert payload["status"] == "stale"
    assert payload["ok"] is False
    assert payload["counts"]["semantic_vector_rows"] == 4
    assert payload["counts"]["stale_vector_rows"] == 1
    assert payload["counts"]["shared_remote_risk_vector_rows"] == 3
    assert payload["readiness"]["shared_remote_vector_read"] is False
    assert any("shared-read policy" in item or "local-only" in item for item in payload["next_actions"])


def test_vector_index_plan_groups_metadata_without_raw_content(tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()
    db_path = project / "vault.db"
    with VaultDB(db_path) as db:
        missing_id = db.add_knowledge(
            title="Missing vector",
            content_raw="raw content should not appear in plan",
            scope="project",
            sensitivity="low",
        )
        stale_id = db.add_knowledge(
            title="Stale vector",
            content_raw="stale raw content should not appear",
            scope="project",
            sensitivity="low",
        )
        private_id = db.add_knowledge(
            title="Private vector",
            content_raw="private raw content should not appear",
            scope="private",
            sensitivity="low",
        )
        for knowledge_id, content_hash in [
            (missing_id, "missing-current"),
            (stale_id, "stale-current"),
            (private_id, "private-current"),
        ]:
            db.conn.execute("UPDATE knowledge SET content_hash=? WHERE id=?", (content_hash, knowledge_id))
        for knowledge_id, content_hash in [
            (stale_id, "stale-old"),
            (private_id, "private-current"),
        ]:
            db.conn.execute(
                """INSERT INTO semantic_vectors
                   (knowledge_id, vector_kind, item_uid, provider_id, dimension, vector,
                    source_text, content_hash, updated_at)
                   VALUES (?, 'claim', ?, 'hash-deterministic-v1', 8,
                           '[0,0,0,0,0,0,0,1]', 'source text hidden', ?, '2026-07-07T00:00:00Z')""",
                (knowledge_id, f"claim-{knowledge_id}", content_hash),
            )
        db.conn.commit()
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute(
            """INSERT INTO semantic_vectors
               (knowledge_id, vector_kind, item_uid, provider_id, dimension, vector,
                source_text, content_hash, updated_at)
               VALUES (9999, 'claim', 'claim-9999', 'hash-deterministic-v1', 8,
                       '[0,0,0,0,0,0,0,1]', 'source text hidden', 'orphan-current',
                       '2026-07-07T00:00:00Z')"""
        )
        conn.commit()

    main(["--project-dir", str(project), "vector-index", "plan", "--json", "--limit", "5"])
    payload = json.loads(capsys.readouterr().out)

    assert payload["artifact_type"] == "central_derived_vector_index_plan"
    assert payload["dry_run"] is True
    assert payload["counts"]["missing_default_policy_rows_sampled"] == 1
    assert payload["counts"]["stale_rows_sampled"] == 1
    assert payload["counts"]["shared_remote_risk_rows_sampled"] == 1
    assert payload["counts"]["orphan_vector_rows_sampled"] == 1
    assert payload["groups"]["missing_default_policy"][0]["knowledge_id"] == missing_id
    assert payload["groups"]["stale"][0]["knowledge_id"] == stale_id
    assert payload["groups"]["shared_remote_risk"][0]["knowledge_id"] == private_id
    rendered = json.dumps(payload)
    assert "raw content should not appear" not in rendered
    assert "source text hidden" not in rendered
    assert "vault semantic rebuild --changed-only" in payload["recommended_commands"]


def test_vector_index_plan_write_report_is_metadata_only(tmp_path, capsys):
    project = _init_project(tmp_path)

    main(["--project-dir", str(project), "vector-index", "plan", "--write-report", "--json", "--limit", "5"])
    payload = json.loads(capsys.readouterr().out)

    assert payload["paths"]["json"] == "reports/vector-index/plan-latest.json"
    assert payload["paths"]["markdown"] == "reports/vector-index/plan-latest.md"
    json_report = project / payload["paths"]["json"]
    markdown_report = project / payload["paths"]["markdown"]
    assert json_report.exists()
    assert markdown_report.exists()

    rendered_json = json_report.read_text(encoding="utf-8")
    rendered_markdown = markdown_report.read_text(encoding="utf-8")
    assert "Shared reviewed memory." not in rendered_json
    assert "Shared reviewed memory." not in rendered_markdown
    assert "# Vault Vector Index Plan" in rendered_markdown
    assert "metadata-only dry run" in rendered_markdown


def test_vector_index_repair_dry_run_does_not_write_vectors(tmp_path, capsys):
    project = _init_project(tmp_path)

    main(["--project-dir", str(project), "vector-index", "repair", "--json", "--limit", "5"])
    payload = json.loads(capsys.readouterr().out)

    assert payload["artifact_type"] == "central_derived_vector_index_repair"
    assert payload["dry_run"] is True
    assert payload["apply"] is False
    assert payload["before"]["status"] == "empty"
    assert payload["before"]["repair_rows_sampled"] == 1
    assert payload["rebuild"] is None
    assert payload["after"] is None
    assert payload["safety"]["semantic_vector_writes"] is False
    assert "vault vector-index repair" in payload["next_actions"][1]
    with VaultDB(project / "vault.db") as db:
        count = db.conn.execute("SELECT count(*) AS count FROM semantic_vectors").fetchone()["count"]
    assert count == 0


def test_vector_index_repair_apply_hash_writes_metadata_report_without_raw_content(tmp_path, capsys):
    project = _init_project(tmp_path)

    main(
        [
            "--project-dir",
            str(project),
            "vector-index",
            "repair",
            "--apply",
            "--allow-hash",
            "--hash-dim",
            "8",
            "--write-report",
            "--json",
            "--limit",
            "5",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["dry_run"] is False
    assert payload["apply"] is True
    assert payload["rebuild"]["provider_id"] == "hash-deterministic-v1"
    assert payload["rebuild"]["knowledge_rows"] == 1
    assert payload["after"]["semantic_vector_rows"] >= 1
    assert payload["after"]["stale_vector_rows"] == 0
    assert payload["safety"]["writes_candidates"] is False
    assert payload["safety"]["active_memory_writes"] is False
    assert payload["safety"]["remote_vector_read"] is False
    assert payload["paths"]["json"] == "reports/vector-index/repair-latest.json"
    assert payload["paths"]["markdown"] == "reports/vector-index/repair-latest.md"
    report_json = (project / payload["paths"]["json"]).read_text(encoding="utf-8")
    report_md = (project / payload["paths"]["markdown"]).read_text(encoding="utf-8")
    assert "Shared reviewed memory." not in report_json
    assert "Shared reviewed memory." not in report_md
    assert "# Vault Vector Index Repair" in report_md
