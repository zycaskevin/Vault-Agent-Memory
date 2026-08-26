# Fix Scope

## Smallest sufficient change

Add one canonical 14-item disposition list, make historical rollback and
reproduction commands executable and pinned, and add a current binding test.
For artifacts with unavailable raw source, preserve the historic record and
replace only its present-day claim with fresh successor evidence.
Historical evidence must not be rewritten without its raw source.

## Files or components in scope

- `DEP-VAM-002-CODERABBIT-FINAL14-REMEDIATION/`
- `DEP-VAM-002-FULL-SUITE-COMPATIBILITY/`
- `DEP-VAM-002-CODERABBIT-CURRENT-HEAD-REMEDIATION/`
- `DEP-VAM-002-CODERABBIT-REPLACEMENT-REVIEW-REMEDIATION/`
- `DEP-VAM-002-BUILDER-LOCAL-GREEN-PATH/`
- `DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/`
- `tests/test_vault_boundary_freeze.py`

## Explicit non-scope

No Vault runtime/API logic, database schema, data migration, scope or
sensitivity behavior, shared install, external review, push, signing, trust
change, merge, release, deployment, Hermes, or production-data access.

## Blast radius

Documentation and proof-chain only. The new test reads repository files and
does not contact a service or mutate data.
