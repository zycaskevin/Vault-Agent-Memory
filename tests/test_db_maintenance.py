import pytest

from vault.db import VaultDB


def test_db_maintenance_helpers_preserve_config_lint_and_stats(tmp_path):
    db = VaultDB(tmp_path / "vault.db").connect()
    try:
        kid = db.add_knowledge(title="Maintained memory", content_raw="remember this", trust=0.8)

        db.set_config("maintenance_key", "maintenance_value")
        assert db.get_config("maintenance_key") == "maintenance_value"
        assert db.get_config("missing", "fallback") == "fallback"

        db.add_lint_result(kid, "format", "ok")
        assert db.get_lint_results(kid)[0]["result"] == "ok"

        db.update_convergence(kid, "complete", 0.91)
        db.update_freshness(kid, 0.73, "2026-06-26T00:00:00+00:00")

        row = db.get_knowledge(kid)
        assert row["convergence_status"] == "complete"
        assert row["convergence_score"] == 0.91
        assert row["freshness"] == 0.73

        stats = db.stats()
        assert stats["knowledge_count"] == 1
        assert stats["convergence"]["complete"] == 1
        assert stats["avg_freshness"] == 0.73
        assert stats["db_path"].endswith("vault.db")
    finally:
        db.close()


def test_db_migration_helpers_preserve_schema_status_and_migrate(tmp_path):
    db = VaultDB(tmp_path / "vault.db").connect()
    try:
        status = db.schema_status()
        assert status["current_version"] == db.SCHEMA_VERSION
        assert status["target_version"] == db.SCHEMA_VERSION
        assert status["tables_missing"] == []
        assert status["needs_migration"] is False
        assert db.applied_migrations()

        migrated = db.migrate()
        assert migrated["ok"] is True
        assert migrated["to_version"] == db.SCHEMA_VERSION

        with pytest.raises(ValueError, match="unsupported target schema version"):
            db.migrate(db.SCHEMA_VERSION + 1)
    finally:
        db.close()
