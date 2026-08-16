# Work Package: SDG-005 Mission V5 activation delivery

## References

- Issue: #457
- SDD: `docs/decision_records/2026-08-15-mission-v5-post-sdg-activation.md`
  and `.agentic-sdd-governance/core/POLICY_KERNEL.md`
- Owner-confirmed authority: proposal
  `8f8fc9390445cbe00b6cd4f3b31013ce0002d4b03263ca986fd2ea34a8f5cfcc`,
  receipt SHA-256
  `a35081985198c863c3f42af9b07cc9eed3d4eb5c847e8217e8cad894357addad`,
  confirmation reference `chat:mission-v5:8f8fc9390445cbe0`
- Protocol base: merged SDG-011 PR #486 at
  `9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0`
- Risk: L1

## Objective Contract

- Outcome: deliver the exact owner-confirmed Mission V5 proof through the
  already-defined closed activation package without changing authority or
  product semantics.
- Success metric: the candidate topic is mechanically `preliminary` and keeps
  Mission V5 `INACTIVE`; one normal two-parent merge from the exact protocol
  base, with merge tree equal to its reviewed topic tree, becomes `ACTIVE`.
- Guardrails: preserve the proposal/proof bytes, canonical five, v1-v4,
  T-001 through T-003, progress sequence 6, current task ledger, product code,
  private inputs, and all L2/L3 boundaries. A PR head never grants task
  authority.
- Keep condition: the exact proof SHA-256 is
  `70113552d582f5f579a0c9d01a5206ff74df678801accca59173ff76bae6d528`,
  every activation path/action/mode is exact, review is independent, and
  active replay succeeds only after the reviewed two-parent merge.
- Rollback condition: proof drift, premature activation, wrong parent/order or
  tree, extra path, hidden add/delete, action/mode drift, gate/receipt drift,
  or any required verification failure.

## Scope

- In scope: the exact immutable Mission V5 proof; this Work Package; strict
  public-safe DEP; claim/event; merge gate; independent protected-file review;
  candidate preliminary replay; hosted CI; and post-merge active readback.
- Non-scope: proposal or proof generation/replacement, runner or test changes,
  task progress/ledger mutation, T-004 implementation, product behavior,
  canonical rebaseline, private/live data, production, deployment, release,
  billing, credentials, provider consoles, destructive operations, L2, or L3.
- Dependencies: Issue #457 owner authority; exact clean `origin/main`
  `9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0`; exact external proof bytes;
  existing Mission V5 activation validator and genuine topology regressions.
- Evidence requirement: byte-for-byte proof equality; closed 16-path static
  audit; candidate preliminary replay; focused activation regressions; strict
  DEP; full Local Green under an exclusive lease; independent review; one
  hosted run; exact merge readback; and post-merge active dispatcher replay.

## Claim

- Agent: codex
- Claimed at: 2026-08-16T10:05:28Z
- Expires at: 2026-08-16T18:05:28Z
