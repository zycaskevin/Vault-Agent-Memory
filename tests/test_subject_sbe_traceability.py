from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/export_subject_sbe_traceability.py"
TRACEABILITY = REPO_ROOT / "specs/subject-distillation/traceability.md"
MAPPING = REPO_ROOT / "specs/subject-distillation/sbe-traceability.json"

EXPECTED_REQUIREMENTS = [f"R-SD-{number:03d}" for number in range(1, 27)]
EXPECTED_SBE_IDS = (
    [f"E-P-{number:03d}" for number in range(1, 19)]
    + [f"E-O-{number:03d}" for number in range(1, 6)]
    + [f"E-F-{number:03d}" for number in range(1, 21)]
)


def _load():
    spec = importlib.util.spec_from_file_location("subject_sbe_traceability", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _read_json(path: Path) -> dict[str, object]:
    def reject(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise AssertionError(f"duplicate key: {key}")
            value[key] = item
        return value

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject)


@pytest.fixture()
def exporter():
    return _load()


def test_planned_seed_is_canonical_and_exact(exporter) -> None:
    value = _read_json(MAPPING)
    raw = MAPPING.read_bytes()

    assert raw == exporter._canonical(value)
    assert set(value) == {
        "schema_version",
        "artifact_kind",
        "mode",
        "source_traceability_sha256",
        "fixture_manifest_sha256",
        "requirements_sha256",
        "requirement_ids",
        "examples",
    }
    assert value["schema_version"] == 1
    assert value["artifact_kind"] == "subject-sbe-traceability"
    assert value["mode"] == "planned"
    assert value["requirement_ids"] == EXPECTED_REQUIREMENTS

    examples = value["examples"]
    assert isinstance(examples, list)
    assert [row["sbe_id"] for row in examples] == EXPECTED_SBE_IDS
    assert len({row["sbe_id"] for row in examples}) == 43
    assert all(
        set(row)
        == {
            "sbe_id",
            "approved_behavior",
            "design_contracts",
            "tasks",
            "fixture_id",
            "fixture_path",
            "planned_tests",
        }
        for row in examples
    )
    assert all(row["planned_tests"] for row in examples)
    assert all(
        test.startswith("tests/test_") and test.endswith(".py")
        for row in examples
        for test in row["planned_tests"]
    )
    assert all("collected" not in key for row in examples for key in row)
    assert exporter._build_planned(REPO_ROOT, TRACEABILITY) == value


def test_fixture_ownership_matches_every_normative_row(exporter) -> None:
    value = exporter._build_planned(REPO_ROOT, TRACEABILITY)
    fixtures = {
        row["sbe_id"]: row
        for path in exporter.FIXTURE_PATHS
        for row in _read_json(REPO_ROOT / path)["cases"]
    }
    assert set(fixtures) == set(EXPECTED_SBE_IDS)
    for row in value["examples"]:
        fixture = fixtures[row["sbe_id"]]
        assert fixture["title"] == row["approved_behavior"]
        assert fixture["planned_tests"] == row["planned_tests"]
        assert fixture["synthetic"] is True


def test_fixture_manifest_or_owned_byte_drift_denies(
    exporter, tmp_path: Path
) -> None:
    source = REPO_ROOT / "tests/fixtures/subject_distillation"
    target = tmp_path / "tests/fixtures/subject_distillation"
    shutil.copytree(source, target)
    fixture = target / "person/person-cases.json"
    fixture.write_bytes(fixture.read_bytes() + b"\n")

    with pytest.raises(exporter.Denied):
        exporter._fixture_owners(tmp_path)


def test_same_descriptor_reader_denies_symlink_hardlink_and_one_over(
    exporter, tmp_path: Path
) -> None:
    source = tmp_path / "source.json"
    source.write_bytes(b"{}\n")
    alias = tmp_path / "alias.json"
    alias.symlink_to(source)
    with pytest.raises(exporter.Denied):
        exporter._read_regular(alias)

    alias.unlink()
    os.link(source, alias)
    with pytest.raises(exporter.Denied):
        exporter._read_regular(source)

    alias.unlink()
    source.write_bytes(b"x" * (exporter.MAX_INPUT_BYTES + 1))
    with pytest.raises(exporter.Denied):
        exporter._read_regular(source)


def test_writer_checks_identity_before_truncate(exporter, tmp_path: Path) -> None:
    target = tmp_path / exporter.MAPPING_PATH
    target.parent.mkdir(parents=True)
    shared = tmp_path / "shared.json"
    shared.write_bytes(b"original\n")
    os.link(shared, target)
    with pytest.raises(exporter.Denied):
        exporter._write_fixed(tmp_path, exporter.MAPPING_PATH, b"replacement\n")
    assert shared.read_bytes() == b"original\n"

    target.unlink()
    target.symlink_to(shared)
    with pytest.raises(exporter.Denied):
        exporter._write_fixed(tmp_path, exporter.MAPPING_PATH, b"replacement\n")
    assert shared.read_bytes() == b"original\n"


def test_writer_short_write_preserves_old_bytes_and_cleans_pending(
    exporter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / exporter.MAPPING_PATH
    target.parent.mkdir(parents=True)
    target.write_bytes(b"old-mapping\n")
    target.chmod(0o644)
    original_write = exporter.os.write
    calls = 0

    def fail_after_prefix(fd: int, raw: bytes) -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            return original_write(fd, raw[:3])
        raise OSError("synthetic short write")

    monkeypatch.setattr(exporter.os, "write", fail_after_prefix)
    with pytest.raises(exporter.Denied):
        exporter._write_fixed(tmp_path, exporter.MAPPING_PATH, b"new-mapping\n")

    assert target.read_bytes() == b"old-mapping\n"
    assert not (target.parent / ".task-authorization.pending").exists()


def test_writer_recovers_exact_pending_with_atomic_replace(
    exporter, tmp_path: Path
) -> None:
    target = tmp_path / exporter.MAPPING_PATH
    target.parent.mkdir(parents=True)
    target.write_bytes(b"old-mapping\n")
    target.chmod(0o644)
    pending = target.parent / ".task-authorization.pending"
    pending.write_bytes(b"new-mapping\n")
    pending.chmod(0o600)

    exporter._write_fixed(tmp_path, exporter.MAPPING_PATH, b"new-mapping\n")

    assert target.read_bytes() == b"new-mapping\n"
    assert target.stat().st_mode & 0o777 == 0o644
    assert not pending.exists()


def test_writer_atomically_replaces_existing_mapping_without_retained_pending(
    exporter, tmp_path: Path
) -> None:
    target = tmp_path / exporter.MAPPING_PATH
    target.parent.mkdir(parents=True)
    target.write_bytes(b"old-mapping\n")
    target.chmod(0o644)

    exporter._write_fixed(tmp_path, exporter.MAPPING_PATH, b"new-mapping\n")

    assert target.read_bytes() == b"new-mapping\n"
    assert target.stat().st_mode & 0o777 == 0o644
    assert target.stat().st_nlink == 1
    assert not (target.parent / ".task-authorization.pending").exists()


def test_writer_rejects_mismatching_pending_without_deleting_it(
    exporter, tmp_path: Path
) -> None:
    target = tmp_path / exporter.MAPPING_PATH
    target.parent.mkdir(parents=True)
    target.write_bytes(b"old-mapping\n")
    target.chmod(0o644)
    pending = target.parent / ".task-authorization.pending"
    pending.write_bytes(b"hostile\n")
    pending.chmod(0o600)

    with pytest.raises(exporter.Denied):
        exporter._write_fixed(tmp_path, exporter.MAPPING_PATH, b"new-mapping\n")

    assert target.read_bytes() == b"old-mapping\n"
    assert pending.read_bytes() == b"hostile\n"


def test_writer_detects_pending_replacement_during_publication(
    exporter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / exporter.MAPPING_PATH
    target.parent.mkdir(parents=True)
    target.write_bytes(b"old-mapping\n")
    target.chmod(0o644)
    pending = target.parent / ".task-authorization.pending"
    original_replace = exporter.os.replace
    injected = False

    def replace_with_hostile(src, dst, *, src_dir_fd=None, dst_dir_fd=None):
        nonlocal injected
        if not injected:
            injected = True
            pending.unlink()
            pending.write_bytes(b"hostile\n")
            pending.chmod(0o644)
        return original_replace(
            src,
            dst,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    monkeypatch.setattr(exporter.os, "replace", replace_with_hostile)
    with pytest.raises(exporter.Denied):
        exporter._write_fixed(tmp_path, exporter.MAPPING_PATH, b"new-mapping\n")

    assert target.read_bytes() == b"old-mapping\n"
    assert not pending.exists()


def test_writer_parent_fsync_failure_restores_complete_old_bytes(
    exporter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / exporter.MAPPING_PATH
    target.parent.mkdir(parents=True)
    target.write_bytes(b"old-mapping\n")
    target.chmod(0o644)
    original_fsync = exporter.os.fsync
    failed = False

    def fail_directory_fsync(fd: int) -> None:
        nonlocal failed
        if not failed and os.path.samestat(os.fstat(fd), target.parent.stat()):
            failed = True
            raise OSError("synthetic directory fsync failure")
        original_fsync(fd)

    monkeypatch.setattr(exporter.os, "fsync", fail_directory_fsync)
    with pytest.raises(exporter.Denied):
        exporter._write_fixed(tmp_path, exporter.MAPPING_PATH, b"new-mapping\n")

    assert target.read_bytes() == b"old-mapping\n"
    assert not (target.parent / ".task-authorization.pending").exists()


def test_repo_reader_denies_parent_replacement_between_open_and_audit(
    exporter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = tmp_path / exporter.TRACEABILITY_PATH
    original.parent.mkdir(parents=True)
    original.write_bytes(b"trusted\n")
    original_open = exporter.os.open
    swapped = False

    def replace_parent(name, flags, *args, dir_fd=None, **kwargs):
        nonlocal swapped
        if name == "traceability.md" and dir_fd is not None and not swapped:
            swapped = True
            specs = tmp_path / "specs"
            specs.rename(tmp_path / "specs-retained")
            replacement = tmp_path / "specs/subject-distillation"
            replacement.mkdir(parents=True)
            (replacement / "traceability.md").write_bytes(b"hostile\n")
        return original_open(name, flags, *args, dir_fd=dir_fd, **kwargs)

    monkeypatch.setattr(exporter.os, "open", replace_parent)
    with pytest.raises(exporter.Denied):
        exporter._read_repo_file(tmp_path, exporter.TRACEABILITY_PATH)


def test_bounded_child_drains_both_pipes_and_denies_one_over(
    exporter, tmp_path: Path
) -> None:
    result = exporter._run_bounded_child(
        [
            sys.executable,
            "-c",
            "import os; os.write(1,b'o'*64); os.write(2,b'e'*64)",
        ],
        cwd=tmp_path,
        stdout_limit=64,
        stderr_limit=64,
        timeout_seconds=2.0,
        terminate_grace_seconds=0.2,
    )
    assert result.returncode == 0
    assert result.stdout == b"o" * 64
    assert result.stderr == b"e" * 64

    with pytest.raises(exporter.Denied):
        exporter._run_bounded_child(
            [sys.executable, "-c", "import os; os.write(1,b'x'*65)"],
            cwd=tmp_path,
            stdout_limit=64,
            stderr_limit=64,
            timeout_seconds=2.0,
            terminate_grace_seconds=0.2,
        )


def test_bounded_child_timeout_kills_and_reaps_process_group(
    exporter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pids: list[int] = []
    original_popen = exporter.subprocess.Popen

    def track_popen(*args, **kwargs):
        child = original_popen(*args, **kwargs)
        pids.append(child.pid)
        return child

    monkeypatch.setattr(exporter.subprocess, "Popen", track_popen)
    with pytest.raises(exporter.Denied):
        exporter._run_bounded_child(
            [
                sys.executable,
                "-c",
                "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)",
            ],
            cwd=tmp_path,
            stdout_limit=64,
            stderr_limit=64,
            timeout_seconds=0.1,
            terminate_grace_seconds=0.1,
        )

    assert len(pids) == 1
    deadline = time.monotonic() + 1.0
    while True:
        try:
            os.kill(pids[0], 0)
        except ProcessLookupError:
            break
        if time.monotonic() >= deadline:
            pytest.fail("timed-out collection child was not reaped")
        time.sleep(0.01)


def test_bounded_child_reaps_descendant_that_holds_pipes(
    exporter, tmp_path: Path
) -> None:
    pid_file = tmp_path / "descendant.pid"
    program = (
        "import pathlib,subprocess,sys; "
        "p=subprocess.Popen([sys.executable,'-c',"
        "'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)']); "
        f"pathlib.Path({str(pid_file)!r}).write_text(str(p.pid)); "
        "sys.exit(0)"
    )
    with pytest.raises(exporter.Denied):
        exporter._run_bounded_child(
            [sys.executable, "-c", program],
            cwd=tmp_path,
            stdout_limit=64,
            stderr_limit=64,
            timeout_seconds=0.2,
            terminate_grace_seconds=0.1,
        )

    descendant = int(pid_file.read_text(encoding="utf-8"))
    deadline = time.monotonic() + 1.0
    while True:
        try:
            os.kill(descendant, 0)
        except ProcessLookupError:
            break
        if time.monotonic() >= deadline:
            pytest.fail("descendant retained collection pipes after cleanup")
        time.sleep(0.01)


def test_collector_executes_retained_test_bytes_not_replaced_pathname(
    exporter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    source = tests / "test_subject_retained.py"
    source.write_text("def test_e_p_001_retained():\n    pass\n", encoding="utf-8")
    source.chmod(0o644)
    marker = tmp_path / "hostile-executed"
    hostile = (
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n"
        "def test_e_p_001_hostile():\n    pass\n"
    )
    original_popen = exporter.subprocess.Popen
    replaced = False

    def swap_then_popen(*args, **kwargs):
        nonlocal replaced
        if not replaced:
            replaced = True
            source.unlink()
            source.write_text(hostile, encoding="utf-8")
            source.chmod(0o644)
        return original_popen(*args, **kwargs)

    monkeypatch.setattr(exporter.subprocess, "Popen", swap_then_popen)
    with pytest.raises(exporter.Denied):
        exporter._collect(
            tmp_path,
            "python -m pytest --collect-only -q tests/test_subject_*.py",
        )

    assert not marker.exists()


def test_collector_executes_snapshot_not_in_place_mutated_inode(
    exporter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    source = tests / "test_subject_retained.py"
    source.write_text("def test_e_p_001_retained():\n    pass\n", encoding="utf-8")
    source.chmod(0o644)
    marker = tmp_path / "hostile-executed"
    hostile = (
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n"
        "def test_e_p_001_hostile():\n    pass\n"
    )
    original_popen = exporter.subprocess.Popen
    mutated = False

    def mutate_then_popen(*args, **kwargs):
        nonlocal mutated
        if not mutated:
            mutated = True
            source.write_text(hostile, encoding="utf-8")
            source.chmod(0o644)
        return original_popen(*args, **kwargs)

    monkeypatch.setattr(exporter.subprocess, "Popen", mutate_then_popen)
    with pytest.raises(exporter.Denied):
        exporter._collect(
            tmp_path,
            "python -m pytest --collect-only -q tests/test_subject_*.py",
        )

    assert not marker.exists()


def test_first_collected_module_cannot_rewrite_second_snapshot_fd(
    exporter, tmp_path: Path
) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    attack_result = tmp_path / "attack-result"
    trusted_result = tmp_path / "trusted-result"
    attack_result.write_text("", encoding="utf-8")
    trusted_result.write_text("", encoding="utf-8")
    first = tests / "test_subject_a.py"
    second = tests / "test_subject_b.py"
    first.write_text(
        "import json,os,sys\n"
        "try:\n"
        "    items=json.loads(sys.argv[2])\n"
        "    target=next(item['fd'] for item in items if item['path'].endswith('test_subject_b.py'))\n"
        "    os.ftruncate(target,0)\n"
        "except (IndexError,KeyError,OSError,StopIteration,ValueError):\n"
        f"    open({str(attack_result)!r},'w').write('blocked')\n"
        "else:\n"
        f"    open({str(attack_result)!r},'w').write('rewritten')\n"
        "def test_e_p_001_first():\n"
        "    pass\n",
        encoding="utf-8",
    )
    second.write_text(
        f"open({str(trusted_result)!r},'w').write('trusted')\n"
        "def test_e_p_002_second():\n"
        "    pass\n",
        encoding="utf-8",
    )
    first.chmod(0o644)
    second.chmod(0o644)

    nodes = exporter._collect(
        tmp_path,
        "python -m pytest --collect-only -q tests/test_subject_*.py",
    )

    assert len(nodes) == 2
    assert attack_result.read_text(encoding="utf-8") == "blocked"
    assert trusted_result.read_text(encoding="utf-8") == "trusted"


def test_collection_child_ignores_python_and_pytest_environment_injection(
    exporter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    source = tests / "test_subject_safe.py"
    source.write_text("def test_e_p_001_safe():\n    pass\n", encoding="utf-8")
    source.chmod(0o644)
    injection = tmp_path / "injection"
    injection.mkdir()
    startup_marker = tmp_path / "startup-marker"
    plugin_marker = tmp_path / "plugin-marker"
    startup_marker.write_text("safe", encoding="utf-8")
    plugin_marker.write_text("safe", encoding="utf-8")
    (injection / "sitecustomize.py").write_text(
        f"from pathlib import Path\nPath({str(startup_marker)!r}).write_text('hostile')\n",
        encoding="utf-8",
    )
    (injection / "hostile_plugin.py").write_text(
        f"from pathlib import Path\nPath({str(plugin_marker)!r}).write_text('hostile')\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PYTHONPATH", str(injection))
    monkeypatch.setenv("PYTHONSTARTUP", str(injection / "sitecustomize.py"))
    monkeypatch.setenv("PYTEST_ADDOPTS", "-p hostile_plugin")
    monkeypatch.setenv("PYTEST_PLUGINS", "hostile_plugin")

    nodes = exporter._collect(
        tmp_path,
        "python -m pytest --collect-only -q tests/test_subject_*.py",
    )

    assert nodes == ["tests/test_subject_safe.py::test_e_p_001_safe"]
    assert startup_marker.read_text(encoding="utf-8") == "safe"
    assert plugin_marker.read_text(encoding="utf-8") == "safe"


def test_collection_child_does_not_write_bytecode_for_repo_imports(
    exporter, tmp_path: Path
) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    helper = tmp_path / "subject_collection_helper.py"
    helper.write_text("VALUE = 'trusted'\n", encoding="utf-8")
    helper.chmod(0o644)
    source = tests / "test_subject_import.py"
    source.write_text(
        "import subject_collection_helper\n"
        "def test_e_p_001_import():\n"
        "    assert subject_collection_helper.VALUE == 'trusted'\n",
        encoding="utf-8",
    )
    source.chmod(0o644)

    nodes = exporter._collect(
        tmp_path,
        "python -m pytest --collect-only -q tests/test_subject_*.py",
    )

    assert nodes == ["tests/test_subject_import.py::test_e_p_001_import"]
    assert not list(tmp_path.rglob("__pycache__"))
    assert not list(tmp_path.rglob("*.pyc"))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda text: text.replace("| E-P-001 |", "| E-P-002 |", 1),
        lambda text: text.replace(
            "Explicit preference remains explicit",
            "TBD",
            1,
        ),
        lambda text: text.replace(
            "`tests/test_subject_auth.py`",
            "`/Users/private/test_subject_auth.py`",
            1,
        ),
        lambda text: text.replace(
            "`tests/test_subject_auth.py`; `tests/test_subject_policy.py`; `tests/test_subject_assertions.py`; `tests/test_subject_context.py`",
            "",
            1,
        ),
    ],
)
def test_normative_mapping_mutations_fail_closed(exporter, mutate) -> None:
    raw = TRACEABILITY.read_text(encoding="utf-8")
    with pytest.raises(exporter.Denied):
        exporter._parse_traceability(mutate(raw).encode("utf-8"))


def test_collected_binding_requires_one_real_node_per_sbe(exporter) -> None:
    planned = exporter._build_planned(REPO_ROOT, TRACEABILITY)
    nodes = [
        f"{row['planned_tests'][0]}::test_{row['sbe_id'].lower().replace('-', '_')}"
        for row in planned["examples"]
    ]
    collected = exporter._bind_collected(planned, nodes, require_count=43)

    assert collected["mode"] == "collected"
    assert len(collected["examples"]) == 43
    assert [row["pytest_node_id"] for row in collected["examples"]] == nodes
    assert all(
        set(row)
        == {
            "sbe_id",
            "approved_behavior",
            "design_contracts",
            "tasks",
            "fixture_id",
            "fixture_path",
            "planned_tests",
            "pytest_node_id",
        }
        for row in collected["examples"]
    )

    for bad in (nodes[:-1], nodes + [nodes[0]], [*nodes[:-1], "tests/other.py::test_e_f_020"]):
        with pytest.raises(exporter.Denied):
            exporter._bind_collected(planned, bad, require_count=43)


def test_collected_node_public_safety_accepts_bounded_public_parameter(
    exporter,
) -> None:
    node = (
        "tests/test_subject_assertions.py::"
        "test_e_p_001_synthetic_case[param-alpha]"
    )
    exporter._public_node_id(node, REPO_ROOT)


def test_unrelated_private_node_is_ignored_but_selected_private_node_denies(
    exporter,
) -> None:
    planned = exporter._build_planned(REPO_ROOT, TRACEABILITY)
    nodes = [
        f"{row['planned_tests'][0]}::test_{row['sbe_id'].lower().replace('-', '_')}"
        for row in planned["examples"]
    ]
    unrelated = [
        *nodes,
        "tests/test_subject_unrelated.py::test_unrelated[file:///private/tmp/operator]",
    ]
    result = exporter._bind_collected(
        planned, unrelated, require_count=43, repo_root=REPO_ROOT
    )
    assert len(result["examples"]) == 43

    selected = list(nodes)
    selected[0] += "_file:///private/tmp/operator"
    with pytest.raises(exporter.Denied):
        exporter._bind_collected(
            planned, selected, require_count=43, repo_root=REPO_ROOT
        )


def test_real_collection_can_bind_synthetic_selected_nodes_without_writing(
    exporter,
) -> None:
    planned = exporter._build_planned(REPO_ROOT, TRACEABILITY)
    collected = exporter._collect(
        REPO_ROOT,
        "python -m pytest --collect-only -q tests/test_subject_*.py",
    )
    selected = [
        f"{row['planned_tests'][0]}::test_{row['sbe_id'].lower().replace('-', '_')}"
        for row in planned["examples"]
    ]
    result = exporter._bind_collected(
        planned,
        [*collected, *selected],
        require_count=43,
        repo_root=REPO_ROOT,
    )
    assert [row["pytest_node_id"] for row in result["examples"]] == selected


@pytest.mark.parametrize(
    "private_suffix",
    [
        "file:///private/tmp/operator-secret",
        "jar:file:///tmp/operator-secret",
        "/Users/private/project",
        "/home/operator/project",
        "/private/tmp/operator-secret",
        r"C:\Temp\operator-secret",
        r"\\server\share\operator-secret",
        os.fspath(REPO_ROOT),
        os.path.expanduser("~"),
        "gh" + "p_" + "abcdefgh12345678",
        "api" + "_key=" + "abcdefgh12345678",
        "bear" + "er:abcdefgh12345678",
        "eyJhb" + "Gci.eyJzdWI.signature",
        "-----BEGIN " + "PRIVATE KEY-----",
        "escape\x1bsequence",
        "bidi\u202esequence",
    ],
)
def test_collected_node_private_or_secret_carriers_deny_before_binding(
    exporter, private_suffix: str
) -> None:
    planned = exporter._build_planned(REPO_ROOT, TRACEABILITY)
    nodes = [
        f"{row['planned_tests'][0]}::test_{row['sbe_id'].lower().replace('-', '_')}"
        for row in planned["examples"]
    ]
    nodes[0] += "_" + private_suffix

    with pytest.raises(exporter.Denied):
        exporter._bind_collected(
            planned,
            nodes,
            require_count=43,
            repo_root=REPO_ROOT,
        )


def test_exact_planned_check_command_passes_without_mutation() -> None:
    before = MAPPING.read_bytes()
    result = subprocess.run(
        [
            sys.executable,
            os.fspath(SCRIPT),
            "--mode",
            "planned",
            "--check",
            "specs/subject-distillation/traceability.md",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        timeout=20,
    )
    assert result.returncode == 0
    assert result.stderr == b""
    assert json.loads(result.stdout) == {
        "examples": 43,
        "mode": "planned",
        "requirements": 26,
        "status": "PASS",
    }
    assert MAPPING.read_bytes() == before


@pytest.mark.parametrize(
    "argv",
    [
        ["--mode", "planned", "--check", "/tmp/traceability.md"],
        ["--mode", "planned", "--check", "specs/subject-distillation/traceability.md", "--unknown"],
        ["--mode", "collected", "--require-count", "43"],
    ],
)
def test_cli_expansion_denies_without_echo(argv: list[str]) -> None:
    result = subprocess.run(
        [sys.executable, os.fspath(SCRIPT), *argv],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        timeout=20,
    )
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == b"SUBJECT_SBE_TRACEABILITY_DENY\n"
