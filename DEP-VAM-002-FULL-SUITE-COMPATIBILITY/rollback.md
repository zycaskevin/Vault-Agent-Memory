# Rollback

## Trigger

Rollback the compatibility fix if malformed-label reads become allowed, known
authorization diagnostics change, or the HTTP regression no longer proves
candidate-first requests leave active knowledge unchanged.

## Reversible steps

Before merge, revert only the eventual compatibility implementation commit and
restore this DEP and merge-gate binding together. Do not revert earlier VAM-002
security fixes or any merged VAM-001/VAM-003 history.

## Data compatibility

No schema or stored data changes are introduced. The reason-code adjustment is
response diagnostic cleanup for an already-denied malformed row.

## Post-rollback verification

Run the two named regression nodes, the adjacent governance-read tests,
`git diff --check`, and the repository governance verification. Confirm the
worktree is clean and no untracked rollback artifact remains.
