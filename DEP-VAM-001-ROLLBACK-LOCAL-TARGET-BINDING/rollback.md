# Rollback

## Trigger

The new local branch/head guard rejects a documented valid post-merge checkout
or the regression assertion fails on unchanged approved wording.

## Reversible steps

Revert only the local-target-binding remediation commit and its audit-only gate
commit. Keep PR #498 blocked until another independently reviewed guard exists.

## Data compatibility

No runtime, schema, database, or stored-memory change exists.

## Post-rollback verification

Run the focused VAM-001 documentation tests, all strict VAM-001 DEPs, complete
Local Green, and independent review against the replacement exact head.
