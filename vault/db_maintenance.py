"""Config, lint, convergence, freshness, and stats helpers for VaultDB."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Any

from .diagnostics import embedding_stats


UsageStats = Callable[..., dict]


def set_config(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO config(key, value) VALUES(?, ?)",
        (key, value),
    )
    conn.commit()


def get_config(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def add_lint_result(
    conn: sqlite3.Connection,
    knowledge_id: int,
    check_type: str,
    result: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO lint_cache(knowledge_id, check_type, result, checked_at) VALUES(?,?,?,?)",
        (knowledge_id, check_type, result, now),
    )
    conn.commit()


def get_lint_results(conn: sqlite3.Connection, knowledge_id: int) -> list[dict]:
    rows = conn.execute("SELECT * FROM lint_cache WHERE knowledge_id=?", (knowledge_id,)).fetchall()
    return [dict(row) for row in rows]


def update_convergence(conn: sqlite3.Connection, knowledge_id: int, status: str, score: float) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE knowledge SET convergence_status=?, convergence_score=?, "
        "convergence_checked_at=? WHERE id=?",
        (status, score, now, knowledge_id),
    )
    conn.commit()


def update_freshness(
    conn: sqlite3.Connection,
    knowledge_id: int,
    freshness: float,
    last_verified: str = "",
) -> None:
    if not last_verified:
        last_verified = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE knowledge SET freshness=?, last_verified=? WHERE id=?",
        (freshness, last_verified, knowledge_id),
    )
    conn.commit()


def stats(
    conn: sqlite3.Connection,
    *,
    db_path: str | Path,
    vec_available: bool,
    vec_load_error: str,
    usage_stats: UsageStats,
) -> dict:
    knowledge_count = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
    vector_stats = embedding_stats(conn, vec_available=vec_available)
    edge_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    entity_count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]

    convergence_stats: dict[str, Any] = {}
    try:
        rows = conn.execute(
            "SELECT convergence_status, COUNT(*) FROM knowledge GROUP BY convergence_status"
        ).fetchall()
        for row in rows:
            convergence_stats[row[0]] = row[1]
    except Exception:
        pass

    avg_freshness = 0.0
    try:
        row = conn.execute("SELECT AVG(freshness) FROM knowledge").fetchone()
        avg_freshness = round(row[0], 3) if row[0] else 0.0
    except Exception:
        pass

    skill_count = 0
    try:
        skill_count = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    except Exception:
        pass

    usage = usage_stats(limit=5)
    path = Path(db_path)
    return {
        "knowledge_count": knowledge_count,
        "active_count": int(usage.get("status_counts", {}).get("active", 0)),
        "archived_count": int(usage.get("status_counts", {}).get("archived", 0)),
        "expired_active_count": int(usage.get("expired_active_count", 0)),
        "total_accesses": int(usage.get("total_accesses", 0)),
        "total_citations": int(usage.get("total_citations", 0)),
        **vector_stats,
        "edge_count": edge_count,
        "entity_count": entity_count,
        "skill_count": skill_count,
        "vec_available": vec_available,
        "vec_load_error": vec_load_error,
        "db_path": str(path),
        "db_size_mb": round(path.stat().st_size / 1024 / 1024, 2) if path.exists() else 0,
        "convergence": convergence_stats,
        "avg_freshness": avg_freshness,
    }
