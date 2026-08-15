# Work Package: SDG-006 Mission V5 verifier compatibility

## References

- Issue: #474
- SDD: `docs/decision_records/2026-08-14-subject-development-mission-v5-recovery.md`,
  `docs/decision_records/2026-08-15-mission-v5-post-sdg-activation.md`, and
  `.agentic-sdd-governance/core/POLICY_KERNEL.md`
- Risk: L1

## Objective Contract

- Outcome: allow the Mission V5 private lifecycle to survive unrelated
  directory membership churn in a shared macOS temporary ancestor while
  retaining fail-closed private-file and directory-object replacement checks.
- Success metric: a deterministic unrelated-sibling RED becomes GREEN; private
  receipt replacement, external-root inode replacement, extra release paths,
  and hidden add/delete history remain DENY.
- Guardrails: preserve the canonical five, v1-v4, T-001 through T-003, the
  sequence-6 ledger, private verifier bytes, authorization schema, task scope,
  and all L2/L3 boundaries. The expired proposal `838274470113d37a...` is not
  reused.
- Keep condition: only Mission V5 uses the versioned compatibility audit;
  frozen v1 bytes remain unchanged and exact private files retain full identity,
  exact bytes, mode, link count, descriptor/path audit, and cleanup.
- Rollback condition: any accepted file/path replacement, protocol-release
  scope drift, private cleanup regression, or required gate failure.

## Scope

- In scope: the Mission V5 private-lifecycle audit wrapper, the exact post-SDG-004
  compatibility release closure, deterministic RED/GREEN and hostile replacement
  tests, this Work Package, one strict public-safe DEP, governance gate records,
  and independent protected review.
- Non-scope: Mission activation, T-004 implementation, canonical rebaseline,
  frozen v1-v4 edits, private/live data, production, deployment, release,
  Billing, credentials, provider consoles, destructive operations, or product
  behavior changes.
- Dependencies: merged SDG-004 PR #478 at
  `d2b62eea0f130df7e02aa230f3592e28fd118617` and owner-approved Mission V5
  protocol decision.
- Evidence requirement: deterministic RED/GREEN proof, strict DEP, doctor, CI
  Cost Guard, full Local Green, independent protected review, one hosted CI run,
  and exact merge readback.
- Verification plan: focused Mission V5 tests, full protected-file regression,
  Ruff, Python 3.10 grammar, `git diff --check`, `sddgov doctor .`,
  `sddgov ci verify .`, `sddgov ci local-gate .`, and a fresh reviewer receipt.

## Claim

- Agent: codex
- Claimed at: 2026-08-15T16:10:57Z
- Expires at: 2026-08-15T20:10:57Z
