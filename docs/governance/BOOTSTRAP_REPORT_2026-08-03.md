# Governance Bootstrap Report — 2026-08-03

## Executive checkpoint

**Yellow.** Vault Agent Memory has a broad, tested local-first governed-memory
core. The Human-on-the-loop control plane was missing and is now being added.
Subject Distillation has an approved canonical design but no runtime; B-001 is
the first unblocked implementation dependency after this Bootstrap.

## End-to-end capabilities already present

- local SQLite/Markdown memory, compile, search and bounded reads;
- candidate-first review/promotion and audit-oriented governance;
- CLI and scoped MCP tools;
- backup/restore, schema migration and Obsidian import/export;
- optional semantic search, Document Map and search QA;
- agent setup/registry, automation, daily reports and Task Ledger;
- authenticated Gateway/remote and optional Supabase/multi-host adapters;
- public benchmark and external-reproduction validation tooling.

## Fresh implementation/test inventory

- Documentation inventory contains 343 tracked Markdown files, 131 dated
  decision records and the complete seven-artifact Subject canonical package.
- Python package version 0.10.2 with vault and vault-mcp entry points.
- 156 Python modules pass the module-size gate.
- 2902 tests collect on the current codebase.
- Fresh core and platform subsets passed: 344 passed / 2 skipped and
  184 passed / 10 skipped.
- Existing required CI includes Python 3.10–3.12 pytest, compileall, Linux and
  Windows install smoke, frozen uv lock, search QA, governance benchmark,
  package/wheel smoke, release parity, module size and public-safety scans.
- CI gaps are Ruff/typecheck/coverage/dependency scanning/migration dry-run and
  a named Staging smoke stage. Full-repo Ruff currently contains historical debt
  and must not be enabled as an undifferentiated blocking gate.

## Completed but not newly released

Subject Distillation requirements, design, schema v15, task plan and exact SBE
traceability are canonical. B-000 and its scanner recovery are merged. Main also
contains additional governance and benchmark work after release tag v0.10.2.
These are development facts, not a new package release or Production deployment.

## Incomplete core capabilities

- B-001 identity-safe proposal/confirmation/cleanup runner;
- T-001 baseline/evidence/progress control plane;
- generic Subject store, auth/policy, evidence/assertions, models/context;
- Subject CLI/MCP/Gateway surfaces, evaluation, recovery and final closure.

## Conflicts, duplicates and stale evidence

- The repository lacked the required autonomous-governance state and templates.
- SUBJECT_DISTILLATION_PROGRESS.md is stale against canonical tasks/roadmap.
- readme_claim_matrix.md names v0.9.0 while package/README name v0.10.2.
- Legacy Subject planning contains repeated approval stops superseded for risk:L0/risk:L1
  delivery by the owner-approved Human-on-the-loop mission. Product security,
  privacy, exact-scope and cleanup controls remain unchanged.
- A B-001 runner/test candidate exists only as two untracked files on an older
  base. It avoids duplicate implementation work, but one of 55 runner tests
  fails because its non-goals are stale. It is not completion evidence.
- No active Staging deployment is recorded. GitHub Pages and release/PyPI
  workflows are Production surfaces and remain separately gated.

## First Work Packages

| Package | Outcome | Risk | Dependencies | Gate |
|---|---|---:|---|---|
| WP-GOV-001 | Auditable autonomous delivery control plane | risk:L0 | none | validator/tests, independent review, CI, merge |
| WP-SD-B001 | Canonical T-001 proposal can be verified without persistent private bytes | risk:L1 security | WP-GOV-001 | 55 runner tests, B-000 integration, Ruff, independent security review, CI |
| WP-CI-001 | New PRs cannot add lint/dependency debt without blocking on historical debt | risk:L0 | governance | changed-file checks, fixed debt baseline/report, no weakened gates |
| WP-SD-T001 | Exact implementation baseline/evidence/progress is machine-controlled | risk:L1 | B-001 | negative/positive contract tests and exact scope |
| WP-SD-FOUNDATION | Synthetic fixtures, traceability and generic contracts are executable | risk:L1 | T-001 | 43-example binding and contract tests |
| WP-SD-SCHEMA | v15 lifecycle/migration/store works and rolls back | risk:L1; risk:L3 only for live migration | foundation | direct-SQL negatives, dry-run, rollback |

See CAPABILITY_MAP.md and DEPENDENCY_GRAPH.md for the full sequence.
The first batch is tracked by Issues #427 (governance), #429 (B-001) and #428
(incremental CI assurance).

## Potential risk:L2/risk:L3 triggers

- risk:L2: changing Subject-visible behavior, evidence/data use or retention,
  privacy/permission guarantees, public APIs, evaluation thresholds or accepted
  examples.
- risk:L3: Production deployment, live/private data, destructive migration, package
  release, production secrets, payment, DNS or external publication.

## Live GitHub and delivery readback

- Exact main: cfee9429c64a1dfa86bc14b126666979a6ce2611.
- Latest main Release Readiness CI run 30755710976: success.
- Main has no branch protection and no repository ruleset. CI is strong but is
  not technically required by GitHub settings; autonomous merges therefore
  require an explicit exact-head readback until a dedicated settings package is
  approved and applied.
- Two open PRs exist. PR #426 adds Spanish positioning with missing site links
  and is held for product scope/language quality. PR #401 contains stale Taiwan
  privacy fixtures and must be replayed from current main before review.
- Twelve open Issues after Bootstrap issue creation include stale Subject
  baseline Issues #410/#421, new Issues #427/#428/#429 and older
  retrieval/privacy/integration packages needing capability re-triage.
- Thirty-one remote branches are ancestors or patch-equivalent to main and may
  later be cleanup candidates; sixteen old branches contain unique/drifted
  commits and must not be deleted without archaeology.
- Latest release/PyPI is v0.10.2 at 2c66aebb. Current main is 35 commits and 135
  files ahead. Release/version selection is risk:L2 and publishing is risk:L3.
- Environments are github-pages and pypi only. No Development/Staging/runtime
  Production deployment is proven by repository evidence.
- Bootstrap found that docs merges automatically trigger GitHub Pages and
  therefore cross the risk:L3 public-deployment boundary. WP-GOV-001 does not
  silently change publication cadence; its merge requires an operation-specific
  risk:L3 approval while the automatic workflow remains active.

## Next unblocked Work Package

WP-CI-001 is next and can proceed without changing product behavior or crossing
the Subject trust root. WP-SD-B001 remains the next Subject dependency; its
preserved candidate is untrusted salvage input and requires the normative exact
owner lane/base after the Governance Bootstrap merge commit exists.

**Human intervention:** one operation-specific risk:L3 approval will be required
immediately before merging WP-GOV-001 because that docs merge automatically
deploys GitHub Pages. No response is needed while review, CI and the next
unblocked engineering package continue.
