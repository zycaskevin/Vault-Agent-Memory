"""HMAC helpers for remote sync payload integrity."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any


SYNC_HMAC_ALGORITHM = "hmac-sha256-v1"
SYNC_HMAC_ENV = "VAULT_SYNC_HMAC_SECRET"
SYNC_HMAC_SECRETS_ENV = "VAULT_SYNC_HMAC_SECRETS"
SYNC_HMAC_FIELDS = [
    "title",
    "content",
    "from_agent",
    "reason",
    "category",
    "tags",
    "trust",
    "scope",
    "sensitivity",
    "owner_agent",
    "allowed_agents",
    "memory_type",
    "source_ref",
    "idempotency_key",
]


def sync_hmac_secret_from_env() -> str:
    """Return the optional shared secret used for sync payload signatures."""
    return os.environ.get(SYNC_HMAC_ENV, "").strip()


def sync_hmac_secrets_from_env() -> list[dict[str, str]]:
    """Return active sync HMAC secrets without exposing them to callers."""
    keys: list[dict[str, str]] = []
    raw_entries = os.environ.get(SYNC_HMAC_SECRETS_ENV, "").replace("\n", ",").split(",")
    for entry in raw_entries:
        parsed = _parse_secret_entry(entry, source=SYNC_HMAC_SECRETS_ENV)
        if parsed:
            keys.append(parsed)
    legacy_secret = sync_hmac_secret_from_env()
    if legacy_secret:
        legacy = {
            "key_id": sync_hmac_key_fingerprint(legacy_secret),
            "secret": legacy_secret,
            "source": SYNC_HMAC_ENV,
        }
        if not any(item["key_id"] == legacy["key_id"] for item in keys):
            keys.append(legacy)
    return keys


def sync_hmac_primary_secret_from_env() -> dict[str, str]:
    """Return the first configured sync HMAC key for signing outgoing payloads."""
    keys = sync_hmac_secrets_from_env()
    return keys[0] if keys else {"key_id": "", "secret": "", "source": ""}


def sync_hmac_key_fingerprint(secret: str) -> str:
    """Return a stable non-secret key id for sync HMAC rotation."""
    secret_text = str(secret or "").strip()
    if not secret_text:
        return ""
    return "sha256:" + hashlib.sha256(secret_text.encode("utf-8")).hexdigest()[:16]


def sync_hmac_key_report() -> dict[str, Any]:
    """Return a secret-free report for operators rotating sync HMAC keys."""
    keys = sync_hmac_secrets_from_env()
    key_ids = [item["key_id"] for item in keys]
    return {
        "ok": True,
        "status": "configured" if keys else "missing",
        "hmac_supported": True,
        "active_key_count": len(keys),
        "primary_key_id": key_ids[0] if key_ids else "",
        "key_ids": key_ids,
        "sources": sorted({item["source"] for item in keys}),
        "rotation_supported": True,
        "next_action": (
            "Use VAULT_SYNC_HMAC_SECRETS='new-id:new-secret,old-id:old-secret' during rotation; "
            "remove old keys after every submitter has moved to the new primary key."
            if keys
            else "Set VAULT_SYNC_HMAC_SECRETS or VAULT_SYNC_HMAC_SECRET before requiring HMAC."
        ),
    }


def sync_payload_hash(payload: dict[str, Any]) -> str:
    """Return a stable SHA256 digest for the signed sync payload subset."""
    return hashlib.sha256(_canonical_payload(payload)).hexdigest()


def sign_sync_payload(payload: dict[str, Any], secret: str, *, key_id: str = "") -> dict[str, str]:
    """Return signature metadata for a remote sync payload."""
    secret_text = str(secret or "").strip()
    if not secret_text:
        return {}
    canonical = _canonical_payload(payload)
    signature = hmac.new(secret_text.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
    result = {
        "hmac_algorithm": SYNC_HMAC_ALGORITHM,
        "payload_hash": hashlib.sha256(canonical).hexdigest(),
        "hmac_signature": signature,
    }
    key_text = str(key_id or "").strip()
    if key_text:
        result["hmac_key_id"] = key_text
    return result


def verify_sync_payload(
    payload: dict[str, Any],
    secret: str | list[dict[str, str]],
    *,
    require_signature: bool = False,
) -> dict[str, Any]:
    """Verify optional HMAC metadata on a remote sync payload."""
    signature = str(payload.get("hmac_signature") or "").strip()
    algorithm = str(payload.get("hmac_algorithm") or "").strip()
    payload_hash = str(payload.get("payload_hash") or "").strip()
    key_id = str(payload.get("hmac_key_id") or "").strip()
    if not signature and not payload_hash and not algorithm:
        return {
            "ok": not require_signature,
            "status": "missing" if require_signature else "unsigned",
            "error": "missing_signature" if require_signature else "",
        }
    keys = _normalize_secret_keys(secret)
    if not keys:
        return {"ok": False, "status": "unverified", "error": "hmac_secret_missing"}
    if algorithm != SYNC_HMAC_ALGORITHM:
        return {"ok": False, "status": "invalid", "error": "unsupported_hmac_algorithm"}
    expected_hash = sync_payload_hash(payload)
    if payload_hash and not hmac.compare_digest(payload_hash, expected_hash):
        return {"ok": False, "status": "invalid", "error": "payload_hash_mismatch"}
    candidate_keys = keys
    if key_id:
        candidate_keys = [item for item in keys if item["key_id"] == key_id]
        if not candidate_keys:
            return {"ok": False, "status": "invalid", "error": "unknown_hmac_key_id", "hmac_key_id": key_id}
    for item in candidate_keys:
        expected = sign_sync_payload(payload, item["secret"], key_id=item["key_id"])
        if hmac.compare_digest(signature, expected["hmac_signature"]):
            return {
                "ok": True,
                "status": "verified",
                "error": "",
                "payload_hash": expected_hash,
                "hmac_key_id": item["key_id"],
            }
    if key_id:
        return {"ok": False, "status": "invalid", "error": "hmac_signature_mismatch"}
    return {"ok": False, "status": "invalid", "error": "hmac_signature_mismatch"}


def _canonical_payload(payload: dict[str, Any]) -> bytes:
    data = {field: _canonical_value(payload.get(field)) for field in SYNC_HMAC_FIELDS}
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _parse_secret_entry(entry: str, *, source: str) -> dict[str, str]:
    text = str(entry or "").strip()
    if not text:
        return {}
    if ":" in text:
        key_id, secret = text.split(":", 1)
        key_id = key_id.strip()
        secret = secret.strip()
        if key_id and secret:
            return {"key_id": key_id[:80], "secret": secret, "source": source}
    return {"key_id": sync_hmac_key_fingerprint(text), "secret": text, "source": source}


def _normalize_secret_keys(secret: str | list[dict[str, str]]) -> list[dict[str, str]]:
    if isinstance(secret, list):
        return [
            {
                "key_id": str(item.get("key_id") or sync_hmac_key_fingerprint(item.get("secret", ""))).strip(),
                "secret": str(item.get("secret") or "").strip(),
            }
            for item in secret
            if str(item.get("secret") or "").strip()
        ]
    secret_text = str(secret or "").strip()
    if not secret_text:
        return []
    return [{"key_id": sync_hmac_key_fingerprint(secret_text), "secret": secret_text}]


def _canonical_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, dict):
        return {str(key): _canonical_value(val) for key, val in sorted(value.items())}
    text = str(value).strip()
    if text.startswith("["):
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, list):
            return [str(item).strip() for item in decoded if str(item).strip()]
    return text
