#!/usr/bin/env python3
"""Run frozen identity-sensitive subject tests in one process per node."""

from __future__ import annotations

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
    ("tests/test_subject_development_mission_v5.py", 76),
    ("tests/test_subject_baseline_control.py", 53),
)
DARWIN_DEFAULT_TEMP_NODE = (
    "tests/test_subject_authorization_runner.py::"
    "test_verify_uses_canonicalized_default_temp_root_and_cleans"
)


def _environment(home: Path, temp_root: Path) -> dict[str, str]:
    environment = dict(os.environ)
    environment["HOME"] = os.fspath(home)
    environment["TMPDIR"] = os.fspath(temp_root)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
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
    if len(nodes) != sum(count for _path, count in FILES):
        raise RuntimeError("identity test collection total drift")
    return nodes


def main() -> int:
    try:
        parent = Path.home() / ".codex" / "sddgov-test-temp" / "identity-nodes"
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        parent_info = parent.lstat()
        if not stat.S_ISDIR(parent_info.st_mode) or stat.S_ISLNK(parent_info.st_mode):
            raise RuntimeError("identity test root is not a physical directory")
        environment = _environment(Path.home(), Path(tempfile.gettempdir()))
        nodes = _collect(environment)
        for node in nodes:
            if sys.platform == "darwin" and node == DARWIN_DEFAULT_TEMP_NODE:
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", "-q", node],
                    check=False,
                    env=_environment(Path.home(), Path(tempfile.gettempdir())),
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
            environment = _environment(home, temp_root)
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
