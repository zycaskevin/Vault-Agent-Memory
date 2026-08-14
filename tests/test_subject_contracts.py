from __future__ import annotations

import ast
import math
from datetime import datetime, timezone
from pathlib import Path

import pytest

from vault.subject_contracts import (
    BUILTIN_SUBJECT_TYPES,
    AssertionClass,
    AssertionDescriptor,
    AssertionNamespace,
    ContractError,
    EffectiveInterval,
    IdentityMode,
    OutputKind,
    SubjectIdentity,
    ValueState,
    ValueStateKind,
    canonical_json_bytes,
    parse_utc_rfc3339,
    private_hmac_sha256,
    public_sha256,
    validate_subject_type,
    validate_utc_rfc3339,
    validate_uuid,
)


@pytest.mark.parametrize(
    "subject_type",
    ["person", "organization", "team", "project", "role", "custom.person-v2"],
)
def test_subject_type_accepts_builtin_and_namespaced_values(subject_type: str) -> None:
    assert validate_subject_type(subject_type) == subject_type


@pytest.mark.parametrize(
    "subject_type",
    ["", "Person", ".person", "person/type", "person type", "p" * 65],
)
def test_subject_type_rejects_noncanonical_values(subject_type: str) -> None:
    with pytest.raises(ContractError):
        validate_subject_type(subject_type)


def test_subject_identity_requires_canonical_uuid_and_enum_mode() -> None:
    value = SubjectIdentity(
        subject_id="123e4567-e89b-12d3-a456-426614174000",
        subject_type="person",
        identity_mode=IdentityMode.CANONICAL,
    )
    assert value.subject_type in BUILTIN_SUBJECT_TYPES
    assert value.to_dict() == {
        "identity_mode": "canonical",
        "subject_id": "123e4567-e89b-12d3-a456-426614174000",
        "subject_type": "person",
    }

    for candidate in (
        "123E4567-E89B-12D3-A456-426614174000",
        "{123e4567-e89b-12d3-a456-426614174000}",
        "not-a-uuid",
    ):
        with pytest.raises(ContractError):
            validate_uuid(candidate)

    with pytest.raises(ContractError):
        SubjectIdentity(
            subject_id="123e4567-e89b-12d3-a456-426614174000",
            subject_type="person",
            identity_mode="canonical",  # type: ignore[arg-type]
        )


def test_utc_rfc3339_and_half_open_interval_contract() -> None:
    assert validate_utc_rfc3339("2026-08-14T06:36:20Z") == "2026-08-14T06:36:20Z"
    assert parse_utc_rfc3339("2026-08-14T06:36:20.123456Z") == datetime(
        2026, 8, 14, 6, 36, 20, 123456, tzinfo=timezone.utc
    )
    assert EffectiveInterval("2026-08-14T06:36:20Z").valid_until is None
    interval = EffectiveInterval(
        "2026-08-14T06:36:20Z", "2026-08-14T06:36:21Z"
    )
    assert interval.contains("2026-08-14T06:36:20Z")
    assert not interval.contains("2026-08-14T06:36:21Z")

    for candidate in (
        "2026-08-14T06:36:20",
        "2026-08-14T06:36:20+00:00",
        "2026-02-30T06:36:20Z",
        "2026-08-14T06:36:20.1234567Z",
    ):
        with pytest.raises(ContractError):
            validate_utc_rfc3339(candidate)

    for end in ("2026-08-14T06:36:20Z", "2026-08-14T06:36:19Z"):
        with pytest.raises(ContractError):
            EffectiveInterval("2026-08-14T06:36:20Z", end)


def test_value_state_is_closed_and_semantically_valid() -> None:
    assert ValueState.known({"name": "Ada"}).to_dict() == {
        "state": "known",
        "value": {"name": "Ada"},
    }
    assert ValueState.unknown("not_reported").to_dict() == {
        "reason": "not_reported",
        "state": "unknown",
    }
    assert ValueState.withheld("policy").to_dict()["state"] == "withheld"
    assert ValueState.unavailable("source_revoked").to_dict()["state"] == "unavailable"

    with pytest.raises(ContractError):
        ValueState(ValueStateKind.KNOWN)
    with pytest.raises(ContractError):
        ValueState(ValueStateKind.UNKNOWN, value="leak", reason="not_reported")
    with pytest.raises(ContractError):
        ValueState(ValueStateKind.WITHHELD, reason="")
    with pytest.raises(ContractError):
        ValueState("known", value=True)  # type: ignore[arg-type]


def test_assertion_taxonomy_and_output_kinds_are_exact() -> None:
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
    assert {item.value for item in OutputKind} == {
        "descriptive",
        "aspirational",
        "decision_policy",
        "delegation_policy",
    }
    descriptor = AssertionDescriptor(
        AssertionClass.EXPLICIT,
        AssertionNamespace.CANONICAL,
        OutputKind.DESCRIPTIVE,
    )
    assert descriptor.to_dict()["assertion_class"] == "explicit"
    with pytest.raises(ContractError):
        AssertionDescriptor(
            "explicit",  # type: ignore[arg-type]
            AssertionNamespace.CANONICAL,
            OutputKind.DESCRIPTIVE,
        )


def test_canonical_json_and_digests_are_stable_and_domain_separated() -> None:
    first = {"z": [True, None, 7], "a": "café"}
    second = {"a": "café", "z": [True, None, 7]}
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert canonical_json_bytes(first) == (
        b'{"a":"caf\xc3\xa9","z":[true,null,7]}'
    )
    assert public_sha256(first) == public_sha256(second)
    assert len(public_sha256(first)) == 64

    key = b"k" * 32
    digest = private_hmac_sha256(first, key=key, domain="subject-identity-v1")
    assert digest == private_hmac_sha256(second, key=key, domain="subject-identity-v1")
    assert digest != public_sha256(first)
    assert digest != private_hmac_sha256(first, key=key, domain="subject-assertion-v1")


@pytest.mark.parametrize(
    "value",
    [math.nan, math.inf, -math.inf, datetime.now(timezone.utc), {"unordered"}, {1: "x"}],
)
def test_canonical_json_rejects_implicit_or_nondeterministic_types(value: object) -> None:
    with pytest.raises(ContractError):
        canonical_json_bytes(value)


def test_contract_module_has_no_database_or_network_imports() -> None:
    module_path = Path(__file__).parents[1] / "vault" / "subject_contracts.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert imported.isdisjoint(
        {"sqlite3", "socket", "requests", "httpx", "urllib", "vault.db"}
    )
