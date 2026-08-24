# Fix Scope

## Smallest sufficient change

Replace exact-parent equality with an ancestry check and require an empty diff
after excluding only `.sddgov/merge-gate.json` and the exact VAM-002 receipt.
Strengthen the static regression and correct the predecessor DEP disposition.

## Files or components in scope

- `DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md`
- `tests/test_vault_boundary_freeze.py`
- The two successor DEP records that explain finding 11
- This bounded DEP

## Explicit non-scope

No memory runtime, API, database, write path, cursor, revision, identity model,
Reviewer trust, receipt, merge, deployment, or live Hermes data change.

## Blast radius

Post-merge rollback preparation only. The guard becomes compatible with the
existing governance audit model while remaining fail-closed for every other
path.
