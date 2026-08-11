#!/usr/bin/env python3
"""Read the mechanically verified Subject Distillation baseline identifier."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import validate_subject_baseline as baseline
except ImportError:  # pragma: no cover - import path used by test loaders
    from scripts import validate_subject_baseline as baseline


DENY = "SUBJECT_BASELINE_ID_DENY\n"


class _Parser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise baseline.ValidationError("arguments_invalid")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(add_help=False)
    parser.add_argument("--manifest", required=True)
    try:
        args = parser.parse_args(argv)
        repo_root = Path(__file__).absolute().parents[1]
        result = baseline.validate(Path(args.manifest), repo_root)
        baseline_id = result["baseline_id"]
        if not isinstance(baseline_id, str) or len(baseline_id) != 16:
            raise baseline.ValidationError("baseline_id_invalid")
    except (SystemExit, OSError, KeyError, TypeError, baseline.ValidationError):
        sys.stderr.write(DENY)
        return 2
    sys.stdout.write(baseline_id + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
