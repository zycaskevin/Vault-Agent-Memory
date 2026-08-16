#!/usr/bin/env python3
"""Run frozen identity-sensitive subject tests in one process per node."""

from __future__ import annotations

import argparse
import ast
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

FILES = (
    ("tests/test_subject_authorization_bootstrap.py", 96),
    ("tests/test_subject_authorization_runner.py", 74),
    ("tests/test_subject_progress_v2.py", 26),
    ("tests/test_subject_progress_v3.py", 29),
    ("tests/test_subject_task_authorization_v2.py", 37),
    ("tests/test_subject_task_authorization_v3.py", 39),
    ("tests/test_subject_development_mission_v5.py", 90),
    ("tests/test_subject_task_authorization_dispatch_v5.py", 2),
    ("tests/test_subject_baseline_control.py", 53),
)
DISPATCHER_NODES = (
    (
        "tests/test_subject_task_authorization_dispatch_v5.py::"
        "test_dispatch_accepts_exact_current_mission_phase"
    ),
    (
        "tests/test_subject_task_authorization_dispatch_v5.py::"
        "test_dispatch_cli_is_exact_and_no_abbreviation"
    ),
)
DARWIN_DEFAULT_TEMP_NODE = (
    "tests/test_subject_authorization_runner.py::"
    "test_verify_uses_canonicalized_default_temp_root_and_cleans"
)
PLATFORM_SKIP_ALLOWLIST = (
    (
        DARWIN_DEFAULT_TEMP_NODE,
        "darwin",
        "Darwin system alias integration",
    ),
)
ALLOWED_DISPATCHER_PYTEST_ATTRIBUTES = {
    "fixture",
    "MonkeyPatch",
    "TempPathFactory",
}
FORBIDDEN_DISPATCHER_OUTCOMES = {
    "importorskip",
    "skip",
    "skipif",
    "xfail",
}
FORBIDDEN_DYNAMIC_ACCESS = {
    "__import__",
    "compile",
    "eval",
    "exec",
    "getattr",
    "setattr",
}


def _expression_root(node: ast.AST) -> str | None:
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _validate_dispatcher_source(source: str) -> None:
    """Reject static and dynamically spelled pytest outcome bypasses."""
    tree = ast.parse(source)
    pytest_aliases = {"pytest"}
    dynamic_aliases = set(FORBIDDEN_DYNAMIC_ACCESS)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pytest" and alias.asname is not None:
                    raise RuntimeError("dispatcher pytest alias is not closed")
        elif isinstance(node, ast.ImportFrom) and node.module == "pytest":
            raise RuntimeError("dispatcher pytest imports are not closed")
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if isinstance(value, ast.Name):
                for target in targets:
                    if isinstance(target, ast.Name):
                        if value.id in pytest_aliases:
                            pytest_aliases.add(target.id)
                        if value.id in dynamic_aliases:
                            dynamic_aliases.add(target.id)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and _expression_root(node) in pytest_aliases
            and node.attr not in ALLOWED_DISPATCHER_PYTEST_ATTRIBUTES
        ):
            raise RuntimeError("dispatcher pytest attribute is not closed")
        if isinstance(node, ast.Subscript) and _expression_root(node) in pytest_aliases:
            raise RuntimeError("dispatcher pytest subscript is not closed")
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value in FORBIDDEN_DISPATCHER_OUTCOMES
        ):
            raise RuntimeError("dispatcher pytest outcome string is forbidden")
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_DISPATCHER_OUTCOMES:
            raise RuntimeError("dispatcher pytest outcome name is forbidden")
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in dynamic_aliases
        ):
            raise RuntimeError("dispatcher dynamic access is forbidden")


def _single_junit_case(path: Path) -> tuple[ET.Element, ET.Element]:
    """Return one exact suite/case pair or deny malformed outcome evidence."""
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise RuntimeError("identity test outcome XML is invalid") from exc
    suites = [
        node
        for node in root.iter()
        if node.tag.rsplit("}", 1)[-1] == "testsuite"
        and node.attrib.get("tests") is not None
    ]
    cases = [
        node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "testcase"
    ]
    if len(suites) != 1 or len(cases) != 1:
        raise RuntimeError("identity test outcome count drift")
    return suites[0], cases[0]


def _verify_single_pass_junit(path: Path) -> None:
    """Require one real PASS; rc=0 alone may conceal skip or non-strict xfail."""
    suite, case = _single_junit_case(path)
    if {
        name: suite.attrib.get(name, "0")
        for name in ("tests", "skipped", "failures", "errors")
    } != {"tests": "1", "skipped": "0", "failures": "0", "errors": "0"}:
        raise RuntimeError("identity test did not report one exact pass")
    if any(
        child.tag.rsplit("}", 1)[-1] in {"skipped", "failure", "error"}
        for child in case
    ):
        raise RuntimeError("identity test reported a non-pass outcome")


def _platform_skip_reason(node: str, platform: str) -> str | None:
    matches = [
        reason
        for allowed_node, required_platform, reason in PLATFORM_SKIP_ALLOWLIST
        if node == allowed_node and platform != required_platform
    ]
    if len(matches) > 1:
        raise RuntimeError("identity platform skip allowlist is ambiguous")
    return matches[0] if matches else None


def _verify_single_platform_skip_junit(path: Path, *, expected_reason: str) -> None:
    """Require the one exact allowlisted platform skip and no other outcome."""
    suite, case = _single_junit_case(path)
    if {
        name: suite.attrib.get(name, "0")
        for name in ("tests", "skipped", "failures", "errors")
    } != {"tests": "1", "skipped": "1", "failures": "0", "errors": "0"}:
        raise RuntimeError("identity platform skip outcome count drift")
    children = list(case)
    if len(children) != 1 or children[0].tag.rsplit("}", 1)[-1] != "skipped":
        raise RuntimeError("identity platform skip outcome is invalid")
    if children[0].attrib != {
        "type": "pytest.skip",
        "message": expected_reason,
    }:
        raise RuntimeError("identity platform skip reason or type drift")


def _verify_identity_junit(path: Path, *, node: str, platform: str) -> None:
    """Require PASS except for the one exact off-Darwin integration skip."""
    platform_skip_reason = _platform_skip_reason(node, platform)
    if platform_skip_reason is None:
        _verify_single_pass_junit(path)
    else:
        _verify_single_platform_skip_junit(
            path,
            expected_reason=platform_skip_reason,
        )


def _environment(home: Path, temp_root: Path, phase: str) -> dict[str, str]:
    environment = dict(os.environ)
    environment["HOME"] = os.fspath(home)
    environment["TMPDIR"] = os.fspath(temp_root)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["SUBJECT_MISSION_V5_PHASE"] = phase
    return environment


def _collect(environment: dict[str, str]) -> list[str]:
    dispatcher_path = Path("tests/test_subject_task_authorization_dispatch_v5.py")
    _validate_dispatcher_source(dispatcher_path.read_text(encoding="utf-8"))
    paths = [path for path, _count in FILES]
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", *paths],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
        timeout=120,
    )
    if result.returncode != 0 or result.stderr:
        raise RuntimeError("identity test collection failed")
    nodes = [
        line
        for line in result.stdout.splitlines()
        if line.startswith("tests/") and "::" in line
    ]
    if len(nodes) != len(set(nodes)) or any(
        len(node) > 4_096 or any(ord(character) < 32 for character in node)
        for node in nodes
    ):
        raise RuntimeError("identity test collection is not closed")
    for path, expected in FILES:
        if sum(node.startswith(path + "::") for node in nodes) != expected:
            raise RuntimeError("identity test collection count drift")
    dispatcher_nodes = tuple(
        node
        for node in nodes
        if node.startswith("tests/test_subject_task_authorization_dispatch_v5.py::")
    )
    if dispatcher_nodes != DISPATCHER_NODES:
        raise RuntimeError("dispatcher identity test node drift")
    if len(nodes) != sum(count for _path, count in FILES):
        raise RuntimeError("identity test collection total drift")
    return nodes


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--phase", choices=("candidate", "active"), required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = _arguments(argv)
        parent = Path.home() / ".codex" / "sddgov-test-temp" / "identity-nodes"
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        parent_info = parent.lstat()
        if not stat.S_ISDIR(parent_info.st_mode) or stat.S_ISLNK(parent_info.st_mode):
            raise RuntimeError("identity test root is not a physical directory")
        environment = _environment(
            Path.home(), Path(tempfile.gettempdir()), arguments.phase
        )
        nodes = _collect(environment)
        for node in nodes:
            outer = Path(tempfile.mkdtemp(prefix="node-", dir=parent))
            home = outer / "home"
            temp_root = outer / "tmp"
            junit = outer / "outcome.xml"
            try:
                if sys.platform == "darwin" and node == DARWIN_DEFAULT_TEMP_NODE:
                    environment = _environment(
                        Path.home(), Path(tempfile.gettempdir()), arguments.phase
                    )
                    basetemp: list[str] = []
                else:
                    home.mkdir(mode=0o700)
                    temp_root.mkdir(mode=0o700)
                    environment = _environment(home, temp_root, arguments.phase)
                    basetemp = [f"--basetemp={outer / 'pytest'}"]
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "-q",
                        "-o",
                        "xfail_strict=true",
                        f"--junitxml={junit}",
                        *basetemp,
                        node,
                    ],
                    check=False,
                    env=environment,
                    timeout=180,
                )
                if result.returncode != 0:
                    print(f"identity-isolated node failed: {node}", file=sys.stderr)
                    return 1
                _verify_identity_junit(junit, node=node, platform=sys.platform)
            finally:
                shutil.rmtree(outer, ignore_errors=True)
        print(f"identity-isolated subject tests passed: {len(nodes)} nodes")
        return 0
    except (OSError, subprocess.SubprocessError, RuntimeError):
        print("identity-isolated subject tests failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
