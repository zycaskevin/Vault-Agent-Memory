# Fix Scope

## Smallest sufficient change

For every fresh private Builder or Reviewer clone, fetch GitHub `main` into the
explicit `refs/remotes/origin/main` selector and fail closed unless it equals
the PR's exact current base SHA. Separately assert detached `HEAD` equals the PR
head and the complete worktree is clean before running Local Green.

## Files or components in scope

- Local Builder/Reviewer checkout preparation
- This DEP and the PR #498 merge-gate evidence binding
- Read-only GitHub base/head lookup and Git remote-tracking refs

## Explicit non-scope

- No source, test, frozen Subject, Memory Layer, API, schema, runtime, or
  acceptance-criteria change
- No retry of the consumed Builder Local Green
- No Push, receipt, signature, or Merge while the exact pre-push gate is red

## Blast radius

Local review infrastructure only. Fetching the exact remote-tracking ref does
not change the checked-out tree, production, Vault data, or shipped artifacts.
