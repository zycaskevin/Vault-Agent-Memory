# Work Package: SDG-012 Mission V5 dispatcher phase isolation

## References

- Issue: #488
- Hosted RED: PR #487, run `31943149157`, job `95155106192`
- SDD: `docs/decision_records/2026-08-15-mission-v5-post-sdg-activation.md`
  and `.agentic-sdd-governance/core/POLICY_KERNEL.md`
- Protocol base: merged SDG-011 PR #486 at
  `9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0`
- Risk: L1

## Objective Contract

- Outcome: run both Mission V5 dispatcher assertions inside the same explicit
  candidate/active identity-isolation boundary as the Mission V5 suite.
- Success metric: candidate PR heads replay dispatcher assertions at their
  inactive protocol/delivery anchor; active main replays the exact active
  delivery. The two dispatcher nodes execute exactly once and the disjoint
  remainder excludes their file.
- Guardrails: do not change production dispatcher, validator, updater, or
  activation semantics. Do not use skip, xfail, deselect, `-k`, abbreviation,
  `continue-on-error`, or a production runtime phase environment.
- Keep condition: the identity harness contains the dispatcher file at exact
  count 2, both exact node IDs, and total count 446; AST guards reject every
  skip/xfail/importorskip bypass; both local and hosted remainders contain one
  exact ignore; candidate remains unauthorized while active assertions remain
  unchanged.
- Rollback condition: either phase admits incorrect authority, a node is lost
  or duplicated, collection count drifts, CI pins drift, or verification fails.

## Scope

- In scope: dispatcher test-only phase-neutral snapshot fixture; identity
  harness count/collection; local and hosted remainder exclusions; CI pins;
  one closed SDG-012 compatibility delivery; this WP, strict DEP, claim/event,
  gate, independent review, hosted CI, and merge readback.
- Non-scope: production dispatcher/validator/updater bytes, activation proof,
  authority, task progress/ledger, product behavior, private/live data,
  production, deployment, release, billing, credentials, L2, or L3.
- Dependencies: exact clean main
  `9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0`; Issue #488; retained hosted
  RED from PR #487.
- Evidence requirement: exact hosted RED, static phase/collection assertions,
  focused candidate and active Green, exact 446-node collection, disjoint
  remainder, strict DEP, full Local Green under an external exclusive lease,
  independent review, one hosted run, and exact merge readback.

## CodeRabbit remediation v2

- PR #489 reported five valid review findings: rollback branch/worktree safety,
  two-phase rollback verification, semantic node/bypass guards, and exact proof
  state wording.
- The remediation topic is rebuilt from exact protocol base
  `9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0` on branch
  `agent/sdg012-mission-v5-dispatch-phase-isolation-v2`. It does not contain or
  descend from PR #489's stale receipt commit.
- The Builder source keeps `.sddgov/reviews/REV-SDG-012.json` absent. A fresh
  gate must bind the final source before an independent reviewer adds the only
  receipt commit.
- Pre-merge checks bind only their exact topic head. Merge/readback, proposal,
  task start, and production outcome remain post-delivery and unclaimed.
- Fresh focused and Full Local Green pass on exact rebuilt source
  `bcd2686eb9dff28365a8bd24ae600e808506885e`; a fresh independent receipt and
  hosted CI remain separate pre-merge gates.
- Security re-review found three additional fail-closed requirements. The
  per-node harness must prove one real JUnit PASS rather than accept `rc=0`
  after skip or non-strict xfail; its AST guard must reject alias, dynamic
  access, and string-spelled outcome bypasses. Rollback must bind canonical
  origin and freshly fetched exact delivery state, preserve reviewed phase
  bytes outside the repository, complete candidate/active/malformed phase proof
  before the revert, then claim only base-compatible INACTIVE proof after the
  revert. The earlier Green remains evidence for its exact source only; this
  remediation requires fresh focused and Local Green before review.

## Claim

- Agent: codex
- Claimed at: 2026-08-16T11:11:20Z
- Expires at: 2026-08-16T19:11:20Z
