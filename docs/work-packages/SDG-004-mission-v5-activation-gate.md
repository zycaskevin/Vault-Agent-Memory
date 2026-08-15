# Work Package: SDG-004 Mission V5 activation gate compatibility

## References

- Issue: #477
- SDD: `docs/decision_records/2026-08-14-subject-development-mission-v5-recovery.md`,
  `docs/decision_records/2026-08-15-mission-v5-post-sdg-activation.md`,
  `docs/decision_records/2026-08-15-mission-v5-activation-sdg-gate.md`, and
  `.agentic-sdd-governance/core/POLICY_KERNEL.md`
- Risk: L1

## Objective Contract

- Outcome: make one owner-confirmed Mission V5 activation delivery satisfy both
  the exact Mission replay and the team-standard signed Merge Gate.
- Success metric: proof-only or extra-path activation denies; the exact closed
  mission proof plus SDG-005 Work Package, strict DEP, gate, and review receipt
  passes local, hosted, and post-merge replay.
- Guardrails: preserve the canonical five, v1-v4, T-001 through T-003, the
  sequence-6 ledger, product behavior, task descriptors, and all L2/L3
  boundaries. The local proof generated before this repair is invalid and must
  not be reused.
- Keep condition: all new activation-support paths are closed, mode/action
  exact, independently reviewed, and cannot grant task authority.
- Rollback condition: any proof reuse, acceptance of a proof-only delivery,
  extra path, hidden add/delete, side merge, trust-root drift, or regression.

## Scope

- In scope: the minimum Mission V5 release and activation-delivery validators,
  genuine RED/GREEN temp-Git tests, current CI trust pin, deterministic local
  per-node process isolation for the six complete identity-sensitive suites,
  this Work Package, one decision record, and a strict public-safe DEP.
- Non-scope: Mission activation, T-004 implementation, canonical rebaseline,
  private/live data, production, deployment, release, Billing, credentials,
  provider consoles, destructive operations, or new product decisions.
- Dependencies: merged SDG-003 PR #476 at
  `3374ac372930ee6200d38c1f02289a0c8fa1eb84` and Issue #457 owner authority.
- Evidence requirement: deterministic RED/GREEN proof, strict DEP, doctor, CI
  Cost Guard, full Local Green, independent protected review, one hosted CI run,
  and exact merge readback.
- Verification plan: focused Mission V5 tests, Ruff, Python 3.10 grammar,
  `git diff --check`, `sddgov doctor .`, `sddgov ci verify .`,
  `sddgov ci local-gate .`, and a fresh protected reviewer receipt.

## Claim

- Agent: codex
- Claimed at: 2026-08-15T11:14:12Z
- Expires at: 2026-08-15T15:14:12Z
