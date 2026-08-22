# Rollback

## Trigger

Hosted verification still reports a digest mismatch, or the pinned environment
does not reproduce the declared gate value.

## Reversible steps

Do not restore the incorrect digest. Keep the PR blocked, open a new DEP, and
replace only the audit metadata after a canonical digest is proven.

## Data compatibility

No runtime, schema, database, or stored-memory compatibility impact exists.

## Post-rollback verification

Recalculate under the exact CI contract, strictly verify all VAM-001 DEPs, run
complete Local Green and hosted CI, and obtain a fresh independent receipt.
