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
  count 2 and total count 446; both local and hosted remainders contain one
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

## Claim

- Agent: codex
- Claimed at: 2026-08-16T11:11:20Z
- Expires at: 2026-08-16T19:11:20Z
