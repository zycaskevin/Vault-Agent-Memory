# Rollback

## Trigger

The fast-forward introduces any failure beyond the known lifecycle repair or
changes a file outside the reviewed upstream commit.

## Reversible steps

Do not rewrite or reset the dirty worktree. Preserve user files and create a
new local branch at the pre-fix commit for comparison; any actual rollback of
the current branch requires an explicit, non-destructive plan.

## Data compatibility

No data or runtime format changes.

## Post-rollback verification

Run the original focused lifecycle test and compare `git diff --name-status`
against the exact upstream repair.

Rollback was not required: the focused and full gates passed.
