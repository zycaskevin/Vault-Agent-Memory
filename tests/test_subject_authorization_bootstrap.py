from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / (
    "specs/subject-distillation/evidence-schemas/"
    "implementation-authorization.schema.json"
)
VERIFIER_PATH = REPO_ROOT / "scripts/verify_subject_implementation_authorization.py"
MANIFEST_PATH = REPO_ROOT / "specs/subject-distillation/baseline-manifest.json"
NOW = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)


def _load_verifier():
    spec = importlib.util.spec_from_file_location("subject_authorization_verifier", VERIFIER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


verifier = _load_verifier()


@pytest.fixture(autouse=True)
def _run_subject_authorization_from_repo_root(monkeypatch) -> None:
    monkeypatch.chdir(REPO_ROOT)


def _canonical(value: Any, *, newline: bool = True) -> bytes:
    result = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return (result + ("\n" if newline else "")).encode()


def _write(path: Path, raw: bytes) -> None:
    path.write_bytes(raw)


def _build(
    tmp_path: Path,
    *,
    receipt_change: Callable[[dict[str, Any]], None] | None = None,
    scope_change: Callable[[dict[str, Any]], None] | None = None,
    receipt_canonical: bool = True,
) -> tuple[list[str], dict[str, Any]]:
    manifest = json.loads(MANIFEST_PATH.read_text())
    scope = {
        "schema_version": 1,
        "artifact_kind": "subject-distillation-implementation-scope",
        "baseline_id": manifest["closure"]["baseline_id"],
        "baseline_full_digest": manifest["closure"]["full_digest"],
        "authorized_task": "T-001",
        "allowed_repo_relative_paths": ["scripts/read_subject_baseline_id.py"],
        "non_goals": ["product.runtime"],
        "prohibited_operations": sorted(verifier.PROHIBITED),
    }
    if scope_change is not None:
        scope_change(scope)
    scope_raw = _canonical(scope)
    scope_path = tmp_path / "scope.json"
    _write(scope_path, scope_raw)
    receipt = {
        "schema_version": 1,
        "artifact_kind": "subject-distillation-implementation-authorization",
        "baseline_id": manifest["closure"]["baseline_id"],
        "baseline_full_digest": manifest["closure"]["full_digest"],
        "authorizing_principal": "github:zycaskevin",
        "authorized_task": "T-001",
        "scope_sha256": hashlib.sha256(scope_raw).hexdigest(),
        "authorization_verifier_sha256": hashlib.sha256(VERIFIER_PATH.read_bytes()).hexdigest(),
        "authorization_schema_sha256": hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest(),
        "issued_at_utc": "2026-08-02T11:00:00Z",
        "expires_at_utc": "2026-08-02T13:00:00Z",
    }
    if receipt_change is not None:
        receipt_change(receipt)
    receipt["authorization_id"] = hashlib.sha256(
        _canonical(receipt, newline=False)
    ).hexdigest()
    receipt_raw = (
        _canonical(receipt)
        if receipt_canonical
        else (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    )
    receipt_path = tmp_path / "receipt.json"
    _write(receipt_path, receipt_raw)
    args = [
        "--receipt",
        str(receipt_path),
        "--expected-receipt-sha256",
        hashlib.sha256(receipt_raw).hexdigest(),
        "--scope",
        str(scope_path),
        "--manifest",
        verifier.MANIFEST_PATH,
        "--schema",
        verifier.SCHEMA_PATH,
        "--expected-authority",
        "github:zycaskevin",
        "--expected-task",
        "T-001",
        "--json",
    ]
    return args, receipt


def _run(args: list[str], capsys, **kwargs):
    code = verifier.main(args, _now=NOW, **kwargs)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_bootstrap_artifacts_exist_and_schema_is_fixed() -> None:
    assert SCHEMA_PATH.is_file()
    assert VERIFIER_PATH.is_file()
    schema = verifier._parse(SCHEMA_PATH.read_bytes())
    verifier._scan(schema)
    verifier._schema_shape(schema)
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        lambda schema: schema.update({"$id": "https://example.invalid/other"}),
        lambda schema: schema["properties"].pop("authorization_id"),
        lambda schema: schema["properties"]["schema_version"].update(type="string"),
        lambda schema: schema["properties"]["schema_version"].update(const=True),
        lambda schema: schema["properties"]["schema_version"].update(const=1.0),
        lambda schema: schema["properties"]["artifact_kind"].update(const="other"),
        lambda schema: schema["properties"]["baseline_id"].update(
            pattern="^[0-9a-f]{15}$"
        ),
        lambda schema: schema["required"].reverse(),
        lambda schema: schema.update(additionalProperties=True),
        lambda schema: schema.update(unknown_keyword=True),
    ],
)
def test_schema_exact_matrix_mutations_deny(mutation) -> None:
    schema = copy.deepcopy(verifier._expected_schema())
    mutation(schema)
    with pytest.raises(verifier.Denied):
        verifier._schema_shape(schema)


def test_valid_receipt_passes_with_exact_output(tmp_path: Path, capsys) -> None:
    args, receipt = _build(tmp_path)
    code, stdout, stderr = _run(args, capsys)
    assert code == 0
    assert stderr == ""
    assert stdout == _canonical(
        {
            "authorization_id": receipt["authorization_id"],
            "authorized_task": "T-001",
            "baseline_id": receipt["baseline_id"],
            "status": "PASS",
        }
    ).decode()


def test_non_repo_cwd_is_fixed_deny(tmp_path: Path, capsys, monkeypatch) -> None:
    args, _ = _build(tmp_path)
    foreign_cwd = tmp_path / "foreign-cwd"
    foreign_cwd.mkdir()
    monkeypatch.chdir(foreign_cwd)
    assert _run(args, capsys) == (2, "", verifier.DENY)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.upper(),
        lambda value: "0" + value,
        lambda value: value + "0",
        lambda value: value[:-1],
        lambda value: value[:-1] + "b",
    ],
)
def test_manifest_domain_value_mutations_deny(mutation) -> None:
    with pytest.raises(verifier.Denied):
        verifier._scan({verifier.DOMAIN_KEY: mutation(verifier.DOMAIN_HEX)})


@pytest.mark.parametrize(
    "key",
    [
        "Domain_separator_utf8_hex",
        "domain.separator.utf8.hex",
        "domain-separator-utf8-hex",
        "domain__separator_utf8_hex",
        "other",
    ],
)
def test_manifest_domain_key_mutations_deny(key: str) -> None:
    with pytest.raises(verifier.Denied):
        verifier._scan({key: verifier.DOMAIN_HEX})


def test_exact_manifest_domain_and_digest_neighbors_allow() -> None:
    verifier._scan(
        {
            verifier.DOMAIN_KEY: verifier.DOMAIN_HEX,
            "sha256": "a" * 64,
            "full_digest": "b" * 64,
            "private_shadow_receipt_sha256": "c" * 64,
            "namespace": "private-shadow-pass:" + "d" * 64,
        }
    )


@pytest.mark.parametrize("key", sorted(verifier.DIGEST_KEYS))
def test_every_named_digest_field_allows_exact_lowercase_hex(key: str) -> None:
    verifier._scan({key: "a" * 64})


@pytest.mark.parametrize(
    "value",
    [
        "xprivate-shadow-pass:" + "a" * 64,
        "private-shadow-pass:" + "a" * 64 + "x",
        "private-shadow-pass:" + "A" * 64,
    ],
)
def test_private_shadow_namespace_mutations_deny(value: str) -> None:
    with pytest.raises(verifier.Denied):
        verifier._scan({"namespace": value})


@pytest.mark.parametrize(
    "value",
    [
        "gho_example",
        "Bearer:value",
        "abc.def.ghi",
        "client-secret=value",
        "-----BEGIN PRIVATE KEY-----",
        "a" * 32,
        "b" * 64,
        "c" * 128,
    ],
)
def test_public_safety_families_deny(value: str) -> None:
    with pytest.raises(verifier.Denied):
        verifier._scan({"ordinary": value})


@pytest.mark.parametrize(
    "key",
    ["secret", "Api.Key", "client-secret", "raw_evidence", "absolute.path"],
)
def test_forbidden_key_normalization_denies(key: str) -> None:
    with pytest.raises(verifier.Denied):
        verifier._scan({key: "ordinary"})


def test_every_forbidden_key_and_separator_variant_denies() -> None:
    for key in verifier.FORBIDDEN_KEYS:
        variants = {
            key,
            key.upper(),
            key.replace("_", "."),
            key.replace("_", "-"),
            key.replace("_", "__"),
        }
        for variant in variants:
            with pytest.raises(verifier.Denied):
                verifier._scan({variant: "ordinary"})


def test_digest_field_requires_exact_lowercase_64_hex() -> None:
    for value in ("a" * 63, "a" * 65, "A" * 64):
        with pytest.raises(verifier.Denied):
            verifier._scan({"scope_sha256": value})


def test_duplicate_keys_and_schema_unknown_keyword_deny() -> None:
    with pytest.raises(verifier.Denied):
        verifier._parse(b'{"a":1,"a":2}')
    schema = verifier._parse(SCHEMA_PATH.read_bytes())
    schema["properties"]["schema_version"]["minimum"] = 1
    with pytest.raises(verifier.Denied):
        verifier._schema_shape(schema)
    with pytest.raises(verifier.Denied):
        verifier._parse(b'{"value":NaN}')


def test_hostile_large_integer_is_caller_deny_not_internal_error(
    tmp_path: Path, capsys
) -> None:
    args, _ = _build(tmp_path)
    hostile = b'{"value":' + b"9" * 5_000 + b"}\n"
    receipt_path = Path(args[1])
    receipt_path.write_bytes(hostile)
    args[3] = hashlib.sha256(hostile).hexdigest()
    assert _run(args, capsys) == (2, "", verifier.DENY)


def test_manifest_scope_rejects_integer_as_boolean() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    manifest["scope"]["generic_subject_core"] = 1
    with pytest.raises(verifier.Denied):
        verifier._manifest(manifest)


def test_schema_integer_rejects_boolean() -> None:
    schema = verifier._parse(SCHEMA_PATH.read_bytes())
    value = {key: definition.get("const", "a") for key, definition in schema["properties"].items()}
    value.update(
        baseline_id="a" * 16,
        baseline_full_digest="a" * 64,
        authorized_task="T-001",
        scope_sha256="a" * 64,
        authorization_verifier_sha256="a" * 64,
        authorization_schema_sha256="a" * 64,
        issued_at_utc="2026-08-02T11:00:00Z",
        expires_at_utc="2026-08-02T13:00:00Z",
        authorization_id="a" * 64,
    )
    value["schema_version"] = True
    with pytest.raises(verifier.Denied):
        verifier._schema_validate(schema, value)


def test_structure_exact_boundaries_and_one_over() -> None:
    depth = "0"
    for _ in range(verifier.MAX_DEPTH - 1):
        depth = "[" + depth + "]"
    verifier._parse(depth.encode())
    with pytest.raises(verifier.Denied):
        verifier._parse(("[" + depth + "]").encode())
    verifier._parse(_canonical([0] * verifier.MAX_MEMBERS, newline=False))
    with pytest.raises(verifier.Denied):
        verifier._parse(_canonical([0] * (verifier.MAX_MEMBERS + 1), newline=False))
    exact_nodes = [[0] * 7 for _ in range(verifier.MAX_MEMBERS - 1)] + [[0] * 6]
    verifier._parse(_canonical(exact_nodes, newline=False))
    one_over = [[0] * 7 for _ in range(verifier.MAX_MEMBERS)]
    with pytest.raises(verifier.Denied):
        verifier._parse(_canonical(one_over, newline=False))


def _close_all(owned: list[int]) -> None:
    for fd in reversed(owned):
        os.close(fd)


def test_manifest_entries_bind_current_canonical_file_bytes(tmp_path: Path) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    for entry in manifest["files"]:
        source = REPO_ROOT / entry["path"]
        destination = tmp_path / entry["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())

    owned: list[int] = []
    root_fd = os.open("/", verifier._flags(directory=True))
    owned.append(root_fd)
    repo = verifier._open_chain(
        root_fd,
        verifier._absolute_parts(str(tmp_path.resolve())),
        owned,
        final_directory=True,
    )
    handles = [repo]
    verifier._bind_manifest_files(manifest, repo, owned, handles)
    verifier._audit(handles)
    _close_all(owned)

    first = tmp_path / manifest["files"][0]["path"]
    first.write_bytes(first.read_bytes() + b"drift")
    owned = []
    root_fd = os.open("/", verifier._flags(directory=True))
    owned.append(root_fd)
    repo = verifier._open_chain(
        root_fd,
        verifier._absolute_parts(str(tmp_path.resolve())),
        owned,
        final_directory=True,
    )
    with pytest.raises(verifier.Denied):
        verifier._bind_manifest_files(manifest, repo, owned, [repo])
    _close_all(owned)


@pytest.mark.parametrize("role", ["receipt", "scope", "manifest", "schema", "verifier"])
def test_each_bounded_input_byte_cap_exact_and_one_over(tmp_path: Path, role: str) -> None:
    path = tmp_path / role
    path.write_bytes(b"x" * verifier.MAX_BYTES)
    root_fd = os.open(tmp_path, verifier._flags(directory=True))
    owned = [root_fd]
    handle = verifier._open_chain(root_fd, [role], owned)
    assert len(verifier._read(handle)) == verifier.MAX_BYTES
    _close_all(owned)

    path.write_bytes(b"x" * (verifier.MAX_BYTES + 1))
    root_fd = os.open(tmp_path, verifier._flags(directory=True))
    owned = [root_fd]
    handle = verifier._open_chain(root_fd, [role], owned)
    with pytest.raises(verifier.Denied):
        verifier._read(handle)
    _close_all(owned)


@pytest.mark.parametrize("role", ["manifest", "schema", "verifier"])
def test_each_fixed_repo_input_rejects_symlink_and_replacement_race(
    tmp_path: Path, role: str
) -> None:
    root_fd = os.open(tmp_path, verifier._flags(directory=True))
    owned = [root_fd]
    target = tmp_path / f"{role}-target"
    target.write_text("safe")
    link = tmp_path / role
    link.symlink_to(target)
    with pytest.raises(verifier.Denied):
        verifier._open_chain(root_fd, [role], owned)
    _close_all(owned)

    link.unlink()
    link.write_text("first")
    root_fd = os.open(tmp_path, verifier._flags(directory=True))
    owned = [root_fd]
    handle = verifier._open_chain(root_fd, [role], owned)
    replacement = tmp_path / f"{role}-replacement"
    replacement.write_text("second")
    os.replace(replacement, link)
    with pytest.raises(verifier.Denied):
        verifier._audit([handle])
    _close_all(owned)


def test_cli_and_canonical_input_failures_are_fixed_deny(tmp_path: Path, capsys) -> None:
    args, _ = _build(tmp_path, receipt_canonical=False)
    code, stdout, stderr = _run(args, capsys)
    assert (code, stdout, stderr) == (2, "", verifier.DENY)
    code, stdout, stderr = _run(args + ["--unknown"], capsys)
    assert (code, stdout, stderr) == (2, "", verifier.DENY)
    code, stdout, stderr = _run(args + ["--json"], capsys)
    assert (code, stdout, stderr) == (2, "", verifier.DENY)


def test_scope_traversal_and_expiry_equality_deny(tmp_path: Path, capsys) -> None:
    args, _ = _build(
        tmp_path,
        scope_change=lambda scope: scope.update(allowed_repo_relative_paths=["../escape"]),
    )
    assert _run(args, capsys) == (2, "", verifier.DENY)
    args, _ = _build(
        tmp_path,
        scope_change=lambda scope: scope.update(
            allowed_repo_relative_paths=["bad\x7fpath"]
        ),
    )
    assert _run(args, capsys) == (2, "", verifier.DENY)


def test_scope_requires_all_safety_prohibitions_with_two_contract_exceptions(
    tmp_path: Path, capsys
) -> None:
    args, _ = _build(
        tmp_path,
        scope_change=lambda scope: scope.update(
            prohibited_operations=sorted(
                verifier.PROHIBITED - {"migration", "product_runtime"}
            )
        ),
    )
    code, _, _ = _run(args, capsys)
    assert code == 0

    args, _ = _build(
        tmp_path,
        scope_change=lambda scope: scope.update(
            prohibited_operations=sorted(verifier.PROHIBITED - {"deploy"})
        ),
    )
    assert _run(args, capsys) == (2, "", verifier.DENY)
    args, _ = _build(
        tmp_path,
        receipt_change=lambda receipt: receipt.update(expires_at_utc="2026-08-02T12:00:00Z"),
    )
    assert _run(args, capsys) == (2, "", verifier.DENY)


def test_symlink_private_input_denies_without_echo(tmp_path: Path, capsys) -> None:
    args, _ = _build(tmp_path)
    original = Path(args[1])
    link = tmp_path / "receipt-link.json"
    link.symlink_to(original)
    args[1] = str(link)
    code, stdout, stderr = _run(args, capsys)
    assert (code, stdout, stderr) == (2, "", verifier.DENY)
    assert str(link) not in stderr


def test_injected_internal_fault_is_fixed_error(tmp_path: Path, capsys) -> None:
    args, _ = _build(tmp_path)

    def fault() -> None:
        raise RuntimeError("harmless-internal-marker")

    code, stdout, stderr = _run(args, capsys, _fault=fault)
    assert (code, stdout, stderr) == (3, "", verifier.ERROR)
    assert "harmless-internal-marker" not in stderr


def test_receipt_digest_and_self_hash_mismatch_deny(tmp_path: Path, capsys) -> None:
    args, _ = _build(tmp_path)
    args[3] = "0" * 64
    assert _run(args, capsys) == (2, "", verifier.DENY)
    args, _ = _build(
        tmp_path,
        receipt_change=lambda receipt: receipt.update(
            authorization_verifier_sha256="0" * 64
        ),
    )
    assert _run(args, capsys) == (2, "", verifier.DENY)


def test_byte_cap_symlink_ancestor_and_mutation_race_deny(tmp_path: Path, capsys) -> None:
    args, _ = _build(tmp_path)
    receipt_path = Path(args[1])
    receipt_path.write_bytes(b"x" * (verifier.MAX_BYTES + 1))
    args[3] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    assert _run(args, capsys) == (2, "", verifier.DENY)

    real_dir = tmp_path / "real"
    real_dir.mkdir()
    args, _ = _build(real_dir)
    linked_dir = tmp_path / "linked"
    linked_dir.symlink_to(real_dir, target_is_directory=True)
    args[1] = str(linked_dir / "receipt.json")
    args[5] = str(linked_dir / "scope.json")
    assert _run(args, capsys) == (2, "", verifier.DENY)

    args, _ = _build(tmp_path)
    race_path = Path(args[1])

    def mutate() -> None:
        race_path.write_bytes(race_path.read_bytes() + b" ")

    assert _run(args, capsys, _fault=mutate) == (2, "", verifier.DENY)


@pytest.mark.parametrize(
    "path",
    ["relative.json", "/tmp/../escape", "/tmp//double", "/tmp/back\\slash"],
)
def test_private_path_lexical_mutations_deny(path: str) -> None:
    with pytest.raises(verifier.Denied):
        verifier._absolute_parts(path)


def test_only_b000_paths_are_present() -> None:
    assert not (REPO_ROOT / "scripts/read_subject_baseline_id.py").exists()
    assert not (REPO_ROOT / "specs/subject-distillation/implementation-progress.json").exists()
    assert {
        path.relative_to(REPO_ROOT).as_posix()
        for path in (VERIFIER_PATH, SCHEMA_PATH, Path(__file__).resolve())
    } == {
        "scripts/verify_subject_implementation_authorization.py",
        "specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json",
        "tests/test_subject_authorization_bootstrap.py",
    }
