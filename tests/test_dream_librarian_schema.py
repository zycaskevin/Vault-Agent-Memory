"""Schema foundation tests for Guardrails Dream/Librarian DL-1."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrails_lite.guardrails_db import GuardrailsDB


CANDIDATE_COLUMNS = {
    "candidate_id",
    "created_at",
    "updated_at",
    "source_type",
    "source_agent",
    "source_session_id",
    "source_channel",
    "source_refs_json",
    "proposed_title",
    "summary",
    "content_draft",
    "category",
    "tags_json",
    "classification",
    "privacy_status",
    "privacy_flags_json",
    "dedupe_status",
    "dedupe_candidates_json",
    "status",
    "recommended_action",
    "decision_reason",
    "reviewer",
    "reviewed_at",
    "trust_initial",
    "freshness_initial",
    "convergence_status_initial",
    "audit_log_json",
}

REVIEW_ITEM_COLUMNS = {
    "review_id",
    "created_at",
    "updated_at",
    "source_report",
    "issue_type",
    "knowledge_ids_json",
    "titles_json",
    "safe_reason",
    "evidence_refs_json",
    "severity",
    "recommended_action",
    "status",
    "reviewer",
    "reviewed_at",
    "decision_reason",
    "audit_log_json",
}

CANDIDATE_INDEXES = {
    "idx_knowledge_candidates_status",
    "idx_knowledge_candidates_created_at",
    "idx_knowledge_candidates_source_session_id",
    "idx_knowledge_candidates_proposed_title",
}


def _table_columns(conn, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def _table_indexes(conn, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA index_list({table})")}


def test_dream_librarian_tables_columns_and_indexes_exist(tmp_path):
    db = GuardrailsDB(tmp_path / "guardrails.db").connect()
    try:
        tables = {
            row["name"]
            for row in db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "knowledge_candidates" in tables
        assert "knowledge_review_items" in tables
        assert CANDIDATE_COLUMNS <= _table_columns(db.conn, "knowledge_candidates")
        assert REVIEW_ITEM_COLUMNS <= _table_columns(db.conn, "knowledge_review_items")
        assert CANDIDATE_INDEXES <= _table_indexes(db.conn, "knowledge_candidates")
    finally:
        db.close()


def test_dream_librarian_schema_is_idempotent(tmp_path):
    db_path = tmp_path / "guardrails.db"

    first = GuardrailsDB(db_path).connect()
    first.close()

    second = GuardrailsDB(db_path).connect()
    try:
        assert CANDIDATE_COLUMNS <= _table_columns(second.conn, "knowledge_candidates")
        assert REVIEW_ITEM_COLUMNS <= _table_columns(second.conn, "knowledge_review_items")
        assert CANDIDATE_INDEXES <= _table_indexes(second.conn, "knowledge_candidates")
    finally:
        second.close()
