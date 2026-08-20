# Work Package: SDG-005 Mission V5 activation delivery

## References

- Issue: #457
- SDD: `docs/decision_records/2026-08-14-subject-development-mission-v5-recovery.md`
  and `.agentic-sdd-governance/core/POLICY_KERNEL.md`
- Owner-confirmed authority: proposal
  `79dfda8a4abd26fa1314bea0e8d46bcb0cfbc2d91d8e1c7631f9eb1a85029ab6`,
  receipt SHA-256
  `d7aca64a17ff670c95e1f90ddf7ebb2864ece9756ea9eda0fdf5a16ad7a163fa`,
  confirmation reference `chat:mission-v5:79dfda8a4abd26fa`
- Protocol base: merged SDG-012 PR #492 at
  `327ebe1b557fc30cbc5482a1de87e1757b8873da`
- Risk: L1

## Objective Contract

- Outcome: deliver the exact owner-confirmed Mission V5 proof through the
  already-defined closed activation package without changing authority or
  product semantics.
- Success metric: the candidate topic is mechanically preliminary and keeps
  Mission V5 inactive; one normal two-parent merge from the exact protocol
  base, with merge tree equal to its reviewed topic tree, becomes active.
- Guardrails: preserve proof bytes, canonical five, V1-V4, T-001 through
  T-003, progress sequence 6, task ledger, product code, private inputs, and
  all L2/L3 boundaries. A PR head never grants task authority.
- Keep condition: proof SHA-256 remains
  `f1c38461dd4639c50f82bd9ddc39029d8a8a02f63fbbedc6cce2df9461ec2465`,
  every activation path/action/mode is exact, review is independent, and
  active replay succeeds only after the reviewed two-parent merge.
- Rollback condition: proof drift, premature activation, wrong parent/order
  or tree, extra path, hidden add/delete, action/mode drift, gate/receipt
  drift, or any required verification failure.

## Scope

- In scope: exact immutable proof; this Work Package; strict public-safe DEP;
  claim/event; merge gate; independent protected-file review; candidate
  replay; hosted CI; and post-merge active readback.
- Non-scope: proof replacement, runner/test changes, progress/ledger mutation,
  T-004 implementation, product behavior, canonical rebaseline, private/live
  data, production, deployment, release, billing, credentials, provider
  consoles, destructive operations, L2, or L3.
- Dependencies: Issue #457 owner authority; clean canonical `origin/main`
  `327ebe1b557fc30cbc5482a1de87e1757b8873da`; exact generated proof bytes;
  existing activation validator and topology regressions.
- Evidence requirement: byte-identical proof; closed 16-path static audit;
  candidate preliminary replay; focused activation regressions; strict DEP;
  full Local Green under an exclusive lease; independent review; one hosted
  run; exact merge readback; and post-merge active dispatcher replay.

## Claim

- Agent: codex
- Claimed at: 2026-08-20T05:38:43Z
- Expires at: 2026-08-20T13:38:43Z
