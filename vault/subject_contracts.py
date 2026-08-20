"""Pure value contracts shared by every Subject adapter."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Generic, TypeVar
from uuid import RFC_4122, UUID


class ContractError(ValueError):
    """Raised when an input is outside the public Subject contract."""


BUILTIN_SUBJECT_TYPES = frozenset({"person", "organization", "team", "project", "role"})

_SUBJECT_TYPE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_UTC_RFC3339 = re.compile(
    r"^(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})"
    r"T(?P<time>[0-9]{2}:[0-9]{2}:[0-9]{2})"
    r"(?P<fraction>\.[0-9]{1,6})?Z$"
)
_BOUNDED_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")


def validate_subject_type(value: str) -> str:
    """Return an already-canonical extensible Subject type."""

    if type(value) is not str or _SUBJECT_TYPE.fullmatch(value) is None:
        raise ContractError("invalid subject_type")
    return value


def validate_uuid(value: str) -> str:
    """Return a lowercase hyphenated RFC 4122 UUID."""

    if type(value) is not str or _UUID.fullmatch(value) is None:
        raise ContractError("invalid UUID")
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise ContractError("invalid UUID") from exc
    if parsed.int == 0 or parsed.variant != RFC_4122 or parsed.version is None or str(parsed) != value:
        raise ContractError("invalid UUID")
    return value


def parse_utc_rfc3339(value: str) -> datetime:
    """Parse the canonical UTC RFC3339 subset used by Subject records."""

    if type(value) is not str or _UTC_RFC3339.fullmatch(value) is None:
        raise ContractError("invalid UTC RFC3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError("invalid UTC RFC3339 timestamp") from exc
    if parsed.tzinfo != timezone.utc:
        raise ContractError("timestamp is not UTC")
    return parsed


@dataclass(frozen=True, slots=True)
class SubjectRef:
    """Stable generic Subject identity."""

    subject_id: str
    subject_type: str

    def __post_init__(self) -> None:
        validate_uuid(self.subject_id)
        validate_subject_type(self.subject_type)


@dataclass(frozen=True, slots=True)
class EffectiveInterval:
    """UTC half-open interval ``[valid_from, valid_until)``."""

    valid_from: str
    valid_until: str | None = None

    def __post_init__(self) -> None:
        start = parse_utc_rfc3339(self.valid_from)
        if self.valid_until is not None:
            end = parse_utc_rfc3339(self.valid_until)
            if end <= start:
                raise ContractError("effective interval must be non-empty and increasing")

    def contains(self, value: str) -> bool:
        """Return whether ``value`` falls inside the half-open interval."""

        point = parse_utc_rfc3339(value)
        start = parse_utc_rfc3339(self.valid_from)
        if point < start:
            return False
        return self.valid_until is None or point < parse_utc_rfc3339(self.valid_until)


class ValueStateKind(str, Enum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    WITHHELD = "withheld"
    UNAVAILABLE = "unavailable"


_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class ValueState(Generic[_T]):
    """A value that keeps unknown, withheld, and unavailable distinct."""

    state: ValueStateKind
    value: _T | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if type(self.state) is not ValueStateKind:
            raise ContractError("invalid value state")
        if self.state is ValueStateKind.KNOWN:
            if self.value is None or self.reason is not None:
                raise ContractError("known values require only a value")
            canonical_json_bytes(self.value)
            return
        if self.value is not None:
            raise ContractError("non-known values cannot carry a guessed value")
        if type(self.reason) is not str or _BOUNDED_CODE.fullmatch(self.reason) is None:
            raise ContractError("non-known values require a bounded reason")

    @classmethod
    def known(cls, value: _T) -> ValueState[_T]:
        return cls(ValueStateKind.KNOWN, value=value)

    @classmethod
    def unknown(cls, reason: str) -> ValueState[Any]:
        return cls(ValueStateKind.UNKNOWN, reason=reason)

    @classmethod
    def withheld(cls, reason: str) -> ValueState[Any]:
        return cls(ValueStateKind.WITHHELD, reason=reason)

    @classmethod
    def unavailable(cls, reason: str) -> ValueState[Any]:
        return cls(ValueStateKind.UNAVAILABLE, reason=reason)

    def to_json(self) -> dict[str, Any]:
        if self.state is ValueStateKind.KNOWN:
            return {"state": self.state.value, "value": self.value}
        return {"state": self.state.value, "reason": self.reason}


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
    FACT = "fact"
    HYPOTHESIS = "hypothesis"
    ASPIRATION = "aspiration"
    STRATEGY = "strategy"
    RECOMMENDATION = "recommendation"


ASSERTION_OUTPUT_KINDS = MappingProxyType(
    {
        AssertionClass.EXPLICIT: OutputKind.FACT,
        AssertionClass.CONTROLLER_ATTESTED: OutputKind.FACT,
        AssertionClass.THIRD_PARTY_REPORTED: OutputKind.FACT,
        AssertionClass.OBSERVED: OutputKind.FACT,
        AssertionClass.INFERRED: OutputKind.HYPOTHESIS,
        AssertionClass.ASPIRATIONAL: OutputKind.ASPIRATION,
        AssertionClass.STRATEGIC: OutputKind.STRATEGY,
        AssertionClass.RECOMMENDATION: OutputKind.RECOMMENDATION,
    }
)


def assertion_output_kind(value: AssertionClass) -> OutputKind:
    """Return the immutable renderer category for an assertion class."""

    if type(value) is not AssertionClass:
        raise ContractError("invalid assertion class")
    return ASSERTION_OUTPUT_KINDS[value]


def _validate_json_value(value: Any) -> None:
    if value is None or type(value) in {str, bool, int}:
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ContractError("non-finite JSON number")
        return
    if type(value) is list:
        for item in value:
            _validate_json_value(item)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ContractError("JSON object keys must be strings")
            _validate_json_value(item)
        return
    raise ContractError("value is not canonical JSON data")


def canonical_json_bytes(value: Any) -> bytes:
    """Encode recursively sorted UTF-8 JSON without insignificant whitespace."""

    _validate_json_value(value)
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ContractError("value cannot be encoded as canonical JSON") from exc


def public_sha256(value: Any) -> str:
    """Hash public or synthetic canonical JSON."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def private_hmac_sha256(key: bytes, domain_separator: bytes, value: Any) -> str:
    """Authenticate private canonical JSON with an explicit domain separator."""

    if type(key) is not bytes or not key:
        raise ContractError("HMAC key must be non-empty bytes")
    if type(domain_separator) is not bytes or not domain_separator:
        raise ContractError("HMAC domain separator must be non-empty bytes")
    return hmac.new(
        key,
        len(domain_separator).to_bytes(8, "big")
        + domain_separator
        + canonical_json_bytes(value),
        hashlib.sha256,
    ).hexdigest()


__all__ = [
    "ASSERTION_OUTPUT_KINDS",
    "BUILTIN_SUBJECT_TYPES",
    "AssertionClass",
    "AssertionNamespace",
    "ContractError",
    "EffectiveInterval",
    "OutputKind",
    "SubjectRef",
    "ValueState",
    "ValueStateKind",
    "assertion_output_kind",
    "canonical_json_bytes",
    "parse_utc_rfc3339",
    "private_hmac_sha256",
    "public_sha256",
    "validate_subject_type",
    "validate_uuid",
]
