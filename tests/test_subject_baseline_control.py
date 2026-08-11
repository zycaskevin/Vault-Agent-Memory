from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
MANIFEST = REPO_ROOT / "specs/subject-distillation/baseline-manifest.json"
EVIDENCE_DIR = REPO_ROOT / "specs/subject-distillation/evidence/0dc10cfc4a429662"
READER = REPO_ROOT / "scripts/read_subject_baseline_id.py"
VALIDATOR = REPO_ROOT / "scripts/validate_subject_evidence.py"
SCHEMA_DIR = REPO_ROOT / "specs/subject-distillation/evidence-schemas"
SCHEMA_NAMES = (
    "attestation",
    "backup-restore",
    "environment",
    "fresh-review",
    "migration",
    "review-result",
)


def _run(*args: str) -> subprocess.CompletedProcess[bytes]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [PYTHON, *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        check=False,
        timeout=20,
    )


def _load_validator():
    spec = importlib.util.spec_from_file_location("subject_evidence_validator", VALIDATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def test_t001_control_plane_artifacts_exist_with_expected_modes() -> None:
    expected = {
        READER: 0o755,
        VALIDATOR: 0o755,
        REPO_ROOT / "scripts/validate_subject_progress.py": 0o755,
        REPO_ROOT / "scripts/update_subject_progress.py": 0o755,
    }
    for path, mode in expected.items():
        assert path.is_file()
        assert path.stat().st_mode & 0o777 == mode
    for name in SCHEMA_NAMES:
        path = SCHEMA_DIR / f"{name}.schema.json"
        assert path.is_file()
        assert path.stat().st_mode & 0o777 == 0o644


def test_baseline_reader_accepts_exact_manifest() -> None:
    result = _run(str(READER), "--manifest", str(MANIFEST))
    assert result.returncode == 0
    assert result.stdout == b"0dc10cfc4a429662\n"
    assert result.stderr == b""


def test_baseline_reader_rejects_tampered_manifest_without_echo(tmp_path: Path) -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    value["baseline_id"] = "0" * 16
    candidate = tmp_path / "manifest.json"
    candidate.write_bytes(_canonical(value))
    result = _run(str(READER), "--manifest", str(candidate))
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == b"SUBJECT_BASELINE_ID_DENY\n"
    assert str(candidate).encode() not in result.stderr


def test_six_schema_files_are_exact_closed_contracts() -> None:
    validator = _load_validator()
    expected = validator._expected_schemas()
    assert set(expected) == set(SCHEMA_NAMES)
    for name, schema in expected.items():
        raw = (SCHEMA_DIR / f"{name}.schema.json").read_bytes()
        assert raw == _canonical(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["additionalProperties"] is False


def _schema_sample(schema: dict) -> object:
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    expected_type = schema.get("type")
    if isinstance(expected_type, list):
        if "null" in expected_type:
            return None
        expected_type = expected_type[0]
    if expected_type == "object":
        return {
            key: _schema_sample(value)
            for key, value in schema["properties"].items()
        }
    if expected_type == "array":
        return [
            _schema_sample(schema["items"])
            for _ in range(schema.get("minItems", 0))
        ]
    if expected_type == "integer":
        return schema.get("minimum", 0)
    if expected_type == "boolean":
        return False
    pattern = schema.get("pattern", "")
    if "git:" in pattern:
        return "git:" + "a" * 40
    if "{64}" in pattern:
        return "a" * 64
    if "{16}" in pattern:
        return "a" * 16
    if "T[0-9]" in pattern:
        return "2026-08-10T00:00:00Z"
    if "A-Z" in pattern and "A-Za-z" not in pattern:
        return "CODE"
    if "/" in pattern:
        return "file.txt"
    return "opaque"


def test_all_six_schemas_have_positive_and_closed_negative_controls() -> None:
    validator = _load_validator()
    for schema in validator._expected_schemas().values():
        sample = _schema_sample(schema)
        validator._validate_schema(schema, sample)
        unknown = deepcopy(sample)
        unknown["unexpected"] = "value"
        with pytest.raises(validator.Denied):
            validator._validate_schema(schema, unknown)
        invalid_integer = deepcopy(sample)
        invalid_integer["schema_version"] = True
        with pytest.raises(validator.Denied):
            validator._validate_schema(schema, invalid_integer)


def test_environment_evidence_reconstructs_authorization_packet() -> None:
    result = _run(
        str(VALIDATOR),
        "--manifest",
        str(MANIFEST),
        "--evidence-dir",
        str(EVIDENCE_DIR),
        "--require",
        "environment",
    )
    assert result.returncode == 0
    assert result.stderr == b""
    payload = json.loads(result.stdout)
    assert payload == {
        "baseline_id": "0dc10cfc4a429662",
        "status": "PASS",
        "validated": ["environment"],
    }


@pytest.mark.parametrize(
    ("owning_key", "value", "allowed"),
    [
        ("sha256", "a" * 64, True),
        ("source_commit", "git:" + "a" * 40, True),
        ("ordinary", "four.part.public.identifier", True),
        ("ordinary", "a" * 64, False),
        ("sha256", "A" * 64, False),
        ("ordinary", "prefix ghp_example", False),
        ("ordinary", "credential=value", False),
        ("ordinary", "-----BEGIN PRIVATE KEY-----", False),
    ],
)
def test_evidence_uses_shared_public_safety_scanner(
    owning_key: str, value: str, allowed: bool
) -> None:
    validator = _load_validator()
    candidate = {owning_key: value}
    if allowed:
        validator._scan_public(candidate)
    else:
        with pytest.raises(validator.Denied):
            validator._scan_public(candidate)


def test_all_shared_digest_keys_are_exact_and_malformed_values_deny() -> None:
    validator = _load_validator()
    assert len(validator.authorization.DIGEST_KEYS) == 22
    for key in validator.authorization.DIGEST_KEYS:
        validator._scan_public({key: "a" * 64})
        for invalid in ("A" * 64, "a" * 63, "a" * 65):
            with pytest.raises(validator.Denied):
                validator._scan_public({key: invalid})
    for length in (32, 64, 128):
        with pytest.raises(validator.Denied):
            validator._scan_public({"ordinary": "a" * length})


@pytest.mark.parametrize(
    "unsafe",
    [
        "prefix ghp_example",
        "prefix rk_test_example",
        "prefix whsec_example",
        "prefix Bearer:example",
        "prefix eyJabc.def.ghi",
        "prefix password=value",
        "prefix -----BEGIN PRIVATE KEY----- suffix",
    ],
)
def test_shared_scanner_denies_embedded_secret_families(unsafe: str) -> None:
    validator = _load_validator()
    with pytest.raises(validator.Denied):
        validator._scan_public({"ordinary": unsafe})


def test_environment_rejects_authorization_digest_mutation() -> None:
    validator = _load_validator()
    value = json.loads((EVIDENCE_DIR / "environment.json").read_text(encoding="utf-8"))
    value["implementation_authorization"]["authorization_pass_packet_sha256"] = "0" * 64
    manifest, _result = validator._manifest(REPO_ROOT, MANIFEST)
    with pytest.raises(validator.Denied):
        validator._validate_environment(
            REPO_ROOT,
            value,
            manifest,
            validator._expected_schemas()["environment"],
        )


def test_environment_authorization_is_independent_of_process_cwd(
    tmp_path: Path, monkeypatch
) -> None:
    validator = _load_validator()
    value = json.loads((EVIDENCE_DIR / "environment.json").read_text(encoding="utf-8"))
    manifest, _result = validator._manifest(REPO_ROOT, MANIFEST)
    monkeypatch.chdir(tmp_path)
    validator._validate_environment(
        REPO_ROOT,
        value,
        manifest,
        validator._expected_schemas()["environment"],
    )


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("source_commit",), "git:" + "0" * 40),
        (("implementation_authorization", "implementation_base_commit"), "git:" + "0" * 40),
        (("implementation_authorization", "authorization_id"), "0" * 64),
        (("implementation_authorization", "proposal_id"), "0" * 64),
        (("implementation_authorization", "receipt_sha256"), "0" * 64),
        (("implementation_authorization", "scope_sha256"), "0" * 64),
        (("implementation_authorization", "authorization_pass_packet_sha256"), "0" * 64),
        (("implementation_authorization", "authorization_verifier_sha256"), "0" * 64),
        (("implementation_authorization", "authorization_schema_sha256"), "0" * 64),
        (("implementation_authorization", "recorded_at_utc"), "2026-08-10T00:00:00Z"),
        (("implementation_authorization", "owner_confirmation_ref"), "owner-confirmation:mutated"),
        (("implementation_authorization", "runner", "sha256"), "0" * 64),
    ],
)
def test_environment_authorization_reconstruction_rejects_every_binding_mutation(
    path: tuple[str, ...], replacement: object
) -> None:
    validator = _load_validator()
    repo_root = REPO_ROOT
    manifest, _result = validator._manifest(repo_root, MANIFEST)
    schema = validator._expected_schemas()["environment"]
    value = json.loads((EVIDENCE_DIR / "environment.json").read_text(encoding="utf-8"))
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement
    with pytest.raises(validator.Denied):
        validator._validate_environment(repo_root, value, manifest, schema)


def _semantic_common(kind: str, producer: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "artifact_kind": kind,
        "baseline_id": "0dc10cfc4a429662",
        "source_commit": "git:1eb4d0ef7209cf3f04c5d163561403e835311aeb",
        "created_at_utc": "2026-08-10T00:00:00Z",
        "producer_task": producer,
    }


def _review_value(validator, manifest, scope: str, index: int) -> dict[str, object]:
    return {
        **_semantic_common("subject-distillation-review-result", "T-031"),
        "review_id": f"review-{index}",
        "builder_principal": "builder",
        "reviewer_principal": f"reviewer-{index}",
        "review_scope": scope,
        "reviewed_normative_hashes": validator._normative_entries(manifest),
        "reviewed_tree_sha256": "4" * 64,
        "p0": 0,
        "p1": 0,
        "p2": 0,
        "verdict": "PASS",
        "findings": [],
    }


def _fresh_review_fixture(validator, manifest, evidence_dir: Path):
    scopes = (
        "requirements-architecture",
        "security-privacy",
        "execution-traceability",
    )
    review_dir = evidence_dir / "reviews"
    review_dir.mkdir(parents=True)
    reviews = []
    values = {}
    for index, scope in enumerate(scopes):
        review = _review_value(validator, manifest, scope, index)
        raw = validator._canonical(review)
        (review_dir / f"{scope}.json").write_bytes(raw)
        values[scope] = review
        reviews.append(
            {
                "review_scope": scope,
                "review_id": review["review_id"],
                "reviewer_principal": review["reviewer_principal"],
                "artifact_sha256": hashlib.sha256(raw).hexdigest(),
                "p0": 0,
                "p1": 0,
                "p2": 0,
                "verdict": "PASS",
            }
        )
    fresh = {
        **_semantic_common("subject-distillation-fresh-review", "T-031"),
        "builder_principal": "builder",
        "reviews": reviews,
        "reviewed_normative_hashes": validator._normative_entries(manifest),
        "reviewed_tree_sha256": "4" * 64,
        "p0": 0,
        "p1": 0,
        "p2": 0,
        "verdict": "PASS",
    }
    return fresh, values


def test_migration_and_backup_semantic_contracts() -> None:
    validator = _load_validator()
    manifest, _result = validator._manifest(REPO_ROOT, MANIFEST)
    schemas = validator._expected_schemas()
    command = [
        "python",
        "-m",
        "pytest",
        "-q",
        "tests/test_subject_migration.py",
        "tests/test_db_backup.py",
    ]
    for name in ("migration", "backup-restore"):
        value = {
            **_semantic_common(f"subject-distillation-{name}-evidence", "T-027"),
            "command": command,
            "exit_code": 0,
            "input_hash": "1" * 64,
            "output_hash": "2" * 64,
            "rollback_path": {"kind": "public_safe_locator", "id": "rollback-1"},
            "result": "PASS",
        }
        validator._validate_common(value, manifest, schemas[name], REPO_ROOT)
        validator._validate_simple(
            name,
            value,
            repo_root=REPO_ROOT,
            evidence_dir=EVIDENCE_DIR,
            manifest=manifest,
        )
        for mutation in (
            lambda candidate: candidate.update({"command": [*command[:-1], "wrong"]}),
            lambda candidate: candidate.update({"result": "FAIL"}),
            lambda candidate: candidate.update({"exit_code": 1, "result": "PASS"}),
        ):
            invalid = deepcopy(value)
            mutation(invalid)
            with pytest.raises(validator.Denied):
                validator._validate_simple(
                    name,
                    invalid,
                    repo_root=REPO_ROOT,
                    evidence_dir=EVIDENCE_DIR,
                    manifest=manifest,
                )


def test_review_result_semantic_contract_matrix() -> None:
    validator = _load_validator()
    manifest, _result = validator._manifest(REPO_ROOT, MANIFEST)
    value = _review_value(
        validator,
        manifest,
        "requirements-architecture",
        0,
    )
    value.update(
        {
            "p2": 2,
            "findings": [
                {
                    "finding_id": "finding-a",
                    "severity": "P2",
                    "summary_code": "FOLLOW_UP_A",
                    "disposition": "FOLLOW_UP",
                },
                {
                    "finding_id": "finding-b",
                    "severity": "P2",
                    "summary_code": "FOLLOW_UP_B",
                    "disposition": "DEFERRED",
                },
            ],
        }
    )
    validator._validate_common(
        value,
        manifest,
        validator._expected_schemas()["review-result"],
        REPO_ROOT,
    )
    validator._validate_simple(
        "review-result",
        value,
        repo_root=REPO_ROOT,
        evidence_dir=EVIDENCE_DIR,
        manifest=manifest,
    )
    invalid_values = []
    for mutate in (
        lambda candidate: candidate["findings"].reverse(),
        lambda candidate: candidate["findings"][1].update({"finding_id": "finding-a"}),
        lambda candidate: candidate.update({"reviewer_principal": "builder"}),
        lambda candidate: candidate.update({"p2": 1}),
        lambda candidate: candidate["findings"][0].update({"disposition": None}),
        lambda candidate: candidate.update({"verdict": "FAIL"}),
        lambda candidate: candidate["reviewed_normative_hashes"][0].update(
            {"sha256": "0" * 64}
        ),
    ):
        invalid = deepcopy(value)
        mutate(invalid)
        invalid_values.append(invalid)
    for invalid in invalid_values:
        with pytest.raises(validator.Denied):
            validator._validate_simple(
                "review-result",
                invalid,
                repo_root=REPO_ROOT,
                evidence_dir=EVIDENCE_DIR,
                manifest=manifest,
            )


def test_fresh_review_semantic_contract_matrix(tmp_path: Path) -> None:
    validator = _load_validator()
    manifest, _result = validator._manifest(REPO_ROOT, MANIFEST)
    evidence_dir = tmp_path / "evidence"
    fresh, _reviews = _fresh_review_fixture(validator, manifest, evidence_dir)
    validator._validate_common(
        fresh,
        manifest,
        validator._expected_schemas()["fresh-review"],
        REPO_ROOT,
    )
    validator._validate_simple(
        "fresh-review",
        fresh,
        repo_root=REPO_ROOT,
        evidence_dir=evidence_dir,
        manifest=manifest,
    )
    invalid_values = []
    for mutate in (
        lambda candidate: candidate["reviews"].reverse(),
        lambda candidate: candidate["reviews"][1].update(
            {"reviewer_principal": "reviewer-0"}
        ),
        lambda candidate: candidate["reviews"][0].update(
            {"artifact_sha256": "0" * 64}
        ),
        lambda candidate: candidate.update({"p2": 1}),
        lambda candidate: candidate.update({"reviewed_tree_sha256": "0" * 64}),
        lambda candidate: candidate.update({"verdict": "FAIL"}),
    ):
        invalid = deepcopy(fresh)
        mutate(invalid)
        invalid_values.append(invalid)
    for invalid in invalid_values:
        with pytest.raises(validator.Denied):
            validator._validate_simple(
                "fresh-review",
                invalid,
                repo_root=REPO_ROOT,
                evidence_dir=evidence_dir,
                manifest=manifest,
            )


def test_attestation_semantic_contract_matrix(tmp_path: Path, monkeypatch) -> None:
    validator = _load_validator()
    manifest, _result = validator._manifest(REPO_ROOT, MANIFEST)
    evidence_dir = tmp_path / "evidence"
    fresh, reviews = _fresh_review_fixture(validator, manifest, evidence_dir)
    environment_path = EVIDENCE_DIR / "environment.json"
    environment = json.loads(environment_path.read_text(encoding="utf-8"))
    environment_raw = validator._canonical(environment)
    proof = environment["implementation_authorization"]
    original_load = validator._load_json

    def load_json(path: Path, *, canonical: bool = True):
        if path.name == "fresh-review.json":
            return fresh, validator._canonical(fresh)
        if path.parent.name == "reviews" and path.stem in reviews:
            value = reviews[path.stem]
            return value, validator._canonical(value)
        return original_load(path, canonical=canonical)

    def large_file(path: Path, _maximum: int) -> bytes:
        return f"artifact:{path.relative_to(REPO_ROOT)}".encode()

    monkeypatch.setattr(validator, "_load_json", load_json)
    monkeypatch.setattr(validator, "_read_large_file", large_file)
    artifact_entries = [
        {
            "path": path,
            "sha256": hashlib.sha256(
                f"artifact:{path}".encode()
            ).hexdigest(),
        }
        for path in validator._attestation_paths("0dc10cfc4a429662")
    ]
    reviewer_set = [
        {
            key: item[key]
            for key in (
                "review_scope",
                "review_id",
                "reviewer_principal",
                "artifact_sha256",
            )
        }
        for item in fresh["reviews"]
    ]
    value = {
        **_semantic_common("subject-distillation-attestation", "T-033"),
        "artifact_sha256": artifact_entries,
        "implementation_authorization": {
            "environment_path": (
                "specs/subject-distillation/evidence/"
                "0dc10cfc4a429662/environment.json"
            ),
            "environment_sha256": hashlib.sha256(environment_raw).hexdigest(),
            "authorization_id": proof["authorization_id"],
            "authorization_pass_packet_sha256": proof[
                "authorization_pass_packet_sha256"
            ],
            "proposal_id": proof["proposal_id"],
            "receipt_sha256": proof["receipt_sha256"],
            "scope_sha256": proof["scope_sha256"],
            "owner_confirmation_ref": proof["owner_confirmation_ref"],
            "status": "PASS",
        },
        "reviewer_set": reviewer_set,
        "reviewed_tree_sha256": "4" * 64,
        "release_label": "experimental",
        "private_shadow_receipt_sha256": None,
    }
    validator._validate_common(
        value,
        manifest,
        validator._expected_schemas()["attestation"],
        REPO_ROOT,
    )
    validator._validate_simple(
        "attestation",
        value,
        repo_root=REPO_ROOT,
        evidence_dir=evidence_dir,
        manifest=manifest,
    )
    for mutate in (
        lambda candidate: candidate["artifact_sha256"][0].update(
            {"sha256": "0" * 64}
        ),
        lambda candidate: candidate["implementation_authorization"].update(
            {"authorization_id": "0" * 64}
        ),
        lambda candidate: candidate["reviewer_set"].reverse(),
        lambda candidate: candidate.update({"reviewed_tree_sha256": "0" * 64}),
        lambda candidate: candidate.update(
            {"release_label": "stable", "private_shadow_receipt_sha256": None}
        ),
    ):
        invalid = deepcopy(value)
        mutate(invalid)
        with pytest.raises(validator.Denied):
            validator._validate_simple(
                "attestation",
                invalid,
                repo_root=REPO_ROOT,
                evidence_dir=evidence_dir,
                manifest=manifest,
            )


def test_duplicate_key_noncanonical_and_resource_limits_fail_closed(tmp_path: Path) -> None:
    validator = _load_validator()
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_bytes(b'{"a":1,"a":2}\n')
    with pytest.raises(validator.Denied):
        validator._load_json(duplicate)

    noncanonical = tmp_path / "noncanonical.json"
    noncanonical.write_bytes(b'{"b": 2, "a": 1}\n')
    with pytest.raises(validator.Denied):
        validator._load_json(noncanonical)

    boundary = tmp_path / "boundary.bin"
    boundary.write_bytes(b"x" * 1_048_576)
    assert len(validator._read_file(boundary)) == 1_048_576
    boundary.write_bytes(b"x" * 1_048_577)
    with pytest.raises(validator.Denied):
        validator._read_file(boundary)


def test_descriptor_reader_rejects_symlink(tmp_path: Path) -> None:
    validator = _load_validator()
    target = tmp_path / "target.json"
    target.write_bytes(b"{}\n")
    alias = tmp_path / "alias.json"
    alias.symlink_to(target)
    with pytest.raises(validator.Denied):
        validator._read_file(alias)


def _stage_bytes(
    validator,
    *,
    stage: str = "unit",
    stdout: bytes = b"ok\n",
    stderr: bytes = b"",
) -> bytes:
    header = {
        "schema_version": 1,
        "artifact_kind": "subject-distillation-stage-evidence",
        "baseline_id": "0dc10cfc4a429662",
        "source_commit": "git:1eb4d0ef7209cf3f04c5d163561403e835311aeb",
        "created_at_utc": "2026-08-10T00:00:00Z",
        "producer_task": "T-029",
        "stage": stage,
        "requires": validator.STAGE_REQUIRES[stage],
        "argv": validator.STAGE_ARGV[stage],
        "started_at_utc": "2026-08-10T00:00:00Z",
        "completed_at_utc": "2026-08-10T00:01:00Z",
        "exit_code": 0,
        "result": "PASS",
        "stdout_size_bytes": len(stdout),
        "stderr_size_bytes": len(stderr),
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
    }
    return validator._canonical(header) + stdout + stderr


def test_stage_evidence_exact_framing_and_public_stream_controls(tmp_path: Path) -> None:
    validator = _load_validator()
    manifest, _result = validator._manifest(REPO_ROOT, MANIFEST)
    for stage in validator.STAGES:
        path = tmp_path / f"{stage}.txt"
        path.write_bytes(_stage_bytes(validator, stage=stage))
        validator._validate_stage(REPO_ROOT, path, stage, manifest)
    path = tmp_path / "unit.txt"
    for unsafe in (
        b"ordinary ghp_example\n",
        b"ordinary sk_test_example\n",
        b"ordinary rk_test_example\n",
        b"ordinary whsec_example\n",
        b"api_key=synthetic-value\n",
        b"path:/private/var/example\n",
        b"path:C:\\Users\\example\n",
        b"path:\\\\server\\share\n",
        b"terminal:\x1b[31m\n",
        b"nul:\x00\n",
        b"carriage\rreturn\n",
        "bidi:\u202eexample\n".encode(),
        f"home:{Path.home()}\n".encode(),
        f"repo:{REPO_ROOT}\n".encode(),
    ):
        path.write_bytes(_stage_bytes(validator, stdout=unsafe))
        with pytest.raises(validator.Denied):
            validator._validate_stage(REPO_ROOT, path, "unit", manifest)


def test_stage_header_and_file_resource_boundaries(tmp_path: Path) -> None:
    validator = _load_validator()
    header, body = validator._split_stage(b"x" * 65_535 + b"\nbody")
    assert len(header) == 65_536 and body == b"body"
    with pytest.raises(validator.Denied):
        validator._split_stage(b"x" * 65_536 + b"\n")

    stage = tmp_path / "stage.txt"
    stage.write_bytes(b"x" * 16_777_216)
    assert len(validator._read_large_file(stage, 16_777_216)) == 16_777_216
    with stage.open("ab") as stream:
        stream.write(b"x")
    with pytest.raises(validator.Denied):
        validator._read_large_file(stage, 16_777_216)


def test_evidence_inventory_and_comma_require_parser_fail_closed(tmp_path: Path) -> None:
    validator = _load_validator()
    assert "review-result" not in validator.KINDS
    assert validator._parse_required(["environment,unit", "fixture"]) == [
        "environment",
        "unit",
        "fixture",
    ]
    with pytest.raises(validator.Denied):
        validator._parse_required(["environment,,unit"])
    with pytest.raises(validator.Denied):
        validator._parse_required(["environment", "environment"])
    unknown = tmp_path / "evidence"
    unknown.mkdir()
    (unknown / "unexpected.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(validator.Denied):
        validator._inventory(unknown)


def test_source_commit_length_matches_repository_object_format() -> None:
    validator = _load_validator()
    manifest, _result = validator._manifest(REPO_ROOT, MANIFEST)
    schema = validator._expected_schemas()["environment"]
    value = json.loads((EVIDENCE_DIR / "environment.json").read_text(encoding="utf-8"))
    value["source_commit"] = "git:" + "a" * 64
    value["implementation_authorization"]["implementation_base_commit"] = value[
        "source_commit"
    ]
    with pytest.raises(validator.Denied):
        validator._validate_environment(REPO_ROOT, value, manifest, schema)


def test_environment_schema_version_is_bound_to_authorized_base() -> None:
    validator = _load_validator()
    assert (
        validator._schema_version_at_commit(
            REPO_ROOT,
            "git:1eb4d0ef7209cf3f04c5d163561403e835311aeb",
        )
        == 14
    )


def test_reviewed_tree_recompute_is_validator_owned_and_scope_closed(
    tmp_path: Path, monkeypatch
) -> None:
    validator = _load_validator()
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    hasher = scripts / "hash_subject_review_tree.py"
    hasher.write_text(
        "def compute_reviewed_tree_sha256(repo_root):\n"
        "    return 'a' * 64\n",
        encoding="utf-8",
    )
    source = tmp_path / "vault" / "source.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "scripts", "vault"], cwd=tmp_path, check=True)
    exact_paths = (
        "scripts/hash_subject_review_tree.py",
        "vault/source.py",
    )
    monkeypatch.setattr(validator, "_reviewed_source_paths", lambda _root: exact_paths)
    monkeypatch.setattr(
        validator,
        "_manifest",
        lambda _root, _path: (
            {
                "files": [
                    {
                        "path": "specs/subject-distillation/tasks.md",
                        "sha256": validator.REVIEW_TASKS_SHA256,
                    }
                ]
            },
            {"status": "PASS"},
        ),
    )
    entries = [
        {
            "path": path,
            "sha256": hashlib.sha256((tmp_path / path).read_bytes()).hexdigest(),
        }
        for path in exact_paths
    ]
    expected = hashlib.sha256(validator._canonical(entries)).hexdigest()
    assert validator._current_reviewed_tree_sha256(tmp_path) == expected
    assert expected != "a" * 64

    ledger = tmp_path / "specs/subject-distillation/implementation-progress.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text("excluded\n", encoding="utf-8")
    generated = tmp_path / "specs/subject-distillation/evidence/id/review.json"
    generated.parent.mkdir(parents=True)
    generated.write_text("excluded\n", encoding="utf-8")
    assert validator._current_reviewed_tree_sha256(tmp_path) == expected

    outside = tmp_path / "outside.py"
    outside.write_text("scope drift\n", encoding="utf-8")
    with pytest.raises(validator.Denied):
        validator._current_reviewed_tree_sha256(tmp_path)


def test_reviewed_tree_allowlist_matches_exact_baseline_task_headers() -> None:
    validator = _load_validator()
    literals, globs = validator._declared_review_sources(REPO_ROOT)
    assert literals == set(validator.REVIEW_LITERAL_PATHS)
    assert globs == set(validator.REVIEW_GLOB_PATTERNS)


def test_reviewed_tree_recompute_rejects_symlinked_source(
    tmp_path: Path, monkeypatch
) -> None:
    validator = _load_validator()
    vault = tmp_path / "vault"
    vault.mkdir()
    target = tmp_path / "target.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    (vault / "source.py").symlink_to(target)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "vault/source.py"], cwd=tmp_path, check=True)
    monkeypatch.setattr(
        validator,
        "_reviewed_source_paths",
        lambda _root: ("vault/source.py",),
    )
    monkeypatch.setattr(
        validator,
        "_manifest",
        lambda _root, _path: (
            {
                "files": [
                    {
                        "path": "specs/subject-distillation/tasks.md",
                        "sha256": validator.REVIEW_TASKS_SHA256,
                    }
                ]
            },
            {"status": "PASS"},
        ),
    )
    with pytest.raises(validator.Denied):
        validator._current_reviewed_tree_sha256(tmp_path)


def test_schema_validator_rejects_unknown_nested_property_and_boolean_integer() -> None:
    validator = _load_validator()
    schema = validator._expected_schemas()["environment"]
    value = json.loads((EVIDENCE_DIR / "environment.json").read_text(encoding="utf-8"))
    unknown = deepcopy(value)
    unknown["git_status"]["branch_line"] = "## hidden"
    with pytest.raises(validator.Denied):
        validator._validate_schema(schema, unknown)
    invalid_integer = deepcopy(value)
    invalid_integer["schema_contract_version"] = True
    with pytest.raises(validator.Denied):
        validator._validate_schema(schema, invalid_integer)


def test_cli_argument_errors_are_fixed_and_do_not_echo_paths(tmp_path: Path) -> None:
    marker = tmp_path / "private-marker"
    result = _run(str(VALIDATOR), "--unexpected", str(marker))
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == b"SUBJECT_EVIDENCE_DENY\n"
    assert str(marker).encode() not in result.stderr


def test_environment_file_hash_is_stable_public_evidence() -> None:
    raw = (EVIDENCE_DIR / "environment.json").read_bytes()
    assert raw.endswith(b"\n")
    assert len(raw) <= 1_048_576
    assert hashlib.sha256(raw).hexdigest()
