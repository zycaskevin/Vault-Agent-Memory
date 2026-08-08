# Incremental CI Quality Gates

## Capability

Every Pull Request is checked for newly introduced Python lint findings and
known Python dependency advisories. Existing lint debt remains visible and may
decrease, but it cannot grow silently or block unrelated lines merely because it
already existed.

## Ruff gate

The gate uses exact Ruff `0.15.20` over `vault/`, `scripts/` and `tests/`.
`scripts/ruff_debt_baseline.json` records the per-rule ceiling measured at
governance commit `3e407416123ff093416cac375bbce667f4f71658`.

A change fails when either:

- Ruff reports a finding on a new-side line added by the diff; or
- the repository-wide count for any Ruff rule exceeds its recorded ceiling.

Removing debt is always allowed. A lower baseline may be proposed after a clean
measurement. CI reads the previous baseline from the exact PR base commit and
mechanically rejects a raised existing ceiling or a newly positive rule ceiling.
On the one-time initial baseline, its `initialized_from_commit` must equal the
exact PR base. Changing the baseline to make CI green is forbidden; a deliberate
Ruff version/scope migration requires a separately reviewed Work Package.

## Dependency gate

CI runs exact `pip-audit==2.10.1` against the installed project and development
environment. Every advisory fails unless it matches one exception by exact
package, advisory ID and affected version.

Exceptions live in `scripts/dependency_audit_exceptions.json` and must:

- use the closed machine-readable schema;
- link an Issue in this repository;
- record approval and expiry dates no more than 30 days apart;
- be unexpired and not future-dated; and
- state a non-empty reason.

Unused, duplicate, malformed, broad or expired exceptions fail closed. Raw audit
descriptions are not copied into the normalized report. The uploaded CI artifact
contains the normalized lint and dependency decisions for the exact commit.

## Local verification

Run the deterministic evaluator tests:

```text
python -m pytest -q tests/test_ci_quality_gates.py
ruff check scripts/ci_changed_python_lint.py scripts/ci_dependency_audit.py tests/test_ci_quality_gates.py
```

The live advisory lookup requires network access and is proven by GitHub CI. A
local evaluator test does not claim that the current dependency set is advisory
free.

## Rollback

Revert the Work Package PR. Existing test, build, secret and history-privacy jobs
remain independent and are never disabled by this gate.
