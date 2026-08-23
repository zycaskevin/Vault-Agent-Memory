# Fix Scope

## Smallest sufficient change

Move the independent-review rollback line break so `PR #500 procedure` remains
plain prose, add a bounded regression, and preserve this DEP in the
authoritative PR #500 rollback.

## Files or components in scope

- `DEP-VAM-002-INDEPENDENT-REVIEW-REMEDIATION/rollback.md`
- `DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md`
- `tests/test_vault_boundary_freeze.py`
- this DEP

## Explicit non-scope

No runtime Python, API, database, public contract, authorization, Hermes data,
receipt, trust configuration, merge, release, or deployment change.

## Blast radius

Documentation rendering and rollback-provenance coverage only. Product
behavior and stored data remain byte-identical.
