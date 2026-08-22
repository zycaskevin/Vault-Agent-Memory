# Root Cause Hypothesis

## Hypothesis

The rollback contract bound the remote merge object but omitted the local
checkout as a second mutation target.

## Supporting evidence

The command resolved `merge_oid` and checked ancestry, then executed
`git revert` without a `main` branch or local `HEAD` equality guard.

## Contradicting evidence

The clean-worktree guard limits unrelated edits but does not identify which
branch or commit is checked out.

## Falsification test

Require local branch `main` and `git rev-parse HEAD == merge_oid` before the
approval-consuming autonomy evaluation and revert, then assert the guard order.

## Conclusion

Confirmed. The smallest sufficient fix is a fail-closed local branch/head
binding plus a regression assertion on its position before approval and revert.
