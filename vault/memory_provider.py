"""Memory Provider Interface and the default SQLite provider.

The provider layer sits above ``VaultDB``. ``VaultDB`` remains the concrete
SQLite implementation; providers expose the smaller governance-oriented memory
contract that future backends can implement without changing agent-facing APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .access_policy import can_read_memory, filter_readable_memories, normalize_read_policy
from .db import VaultDB
from .governance_contract import governance_contract_payload
from .memory import create_candidate, promote_candidate
from .memory_change_envelope import (
    MAX_BOUNDED_EVIDENCE_LINES,
    MemoryChangeCursorError,
    change_order_key,
    decode_change_cursor,
    encode_change_cursor,
    memory_change_envelope,
    normalize_change_limit,
    read_policy_fingerprint,
)
from .multi_host import list_audit_log, record_audit_event
from .search_utils import normalize_search_limit


MEMORY_PROVIDER_INTERFACE_VERSION = "2026-08-21"
_MEMORY_CHANGE_SCAN_BATCH_SIZE = 100
_MEMORY_CHANGE_RECORDED_AT_SQL = "COALESCE(NULLIF(updated_at, ''), created_at, '')"
_MEMORY_CHANGE_POLICY_COLUMNS = (
    "id, scope, sensitivity, owner_agent, allowed_agents, status, "
    "updated_at, created_at"
)

# Fields that must never be directly modified through update_memory
_PROTECTED_UPDATE_FIELDS = frozenset({
    "id",
    "created_at",
    "memory_id",
    "actor_agent",  # handled separately via parameter
})

# Valid status transitions for active memory
_VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "active": {"archived", "deleted", "active"},
    "archived": {"active", "deleted", "archived"},
    "deleted": {"active", "deleted"},
    "reviewed": {"active", "archived", "deleted", "reviewed"},
    "candidate": {"active", "archived", "deleted", "reviewed", "candidate"},
}


def _validate_update_fields(before: dict[str, Any], fields: dict[str, Any]) -> tuple[bool, str]:
    """Validate update fields against business rules.

    Returns (ok, error_message). Protected fields and invalid status
    transitions are blocked before reaching the DB layer.
    """
    # Block protected fields
    for field in _PROTECTED_UPDATE_FIELDS:
        if field in fields:
            return False, f"protected_field:{field}"

    # Validate status transition
    if "status" in fields:
        old_status = str(before.get("status") or "active").strip().lower()
        new_status = str(fields["status"] or "").strip().lower()
        if not new_status:
            return False, "invalid_status:empty"
        valid_next = _VALID_STATUS_TRANSITIONS.get(old_status, set())
        if new_status not in valid_next:
            return False, f"invalid_status_transition:{old_status}->{new_status}"

    return True, ""

MEMORY_PROVIDER_OPERATIONS = [
    "list_changes",
    "get_metadata",
    "get_revision",
    "read_bounded_evidence",
    "create_candidate",
    "search_active",
    "get_memory",
    "update_memory",
    "soft_delete_memory",
    "promote_candidate",
    "list_timeline",
    "list_audit",
    "sync",
]


@runtime_checkable
class MemoryProvider(Protocol):
    """Minimal backend contract for governed Vault memory operations."""

    provider_id: str
    backend_type: str

    def status(self) -> dict[str, Any]:
        """Return provider readiness and safety metadata."""

    def create_candidate(self, **kwargs: Any) -> dict[str, Any]:
        """Create a review candidate; never write active memory directly."""

    def list_changes(
        self,
        *,
        cursor: str = "",
        limit: int = 50,
        agent_id: str = "",
        include_private: bool = False,
        max_sensitivity: str = "",
    ) -> dict[str, Any]:
        """List readable current-memory changes using an opaque cursor."""

    def get_metadata(
        self,
        memory_id: int | str,
        *,
        agent_id: str = "",
        include_private: bool = False,
        max_sensitivity: str = "",
    ) -> dict[str, Any] | None:
        """Return one readable current-memory envelope without raw content."""

    def get_revision(
        self,
        memory_id: int | str,
        revision_id: str,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Return current metadata only when its revision matches."""

    def read_bounded_evidence(
        self,
        memory_id: int | str,
        revision_id: str,
        *,
        line_start: int,
        line_end: int,
        max_lines: int = MAX_BOUNDED_EVIDENCE_LINES,
        agent_id: str = "",
        include_private: bool = False,
        max_sensitivity: str = "",
    ) -> dict[str, Any]:
        """Read policy-filtered evidence bound to the current revision."""

    def search_active(
        self,
        query: str,
        *,
        limit: int = 10,
        min_trust: float = 0.0,
        agent_id: str = "",
        include_private: bool = False,
        max_sensitivity: str = "",
    ) -> list[dict[str, Any]]:
        """Search official active memory rows."""

    def get_memory(
        self,
        memory_id: int,
        *,
        agent_id: str = "",
        include_private: bool = False,
        max_sensitivity: str = "",
    ) -> dict[str, Any] | None:
        """Read one memory row by id."""

    def update_memory(self, memory_id: int, **fields: Any) -> dict[str, Any]:
        """Apply a trusted local update to active memory."""

    def soft_delete_memory(self, memory_id: int, *, actor_agent: str, reason: str = "") -> dict[str, Any]:
        """Mark memory deleted without hard-deleting storage rows."""

    def promote_candidate(self, candidate_id: str, *, confirm: bool = False) -> dict[str, Any]:
        """Promote a reviewed candidate through the normal Vault gate."""

    def list_timeline(self, memory_id: int, *, limit: int = 20) -> dict[str, Any]:
        """Return metadata-only memory timeline data."""

    def list_audit(self, *, memory_id: int | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """Return metadata-only audit events."""

    def sync(self, **kwargs: Any) -> dict[str, Any]:
        """Run or describe backend synchronization."""


def memory_provider_contract_payload(*, provider_id: str = "sqlite") -> dict[str, Any]:
    """Return JSON-safe metadata for provider-aware health and OpenAPI surfaces."""
    return {
        "name": "Memory Provider Interface",
        "version": MEMORY_PROVIDER_INTERFACE_VERSION,
        "provider_id": str(provider_id or ""),
        "operations": list(MEMORY_PROVIDER_OPERATIONS),
        "default_provider": "sqlite",
        "semantics": {
            "candidate_first_remote_writes": True,
            "active_memory_write_requires_trusted_local_context": True,
            "remote_direct_active_memory_writes": False,
            "hard_delete_by_remote_agent": False,
            "audit_metadata_required": True,
            "read_policy_filtering": True,
            "change_pages_hide_filtered_counts": True,
            "change_cursors_are_policy_bound": True,
            "bounded_evidence_revision_required": True,
            "semantic_index_is_optional": True,
        },
        "backend_boundary": {
            "sqlite_is_default_local_provider": True,
            "supabase_is_optional_cloud_adapter": True,
            "vault_cloud_is_future_managed_backend": True,
            "qdrant_is_semantic_index_provider_not_source_of_truth": True,
        },
    }


@dataclass
class SQLiteMemoryProvider:
    """Default local-first provider backed by ``VaultDB`` and SQLite."""

    db_path: str | Path
    project_dir: str | Path | None = None

    provider_id: str = "sqlite"
    backend_type: str = "local_sqlite"

    @property
    def resolved_db_path(self) -> Path:
        return Path(self.db_path).expanduser().resolve()

    @property
    def resolved_project_dir(self) -> Path:
        if self.project_dir is not None:
            return Path(self.project_dir).expanduser().resolve()
        return self.resolved_db_path.parent

    def status(self) -> dict[str, Any]:
        db_path = self.resolved_db_path
        return {
            "provider_id": self.provider_id,
            "backend_type": self.backend_type,
            "interface_version": MEMORY_PROVIDER_INTERFACE_VERSION,
            "db_path": str(db_path),
            "db_exists": db_path.exists(),
            "governance_contract": governance_contract_payload(adapter=self.provider_id),
            "provider_contract": memory_provider_contract_payload(provider_id=self.provider_id),
            "safety": _provider_safety_flags(),
            "capabilities": {
                "approved_memory_storage": True,
                "candidate_queue_storage": True,
                "access_policy_metadata": True,
                "audit_trail": True,
                "keyword_search": True,
                "read_policy_filtering": True,
                "semantic_index_optional": True,
                "memory_change_envelope": True,
                "cursor_change_listing": True,
                "revision_bound_bounded_evidence": True,
                "sync": False,
            },
        }

    def list_changes(
        self,
        *,
        cursor: str = "",
        limit: int = 50,
        agent_id: str = "",
        include_private: bool = False,
        max_sensitivity: str = "",
    ) -> dict[str, Any]:
        read_policy = normalize_read_policy(
            agent_id=agent_id,
            include_private=include_private,
            max_sensitivity=max_sensitivity,
        )
        policy_hash = read_policy_fingerprint(read_policy)
        cursor_key: tuple[str, int] | None = None
        if cursor:
            try:
                cursor_key = decode_change_cursor(cursor, policy_fingerprint=policy_hash)
            except MemoryChangeCursorError as exc:
                return {
                    "status": "error",
                    "error": exc.code,
                    "message": "change cursor is invalid for the current read policy",
                }

        limit_i = normalize_change_limit(limit)
        visible: list[dict[str, Any]] = []
        scan_key = cursor_key
        with VaultDB(self.resolved_db_path) as db:
            # Keep policy scanning, selected-row hydration, and audit lookup on
            # one WAL snapshot so a concurrent writer cannot change the page
            # after its visible rows and cursor have already been chosen.
            db.conn.execute("BEGIN")
            while len(visible) <= limit_i:
                where_sql = ""
                parameters: list[Any] = []
                if scan_key is not None:
                    where_sql = (
                        f"WHERE ({_MEMORY_CHANGE_RECORDED_AT_SQL} > ? OR "
                        f"({_MEMORY_CHANGE_RECORDED_AT_SQL} = ? AND id > ?))"
                    )
                    parameters.extend((scan_key[0], scan_key[0], scan_key[1]))
                parameters.append(_MEMORY_CHANGE_SCAN_BATCH_SIZE)
                batch = [
                    dict(row)
                    for row in db.conn.execute(
                        f"""SELECT {_MEMORY_CHANGE_POLICY_COLUMNS}
                            FROM knowledge
                            {where_sql}
                            ORDER BY {_MEMORY_CHANGE_RECORDED_AT_SQL}, id
                            LIMIT ?""",
                        parameters,
                    ).fetchall()
                ]
                if not batch:
                    break
                for row in batch:
                    scan_key = change_order_key(row)
                    if can_read_memory(row, read_policy):
                        visible.append(row)
                        if len(visible) > limit_i:
                            break
                if len(visible) > limit_i or len(batch) < _MEMORY_CHANGE_SCAN_BATCH_SIZE:
                    break

            selected_metadata = visible[:limit_i]
            selected_ids = [int(row["id"]) for row in selected_metadata]
            selected: list[dict[str, Any]] = []
            audit_refs: dict[str, str] = {}
            if selected_ids:
                placeholders = ",".join("?" for _ in selected_ids)
                rows_by_id = {
                    int(row["id"]): dict(row)
                    for row in db.conn.execute(
                        f"SELECT * FROM knowledge WHERE id IN ({placeholders})",
                        selected_ids,
                    ).fetchall()
                }
                selected = [rows_by_id[row_id] for row_id in selected_ids if row_id in rows_by_id]
                audit_refs = {
                    str(row["target_id"]): f"audit:{int(row['audit_id'])}"
                    for row in db.conn.execute(
                        f"""SELECT target_id, MAX(id) AS audit_id
                            FROM memory_audit_log
                            WHERE target_type='knowledge'
                              AND target_id IN ({placeholders})
                            GROUP BY target_id""",
                        [str(row_id) for row_id in selected_ids],
                    ).fetchall()
                }

        changes = [
            memory_change_envelope(row, audit_ref=audit_refs.get(str(row.get("id")), ""))
            for row in selected
        ]
        next_cursor = str(cursor or "")
        if selected:
            recorded_at, row_id = change_order_key(selected[-1])
            next_cursor = encode_change_cursor(
                recorded_at=recorded_at,
                memory_row_id=row_id,
                policy_fingerprint=policy_hash,
            )
        return {
            "status": "ok",
            "changes": changes,
            "count": len(changes),
            "next_cursor": next_cursor,
            "has_more": len(visible) > limit_i,
            "provider": self.provider_id,
            "safety": {
                "read_policy_filtering": True,
                "returns_raw_content": False,
                "hidden_totals_exposed": False,
                "cursor_advances_on_readable_changes_only": True,
            },
        }

    def get_metadata(
        self,
        memory_id: int | str,
        *,
        agent_id: str = "",
        include_private: bool = False,
        max_sensitivity: str = "",
    ) -> dict[str, Any] | None:
        memory_id_i = _positive_memory_id(memory_id)
        if memory_id_i is None:
            return None
        read_policy = normalize_read_policy(
            agent_id=agent_id,
            include_private=include_private,
            max_sensitivity=max_sensitivity,
        )
        with VaultDB(self.resolved_db_path) as db:
            row = db.get_knowledge(memory_id_i)
            audit = db.conn.execute(
                """SELECT id FROM memory_audit_log
                   WHERE target_type='knowledge' AND target_id=?
                   ORDER BY id DESC LIMIT 1""",
                (str(memory_id_i),),
            ).fetchone()
        if not row or not can_read_memory(row, read_policy):
            return None
        audit_ref = f"audit:{int(audit['id'])}" if audit else ""
        return memory_change_envelope(row, audit_ref=audit_ref)

    def get_revision(
        self,
        memory_id: int | str,
        revision_id: str,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        metadata = self.get_metadata(memory_id, **kwargs)
        if metadata is None or metadata.get("revision_id") != str(revision_id or ""):
            return None
        return metadata

    def read_bounded_evidence(
        self,
        memory_id: int | str,
        revision_id: str,
        *,
        line_start: int,
        line_end: int,
        max_lines: int = MAX_BOUNDED_EVIDENCE_LINES,
        agent_id: str = "",
        include_private: bool = False,
        max_sensitivity: str = "",
    ) -> dict[str, Any]:
        memory_id_i = _positive_memory_id(memory_id)
        if memory_id_i is None:
            return {"status": "error", "error": "memory_id_invalid"}
        metadata = self.get_metadata(
            memory_id_i,
            agent_id=agent_id,
            include_private=include_private,
            max_sensitivity=max_sensitivity,
        )
        if metadata is None:
            return {"status": "error", "error": "not_found_or_not_readable"}
        if (
            normalize_read_policy(
                agent_id=agent_id,
                include_private=include_private,
                max_sensitivity=max_sensitivity,
            ).active
            and metadata.get("lifecycle", {}).get("status") != "active"
        ):
            return {"status": "error", "error": "not_found_or_not_readable"}
        expected_revision = str(revision_id or "")
        if not expected_revision:
            return {"status": "error", "error": "revision_id_required"}
        if metadata["revision_id"] != expected_revision:
            return {
                "status": "error",
                "error": "revision_mismatch",
                "memory_id": str(memory_id_i),
                "current_revision_id": metadata["revision_id"],
            }

        from .mcp_read import _vault_read_range_payload

        try:
            requested_max_lines = int(max_lines)
        except (TypeError, ValueError):
            requested_max_lines = MAX_BOUNDED_EVIDENCE_LINES
        if requested_max_lines <= 0:
            requested_max_lines = MAX_BOUNDED_EVIDENCE_LINES
        effective_max_lines = min(requested_max_lines, MAX_BOUNDED_EVIDENCE_LINES)

        payload = _vault_read_range_payload(
            memory_id_i,
            line_start=line_start,
            line_end=line_end,
            max_lines=effective_max_lines,
            agent_id=agent_id,
            include_private=include_private,
            max_sensitivity=max_sensitivity,
            db_path=str(self.resolved_db_path),
        )
        if payload.get("error"):
            payload.setdefault("status", "error")
            return payload
        after = self.get_metadata(
            memory_id_i,
            agent_id=agent_id,
            include_private=include_private,
            max_sensitivity=max_sensitivity,
        )
        if after is None or after.get("revision_id") != expected_revision:
            return {
                "status": "error",
                "error": "revision_changed_during_read",
                "memory_id": str(memory_id_i),
            }
        payload.update(
            {
                "status": "ok",
                "memory_id": str(memory_id_i),
                "revision_id": expected_revision,
                "content_sha256": metadata["content_sha256"],
                "audit_ref": metadata["audit_ref"],
                "provider": self.provider_id,
                "safety": {
                    "bounded_read": True,
                    "max_lines": effective_max_lines,
                    "revision_bound": True,
                    "read_policy_filtering": True,
                    "returns_full_raw_content": False,
                },
            }
        )
        return payload

    def create_candidate(self, **kwargs: Any) -> dict[str, Any]:
        with VaultDB(self.resolved_db_path) as db:
            result = create_candidate(db, **kwargs)
            candidate = db.get_memory_candidate(str(result.get("candidate_id") or ""))
        return {
            **result,
            "candidate": candidate,
            "provider": self.provider_id,
            "safety": {
                "candidate_first": True,
                "writes_active_knowledge": False,
                "hard_delete": False,
            },
        }

    def search_active(
        self,
        query: str,
        *,
        limit: int = 10,
        min_trust: float = 0.0,
        agent_id: str = "",
        include_private: bool = False,
        max_sensitivity: str = "",
    ) -> list[dict[str, Any]]:
        limit_i = normalize_search_limit(limit)
        if limit_i <= 0:
            return []
        read_policy = normalize_read_policy(
            agent_id=agent_id,
            include_private=include_private,
            max_sensitivity=max_sensitivity,
        )
        with VaultDB(self.resolved_db_path) as db:
            rows = db.search_keyword(query, limit=max(limit_i * 10, 100), min_trust=min_trust)
        active = [row for row in rows if str(row.get("status") or "active") == "active"]
        readable = filter_readable_memories(active, read_policy)
        return readable[:limit_i]

    def get_memory(
        self,
        memory_id: int,
        *,
        agent_id: str = "",
        include_private: bool = False,
        max_sensitivity: str = "",
    ) -> dict[str, Any] | None:
        if int(memory_id or 0) <= 0:
            return None
        read_policy = normalize_read_policy(
            agent_id=agent_id,
            include_private=include_private,
            max_sensitivity=max_sensitivity,
        )
        with VaultDB(self.resolved_db_path) as db:
            row = db.get_knowledge(int(memory_id))
        if not row:
            return None
        if str(row.get("status") or "active") != "active" and read_policy.active:
            return None
        if not can_read_memory(row, read_policy):
            return None
        return row

    def update_memory(self, memory_id: int, **fields: Any) -> dict[str, Any]:
        if int(memory_id or 0) <= 0:
            return {"status": "error", "error": "memory_id_invalid"}
        actor = str(fields.pop("actor_agent", "") or "").strip().lower()
        with VaultDB(self.resolved_db_path) as db:
            before = db.get_knowledge(int(memory_id))
            if not before:
                return {"status": "blocked", "error": "memory_not_found", "memory_id": int(memory_id)}
            ok, err = _validate_update_fields(before, fields)
            if not ok:
                return {"status": "blocked", "error": err, "memory_id": int(memory_id)}
            changed = db.update_knowledge(int(memory_id), **fields)
            if changed:
                record_audit_event(
                    db,
                    actor_agent=actor,
                    action="provider:update_memory",
                    target_type="knowledge",
                    target_id=str(int(memory_id)),
                    payload={
                        "provider": self.provider_id,
                        "updated_fields": sorted(fields),
                        "previous_status": before.get("status", ""),
                    },
                )
            after = db.get_knowledge(int(memory_id))
        return {
            "status": "ok" if changed else "unchanged",
            "memory_id": int(memory_id),
            "memory": after,
            "provider": self.provider_id,
            "safety": {
                "trusted_local_update_required": True,
                "remote_direct_active_memory_writes": False,
                "audit_recorded": bool(changed),
            },
        }

    def soft_delete_memory(self, memory_id: int, *, actor_agent: str, reason: str = "") -> dict[str, Any]:
        if int(memory_id or 0) <= 0:
            return {"status": "error", "error": "memory_id_invalid"}
        actor = str(actor_agent or "").strip().lower()
        if not actor:
            return {"status": "error", "error": "actor_agent_required"}
        with VaultDB(self.resolved_db_path) as db:
            before = db.get_knowledge(int(memory_id))
            if not before:
                return {"status": "blocked", "error": "memory_not_found", "memory_id": int(memory_id)}
            changed = db.update_knowledge(int(memory_id), status="deleted", archived_at="")
            record_audit_event(
                db,
                actor_agent=actor,
                action="provider:soft_delete_memory",
                target_type="knowledge",
                target_id=str(int(memory_id)),
                payload={
                    "reason": str(reason or ""),
                    "hard_delete": False,
                    "provider": self.provider_id,
                    "previous_status": before.get("status", ""),
                },
            )
            after = db.get_knowledge(int(memory_id))
        return {
            "status": "ok" if changed else "unchanged",
            "memory_id": int(memory_id),
            "memory": after,
            "provider": self.provider_id,
            "safety": {"hard_delete": False, "audit_recorded": True},
        }

    def promote_candidate(self, candidate_id: str, *, confirm: bool = False) -> dict[str, Any]:
        with VaultDB(self.resolved_db_path) as db:
            result = promote_candidate(
                db,
                str(candidate_id or ""),
                confirm=confirm,
                project_dir=self.resolved_project_dir,
            )
        result["provider"] = self.provider_id
        result.setdefault("safety", {})["promotion_requires_confirm"] = True
        return result

    def list_timeline(self, memory_id: int, *, limit: int = 20) -> dict[str, Any]:
        limit_i = max(1, min(int(limit or 20), 100))
        if int(memory_id or 0) <= 0:
            return {"status": "error", "error": "memory_id_invalid"}
        with VaultDB(self.resolved_db_path) as db:
            current = db.get_knowledge(int(memory_id))
            revisions = db.conn.execute(
                """SELECT id, created_at, operation, status, source_agent, revision_hash, content_hash
                   FROM memory_revisions
                   WHERE knowledge_id=?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (int(memory_id), limit_i),
            ).fetchall()
            audits = self._list_audit_from_db(db, memory_id=int(memory_id), limit=limit_i)
        return {
            "status": "ok",
            "memory_id": int(memory_id),
            "current": _compact_memory_metadata(current or {}),
            "revisions": [dict(row) for row in revisions],
            "audit_events": audits,
            "provider": self.provider_id,
            "safety": {
                "metadata_only": True,
                "returns_raw_memory_content": False,
                "returns_raw_audit_payloads": False,
            },
        }

    def list_audit(self, *, memory_id: int | None = None, limit: int = 20) -> list[dict[str, Any]]:
        limit_i = max(1, min(int(limit or 20), 100))
        with VaultDB(self.resolved_db_path) as db:
            return self._list_audit_from_db(db, memory_id=memory_id, limit=limit_i)

    def sync(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "status": "unsupported",
            "provider": self.provider_id,
            "reason": "local SQLite provider has no remote sync operation; use central sync adapters",
            "requested": dict(kwargs),
        }

    def _list_audit_from_db(
        self,
        db: VaultDB,
        *,
        memory_id: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        rows = list_audit_log(db, limit=max(limit * 3, limit))
        filtered = []
        memory_id_text = str(memory_id or "")
        for row in rows:
            if memory_id_text and str(row.get("target_id") or "") != memory_id_text:
                continue
            filtered.append(_compact_audit_row(row))
            if len(filtered) >= limit:
                break
        return filtered


def sqlite_memory_provider(project_dir: str | Path) -> SQLiteMemoryProvider:
    """Create the default provider for a Vault project directory."""
    project = Path(project_dir).expanduser().resolve()
    return SQLiteMemoryProvider(project / "vault.db", project_dir=project)


def _provider_safety_flags() -> dict[str, bool]:
    return {
        "candidate_first_remote_writes": True,
        "writes_active_knowledge_from_remote": False,
        "hard_delete_by_remote_agent": False,
        "metadata_only_audit": True,
        "metadata_only_timeline": True,
        "read_policy_filtering": True,
        "change_pages_hide_filtered_counts": True,
        "revision_bound_bounded_evidence": True,
    }


def _positive_memory_id(value: Any) -> int | None:
    try:
        memory_id = int(value)
    except (TypeError, ValueError):
        return None
    return memory_id if memory_id > 0 else None


def _compact_memory_metadata(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key)
        for key in (
            "id",
            "title",
            "layer",
            "category",
            "scope",
            "sensitivity",
            "owner_agent",
            "memory_type",
            "status",
            "updated_at",
            "valid_from",
            "valid_until",
            "expires_at",
        )
    } if row else {}


def _compact_audit_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "created_at": row.get("created_at", ""),
        "actor_agent": row.get("actor_agent", ""),
        "action": row.get("action", ""),
        "target_type": row.get("target_type", ""),
        "target_id": row.get("target_id", ""),
        "revision_id": row.get("revision_id", ""),
    }
