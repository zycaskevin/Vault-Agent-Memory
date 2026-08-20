from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from uuid import UUID

import pytest

from vault.subject_contracts import (
    ASSERTION_OUTPUT_KINDS,
    BUILTIN_SUBJECT_TYPES,
    AssertionClass,
    AssertionNamespace,
    ContractError,
    EffectiveInterval,
    OutputKind,
    SubjectRef,
    ValueState,
    ValueStateKind,
    assertion_output_kind,
    canonical_json_bytes,
    parse_utc_rfc3339,
    private_hmac_sha256,
    public_sha256,
    validate_subject_type,
    validate_uuid,
)


def test_subject_type_is_namespaced_extensible_and_has_exact_builtins() -> None:
    assert BUILTIN_SUBJECT_TYPES == frozenset(
        {"person", "organization", "team", "project", "role"}
    )
    for value in (*sorted(BUILTIN_SUBJECT_TYPES), "acme.organization", "team_ops-v2"):
        assert validate_subject_type(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "Person",
        "1person",
        ".person",
        "person/role",
        "person role",
        "a" * 65,
        7,
        None,
    ],
)
def test_subject_type_rejects_noncanonical_or_unbounded_values(value: object) -> None:
    with pytest.raises(ContractError):
        validate_subject_type(value)  # type: ignore[arg-type]


def test_subject_ref_uses_lowercase_uuid_and_generic_subject_type() -> None:
    subject_id = "123e4567-e89b-42d3-a456-426614174000"
    ref = SubjectRef(subject_id=subject_id, subject_type="vendor.organization")

    assert ref.subject_id == subject_id
    assert ref.subject_type == "vendor.organization"
    assert validate_uuid(subject_id) == subject_id
    assert UUID(ref.subject_id).version == 4


@pytest.mark.parametrize(
    "value",
    [
        "123E4567-E89B-42D3-A456-426614174000",
        "123e4567e89b42d3a456426614174000",
        "00000000-0000-0000-0000-000000000000",
        "not-a-uuid",
        123,
    ],
)
def test_uuid_rejects_noncanonical_and_non_rfc4122_values(value: object) -> None:
    with pytest.raises(ContractError):
        validate_uuid(value)  # type: ignore[arg-type]


def test_utc_rfc3339_parser_is_strict_and_semantic() -> None:
    assert parse_utc_rfc3339("2026-08-20T08:29:00Z") == datetime(
        2026, 8, 20, 8, 29, tzinfo=timezone.utc
    )
    assert parse_utc_rfc3339("2026-08-20T08:29:00.123456Z").microsecond == 123456


@pytest.mark.parametrize(
    "value",
    [
        "2026-08-20T08:29:00+00:00",
        "2026-08-20t08:29:00Z",
        "2026-08-20T08:29:00z",
        "2026-08-20T08:29Z",
        "2026-08-20T08:29:00.1234567Z",
        "2026-02-30T08:29:00Z",
        "2026-08-20T24:00:00Z",
        datetime.now(timezone.utc),
    ],
)
def test_utc_rfc3339_parser_rejects_noncanonical_values(value: object) -> None:
    with pytest.raises(ContractError):
        parse_utc_rfc3339(value)  # type: ignore[arg-type]


def test_effective_interval_is_half_open() -> None:
    interval = EffectiveInterval(
        valid_from="2026-08-20T08:29:00Z",
        valid_until="2026-08-20T09:00:00Z",
    )

    assert interval.contains("2026-08-20T08:29:00Z") is True
    assert interval.contains("2026-08-20T08:59:59.999999Z") is True
    assert interval.contains("2026-08-20T09:00:00Z") is False
    assert interval.contains("2026-08-20T08:28:59Z") is False
    assert EffectiveInterval("2026-08-20T08:29:00Z").contains(
        "2099-01-01T00:00:00Z"
    )


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("2026-08-20T08:29:00Z", "2026-08-20T08:29:00Z"),
        ("2026-08-20T08:29:00Z", "2026-08-20T08:28:59Z"),
        ("invalid", None),
    ],
)
def test_effective_interval_rejects_empty_reversed_or_invalid_windows(
    start: str, end: str | None
) -> None:
    with pytest.raises(ContractError):
        EffectiveInterval(start, end)


def test_value_state_has_exact_states_and_closed_payload_shapes() -> None:
    assert {state.value for state in ValueStateKind} == {
        "known",
        "unknown",
        "withheld",
        "unavailable",
    }
    assert ValueState.known("option-b").to_json() == {
        "state": "known",
        "value": "option-b",
    }
    assert ValueState.unknown("not_reported").to_json() == {
        "state": "unknown",
        "reason": "not_reported",
    }
    assert ValueState.withheld("policy").to_json() == {
        "state": "withheld",
        "reason": "policy",
    }
    assert ValueState.unavailable("source_revoked").to_json() == {
        "state": "unavailable",
        "reason": "source_revoked",
    }


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ValueState.known(None),
        lambda: ValueState(ValueStateKind.KNOWN, value="x", reason="extra"),
        lambda: ValueState(ValueStateKind.UNKNOWN, value="guessed", reason="missing"),
        lambda: ValueState.unknown(""),
        lambda: ValueState.withheld(" bad reason "),
    ],
)
def test_value_state_rejects_collapsed_or_ambiguous_values(factory: object) -> None:
    with pytest.raises(ContractError):
        factory()  # type: ignore[operator]


def test_assertion_classes_namespaces_and_output_kinds_are_exact() -> None:
    assert {item.value for item in AssertionClass} == {
        "explicit",
        "controller_attested",
        "third_party_reported",
        "observed",
        "inferred",
        "aspirational",
        "strategic",
        "recommendation",
    }
    assert {item.value for item in AssertionNamespace} == {
        "canonical",
        "relationship_experience",
        "perspective",
    }
    assert set(ASSERTION_OUTPUT_KINDS) == set(AssertionClass)
    assert assertion_output_kind(AssertionClass.INFERRED) is OutputKind.HYPOTHESIS
    assert assertion_output_kind(AssertionClass.ASPIRATIONAL) is OutputKind.ASPIRATION
    assert assertion_output_kind(AssertionClass.STRATEGIC) is OutputKind.STRATEGY
    assert assertion_output_kind(AssertionClass.RECOMMENDATION) is OutputKind.RECOMMENDATION
    for assertion_class in (
        AssertionClass.EXPLICIT,
        AssertionClass.CONTROLLER_ATTESTED,
        AssertionClass.THIRD_PARTY_REPORTED,
        AssertionClass.OBSERVED,
    ):
        assert assertion_output_kind(assertion_class) is OutputKind.FACT


def test_canonical_json_is_recursive_sorted_utf8_and_stable() -> None:
    first = {"z": [3, {"é": True, "a": None}], "a": {"b": 2, "a": 1}}
    second = {"a": {"a": 1, "b": 2}, "z": [3, {"a": None, "é": True}]}
    expected = '{"a":{"a":1,"b":2},"z":[3,{"a":null,"é":true}]}'.encode()

    assert canonical_json_bytes(first) == expected
    assert canonical_json_bytes(second) == expected
    assert public_sha256(first) == hashlib.sha256(expected).hexdigest()


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        -float("inf"),
        {"nested": [1, float("nan")]},
        {1: "non-string-key"},
        {"set": {1, 2}},
        {"tuple": (1, 2)},
        {"bytes": b"secret"},
        {"datetime": datetime.now(timezone.utc)},
    ],
)
def test_canonical_json_rejects_non_json_and_non_finite_values(value: object) -> None:
    with pytest.raises(ContractError):
        canonical_json_bytes(value)


def test_private_hmac_is_domain_separated_and_byte_stable() -> None:
    key = bytes(range(32))
    domain = b"vault-subject-value-v1\x00"
    value = {"subject_id": "123e4567-e89b-42d3-a456-426614174000", "value": "x"}
    expected = hmac.new(
        key,
        len(domain).to_bytes(8, "big") + domain + canonical_json_bytes(value),
        hashlib.sha256,
    ).hexdigest()

    assert private_hmac_sha256(key, domain, value) == expected
    assert private_hmac_sha256(key, domain + b"other", value) != expected
    assert private_hmac_sha256(key, domain, {"value": "y"}) != expected


def test_private_hmac_frames_variable_length_domain_separator() -> None:
    key = bytes(range(32))

    assert b"x" + canonical_json_bytes(10) == b"x1" + canonical_json_bytes(0)
    assert private_hmac_sha256(key, b"x", 10) != private_hmac_sha256(key, b"x1", 0)


@pytest.mark.parametrize(
    ("key", "domain"),
    [(b"", b"domain\x00"), (b"key", b""), ("key", b"domain\x00"), (b"key", "domain")],
)
def test_private_hmac_requires_nonempty_byte_key_and_domain(
    key: object, domain: object
) -> None:
    with pytest.raises(ContractError):
        private_hmac_sha256(key, domain, {})  # type: ignore[arg-type]
