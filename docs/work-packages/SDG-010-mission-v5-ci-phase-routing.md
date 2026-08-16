# Work Package: SDG-010 Mission V5 CI phase routing

## References

- Issue: #457
- Failure record: PR #483, Release Readiness CI governance merge gate
- SDD: `docs/decision_records/2026-08-15-mission-v5-post-sdg-activation.md`
  and `.agentic-sdd-governance/core/POLICY_KERNEL.md`
- Risk: L1

## Objective Contract

- Outcome: make hosted CI evaluate an unmerged Mission V5 activation topic as
  a closed preliminary state, while main evaluates the unchanged exact
  two-parent delivery predicate as active.
- Success metric: a proof-present linear topic passes the preliminary control
  only with the exact protocol base, proof, closed activation paths, and
  protected SDG review; it remains inactive with zero authorized tasks. The
  same topology fails active validation until one exact two-parent merge.
- Guardrails: preserve `validate_mission_activation_delivery`, its exact
  two-parent invariant, identity isolation, merge verification for ordinary
  pull requests, canonical five, v1-v4, T-001 through T-003, and all L2/L3
  boundaries. Preliminary phase never reaches updater or task-action gates.
- Keep condition: phase is an explicit `--phase preliminary|active` CLI value
  with abbreviation disabled; GitHub event routing supplies literal arguments;
  no skip, xfail, `continue-on-error`, or uncontrolled environment selector is
  introduced.
- Rollback condition: a topic can become active without the exact merge, a
  preliminary topic accepts extra/replaced/pending paths, a protected review
  is bypassed, identity collection changes, or Local Green/hosted CI fails.

## Scope

- In scope: Mission V5 preliminary topic validator; phase-aware identity
  harness CLI; CI and Local Green routing; protected workflow/test pins; this
  Work Package, strict DEP, SDG records, review receipt, hosted CI, and merge
  readback.
- Non-scope: Mission activation proof, task execution, progress ledger,
  updater/dispatcher authorization semantics, canonical rebaseline,
  predecessor history, private/live data, production, deployment, release,
  Billing, credentials, provider consoles, destructive work, L2, or L3.
- Dependencies: current `origin/main`
  `46690372e532c50761f9232ff5b2e20e18779d28`; the reviewed #483 failure
  observation; SDG-008 merge.
- Evidence requirement: retained hosted RED record, topic/active negative
  tests, malformed phase rejection, identity collection parity, focused Green,
  strict DEP, full Local Green under an external exclusive test lease,
  independent protected review, one hosted run, and exact merge readback.

## Claim

- Agent: codex
- Claimed at: 2026-08-16T07:00:05Z
- Expires at: 2026-08-16T15:00:05Z
