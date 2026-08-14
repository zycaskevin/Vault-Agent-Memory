"""Pure, deterministic contracts for subject distillation.

This module deliberately owns no storage, network, clock, or process behavior.  It
defines the values that later subject-distillation layers may persist and compare.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ContractError(ValueError):
    """Raised when a value is outside the closed subject contract."""


BUILTIN_SUBJECT_TYPES = frozenset({"person", "organization", "team", "project", "role"})

_SUBJECT_TYPE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_UTC_RFC3339 = re.compile(
    r"^(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})T"
    r"(?P<time>[0-9]{2}:[0-9]{2}:[0-9]{2})"
    r"(?P<fraction>\.[0-9]{1,6})?Z$"
)
_REASON = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_DOMAIN = re.compile(r"^[a-z][a-z0-9_.:-]{0,127}$")


class IdentityMode(str, Enum):
    CANONICAL = "canonical"
    OPAQUE_REFERENCE = "opaque_reference"


class ValueStateKind(str, Enum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    WITHHELD = "withheld"
    UNAVAILABLE = "unavailable"


class AssertionClass(str, Enum):
    EXPLICIT = "explicit"
    CONTROLLER_ATTESTED = "controller_attested"
    THIRD_PARTY_REPORTED = "third_party_reported"
    OBSERVED = "observed"
    INFERRED = "inferred"
    ASPIRATIONAL = "aspirational"
    STRATEGIC = "strategic"
    RECOMMENDATION = "recommendation"


class AssertionNamespace(str, Enum):
    CANONICAL = "canonical"
    RELATIONSHIP_EXPERIENCE = "relationship_experience"
    PERSPECTIVE = "perspective"


class OutputKind(str, Enum):
    DESCRIPTIVE = "descriptive"
    ASPIRATIONAL = "aspirational"
    DECISION_POLICY = "decision_policy"
    DELEGATION_POLICY = "delegation_policy"


def validate_subject_type(value: str) -> str:
    if type(value) is not str or _SUBJECT_TYPE.fullmatch(value) is None:
        raise ContractError("invalid subject_type")
    return value


def validate_uuid(value: str) -> str:
    if type(value) is not str:
        raise ContractError("invalid UUID")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ContractError("invalid UUID") from exc
    if str(parsed) != value:
        raise ContractError("UUID must use canonical lowercase form")
    return value


def parse_utc_rfc3339(value: str) -> datetime:
    if type(value) is not str:
        raise ContractError("invalid UTC RFC3339 timestamp")
    match = _UTC_RFC3339.fullmatch(value)
    if match is None:
        raise ContractError("invalid UTC RFC3339 timestamp")
    fraction = match.group("fraction") or ""
    parse_value = f"{match.group('date')}T{match.group('time')}{fraction}"
    pattern = "%Y-%m-%dT%H:%M:%S.%f" if fraction else "%Y-%m-%dT%H:%M:%S"
    try:
        return datetime.strptime(parse_value, pattern).replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ContractError("invalid UTC RFC3339 timestamp") from exc


def validate_utc_rfc3339(value: str) -> str:
    parse_utc_rfc3339(value)
    return value


def _require_enum(value: object, enum_type: type[Enum], field: str) -> None:
    if type(value) is not enum_type:
        raise ContractError(f"{field} must be a {enum_type.__name__}")


@dataclass(frozen=True, slots=True)
class SubjectIdentity:
    subject_id: str
    subject_type: str
    identity_mode: IdentityMode

    def __post_init__(self) -> None:
        validate_uuid(self.subject_id)
        validate_subject_type(self.subject_type)
        _require_enum(self.identity_mode, IdentityMode, "identity_mode")

    def to_dict(self) -> dict[str, str]:
        return {
            "identity_mode": self.identity_mode.value,
            "subject_id": self.subject_id,
            "subject_type": self.subject_type,
        }


@dataclass(frozen=True, slots=True)
class EffectiveInterval:
    valid_from: str
    valid_until: str | None = None

    def __post_init__(self) -> None:
        start = parse_utc_rfc3339(self.valid_from)
        if self.valid_until is not None:
            end = parse_utc_rfc3339(self.valid_until)
            if end <= start:
                raise ContractError("valid_until must be later than valid_from")

    def contains(self, timestamp: str) -> bool:
        point = parse_utc_rfc3339(timestamp)
        start = parse_utc_rfc3339(self.valid_from)
        if point < start:
            return False
        if self.valid_until is None:
            return True
        return point < parse_utc_rfc3339(self.valid_until)

    def to_dict(self) -> dict[str, str | None]:
        return {"valid_from": self.valid_from, "valid_until": self.valid_until}


def _validate_reason(value: str | None) -> str:
    if type(value) is not str or _REASON.fullmatch(value) is None:
        raise ContractError("invalid ValueState reason")
    return value


@dataclass(frozen=True, slots=True)
class ValueState:
    state: ValueStateKind
    value: Any = None
    reason: str | None = None

    def __post_init__(self) -> None:
        _require_enum(self.state, ValueStateKind, "state")
        if self.state is ValueStateKind.KNOWN:
            if self.value is None or self.reason is not None:
                raise ContractError("known state requires value and forbids reason")
            canonical_json_bytes(self.value)
            return
        if self.value is not None:
            raise ContractError("non-known state forbids value")
        _validate_reason(self.reason)

    @classmethod
    def known(cls, value: Any) -> ValueState:
        return cls(ValueStateKind.KNOWN, value=value)

    @classmethod
    def unknown(cls, reason: str) -> ValueState:
        return cls(ValueStateKind.UNKNOWN, reason=reason)

    @classmethod
    def withheld(cls, reason: str) -> ValueState:
        return cls(ValueStateKind.WITHHELD, reason=reason)

    @classmethod
    def unavailable(cls, reason: str) -> ValueState:
        return cls(ValueStateKind.UNAVAILABLE, reason=reason)

    def to_dict(self) -> dict[str, Any]:
        if self.state is ValueStateKind.KNOWN:
            return {"state": self.state.value, "value": self.value}
        return {"reason": self.reason, "state": self.state.value}


@dataclass(frozen=True, slots=True)
class AssertionDescriptor:
    assertion_class: AssertionClass
    namespace: AssertionNamespace
    output_kind: OutputKind

    def __post_init__(self) -> None:
        _require_enum(self.assertion_class, AssertionClass, "assertion_class")
        _require_enum(self.namespace, AssertionNamespace, "namespace")
        _require_enum(self.output_kind, OutputKind, "output_kind")

    def to_dict(self) -> dict[str, str]:
        return {
            "assertion_class": self.assertion_class.value,
            "namespace": self.namespace.value,
            "output_kind": self.output_kind.value,
        }


def _validate_json_value(value: Any, *, depth: int = 0) -> None:
    if depth > 32:
        raise ContractError("canonical JSON nesting exceeds 32")
    value_type = type(value)
    if value is None or value_type in {str, bool, int}:
        return
    if value_type is float:
        if not math.isfinite(value):
            raise ContractError("canonical JSON forbids non-finite floats")
        return
    if value_type is list:
        if len(value) > 4096:
            raise ContractError("canonical JSON array exceeds 4096 items")
        for item in value:
            _validate_json_value(item, depth=depth + 1)
        return
    if value_type is dict:
        if len(value) > 4096:
            raise ContractError("canonical JSON object exceeds 4096 members")
        for key, item in value.items():
            if type(key) is not str:
                raise ContractError("canonical JSON object keys must be strings")
            _validate_json_value(item, depth=depth + 1)
        return
    raise ContractError("value is not an exact JSON builtin")


def canonical_json_bytes(value: Any) -> bytes:
    """Return recursively key-sorted UTF-8 JSON without whitespace or final LF."""

    _validate_json_value(value)
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ContractError("value cannot be encoded as canonical JSON") from exc
    return encoded


def public_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def private_hmac_sha256(value: Any, *, key: bytes, domain: str) -> str:
    if type(key) is not bytes or len(key) < 32:
        raise ContractError("HMAC key must contain at least 32 bytes")
    if type(domain) is not str or _DOMAIN.fullmatch(domain) is None:
        raise ContractError("invalid HMAC domain")
    message = domain.encode("ascii") + b"\0" + canonical_json_bytes(value)
    return hmac.new(key, message, hashlib.sha256).hexdigest()


__all__ = [
    "BUILTIN_SUBJECT_TYPES",
    "AssertionClass",
    "AssertionDescriptor",
    "AssertionNamespace",
    "ContractError",
    "EffectiveInterval",
    "IdentityMode",
    "OutputKind",
    "SubjectIdentity",
    "ValueState",
    "ValueStateKind",
    "canonical_json_bytes",
    "parse_utc_rfc3339",
    "private_hmac_sha256",
    "public_sha256",
    "validate_subject_type",
    "validate_utc_rfc3339",
    "validate_uuid",
]
