# Rollback

## Trigger

The remote URL is not exact, `origin/main` differs from the current PR base,
detached HEAD differs from the current PR head, the worktree is not clean, or
any subsequent gate fails.

## Reversible steps

1. Do not run Local Green, push, sign, or merge.
2. Delete only the disposable clone's remote-tracking ref or discard the
   explicitly resolved temporary clone after checking it contains no unrelated
   files or Reviewer private identity.
3. Preserve this DEP and open a successor DEP for any new failure.

## Data compatibility

Remote-tracking refs are local metadata. No product data, schema, API, frozen
baseline, Reviewer key, or shipped artifact is modified.

## Post-rollback verification

Confirm the GitHub PR branch, main branch, tracked worktrees, trust variable,
and Review receipt remain unchanged; confirm only the explicitly selected
disposable clone metadata was removed if cleanup occurred.
