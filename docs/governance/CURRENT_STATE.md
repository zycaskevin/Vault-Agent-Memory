# Current State

**As of:** 2026-08-03 Asia/Taipei

**Verified main at Bootstrap start:** cfee9429c64a1dfa86bc14b126666979a6ce2611

**Package version:** 0.10.2
**Status:** Yellow — mature governed-memory core; Subject Distillation runtime not implemented

## Available end-to-end capabilities

The repository currently provides a local-first SQLite/Markdown memory core,
CLI and MCP surfaces, candidate-first propose/review/promote governance, bounded
search and read, audit metadata, backup/restore, Obsidian import/export,
optional semantic retrieval, automation/reporting, task ledger/working sets,
agent setup, Gateway/remote adapters, Supabase sync adapters and public
reproduction/benchmark tooling. Remote and cloud adapters do not replace local
source-of-truth semantics.

## Completed but not part of a new release

- Subject Distillation canonical requirements/design/tasks/schema/traceability
  package and validated baseline.
- B-000 implementation-authorization schema/verifier and hostile tests.
- Scanner contradiction recovery merged through PR #425.

No release is implied by a merged development PR. Package publishing and
Production remain separate risk:L3/release gates.

## Incomplete core capability

Subject Distillation is specification-complete but implementation-incomplete.
B-001 identity-safe proposal/verification/cleanup runner is the first executable
dependency; T-001 control-plane artifacts and T-002+ product/runtime packages
remain downstream.

## Duplicate-work and recovery note

An uncommitted B-001 runner/test candidate is preserved in a separate checkout
at the older b4085eef base. It is evidence and salvage input, not accepted
implementation: its real-verifier test currently fails because it contains the
stale JWT-shaped non-goals no.product.runtime and no.production.migration. It
must be rebased, repaired, reviewed and verified against current main before use.

## Known documentation drift

- docs/plans/SUBJECT_DISTILLATION_PROGRESS.md still describes a pre-B-000 gate
  and conflicts with the canonical current gate in Subject tasks/roadmap.
- docs/readme_claim_matrix.md still identifies v0.9.0 while the package and
  README identify v0.10.2.
- Security/privacy, cost, UX state and repository-wide test contracts are
  fragmented rather than indexed by one authority map.

These are governance debt and do not override the canonical Subject package.

## Deployment state

- Development/Test: local and CI verification available.
- Staging: no canonical active Staging deployment is asserted by Bootstrap.
- Production package: latest release is v0.10.2 at 2c66aebb; current main is
  35 commits ahead, so merged main capabilities are not claimed as published.
- Public docs: latest GitHub Pages evidence is at b4085eef, not current main.
  Automatic docs-to-Pages deployment remains active and is classified as a
  risk:L3 post-merge side effect.
- Runtime Production: not proven by repository deployment evidence.

## GitHub delivery state

- Latest exact-main Release Readiness CI is green.
- Main has no branch protection or ruleset; required checks are not enforced by
  GitHub settings, so the Main Agent must apply the merge gate explicitly.
- PR #426 (Spanish README) is blocked on missing language/site contract and
  first-time-contributor Actions approval.
- PR #401 (Taiwan privacy fixtures) is stale but potentially recoverable; it
  requires current-main replay, privacy regression and security review.
- Issues #410 and #421 contain stale baseline/process information and must be
  converged before their downstream capability work is claimed.

## Next capability targets

- Next unblocked: WP-CI-001 incremental lint/dependency assurance.
- Security dependency: WP-SD-B001 identity-safe runner, blocked only until the
  post-Bootstrap exact main can be named by the normative owner trust root.
