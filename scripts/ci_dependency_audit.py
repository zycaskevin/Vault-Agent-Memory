#!/usr/bin/env python3
"""Validate pip-audit JSON with exact, expiring, issue-bound exceptions."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
ISSUE = re.compile(
    r"^https://github\.com/zycaskevin/Vault-Agent-Memory/issues/[1-9][0-9]*$"
)
EXCEPTION_KEYS = {
    "package",
    "advisory_id",
    "affected_version",
    "approved_on",
    "expires_on",
    "tracking_issue",
    "reason",
}


def _parse_date(value: Any, label: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{label} must be YYYY-MM-DD")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label} must be YYYY-MM-DD")
        return None


def _validate_exceptions(
    payload: dict[str, Any], today: date
) -> tuple[dict[tuple[str, str, str], dict[str, str]], list[str]]:
    if set(payload) != {"schema_version", "exceptions"}:
        return {}, ["exception file must use the closed schema"]
    if payload.get("schema_version") != SCHEMA_VERSION:
        return {}, ["unsupported exception schema"]
    items = payload.get("exceptions")
    if not isinstance(items, list):
        return {}, ["exceptions must be a list"]

    validated: dict[tuple[str, str, str], dict[str, str]] = {}
    errors: list[str] = []
    for index, item in enumerate(items):
        prefix = f"exception[{index}]"
        if not isinstance(item, dict) or set(item) != EXCEPTION_KEYS:
            errors.append(f"{prefix} must use the closed schema")
            continue
        if any(not isinstance(item[key], str) or not item[key].strip() for key in EXCEPTION_KEYS):
            errors.append(f"{prefix} fields must be non-empty strings")
            continue
        approved = _parse_date(item["approved_on"], f"{prefix}.approved_on", errors)
        expires = _parse_date(item["expires_on"], f"{prefix}.expires_on", errors)
        if approved is not None and expires is not None:
            if expires < approved:
                errors.append(f"{prefix} expires before approval")
            if expires - approved > timedelta(days=30):
                errors.append(f"{prefix} maximum duration is 30 days")
            if expires < today:
                errors.append(f"{prefix} is expired")
            if approved > today:
                errors.append(f"{prefix} approval date is in the future")
        if ISSUE.fullmatch(item["tracking_issue"]) is None:
            errors.append(f"{prefix} must link a repository GitHub issue")
        key = (item["package"], item["advisory_id"], item["affected_version"])
        if key in validated:
            errors.append(f"duplicate exception {'/'.join(key)}")
        else:
            validated[key] = item
    return validated, errors


def _audit_findings(audit: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    dependencies = audit.get("dependencies")
    if not isinstance(dependencies, list):
        return [], ["pip-audit dependencies must be a list"]
    findings: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            errors.append(f"dependency[{index}] must be an object")
            continue
        package = dependency.get("name")
        version = dependency.get("version")
        vulnerabilities = dependency.get("vulns")
        if not isinstance(package, str) or not isinstance(version, str):
            errors.append(f"dependency[{index}] has invalid identity")
            continue
        if not isinstance(vulnerabilities, list):
            errors.append(f"dependency[{index}].vulns must be a list")
            continue
        for vuln_index, vulnerability in enumerate(vulnerabilities):
            if not isinstance(vulnerability, dict) or not isinstance(
                vulnerability.get("id"), str
            ):
                errors.append(
                    f"dependency[{index}].vulns[{vuln_index}] has invalid advisory"
                )
                continue
            aliases = vulnerability.get("aliases", [])
            fixes = vulnerability.get("fix_versions", [])
            if not isinstance(aliases, list) or any(
                not isinstance(value, str) for value in aliases
            ):
                errors.append(
                    f"dependency[{index}].vulns[{vuln_index}].aliases must be strings"
                )
                aliases = []
            if not isinstance(fixes, list) or any(
                not isinstance(value, str) for value in fixes
            ):
                errors.append(
                    f"dependency[{index}].vulns[{vuln_index}].fix_versions must be strings"
                )
                fixes = []
            findings.append(
                {
                    "package": package,
                    "affected_version": version,
                    "advisory_id": vulnerability["id"],
                    "aliases": sorted(aliases),
                    "fix_versions": sorted(fixes),
                }
            )
    findings.sort(
        key=lambda item: (
            item["package"], item["affected_version"], item["advisory_id"]
        )
    )
    return findings, errors


def evaluate_audit(
    audit: dict[str, Any], exceptions: dict[str, Any], *, today: date
) -> dict[str, Any]:
    """Return a redacted, machine-readable dependency decision report."""

    known, exception_errors = _validate_exceptions(exceptions, today)
    findings, audit_errors = _audit_findings(audit)
    excepted: list[dict[str, Any]] = []
    unexcepted: list[dict[str, Any]] = []
    used: set[tuple[str, str, str]] = set()
    for finding in findings:
        key = (
            finding["package"],
            finding["advisory_id"],
            finding["affected_version"],
        )
        if key in known:
            used.add(key)
            value = dict(finding)
            value["exception_expires_on"] = known[key]["expires_on"]
            value["tracking_issue"] = known[key]["tracking_issue"]
            excepted.append(value)
        else:
            unexcepted.append(finding)
    for key in sorted(set(known) - used):
        exception_errors.append(f"unused exception {'/'.join(key)}")

    errors = audit_errors + exception_errors
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": not errors and not unexcepted,
        "as_of": today.isoformat(),
        "findings": findings,
        "findings_count": len(findings),
        "excepted": excepted,
        "excepted_count": len(excepted),
        "unexcepted": unexcepted,
        "unexcepted_count": len(unexcepted),
        "audit_errors": audit_errors,
        "exception_errors": exception_errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-json", required=True)
    parser.add_argument("--exceptions", required=True)
    parser.add_argument("--today")
    parser.add_argument("--report", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        audit = json.loads(Path(args.audit_json).read_text(encoding="utf-8"))
        exceptions = json.loads(Path(args.exceptions).read_text(encoding="utf-8"))
        if not isinstance(audit, dict) or not isinstance(exceptions, dict):
            raise ValueError("audit and exceptions must be JSON objects")
        today = date.fromisoformat(args.today) if args.today else date.today()
        report = evaluate_audit(audit, exceptions, today=today)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        report = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "error": f"invalid dependency audit input: {type(exc).__name__}",
        }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
