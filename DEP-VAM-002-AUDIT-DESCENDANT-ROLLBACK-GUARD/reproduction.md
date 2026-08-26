# Reproduction

## Expected

The authoritative rollback must prove that the merge commit's second parent
descends from the reviewed head and that every byte between them is limited to
`.sddgov/merge-gate.json` and `.sddgov/reviews/REV-VAM-002.json`. This matches
the governance verifier's audit-descendant contract while rejecting arbitrary
post-review code or evidence changes.

## Actual

The rollback used exact equality between the gate's reviewed head and the merge
second parent. A legitimate gate-only and receipt-only descendant therefore
failed the guard even though the hosted verifier explicitly permits it.

## Deterministic steps

Run:

`python -m pytest -q tests/test_vault_boundary_freeze.py::test_vam002_replacement_review_findings_have_current_reproducible_records`

RED result: one failed test. The oracle reported
`F11_reviewed_head_ancestry`, `F11_missing_audit_only_diff`, missing exact gate
and receipt exclusions, and `F11_exact_parent_rejects_audit_descendants`.

## Environment and preconditions

Clean local branch at exact evidence head
`26d3d03712c7008d0a7dda7eb749612cb5cdc0d3`; only the test oracle was changed
before the RED run. No network, database, live Hermes, trust, receipt, merge, or
deployment action was involved.
