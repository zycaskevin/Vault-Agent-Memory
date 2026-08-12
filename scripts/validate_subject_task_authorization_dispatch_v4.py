#!/usr/bin/env python3
"""Version-dispatch Subject authorization through Development Mission v4."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from scripts import run_subject_development_mission_v4 as mission
    from scripts import validate_subject_development_mission_v4 as validator
except ImportError:  # pragma: no cover - direct script execution
    try:
        import run_subject_development_mission_v4 as mission
        import validate_subject_development_mission_v4 as validator
    except Exception:
        if __name__ == "__main__":
            sys.stderr.write("SUBJECT_TASK_AUTHORIZATION_DISPATCH_V4_ERROR\n")
            raise SystemExit(3) from None
        raise
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
