# Rollback

## Trigger

The claim points at the wrong Work Package, has the wrong Agent, or blocks a
different active claim.

## Reversible steps

Allow the bounded claim to expire or use the governance claim lifecycle to
replace it with the correct non-overlapping record. Do not hand-edit an active
claim to bypass ownership.

## Data compatibility

The record is coordination metadata only; no product or user data is affected.

## Post-rollback verification

Run `sddgov status .` and verify no stale active claim remains.
