"""Provider-independent current-memory change envelope helpers."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from typing import Any

from .access_policy import ReadPolicy
from .memory_object import legacy_memory_type_metadata, memory_kind_from_record


MEMORY_CHANGE_SCHEMA_VERSION = "vault.memory-change.v1"
MEMORY_CHANGE_CURSOR_VERSION = 1
MAX_MEMORY_CHANGE_PAGE_SIZE = 100
MAX_BOUNDED_EVIDENCE_LINES = 80

_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


class MemoryChangeCursorError(ValueError):
    """A cursor is malformed or cannot be reused with the current policy."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def full_content_sha256(content: Any) -> str:
    """Return the full SHA-256 of exact UTF-8 memory content."""
    return hashlib.sha256(str(content or "").encode("utf-8")).hexdigest()


def memory_change_envelope(
    row: dict[str, Any],
    *,
    audit_ref: str = "",
) -> dict[str, Any]:
    """Build the stable public envelope for one current knowledge snapshot."""
    memory_id = str(int(row.get("id") or 0))
    content_sha256 = full_content_sha256(row.get("content_raw"))
    created_at = str(row.get("created_at") or "")
    recorded_at = str(row.get("updated_at") or created_at)
    valid_from = str(row.get("valid_from") or "")
    valid_until = str(row.get("valid_until") or "")
    occurred_at = valid_from or created_at
    status = str(row.get("status") or "active")
    stored_type = str(row.get("memory_type") or "knowledge")
    application_metadata = legacy_memory_type_metadata(stored_type)
    revision_material = {
        "memory_id": memory_id,
        "title": str(row.get("title") or ""),
        "kind": memory_kind_from_record(stored_type),
        "application_metadata": application_metadata,
        "content_sha256": content_sha256,
        "occurred_at": occurred_at,
        "recorded_at": recorded_at,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "source": str(row.get("source") or ""),
        "confidence": _confidence(row.get("trust")),
        "status": status,
        "scope": str(row.get("scope") or "project"),
        "sensitivity": str(row.get("sensitivity") or "low"),
    }
    revision_id = "rev_" + hashlib.sha256(
        json.dumps(
            revision_material,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": MEMORY_CHANGE_SCHEMA_VERSION,
        "memory_id": memory_id,
        "revision_id": revision_id,
        "change_type": "delete" if status == "deleted" else "upsert",
        "title": revision_material["title"],
        "kind": revision_material["kind"],
        "application_metadata": application_metadata,
        "content_sha256": content_sha256,
        "occurred_at": occurred_at,
        "recorded_at": recorded_at,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "provenance": {"source": revision_material["source"]},
        "confidence": revision_material["confidence"],
        "lifecycle": {"status": status},
        "governance": {
            "scope": revision_material["scope"],
            "sensitivity": revision_material["sensitivity"],
        },
        "audit_ref": str(audit_ref or ""),
        "evidence_ref": {
            "memory_id": memory_id,
            "revision_id": revision_id,
            "operation": "read_bounded_evidence",
        },
    }


def change_order_key(row: dict[str, Any]) -> tuple[str, int]:
    """Return the stable cursor ordering key for a knowledge row."""
    recorded_at = str(row.get("updated_at") or row.get("created_at") or "")
    return recorded_at, int(row.get("id") or 0)


def read_policy_fingerprint(policy: ReadPolicy) -> str:
    """Bind pagination to the exact read-policy inputs without exposing them."""
    material = {
        "agent_id": policy.agent_id,
        "include_private": policy.include_private,
        "max_sensitivity": policy.max_sensitivity,
        "allowed_statuses": list(policy.allowed_statuses),
    }
    return hashlib.sha256(
        json.dumps(material, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def encode_change_cursor(
    *,
    recorded_at: str,
    memory_row_id: int,
    policy_fingerprint: str,
) -> str:
    """Encode an opaque pagination cursor."""
    payload = {
        "v": MEMORY_CHANGE_CURSOR_VERSION,
        "recorded_at": str(recorded_at or ""),
        "memory_row_id": int(memory_row_id),
        "policy": str(policy_fingerprint or ""),
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_change_cursor(cursor: str, *, policy_fingerprint: str) -> tuple[str, int]:
    """Validate a cursor and return its ordering key."""
    token = str(cursor or "")
    if not token or len(token) > 2048 or token.strip() != token:
        raise MemoryChangeCursorError("invalid_cursor")
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.b64decode(padded, altchars=b"-_", validate=True)
        payload = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise MemoryChangeCursorError("invalid_cursor") from None
    if not isinstance(payload, dict) or set(payload) != {
        "v",
        "recorded_at",
        "memory_row_id",
        "policy",
    }:
        raise MemoryChangeCursorError("invalid_cursor")
    if payload.get("v") != MEMORY_CHANGE_CURSOR_VERSION:
        raise MemoryChangeCursorError("invalid_cursor")
    try:
        memory_row_id = int(payload.get("memory_row_id"))
    except (TypeError, ValueError):
        raise MemoryChangeCursorError("invalid_cursor") from None
    recorded_at = payload.get("recorded_at")
    encoded_policy = payload.get("policy")
    if (
        memory_row_id <= 0
        or not isinstance(recorded_at, str)
        or not isinstance(encoded_policy, str)
        or not _SHA256_RE.fullmatch(encoded_policy)
    ):
        raise MemoryChangeCursorError("invalid_cursor")
    if encoded_policy != policy_fingerprint:
        raise MemoryChangeCursorError("cursor_policy_mismatch")
    return recorded_at, memory_row_id


def normalize_change_limit(value: Any, *, default: int = 50) -> int:
    """Return a positive change-page size capped by the public contract."""
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = default
    if limit <= 0:
        limit = default
    return min(limit, MAX_MEMORY_CHANGE_PAGE_SIZE)


def _confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = 0.5
    return max(0.0, min(confidence, 1.0))
