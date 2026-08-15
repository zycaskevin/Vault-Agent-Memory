# Work Package: SDG-003 Mission V5 post-SDG activation compatibility

## References

- Issue: #475
- SDD: `docs/decision_records/2026-08-14-subject-development-mission-v5-recovery.md`,
  `specs/subject-distillation/development-mission-v5.contract.json`, and
  `.agentic-sdd-governance/core/POLICY_KERNEL.md`
- Risk: L1

## Objective Contract

- Outcome: Permit a fresh Mission V5 proposal on the exact reviewed main after
  the SDG-001 merge without accepting arbitrary intervening history.
- Success metric: the current exact clean main passes proposal preflight while
  unauthorized commits, paths, modes, parent topology, or byte drift deny.
- Guardrails: Keep the canonical five, v1-v4, T-001 through T-003 authority
  artifacts, and the sequence-6 ledger byte-identical. Do not publish a mission
  proof or start T-004 in this Work Package.
- Keep condition: the frozen V5 bridge and exact SDG merge/receipt/gate closure
  are mechanically bound and full Local Green remains green.
- Rollback condition: any authority expansion, mixed snapshot, proof reuse,
  historical-byte drift, or required-test regression.

## Scope

- In scope: the minimum V5 trust-root compatibility code, focused regression
  tests, CI pin updates required by those exact bytes, this Work Package, and a
  strict public-safe DEP.
- Non-scope: product semantics, T-004 implementation, private/live data,
  credentials, production, deployment, release, Billing, provider consoles,
  destructive operations, and canonical rebaseline.
- Dependencies: merged PR #473 at `4c4c29a16decfeedda59b685886801f65b9fd878`
  with signed reviewed head `cbdfd04db9697bc465d1e5d4b6ab14528ef9aa0e`.
- Evidence requirement: deterministic RED/GREEN ancestry tests, strict DEP,
  doctor, CI Cost Guard, full Local Green, independent protected review, one
  hosted CI run, and merge readback.
- Verification plan: focused Mission V5 tests, `sddgov doctor .`,
  `sddgov ci verify .`, `sddgov ci local-gate .`, `git diff --check`, and
  independent review of the frozen candidate.
