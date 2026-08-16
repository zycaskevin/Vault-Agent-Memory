#!/usr/bin/env python3
"""Run frozen identity-sensitive subject tests in one process per node."""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import tempfile
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


def _environment(home: Path, temp_root: Path, phase: str) -> dict[str, str]:
    environment = dict(os.environ)
    environment["HOME"] = os.fspath(home)
    environment["TMPDIR"] = os.fspath(temp_root)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["SUBJECT_MISSION_V5_PHASE"] = phase
    return environment


def _collect(environment: dict[str, str]) -> list[str]:
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
            if sys.platform == "darwin" and node == DARWIN_DEFAULT_TEMP_NODE:
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", "-q", node],
                    check=False,
                    env=_environment(
                        Path.home(), Path(tempfile.gettempdir()), arguments.phase
                    ),
                    timeout=180,
                )
                if result.returncode != 0:
                    print(f"identity-isolated node failed: {node}", file=sys.stderr)
                    return 1
                continue
            outer = Path(tempfile.mkdtemp(prefix="node-", dir=parent))
            home = outer / "home"
            temp_root = outer / "tmp"
            home.mkdir(mode=0o700)
            temp_root.mkdir(mode=0o700)
            environment = _environment(home, temp_root, arguments.phase)
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "-q",
                        f"--basetemp={outer / 'pytest'}",
                        node,
                    ],
                    check=False,
                    env=environment,
                    timeout=180,
                )
            finally:
                shutil.rmtree(outer, ignore_errors=True)
            if result.returncode != 0:
                print(f"identity-isolated node failed: {node}", file=sys.stderr)
                return 1
        print(f"identity-isolated subject tests passed: {len(nodes)} nodes")
        return 0
    except (OSError, subprocess.SubprocessError, RuntimeError):
        print("identity-isolated subject tests failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
