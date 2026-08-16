# Work Package: SDG-011 post-SDG-010 L1 compatibility

## References

- Issue: #485
- SDD: `docs/decision_records/2026-08-15-mission-v5-post-sdg-activation.md`
  and `.agentic-sdd-governance/core/POLICY_KERNEL.md`
- Predecessor delivery: PR #484, merge
  `efa43a4dfb305cd51d8a57a20838be6123ccb514`
- Risk: L1

## Objective Contract

- Outcome: extend the Mission V5 protocol-release chain across the exact
  reviewed SDG-010 delivery and one future exact SDG-011 two-parent delivery.
- Success metric: the exact SDG-010 parent order, topic, tree, closed linear
  change history, file actions, modes, merge-gate bytes, and reviewer-receipt
  bytes validate mechanically. Current `efa43a4` remains DENY; only a
  tree-equal two-parent SDG-011 merge from `efa43a4` with the exact closed path
  set can become the protocol base for a fresh Mission proposal.
- Guardrails: preserve the active Mission delivery predicate, owner-confirmed
  proof semantics, canonical five, v1-v4, T-001 through T-003, updater and
  dispatcher authority, identity isolation, and every L2/L3 boundary.
- Keep condition: wrong parent/order/tree, hidden add-delete, extra path,
  wrong action, mode drift, gate drift, receipt drift, or incomplete SDG-011
  topic all DENY.
- Rollback condition: any current SDG-010-only main passes proposal generation,
  a non-exact SDG-010 anchor passes, an SDG-011 merge accepts scope drift, the
  corrected SDG-010 rollback cannot resolve PR #484, or required verification
  fails.

## Scope

- In scope: Mission V5 protocol-release compatibility checker and regression
  tests; exact SDG-010 delivery pins; exact future SDG-011 closed merge; CI byte
  pins; correction of the already-merged SDG-010 rollback record; this Work
  Package, strict DEP, claim/event, gate, independent review, hosted CI, and
  merge readback.
- Non-scope: Mission proof creation or replacement, owner authorization,
  progress or task ledger mutation, activation delivery changes, task work,
  canonical rebaseline, private/live data, production, deployment, release,
  Billing, credentials, provider consoles, destructive operations, L2, or L3.
- Dependencies: exact `origin/main`
  `efa43a4dfb305cd51d8a57a20838be6123ccb514`; exact SDG-010 base
  `46690372e532c50761f9232ff5b2e20e18779d28`; exact topic
  `7e155ca8907b31a14d5abadeeeb73e3edac71c14`; Issue #485.
- Evidence requirement: deterministic RED for current proposal denial and
  rollback mismatch; genuine positive and negative merge fixtures; exact live
  anchor verification; exact 90-node Mission V5 collection pin; static pins;
  strict DEP; full Local Green under the external exclusive test lease;
  independent protected review; one hosted run; exact two-parent merge
  readback.

## Claim

- Agent: codex
- Claimed at: 2026-08-16T08:18:38Z
- Expires at: 2026-08-16T16:18:38Z
