# Work Package: SDG-007 Mission V5 Local Green isolation

## References

- Issue: #457
- SDD: `docs/decision_records/2026-08-15-mission-v5-post-sdg-activation.md`
  and `.agentic-sdd-governance/core/POLICY_KERNEL.md`
- Risk: L1

## Objective Contract

- Outcome: remove cross-file process-state contamination from the Mission V5
  Local Green gate without reducing collection, skipping tests, or weakening
  any authorization check.
- Success metric: all 75 Mission V5 nodes execute in fresh node-isolated
  processes; the closed harness reports 376/376 PASS; the disjoint remainder
  excludes exactly the already-executed Mission V5 file.
- Guardrails: preserve canonical five, v1-v4, T-001 through T-003, sequence-6
  progress, Mission task scope, activation path closure, private verifier
  semantics, and all L2/L3 prohibitions. The previous Mission proof is not
  reused after this trust-root change.
- Keep condition: collection parity is exact, every selected node runs once,
  no skip/xfail is introduced, hosted CI pins the new harness/runner/test bytes,
  and the SDG-007 release checker denies hidden add/delete or extra paths.
- Rollback condition: collection drift, missing/duplicate node, authorization
  acceptance change, release-scope expansion, Local Green failure, or hosted
  gate failure.

## Scope

- In scope: Mission V5 test routing in `.sddgov/ci-cost-guard.json`; the
  existing identity isolation harness; one exact SDG-007 compatibility release
  checker and regression; CI byte pins; this Work Package, strict DEP, gate,
  review receipt, hosted CI, and exact merge readback.
- Non-scope: Mission activation, a new proof, T-004 start, task output,
  canonical rebaseline, frozen predecessor edits, private/live data,
  production, deployment, release, Billing, credentials, provider consoles,
  destructive operations, or L2/L3 actions.
- Dependencies: merged SDG-006 PR #480 at
  `b1b0be02087f42b222d1de1731ff9dffa4676bf3` and the failed SDG-005 v2
  protected-review Local Green evidence.
- Evidence requirement: deterministic RED, 75-node collection proof, original
  failing node GREEN, 376-node harness GREEN, strict DEP, full Local Green,
  independent protected review, hosted CI, and exact two-parent merge readback.
- Verification plan: targeted Mission V5 tests, exact collection parity,
  complete node-isolated harness, disjoint remainder, Ruff, Python 3.10 grammar,
  diff check, doctor, CI Cost Guard, full Local Green, fresh reviewer receipt,
  one hosted run, and release checker readback.

## Claim

- Agent: codex
- Claimed at: 2026-08-16T02:02:20Z
- Expires at: 2026-08-16T10:02:20Z
