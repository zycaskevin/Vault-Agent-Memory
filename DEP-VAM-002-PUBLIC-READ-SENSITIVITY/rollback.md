# Rollback

## Trigger

Rollback if valid callers regress, error responses expose content/rows, or the
new validation changes legacy non-Memory-API surfaces.

## Reversible steps

Before merge, discard only the unmerged candidate revision under the branch
and CI cost contracts; do not execute a data or production rollback. After
merge, the sole executable implementation rollback is the fail-closed
`## Guarded preparation command` in
`DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md`. It resolves exact PR
#500 merge/base/reviewed-head state, consumes the fresh L3 approval immediately
before `git revert --no-commit`, verifies the staged allowlist, and preserves
this DEP plus the earlier VAM-002 evidence packages. This DEP does not define a
second implementation rollback command.

## Data compatibility

No schema or stored-data rewrite. Valid trusted updates are canonicalized;
unknown scope/sensitivity updates are newly rejected; active VAM-002 reads of
legacy/corrupt unknown governance labels are newly denied; canonical revision
material lowercases scope, sensitivity, and status.

## Post-rollback verification

Run the focused provider/Gateway authorization tests, strict retained DEP
verification, `git diff --check`, module-size gate, and complete Local Green.
