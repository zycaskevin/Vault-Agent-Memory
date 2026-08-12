#!/usr/bin/env python3
"""Dispatch fail-closed Subject task authorization ledger validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_BOOTSTRAP_ERROR = False
try:
    import run_subject_task_authorization_v3 as runner
    import validate_subject_task_authorization_v3 as validator_v3
except ImportError:  # pragma: no cover - package import used by tests
    try:
        from scripts import run_subject_task_authorization_v3 as runner
        from scripts import validate_subject_task_authorization_v3 as validator_v3
    except Exception:  # noqa: BLE001 - fixed startup boundary
        runner = validator_v3 = None
        _BOOTSTRAP_ERROR = True
except Exception:  # noqa: BLE001 - fixed startup boundary
    runner = validator_v3 = None
    _BOOTSTRAP_ERROR = True


DENY_TEXT = "SUBJECT_TASK_AUTHORIZATION_DISPATCH_DENY\n"
ERROR_TEXT = "SUBJECT_TASK_AUTHORIZATION_DISPATCH_ERROR\n"
if _BOOTSTRAP_ERROR:
    class Denied(Exception):
        pass
else:
    Denied = runner.Denied


class _Parser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise Denied


def validate(repo_root: Path) -> dict[str, object]:
    result = validator_v3.validate_ledger(repo_root)
    if (
        type(result) is not dict
        or result.get("status") != "PASS"
        or type(result.get("sequence")) is not int
        or result["sequence"] < 4
    ):
        raise Denied
    return {
        "protocol_version": 3,
        "sequence": result["sequence"],
        "status": "PASS",
    }


def main(argv: list[str] | None = None) -> int:
    if _BOOTSTRAP_ERROR:
        sys.stderr.write(ERROR_TEXT)
        return 3
    try:
        parser = _Parser(add_help=False, allow_abbrev=False)
        parser.add_argument("--ledger", action="store_true")
        parser.add_argument("--json", action="store_true")
        args = parser.parse_args(argv)
        if not args.ledger or not args.json:
            raise Denied
        result = validate(Path.cwd().absolute())
        sys.stdout.buffer.write(runner._canonical(result))
        return 0
    except (Denied, runner.v1.verifier.Denied):
        sys.stderr.write(DENY_TEXT)
        return 2
    except Exception:  # noqa: BLE001 - public CLI fail-closed boundary
        sys.stderr.write(ERROR_TEXT)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
