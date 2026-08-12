from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests/fixtures/subject_distillation"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"
FIXTURE_PATHS = (
    "tests/fixtures/subject_distillation/fragments/failure-boundary-cases.json",
    "tests/fixtures/subject_distillation/migration/migration-boundary-cases.json",
    "tests/fixtures/subject_distillation/organization/authority-boundary-cases.json",
    "tests/fixtures/subject_distillation/person/person-cases.json",
)
ORGANIZATION_PATH = (
    "tests/fixtures/subject_distillation/organization/authority-boundary-cases.json"
)
EXPECTED_IDS = {
    *(f"E-P-{index:03d}" for index in range(1, 19)),
    *(f"E-O-{index:03d}" for index in range(1, 6)),
    *(f"E-F-{index:03d}" for index in range(1, 21)),
}
EXPECTED_ORGANIZATION_IDS = {f"E-O-{index:03d}" for index in range(1, 6)}
PRIMARY_DOMAINS = {
    "context_access",
    "decision_governance",
    "evaluation_release",
    "identity_authority",
    "migration_compatibility",
    "preference_modeling",
    "relationships_fragments",
}
EXPECTED_CASE_KEYS = {
    "evaluation",
    "fixture_id",
    "planned_tests",
    "scenario",
    "sbe_id",
    "source_locator",
    "subject_ref",
    "synthetic",
    "title",
}
EXPECTED_EVALUATION_KEYS = {
    "abstention_probe",
    "contains_contextual_constraint",
    "contains_correction",
    "contains_counter_evidence",
    "primary_domain",
}
FORBIDDEN_KEYS = {
    "address",
    "conversation",
    "email",
    "legal_name",
    "message",
    "phone",
    "private_data",
    "raw",
    "raw_evidence",
    "transcript",
}
PRIVATE_MARKERS = (
    b"arthur",
    b"arthurliao",
    b"zycaskevin",
    b"@gmail.com",
    b"/Users/",
    b"/home/",
    b"C:\\Users\\",
)
SECRET_PATTERNS = (
    re.compile(rb"(?:ghp|github_pat|sk_(?:live|test)|rk_(?:live|test))_[A-Za-z0-9_-]{8,}"),
    re.compile(rb"whsec_[A-Za-z0-9_-]{8,}"),
    re.compile(rb"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    re.compile(rb"(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*[^\s,]{8,}"),
)
ABSOLUTE_PATH = re.compile(rb"(?m)(?:^|[\s\"'])(?:/[A-Za-z0-9._-]+/|[A-Za-z]:\\\\|\\\\\\\\)")


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def _load(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    value = json.loads(raw)
    assert isinstance(value, dict)
    assert raw == _canonical(value), f"{path} must use canonical public fixture JSON"
    return raw, value


def _fixture_documents() -> list[tuple[str, bytes, dict[str, Any]]]:
    documents = []
    for relative_path in FIXTURE_PATHS:
        raw, value = _load(REPO_ROOT / relative_path)
        documents.append((relative_path, raw, value))
    return documents


def _walk_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for child in value.values():
            keys.update(_walk_keys(child))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for child in value:
            keys.update(_walk_keys(child))
        return keys
    return set()


def _walk_strings(value: Any) -> list[bytes]:
    if isinstance(value, str):
        return [value.encode()]
    if isinstance(value, dict):
        return [item for child in value.values() for item in _walk_strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in _walk_strings(child)]
    return []


def _public_safety_errors(raw: bytes, document: dict[str, Any]) -> list[str]:
    payloads = [raw, *_walk_strings(document)]
    errors = []
    if FORBIDDEN_KEYS & _walk_keys(document):
        errors.append("forbidden_key")
    if any(
        marker.lower() in payload.lower()
        for marker in PRIVATE_MARKERS
        for payload in payloads
    ):
        errors.append("private_marker")
    if any(
        pattern.search(payload) is not None
        for pattern in SECRET_PATTERNS
        for payload in payloads
    ):
        errors.append("secret_pattern")
    if any(ABSOLUTE_PATH.search(payload) is not None for payload in payloads):
        errors.append("absolute_path")
    if any(b"../" in payload or b"..\\" in payload for payload in payloads):
        errors.append("path_traversal")
    if any(b"\x00" in payload or b"\r" in payload for payload in payloads):
        errors.append("control_byte")
    return errors


def test_fixture_inventory_has_exact_sbe_ownership_and_closed_shape() -> None:
    owners: dict[str, list[str]] = {}
    fixture_ids: set[str] = set()
    for relative_path, _raw, document in _fixture_documents():
        assert set(document) == {
            "artifact_kind",
            "cases",
            "schema_version",
            "synthetic_only",
        }
        assert document["schema_version"] == 1
        assert document["artifact_kind"] == "subject-distillation-synthetic-fixtures"
        assert document["synthetic_only"] is True
        assert isinstance(document["cases"], list) and document["cases"]
        for case in document["cases"]:
            assert isinstance(case, dict)
            assert set(case) == EXPECTED_CASE_KEYS
            assert case["synthetic"] is True
            assert re.fullmatch(r"E-[POF]-\d{3}", case["sbe_id"])
            assert re.fullmatch(r"synthetic-[a-z0-9-]{3,64}", case["fixture_id"])
            assert case["fixture_id"] not in fixture_ids
            fixture_ids.add(case["fixture_id"])
            assert re.fullmatch(r"subject:synthetic:[a-z0-9-]{3,64}", case["subject_ref"])
            assert case["source_locator"] == (
                f"synthetic://subject-distillation/{case['sbe_id'].lower()}"
            )
            assert isinstance(case["title"], str) and 3 <= len(case["title"]) <= 160
            assert isinstance(case["scenario"], str) and 12 <= len(case["scenario"]) <= 600
            assert isinstance(case["planned_tests"], list) and case["planned_tests"]
            assert case["planned_tests"] == sorted(set(case["planned_tests"]))
            assert all(
                re.fullmatch(r"tests/test_[a-z0-9_]+\.py", item)
                for item in case["planned_tests"]
            )
            evaluation = case["evaluation"]
            assert isinstance(evaluation, dict)
            assert set(evaluation) == EXPECTED_EVALUATION_KEYS
            assert evaluation["primary_domain"] in PRIMARY_DOMAINS
            assert all(
                isinstance(evaluation[key], bool)
                for key in EXPECTED_EVALUATION_KEYS - {"primary_domain"}
            )
            owners.setdefault(case["sbe_id"], []).append(relative_path)

    assert set(owners) == EXPECTED_IDS
    assert all(len(paths) == 1 for paths in owners.values())
    assert len(fixture_ids) == 43


def test_fixture_manifest_binds_every_fixture_byte_and_case_id() -> None:
    raw, manifest = _load(MANIFEST_PATH)
    assert raw.endswith(b"\n")
    assert set(manifest) == {
        "artifact_kind",
        "files",
        "schema_version",
        "synthetic_only",
    }
    assert manifest["schema_version"] == 1
    assert manifest["artifact_kind"] == "subject-distillation-synthetic-fixture-manifest"
    assert manifest["synthetic_only"] is True
    assert isinstance(manifest["files"], list)
    assert [entry["path"] for entry in manifest["files"]] == list(FIXTURE_PATHS)

    for entry in manifest["files"]:
        assert set(entry) == {"case_count", "path", "sbe_ids", "sha256"}
        fixture_raw, fixture = _load(REPO_ROOT / entry["path"])
        case_ids = [case["sbe_id"] for case in fixture["cases"]]
        assert case_ids == sorted(case_ids)
        assert entry["case_count"] == len(case_ids)
        assert entry["sbe_ids"] == case_ids
        assert entry["sha256"] == hashlib.sha256(fixture_raw).hexdigest()


def test_organization_authority_fixture_has_exact_five_owners_and_hash() -> None:
    organization_raw, organization = _load(REPO_ROOT / ORGANIZATION_PATH)
    ids = [case["sbe_id"] for case in organization["cases"]]
    assert ids == sorted(EXPECTED_ORGANIZATION_IDS)

    _manifest_raw, manifest = _load(MANIFEST_PATH)
    entries = [entry for entry in manifest["files"] if entry["path"] == ORGANIZATION_PATH]
    assert len(entries) == 1
    assert entries[0]["sbe_ids"] == ids
    assert entries[0]["sha256"] == hashlib.sha256(organization_raw).hexdigest()


def test_fixtures_are_public_synthetic_and_contain_no_raw_or_private_material() -> None:
    for relative_path, raw, document in _fixture_documents():
        assert _public_safety_errors(raw, document) == [], relative_path


def test_public_safety_scan_rejects_each_forbidden_family() -> None:
    token_like = "gh" + "p_" + "1234567890abcdef"
    controls = (
        ({"note": token_like}, "secret_pattern"),
        ({"note": "synthetic output at /tmp/private/item"}, "absolute_path"),
        ({"note": "synthetic output at C:\\Users\\demo\\item"}, "private_marker"),
        ({"note": "Arthur"}, "private_marker"),
        ({"raw_evidence": "fabricated"}, "forbidden_key"),
        ({"note": "../private-item"}, "path_traversal"),
        ({"note": "fabricated\u0000item"}, "control_byte"),
    )
    for document, expected in controls:
        raw = json.dumps(document).encode()
        assert expected in _public_safety_errors(raw, document)


def test_evaluation_flags_include_abstention_and_calibration_controls() -> None:
    cases = [
        case
        for _relative_path, _raw, document in _fixture_documents()
        for case in document["cases"]
    ]
    assert sum(case["evaluation"]["abstention_probe"] for case in cases) >= 5
    assert sum(case["evaluation"]["contains_correction"] for case in cases) >= 3
    assert sum(case["evaluation"]["contains_counter_evidence"] for case in cases) >= 3
    assert sum(case["evaluation"]["contains_contextual_constraint"] for case in cases) >= 3
    assert {case["evaluation"]["primary_domain"] for case in cases} == PRIMARY_DOMAINS
