#!/usr/bin/env python3
"""Fail when a change adds Ruff findings or grows rule-level lint debt."""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
SCHEMA_VERSION = 1


def _decode_diff_path(value: str) -> str | None:
    value = value.strip()
    if value == "/dev/null":
        return None
    if value.startswith('"') and value.endswith('"'):
        try:
            decoded = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return None
        if not isinstance(decoded, str):
            return None
        value = decoded
    if value.startswith(("a/", "b/")):
        value = value[2:]
    return value


def parse_added_lines(diff_text: str) -> dict[str, set[int]]:
    """Return new-side line numbers added in Python files from a unified diff."""

    added: dict[str, set[int]] = {}
    path: str | None = None
    new_line: int | None = None
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            path = None
            new_line = None
            continue
        if line.startswith("+++ "):
            path = _decode_diff_path(line[4:])
            if path is not None and not path.endswith(".py"):
                path = None
            continue
        match = HUNK.match(line)
        if match:
            new_line = int(match.group(1))
            continue
        if path is None or new_line is None:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added.setdefault(path, set()).add(new_line)
            new_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            continue
        elif not line.startswith("\\"):
            new_line += 1
    return added


def compare_baselines(
    previous: dict[str, Any], proposed: dict[str, Any]
) -> list[dict[str, int | str]]:
    """Return rule counts that grew between two otherwise compatible baselines."""

    old = previous.get("counts") if isinstance(previous, dict) else None
    new = proposed.get("counts") if isinstance(proposed, dict) else None
    if not isinstance(old, dict) or not isinstance(new, dict):
        return [{"code": "INVALID", "previous": 0, "proposed": 0, "delta": 0}]
    growth: list[dict[str, int | str]] = []
    for code in sorted(set(old) | set(new)):
        before = old.get(code, 0)
        after = new.get(code, 0)
        if type(before) is not int or type(after) is not int:
            return [{"code": "INVALID", "previous": 0, "proposed": 0, "delta": 0}]
        if after > before:
            growth.append(
                {
                    "code": code,
                    "previous": before,
                    "proposed": after,
                    "delta": after - before,
                }
            )
    return growth


def _validate_baseline(baseline: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_keys = {
        "schema_version",
        "tool",
        "scope",
        "initialized_from_commit",
        "counts",
        "total",
    }
    if set(baseline) != expected_keys:
        return ["baseline must use the closed schema"]
    tool = baseline.get("tool")
    counts = baseline.get("counts")
    if baseline.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported baseline schema")
    if not isinstance(tool, dict) or set(tool) != {"name", "version"}:
        errors.append("invalid baseline tool identity")
    elif tool.get("name") != "ruff" or not isinstance(tool.get("version"), str):
        errors.append("invalid baseline Ruff identity")
    if baseline.get("scope") != ["vault", "scripts", "tests"]:
        errors.append("invalid baseline scope")
    commit = baseline.get("initialized_from_commit")
    if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        errors.append("invalid baseline commit")
    if not isinstance(counts, dict) or any(
        not isinstance(code, str)
        or re.fullmatch(r"[A-Z]+\d+", code) is None
        or type(count) is not int
        or count < 0
        for code, count in (counts.items() if isinstance(counts, dict) else [])
    ):
        errors.append("invalid per-rule counts")
    elif baseline.get("total") != sum(counts.values()):
        errors.append("baseline total does not match per-rule counts")
    return errors


def _compact_finding(finding: dict[str, Any]) -> dict[str, Any]:
    location = finding.get("location")
    return {
        "code": finding.get("code"),
        "filename": finding.get("filename"),
        "row": location.get("row") if isinstance(location, dict) else None,
    }


def evaluate_findings(
    findings: list[dict[str, Any]],
    *,
    added_lines: dict[str, set[int]],
    baseline: dict[str, Any],
    ruff_version: str,
    previous_baseline: dict[str, Any] | None = None,
    base_commit: str | None = None,
) -> dict[str, Any]:
    """Evaluate Ruff JSON against exact changed lines and a rule-level ceiling."""

    baseline_errors = _validate_baseline(baseline)
    previous_baseline_errors: list[str] = []
    baseline_growth: list[dict[str, int | str]] = []
    if previous_baseline is not None:
        previous_baseline_errors = _validate_baseline(previous_baseline)
        if not previous_baseline_errors:
            if baseline.get("tool") != previous_baseline.get("tool"):
                previous_baseline_errors.append("Ruff baseline tool identity changed")
            if baseline.get("scope") != previous_baseline.get("scope"):
                previous_baseline_errors.append("Ruff baseline scope changed")
            baseline_growth = compare_baselines(previous_baseline, baseline)
    elif base_commit is not None and baseline.get("initialized_from_commit") != base_commit:
        baseline_errors.append("initial baseline is not bound to the exact base commit")
    expected_version = (
        baseline.get("tool", {}).get("version")
        if isinstance(baseline.get("tool"), dict)
        else None
    )
    version_error = None
    if expected_version != ruff_version:
        version_error = f"expected Ruff {expected_version}, found {ruff_version}"

    counts = Counter(
        finding.get("code")
        for finding in findings
        if isinstance(finding, dict) and isinstance(finding.get("code"), str)
    )
    expected_counts = baseline.get("counts")
    debt_growth: list[dict[str, int | str]] = []
    if isinstance(expected_counts, dict):
        for code in sorted(counts):
            ceiling = expected_counts.get(code, 0)
            if type(ceiling) is int and counts[code] > ceiling:
                debt_growth.append(
                    {
                        "code": code,
                        "baseline": ceiling,
                        "current": counts[code],
                        "delta": counts[code] - ceiling,
                    }
                )

    changed: list[dict[str, Any]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        filename = finding.get("filename")
        location = finding.get("location")
        row = location.get("row") if isinstance(location, dict) else None
        if isinstance(filename, str) and type(row) is int and row in added_lines.get(
            filename, set()
        ):
            changed.append(_compact_finding(finding))

    return {
        "schema_version": SCHEMA_VERSION,
        "ok": not baseline_errors
        and not previous_baseline_errors
        and not baseline_growth
        and version_error is None
        and not changed
        and not debt_growth,
        "tool": {"name": "ruff", "version": ruff_version},
        "scope": baseline.get("scope"),
        "findings_total": len(findings),
        "counts": dict(sorted(counts.items())),
        "changed_line_findings": changed,
        "debt_growth": debt_growth,
        "baseline_growth": baseline_growth,
        "baseline_errors": baseline_errors,
        "previous_baseline_errors": previous_baseline_errors,
        "tool_version_error": version_error,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_findings(findings: list[dict[str, Any]], root: Path) -> None:
    resolved_root = root.resolve()
    for finding in findings:
        filename = finding.get("filename")
        if not isinstance(filename, str):
            continue
        candidate = Path(filename)
        if candidate.is_absolute():
            try:
                finding["filename"] = candidate.resolve().relative_to(resolved_root).as_posix()
            except ValueError:
                finding["filename"] = candidate.as_posix()
        else:
            finding["filename"] = candidate.as_posix().removeprefix("./")


def _validate_findings(findings: list[dict[str, Any]]) -> None:
    for finding in findings:
        location = finding.get("location")
        if (
            not isinstance(finding.get("code"), str)
            or not finding["code"]
            or not isinstance(finding.get("filename"), str)
            or not finding["filename"]
            or not isinstance(location, dict)
            or type(location.get("row")) is not int
            or location["row"] < 1
        ):
            raise ValueError("Ruff finding must include code, filename and integer row")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--ruff-json", required=True)
    parser.add_argument("--diff-file", required=True)
    parser.add_argument("--ruff-version", required=True)
    parser.add_argument("--previous-baseline")
    parser.add_argument("--base-commit")
    parser.add_argument("--report", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = Path(args.root)
        baseline = _load_json(Path(args.baseline))
        previous_baseline = (
            _load_json(Path(args.previous_baseline)) if args.previous_baseline else None
        )
        findings = _load_json(Path(args.ruff_json))
        if (
            not isinstance(baseline, dict)
            or (
                previous_baseline is not None
                and not isinstance(previous_baseline, dict)
            )
            or not isinstance(findings, list)
        ):
            raise ValueError("baseline and Ruff output must be JSON objects/list")
        if any(not isinstance(item, dict) for item in findings):
            raise ValueError("Ruff findings must be objects")
        _validate_findings(findings)
        _normalize_findings(findings, root)
        diff = Path(args.diff_file).read_text(encoding="utf-8")
        report = evaluate_findings(
            findings,
            added_lines=parse_added_lines(diff),
            baseline=baseline,
            ruff_version=args.ruff_version,
            previous_baseline=previous_baseline,
            base_commit=args.base_commit,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        report = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "error": f"invalid lint gate input: {type(exc).__name__}",
        }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
