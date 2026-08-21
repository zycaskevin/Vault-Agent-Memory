# Rollback

## Trigger

Rollback if numeric legacy reads regress, policy filtering leaks a hidden row,
cursor behavior changes, content/audits are hydrated beyond selected readable
rows, or the 80-line ceiling is weakened.

## Reversible steps

Revert only the VAM-002 review-fix commit. Keep the earlier Draft PR isolated;
do not alter tables, data rows, reviewer metadata, releases, or deployments.

## Data compatibility

No schema or stored-data change is planned. Opaque identifiers remain API
strings; the SQLite adapter continues to decode its current decimal format.

## Post-rollback verification

Run focused envelope/Gateway tests, OpenAPI assertions, SQL-trace regression,
the complete local governance gate, and strict verification of both VAM-002
DEPs.
