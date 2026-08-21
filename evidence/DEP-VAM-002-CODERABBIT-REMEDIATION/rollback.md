# Rollback

## Trigger

Rollback if numeric legacy reads regress, policy filtering leaks a hidden row,
cursor behavior changes, content/audits are hydrated beyond selected readable
rows, or the 80-line ceiling is weakened.

## Reversible steps

An explicitly approved operator may revert only VAM-002 review-fix commit
`5dd09ef8e2c15800fc8ff750afb51a5e542feb2e`. Keep the earlier Draft PR
isolated; do not alter tables, data rows, reviewer metadata, releases, or
deployments.

## Data compatibility

No schema or stored-data change is planned. Opaque identifiers remain API
strings; the SQLite adapter continues to decode its current decimal format.

## Post-rollback verification

Run focused envelope/Gateway tests, OpenAPI assertions, SQL-trace regression,
the complete local governance gate, and strict verification of both VAM-002
DEPs.
