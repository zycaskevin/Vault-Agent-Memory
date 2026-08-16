# Work Package: SDG-008 large-file identity isolation

## References

- Issue: #457
- SDD: `docs/decision_records/2026-08-15-mission-v5-post-sdg-activation.md`
  and `.agentic-sdd-governance/core/POLICY_KERNEL.md`
- Risk: L1

## Objective Contract

- Outcome: remove shared-filesystem identity interference from the immutable
  T-001 baseline-control suite without modifying its validator or tests.
- Success metric: all 53 baseline-control nodes execute in fresh node-isolated
  processes; the closed harness reports 430/430 PASS; the disjoint remainder
  excludes exactly files already executed by the harness.
- Guardrails: preserve the exact T-001 validator and baseline-control test
  hashes, canonical five, v1-v4, T-001 through T-003, sequence-6 progress,
  Mission scope, private-verifier semantics, and all L2/L3 prohibitions. Any
  Mission proposal bound to the prior protocol base is not reused.
- Keep condition: collection parity is exact, every selected node runs once,
  no skip/xfail is introduced, hosted CI pins the new harness/runner/test bytes,
  and the SDG-008 release checker denies hidden add/delete or extra paths.
- Rollback condition: frozen-byte drift, collection mismatch, missing/duplicate
  node, authorization acceptance change, Local Green failure, or hosted failure.

## Scope

- In scope: baseline-control routing in `.sddgov/ci-cost-guard.json`; the
  existing identity isolation harness; one exact SDG-008 compatibility-release
  checker and regression; CI pins; this Work Package, strict DEP, gate, review
  receipt, hosted CI, and exact merge readback.
- Non-scope: edits to `scripts/validate_subject_evidence.py` or
  `tests/test_subject_baseline_control.py`; Mission activation; a new proof;
  T-004 work; canonical rebaseline; predecessor history; private/live data;
  production, deployment, release, Billing, credentials, provider consoles,
  destructive operations, or L2/L3 actions.
- Dependencies: merged SDG-007 PR #481 at
  `6d499e41ac41b8cd0f560146b0f18939b55a5f3f` and failed SDG-005 v2
  protected-review Local Green evidence.
- Evidence requirement: exact failure record, 53-node collection proof,
  original failing node GREEN, 430-node harness GREEN, frozen-byte proof,
  strict DEP, full Local Green, independent protected review, hosted CI, and
  exact two-parent merge readback.
- Verification plan: baseline-control collection and file, SDG-008 release
  checker, Local Green routing, complete node-isolated harness, disjoint
  remainder, Ruff, Python 3.10 grammar, diff check, doctor, CI Cost Guard,
  full Local Green, fresh reviewer receipt, one hosted run, and merge readback.

## Claim

- Agent: codex
- Claimed at: 2026-08-16T03:40:50Z
- Expires at: 2026-08-16T11:40:50Z
