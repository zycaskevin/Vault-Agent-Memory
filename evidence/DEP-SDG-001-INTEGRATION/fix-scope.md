# Fix Scope

## Smallest sufficient change

Add the team-standard CI Cost Guard contract, give each governed automatic job
a timeout and draft-PR predicate, add ready/draft PR event types and
concurrency where missing, and include governance/evidence paths in CI and the
lightweight secret scan.

## Files or components in scope

`.sddgov/ci-cost-guard.json`, `.github/workflows/ci.yml`,
`.github/workflows/external-reproduction-validation.yml`, the SDG-managed
integration records, and a local raw-evidence ignore rule.

## Explicit non-scope

Product behavior, Subject Distillation implementation, canonical Mission
artifacts, migration, private/live data, deployment, release, Billing, and
repository-wide lint-debt remediation.

## Blast radius

L1. Workflow scheduling and time bounds change, but existing test commands and
acceptance logic remain intact. Deployment and release workflows are explicitly
exempt because their L3 semantics are outside this Work Package.
