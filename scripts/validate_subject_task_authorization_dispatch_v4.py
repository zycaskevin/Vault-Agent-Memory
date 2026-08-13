#!/usr/bin/env python3
"""Version-dispatch Subject authorization through Development Mission v4."""

from __future__ import annotations

import argparse
import os
import stat
import sys
import types
from pathlib import Path


def _load_sibling_dependency(module_name: str, filename: str) -> object:
    path = Path(os.path.abspath(Path(__file__).with_name(filename)))
    flags = os.O_RDONLY
    for name in ("O_NOFOLLOW", "O_CLOEXEC"):
        if not hasattr(os, name):
            raise RuntimeError
        flags |= int(getattr(os, name))
    before_path = os.lstat(path)
    if stat.S_ISLNK(before_path.st_mode):
        raise RuntimeError
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        raw = b""
        while len(raw) <= 1_048_576:
            chunk = os.read(fd, min(65_536, 1_048_577 - len(raw)))
            if not chunk:
                break
            raw += chunk
        after = os.fstat(fd)
    finally:
        os.close(fd)
    identity = lambda info: (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o755
        or before.st_nlink != 1
        or len(raw) > 1_048_576
        or identity(before_path) != identity(before)
        or identity(before) != identity(after)
        or identity(os.lstat(path)) != identity(before)
    ):
        raise RuntimeError
    existing = sys.modules.get(module_name)
    if existing is not None:
        if getattr(existing, "__file__", None) != os.fspath(path):
            raise RuntimeError
        return existing
    module = types.ModuleType(module_name)
    module.__file__ = os.fspath(path)
    module.__package__ = module_name.rpartition(".")[0]
    sys.modules[module_name] = module
    try:
        exec(compile(raw, "<subject-v4-sibling>", "exec"), module.__dict__)  # noqa: S102
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


try:
    mission = _load_sibling_dependency(
        "scripts.run_subject_development_mission_v4",
        "run_subject_development_mission_v4.py",
    )
    validator = _load_sibling_dependency(
        "scripts.validate_subject_development_mission_v4",
        "validate_subject_development_mission_v4.py",
    )
except Exception:
    if __name__ == "__main__":
        sys.stderr.write("SUBJECT_TASK_AUTHORIZATION_DISPATCH_V4_ERROR\n")
        raise SystemExit(3) from None
    raise


Denied = mission.Denied
DENY_TEXT = "SUBJECT_TASK_AUTHORIZATION_DISPATCH_V4_DENY\n"
ERROR_TEXT = "SUBJECT_TASK_AUTHORIZATION_DISPATCH_V4_ERROR\n"


class _Parser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise Denied


def validate(repo_root: Path) -> dict[str, object]:
    result = validator.validate(repo_root)
    return {
        "active": result["active"],
        "mission_id": result["mission_id"],
        "mission_state": result["mission_state"],
        "protocol_version": 4,
        "sequence": result["sequence"],
        "status": "PASS",
    }


def main(argv: list[str] | None = None) -> int:
    try:
        parser = _Parser(add_help=False, allow_abbrev=False)
        parser.add_argument("--ledger", action="store_true")
        parser.add_argument("--json", action="store_true")
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
        if not args.ledger or not args.json:
            raise Denied
        sys.stdout.buffer.write(mission.canonical(validate(Path.cwd().absolute())))
        return 0
    except (Denied, mission.legacy.v1.Denied, SystemExit):
        sys.stderr.write(DENY_TEXT)
        return 2
    except Exception:  # noqa: BLE001 - fixed no-echo boundary
        sys.stderr.write(ERROR_TEXT)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
