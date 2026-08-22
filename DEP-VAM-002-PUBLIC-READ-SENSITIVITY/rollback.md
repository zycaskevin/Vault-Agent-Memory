# Rollback

## Trigger

Rollback if valid callers regress, error responses expose content/rows, or the
new validation changes legacy non-Memory-API surfaces.

## Reversible steps

Before merge, revert the bounded implementation and its gate together. After
merge, use only the executable guarded PR #500 rollback while preserving this
DEP and the earlier VAM-002 evidence packages.

## Data compatibility

No schema or stored-data rewrite. Valid trusted updates are canonicalized;
unknown scope/sensitivity updates are newly rejected; active VAM-002 reads of
legacy/corrupt unknown governance labels are newly denied; canonical revision
material lowercases scope, sensitivity, and status.

## Post-rollback verification

Run the focused provider/Gateway authorization tests, strict retained DEP
verification, `git diff --check`, module-size gate, and complete Local Green.
