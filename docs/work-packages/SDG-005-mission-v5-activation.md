# Work Package: SDG-005 Mission V5 activation

## References

- Issue: #457
- SDD: `docs/decision_records/2026-08-14-subject-development-mission-v5-recovery.md`,
  `docs/decision_records/2026-08-15-mission-v5-post-sdg-activation.md`, and
  `.agentic-sdd-governance/core/POLICY_KERNEL.md`
- Risk: L1

## Objective Contract

- Outcome: deliver the exact owner-confirmed Mission V5 proof through the
  closed SDG-005 protected-review path and activate T-004 through T-033 only
  after one exact two-parent GitHub merge is read back on current main.
- Success metric: the unmerged topic remains INACTIVE; the exact reviewed
  two-parent merge validates ACTIVE with 30 authorized tasks; any missing,
  extra, replaced, or wrongly-modeled SDG path remains DENY.
- Guardrails: preserve the canonical five, v1-v4, T-001 through T-003,
  sequence-6 progress, Mission V5 protocol/trust-root/registry bytes, and all
  L2/L3 boundaries. Do not start T-004 in this Work Package.
- Keep condition: only the exact proof SHA-256
  `69afd990e5d7d9bdf7fde4a1f7fe97183c909855371445e49eebe50dadbab681`
  is delivered, both Mission pending paths are absent, the topic is linear, and
  activation is impossible before exact merge delivery.
- Rollback condition: any authority expansion, extra path/action/mode,
  protected-review failure, hosted CI failure, or merge readback mismatch.

## Scope

- In scope: the one Mission V5 proof, this Work Package, one strict public-safe
  DEP, SDG claim/event/gate records, one independent protected review receipt,
  one Pull Request, hosted required CI, exact two-parent merge, and post-merge
  ACTIVE readback.
- Non-scope: T-004 implementation or start; changes to runtime product code,
  canonical SDD, frozen authorization generations, task descriptors, progress
  ledger, private/live data, production, deployment, release, Billing,
  credentials, provider consoles, destructive operations, or L2/L3 actions.
- Dependencies: merged SDG-008 PR #482 at
  `46690372e532c50761f9232ff5b2e20e18779d28`; exact owner confirmation for
  proposal `8acdc645348e625cdfacf1f42ca0185c787d042654d18c31fd541c966447b2c9`;
  Mission V5 compatibility, activation-gate, phase-isolation, and large-file
  identity-isolation releases.
- Evidence requirement: strict DEP, synthetic exact-merge tests, expected live
  pre-merge DENY, doctor, CI Cost Guard, phase-correct full Local Green,
  independent protected review, one hosted CI run, and exact merge readback.
- Verification plan: run the four exact activation controls in a clean
  protocol-base clone; build and independently review the exact SDG-005 topic;
  execute Local Green and `merge verify` on an exact synthetic merge topology;
  require hosted required checks and revalidate current main after merge.

## Exact path closure

- Modify `.sddgov/events.jsonl`, `.sddgov/merge-gate.json`, and
  `.sddgov/work-claims.json`.
- Add `.sddgov/reviews/REV-SDG-005.json`, this Work Package, the eight DEP proof
  documents, one redaction report, one public artifact, and
  `specs/subject-distillation/task-authorizations/MISSION-V5-T004-T033.json`.
- All persistent paths are mode `0644`; private/raw evidence and both Mission
  pending paths remain absent from Git.

## Claim

- Agent: codex
- Claimed at: 2026-08-16T05:40:38Z
- Expires at: 2026-08-17T05:40:38Z
