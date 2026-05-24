"""Safe explicit local-only promotion for Dream/Librarian candidates.

DL-3 promotes an already approved candidate into formal local knowledge.  It is
intentionally review-gated and sync-free: callers must pass ``no_sync=True`` and
all safety gates run before any raw file, knowledge row, or candidate status is
modified.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guardrails_lite.dream_queue import _json_dumps, _row_dict, _row_to_candidate
from guardrails_lite.guardrails_db import GuardrailsDB
from guardrails_lite.privacy_scanner import scan_entry

_BLOCKING_DEDUPE_STATUSES = {"duplicate", "near_duplicate", "conflict"}
_SAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connection(db: GuardrailsDB | sqlite3.Connection) -> sqlite3.Connection:
    if isinstance(db, GuardrailsDB):
        if db.conn is None:
            raise ValueError("database is not connected")
        return db.conn
    return db


def _db_object(db: GuardrailsDB | sqlite3.Connection) -> GuardrailsDB:
    if not isinstance(db, GuardrailsDB):
        raise TypeError("promote_candidate requires a GuardrailsDB object for formal knowledge writes")
    if db.conn is None:
        raise ValueError("database is not connected")
    return db


def _load_candidate(conn: sqlite3.Connection, candidate_id: str) -> dict[str, Any]:
    cursor = conn.execute("SELECT * FROM knowledge_candidates WHERE candidate_id=?", (candidate_id,))
    row = cursor.fetchone()
    if row is None:
        raise KeyError(f"candidate not found: {candidate_id}")
    return _row_to_candidate(_row_dict(row, cursor.description))


def _validate_pre_side_effect_gates(
    candidate: dict[str, Any],
    *,
    reviewer: str,
    no_sync: bool,
) -> str:
    clean_reviewer = str(reviewer or "").strip()
    if not clean_reviewer:
        raise ValueError("reviewer is required")
    if no_sync is not True:
        raise ValueError("sync is not supported for dream promote; pass no_sync=True")

    status = str(candidate.get("status") or "")
    if status != "approved":
        raise ValueError(f"promotion requires status=approved (got {status})")

    privacy_status = str(candidate.get("privacy_status") or "")
    if privacy_status != "clear":
        raise ValueError(f"promotion requires privacy_status=clear (got {privacy_status})")

    classification = str(candidate.get("classification") or "")
    if classification != "shared_knowledge":
        raise ValueError(
            f"promotion requires classification=shared_knowledge (got {classification})"
        )

    dedupe_status = str(candidate.get("dedupe_status") or "unknown")
    if dedupe_status in _BLOCKING_DEDUPE_STATUSES:
        raise ValueError(f"promotion blocked by dedupe_status={dedupe_status}")

    scan_payload = {
        "title": candidate.get("proposed_title") or "",
        "summary": candidate.get("summary") or "",
        "content": candidate.get("content_draft") or "",
        "category": candidate.get("category") or "",
        "tags": candidate.get("tags") or [],
        "source_metadata": {
            "candidate_id": candidate.get("candidate_id") or "",
            "source_type": candidate.get("source_type") or "",
            "source_agent": candidate.get("source_agent") or "",
            "source_session_id": candidate.get("source_session_id") or "",
            "source_channel": candidate.get("source_channel") or "",
            "source_refs": candidate.get("source_refs") or [],
        },
    }
    scan = scan_entry(
        scan_payload,
        context={
            "entry_point": "dream_promote",
            "intended_visibility": "shared",
            "source_channel": candidate.get("source_channel") or "unknown",
            "actor": clean_reviewer,
        },
    )
    if scan.outcome != "clear":
        raise ValueError(f"final privacy scan requires outcome clear (final privacy scan outcome={scan.outcome})")

    return clean_reviewer


def _reject_existing_formal_title(conn: sqlite3.Connection, title: str) -> None:
    """Fail before raw/formal writes if compile title-dedupe could delete the new row."""
    existing = conn.execute(
        "SELECT id FROM knowledge WHERE title=? LIMIT 1",
        (title,),
    ).fetchone()
    if existing is not None:
        raise ValueError(
            "promotion blocked by existing formal knowledge title; "
            "review/merge the candidate instead of promoting a duplicate title"
        )


def _reject_existing_formal_source(conn: sqlite3.Connection, source_file: str, raw_path: str) -> None:
    """Fail before writes if compiler source lookup could target an existing formal row."""
    existing = conn.execute(
        "SELECT id FROM knowledge WHERE source IN (?, ?) LIMIT 1",
        (source_file, raw_path),
    ).fetchone()
    if existing is not None:
        raise ValueError(
            "promotion blocked by existing formal knowledge source; "
            "review/repair the stale source collision before promoting"
        )


def _sanitize_filename_part(value: str) -> str:
    sanitized = _SAFE_FILENAME_CHARS.sub("_", value.strip())
    sanitized = sanitized.strip("._-")
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized or "candidate"


def _unique_raw_path(project_dir: Path, candidate_id: str, title: str) -> tuple[Path, str]:
    raw_dir = project_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    safe_id = _sanitize_filename_part(candidate_id)
    safe_title = _sanitize_filename_part(title).replace(".", "_")
    stem = f"{safe_id}_{safe_title}"
    candidate = raw_dir / f"{stem}.md"
    suffix = 2
    while candidate.exists():
        candidate = raw_dir / f"{stem}_{suffix}.md"
        suffix += 1
    return candidate, f"raw/{candidate.name}"


def _tags_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _write_raw_file(raw_file: Path, metadata: dict[str, Any], content: str) -> None:
    frontmatter = json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2)
    body = str(content or "")
    raw_text = f"---\n{frontmatter}\n---\n\n{body.rstrip()}\n"
    raw_file.write_text(raw_text, encoding="utf-8")


def _append_promoted_audit_and_status(
    conn: sqlite3.Connection,
    *,
    candidate: dict[str, Any],
    knowledge_id: int,
    raw_path: str,
    reviewer: str,
    no_sync: bool,
    compile_invoked: bool,
    map_invoked: bool,
) -> str:
    now = _now()
    audit_log = candidate.get("audit_log") or []
    if not isinstance(audit_log, list):
        raise ValueError("audit_log must be a list")
    audit_log = list(audit_log)
    audit_log.append(
        {
            "event": "promoted",
            "created_at": now,
            "knowledge_id": knowledge_id,
            "raw_path": raw_path,
            "reviewer": reviewer,
            "no_sync": no_sync,
            "formal_knowledge_written": True,
            "raw_written": True,
            "sync_invoked": False,
            "auto_promote": False,
            "compile_invoked": compile_invoked,
            "map_invoked": map_invoked,
        }
    )
    cursor = conn.execute(
        """UPDATE knowledge_candidates
           SET status=?, reviewer=?, reviewed_at=?, decision_reason=?, updated_at=?, audit_log_json=?
           WHERE candidate_id=?""",
        (
            "promoted",
            reviewer,
            now,
            "promoted to formal knowledge",
            now,
            _json_dumps(audit_log),
            candidate["candidate_id"],
        ),
    )
    if cursor.rowcount == 0:  # pragma: no cover - load catches this first
        raise KeyError(f"candidate not found: {candidate['candidate_id']}")
    conn.commit()
    return now


def _maybe_compile(project_dir: Path, db: GuardrailsDB, raw_file: Path, run_compile: bool) -> bool:
    if not run_compile:
        return False
    from guardrails_lite.guardrails_compile import GuardrailsCompiler

    compiler = GuardrailsCompiler(project_dir, db=db, embed_provider=None, auto_git=False)
    compiler._compile_file(raw_file, dry_run=False)
    return True


def _maybe_build_map(db: GuardrailsDB, knowledge_id: int, run_map: bool) -> bool:
    if not run_map:
        return False
    from guardrails_lite.guardrails_map import build_document_map_for_entry

    build_document_map_for_entry(db.conn, knowledge_id)
    return True


def promote_candidate(
    db: GuardrailsDB | sqlite3.Connection,
    candidate_id: str,
    *,
    project_dir: str | Path = ".",
    reviewer: str,
    no_sync: bool,
    run_compile: bool = True,
    run_map: bool = True,
) -> dict[str, Any]:
    """Promote one approved dream candidate into local formal knowledge.

    This function never invokes sync.  ``no_sync`` must be true so accidental
    remote writes fail closed before any side effect.
    """
    db_obj = _db_object(db)
    conn = _connection(db_obj)
    candidate = _load_candidate(conn, candidate_id)
    clean_reviewer = _validate_pre_side_effect_gates(
        candidate,
        reviewer=reviewer,
        no_sync=no_sync,
    )

    project_path = Path(project_dir)
    title = str(candidate.get("proposed_title") or "")
    summary = str(candidate.get("summary") or "")
    content = str(candidate.get("content_draft") or "")
    category = str(candidate.get("category") or "general")
    tags = _tags_list(candidate.get("tags"))
    trust = float(candidate.get("trust_initial", 0.4))
    _reject_existing_formal_title(conn, title)

    raw_file, raw_path = _unique_raw_path(project_path, candidate_id, title)
    _reject_existing_formal_source(conn, raw_file.name, raw_path)
    created = _now()
    metadata = {
        "title": title,
        "layer": "L3",
        "category": category,
        "tags": tags,
        "trust": trust,
        "summary": summary,
        "source": raw_path,
        "source_candidate_id": candidate_id,
        "source_agent": candidate.get("source_agent") or "",
        "source_type": candidate.get("source_type") or "",
        "created": created,
    }

    _write_raw_file(raw_file, metadata, content)
    knowledge_id = int(
        db_obj.add_knowledge(
            title,
            content,
            layer="L3",
            category=category,
            tags=",".join(tags),
            trust=trust,
            source=raw_path,
            summary=summary,
        )
    )

    compile_invoked = _maybe_compile(project_path, db_obj, raw_file, bool(run_compile))
    map_invoked = _maybe_build_map(db_obj, knowledge_id, bool(run_map))

    _append_promoted_audit_and_status(
        conn,
        candidate=candidate,
        knowledge_id=knowledge_id,
        raw_path=raw_path,
        reviewer=clean_reviewer,
        no_sync=True,
        compile_invoked=compile_invoked,
        map_invoked=map_invoked,
    )

    readback = db_obj.get_knowledge(knowledge_id)
    readback_verified = bool(readback and readback.get("source") == raw_path)
    if not readback_verified:
        raise RuntimeError("promotion readback verification failed")

    return {
        "success": True,
        "candidate_id": candidate_id,
        "knowledge_id": knowledge_id,
        "raw_path": raw_path,
        "formal_knowledge_written": True,
        "raw_written": True,
        "sync_invoked": False,
        "auto_promote": False,
        "no_sync": True,
        "compile_invoked": compile_invoked,
        "map_invoked": map_invoked,
        "readback_verified": True,
    }


__all__ = ["promote_candidate"]
