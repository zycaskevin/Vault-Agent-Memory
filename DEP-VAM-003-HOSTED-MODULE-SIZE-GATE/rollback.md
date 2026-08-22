# Rollback

## Trigger

Rollback if the formatting-only source change alters runtime behavior or the
module-size gate no longer passes at the frozen allowance.

## Reversible steps

Revert the VAM-003 hosted-gate repair commit. Do not raise the module-size
baseline as part of rollback.

## Data compatibility

No data, schema, migration, or stored-memory change exists.

## Post-rollback verification

Run the module-size gate and VAM-003 focused tests; the original hosted
one-line overage is expected to reappear until another in-scope line reduction
is made.
