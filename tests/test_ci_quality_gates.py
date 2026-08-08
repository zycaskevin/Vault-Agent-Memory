from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import yaml

from scripts import ci_changed_python_lint, ci_dependency_audit


ROOT = Path(__file__).resolve().parents[1]


def _ruff_finding(path: str, row: int, code: str = "F401") -> dict[str, object]:
    return {
        "code": code,
        "filename": path,
        "location": {"row": row, "column": 1},
        "end_location": {"row": row, "column": 5},
        "message": "synthetic lint finding",
        "fix": None,
        "noqa_row": row,
        "url": "https://docs.astral.sh/ruff/rules/example",
    }


def _ruff_baseline(counts: dict[str, int]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "tool": {"name": "ruff", "version": "0.15.20"},
        "scope": ["vault", "scripts", "tests"],
        "initialized_from_commit": "3e407416123ff093416cac375bbce667f4f71658",
        "counts": counts,
        "total": sum(counts.values()),
    }


def _audit(vulnerabilities: list[dict[str, object]]) -> dict[str, object]:
    return {
        "dependencies": [
            {
                "name": "example-package",
                "version": "1.2.3",
                "vulns": vulnerabilities,
            }
        ],
        "fixes": [],
    }


def _exceptions(items: list[dict[str, str]]) -> dict[str, object]:
    return {"schema_version": 1, "exceptions": items}


def _exception(**overrides: str) -> dict[str, str]:
    value = {
        "package": "example-package",
        "advisory_id": "PYSEC-2099-1",
        "affected_version": "1.2.3",
        "approved_on": "2026-08-03",
        "expires_on": "2026-08-20",
        "tracking_issue": "https://github.com/zycaskevin/Vault-Agent-Memory/issues/999",
        "reason": "Temporary bounded exception while the compatible upstream fix is validated.",
    }
    value.update(overrides)
    return value


def test_parse_added_python_lines_tracks_new_side_only() -> None:
    diff = """diff --git a/vault/example.py b/vault/example.py
--- a/vault/example.py
+++ b/vault/example.py
@@ -2,2 +2,3 @@
 unchanged
-old
+replacement
+new_line
diff --git a/docs/readme.md b/docs/readme.md
--- a/docs/readme.md
+++ b/docs/readme.md
@@ -1 +1 @@
-old
+new
"""

    assert ci_changed_python_lint.parse_added_lines(diff) == {
        "vault/example.py": {3, 4}
    }


def test_parse_added_lines_handles_unicode_rename_new_and_deleted_paths() -> None:
    diff = '''diff --git "a/vault/舊 檔.py" "b/vault/新 檔.py"
similarity index 80%
rename from vault/舊 檔.py
rename to vault/新 檔.py
--- "a/vault/舊 檔.py"
+++ "b/vault/新 檔.py"
@@ -1 +1,2 @@
 old
+added
diff --git a/vault/new.py b/vault/new.py
new file mode 100644
--- /dev/null
+++ b/vault/new.py
@@ -0,0 +1 @@
+new
diff --git a/vault/deleted.py b/vault/deleted.py
deleted file mode 100644
--- a/vault/deleted.py
+++ /dev/null
@@ -1 +0,0 @@
-old
'''

    assert ci_changed_python_lint.parse_added_lines(diff) == {
        "vault/新 檔.py": {2},
        "vault/new.py": {1},
    }


def test_changed_line_finding_blocks_but_untouched_historical_finding_does_not() -> None:
    findings = [_ruff_finding("vault/example.py", 10)]
    baseline = _ruff_baseline({"F401": 1})

    unchanged = ci_changed_python_lint.evaluate_findings(
        findings,
        added_lines={"vault/example.py": {11}},
        baseline=baseline,
        ruff_version="0.15.20",
    )
    changed = ci_changed_python_lint.evaluate_findings(
        findings,
        added_lines={"vault/example.py": {10}},
        baseline=baseline,
        ruff_version="0.15.20",
    )

    assert unchanged["ok"] is True
    assert unchanged["changed_line_findings"] == []
    assert changed["ok"] is False
    assert changed["changed_line_findings"][0]["code"] == "F401"


def test_global_per_rule_debt_growth_blocks_even_outside_changed_lines() -> None:
    findings = [
        _ruff_finding("vault/example.py", 10),
        _ruff_finding("vault/other.py", 20),
    ]
    report = ci_changed_python_lint.evaluate_findings(
        findings,
        added_lines={},
        baseline=_ruff_baseline({"F401": 1}),
        ruff_version="0.15.20",
    )

    assert report["ok"] is False
    assert report["debt_growth"] == [
        {"code": "F401", "baseline": 1, "current": 2, "delta": 1}
    ]


def test_ruff_version_or_baseline_growth_cannot_silently_change() -> None:
    baseline = _ruff_baseline({"F401": 1, "I001": 3})
    lower = _ruff_baseline({"F401": 1, "I001": 2})
    raised = _ruff_baseline({"F401": 2, "I001": 2})

    assert ci_changed_python_lint.compare_baselines(baseline, lower) == []
    assert ci_changed_python_lint.compare_baselines(baseline, raised) == [
        {"code": "F401", "previous": 1, "proposed": 2, "delta": 1}
    ]

    report = ci_changed_python_lint.evaluate_findings(
        [_ruff_finding("vault/example.py", 10)],
        added_lines={},
        baseline=baseline,
        ruff_version="0.99.0",
    )
    assert report["ok"] is False
    assert report["tool_version_error"] == "expected Ruff 0.15.20, found 0.99.0"


def test_previous_baseline_blocks_raised_and_new_rule_ceilings() -> None:
    previous = _ruff_baseline({"F401": 1, "I001": 3})
    raised = _ruff_baseline({"F401": 2, "I001": 3})
    added_rule = _ruff_baseline({"F401": 1, "I001": 3, "F841": 1})
    lowered = _ruff_baseline({"F401": 1, "I001": 2})

    raised_report = ci_changed_python_lint.evaluate_findings(
        [],
        added_lines={},
        baseline=raised,
        previous_baseline=previous,
        ruff_version="0.15.20",
    )
    added_report = ci_changed_python_lint.evaluate_findings(
        [],
        added_lines={},
        baseline=added_rule,
        previous_baseline=previous,
        ruff_version="0.15.20",
    )
    lowered_report = ci_changed_python_lint.evaluate_findings(
        [],
        added_lines={},
        baseline=lowered,
        previous_baseline=previous,
        ruff_version="0.15.20",
    )

    assert raised_report["ok"] is False
    assert raised_report["baseline_growth"] == [
        {"code": "F401", "previous": 1, "proposed": 2, "delta": 1}
    ]
    assert added_report["ok"] is False
    assert added_report["baseline_growth"] == [
        {"code": "F841", "previous": 0, "proposed": 1, "delta": 1}
    ]
    assert lowered_report["ok"] is True
    assert lowered_report["baseline_growth"] == []


def test_initial_baseline_must_bind_exact_base_commit() -> None:
    report = ci_changed_python_lint.evaluate_findings(
        [],
        added_lines={},
        baseline=_ruff_baseline({}),
        ruff_version="0.15.20",
        base_commit="0000000000000000000000000000000000000000",
    )
    assert report["ok"] is False
    assert report["baseline_errors"] == [
        "initial baseline is not bound to the exact base commit"
    ]


def test_lint_cli_writes_machine_report_on_failure(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    findings = tmp_path / "ruff.json"
    diff = tmp_path / "change.diff"
    report = tmp_path / "report.json"
    baseline.write_text(json.dumps(_ruff_baseline({"F401": 1})), encoding="utf-8")
    findings.write_text(
        json.dumps([_ruff_finding(str(tmp_path / "vault" / "example.py"), 2)]),
        encoding="utf-8",
    )
    diff.write_text(
        """diff --git a/vault/example.py b/vault/example.py
--- a/vault/example.py
+++ b/vault/example.py
@@ -1 +1,2 @@
 old
+bad
""",
        encoding="utf-8",
    )

    code = ci_changed_python_lint.main(
        [
            "--root",
            str(tmp_path),
            "--baseline",
            str(baseline),
            "--ruff-json",
            str(findings),
            "--diff-file",
            str(diff),
            "--ruff-version",
            "0.15.20",
            "--report",
            str(report),
        ]
    )

    assert code == 1
    assert json.loads(report.read_text(encoding="utf-8"))["ok"] is False


def test_lint_cli_fails_closed_and_reports_malformed_ruff_json(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    findings = tmp_path / "ruff.json"
    diff = tmp_path / "change.diff"
    report = tmp_path / "report.json"
    baseline.write_text(json.dumps(_ruff_baseline({})), encoding="utf-8")
    findings.write_text(json.dumps([{"code": "F401"}]), encoding="utf-8")
    diff.write_text("", encoding="utf-8")

    code = ci_changed_python_lint.main(
        [
            "--root",
            str(tmp_path),
            "--baseline",
            str(baseline),
            "--ruff-json",
            str(findings),
            "--diff-file",
            str(diff),
            "--ruff-version",
            "0.15.20",
            "--report",
            str(report),
        ]
    )

    assert code == 1
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert payload["error"] == "invalid lint gate input: ValueError"


def test_dependency_audit_blocks_unexcepted_advisory() -> None:
    report = ci_dependency_audit.evaluate_audit(
        _audit(
            [
                {
                    "id": "PYSEC-2099-1",
                    "fix_versions": ["1.2.4"],
                    "aliases": ["CVE-2099-0001"],
                    "description": "synthetic",
                }
            ]
        ),
        _exceptions([]),
        today=date(2026, 8, 3),
    )

    assert report["ok"] is False
    assert report["unexcepted_count"] == 1
    assert report["findings"][0]["advisory_id"] == "PYSEC-2099-1"


def test_dependency_exception_is_exact_bounded_and_machine_visible() -> None:
    audit = _audit(
        [
            {
                "id": "PYSEC-2099-1",
                "fix_versions": [],
                "aliases": [],
                "description": "synthetic",
            }
        ]
    )
    report = ci_dependency_audit.evaluate_audit(
        audit,
        _exceptions([_exception()]),
        today=date(2026, 8, 3),
    )
    wrong_version = ci_dependency_audit.evaluate_audit(
        audit,
        _exceptions([_exception(affected_version="1.2")]),
        today=date(2026, 8, 3),
    )

    assert report["ok"] is True
    assert report["excepted_count"] == 1
    assert report["unexcepted_count"] == 0
    assert wrong_version["ok"] is False
    assert wrong_version["unexcepted_count"] == 1
    assert wrong_version["exception_errors"] == [
        "unused exception example-package/PYSEC-2099-1/1.2"
    ]


def test_dependency_exception_rejects_expiry_over_thirty_days_and_missing_issue() -> None:
    audit = _audit([])
    invalid = _exceptions(
        [
            _exception(
                expires_on="2026-10-01",
                tracking_issue="https://example.invalid/issues/1",
            )
        ]
    )

    report = ci_dependency_audit.evaluate_audit(
        audit,
        invalid,
        today=date(2026, 8, 3),
    )

    assert report["ok"] is False
    assert any("maximum duration is 30 days" in item for item in report["exception_errors"])
    assert any("repository GitHub issue" in item for item in report["exception_errors"])


def test_dependency_cli_writes_redacted_machine_report(tmp_path: Path) -> None:
    audit = tmp_path / "audit.json"
    exceptions = tmp_path / "exceptions.json"
    report = tmp_path / "report.json"
    audit.write_text(json.dumps(_audit([])), encoding="utf-8")
    exceptions.write_text(json.dumps(_exceptions([])), encoding="utf-8")

    code = ci_dependency_audit.main(
        [
            "--audit-json",
            str(audit),
            "--exceptions",
            str(exceptions),
            "--today",
            "2026-08-03",
            "--report",
            str(report),
        ]
    )

    assert code == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert "description" not in json.dumps(payload)


def test_dependency_cli_fails_closed_and_reports_malformed_aliases(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "audit.json"
    exceptions = tmp_path / "exceptions.json"
    report = tmp_path / "report.json"
    audit.write_text(
        json.dumps(
            _audit(
                [
                    {
                        "id": "PYSEC-2099-1",
                        "fix_versions": [],
                        "aliases": [1],
                    }
                ]
            )
        ),
        encoding="utf-8",
    )
    exceptions.write_text(json.dumps(_exceptions([])), encoding="utf-8")

    code = ci_dependency_audit.main(
        [
            "--audit-json",
            str(audit),
            "--exceptions",
            str(exceptions),
            "--today",
            "2026-08-03",
            "--report",
            str(report),
        ]
    )

    assert code == 1
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert payload["audit_errors"] == [
        "dependency[0].vulns[0].aliases must be strings"
    ]


def test_release_readiness_keeps_existing_gates_and_adds_incremental_quality() -> None:
    workflow_path = ROOT / ".github" / "workflows" / "ci.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    jobs = workflow["jobs"]

    assert {"test", "build-smoke", "secret-scan-light", "history-privacy-scan"} <= set(jobs)
    assert "python -m pytest -q" in json.dumps(jobs["test"])
    assert "incremental-quality" in jobs

    quality = json.dumps(jobs["incremental-quality"], sort_keys=True)
    assert "pip-audit==2.10.1" in quality
    assert "scripts/ci_changed_python_lint.py" in quality
    assert "scripts/ci_dependency_audit.py" in quality
    assert "actions/upload-artifact@v7" in quality
    assert "core.quotePath=false" in quality
    assert "git show" in quality
    assert "--previous-baseline" in quality
    assert "steps.lint_collect.outcome" in quality
    assert "steps.dependency_collect.outcome" in quality
    assert "if-no-files-found" in quality
    assert quality.count("always()") >= 4
