# Fix Scope

## Smallest sufficient change

Add the immutable 53-node baseline-control test file to the existing per-node
isolation harness and exclude exactly that already-executed file from the
shared remainder. Add a closed SDG-008 release checker so the independently
reviewed merge can become the next legal Mission protocol base.

## Files or components in scope

- `.sddgov/ci-cost-guard.json` and
  `scripts/run_subject_identity_test_isolation.py`.
- `scripts/run_subject_development_mission_v5.py` and its test file.
- Hosted CI byte pins plus SDG-008 Work Package, strict DEP, gate, receipt.

## Explicit non-scope

No modification to `scripts/validate_subject_evidence.py` or
`tests/test_subject_baseline_control.py`; no skip/xfail, collection reduction,
authorization semantic change, canonical five, v1-v4, T-001 through T-003,
sequence-6 ledger, task scope, activation, T-004 output, private/live data,
production, release, Billing, credentials, provider consoles, destructive,
L2, or L3 action.

## Blast radius

Local and hosted test execution topology plus exact protocol-release ancestry.
Product runtime, persisted Subject state, and immutable T-001 bytes are unchanged.
