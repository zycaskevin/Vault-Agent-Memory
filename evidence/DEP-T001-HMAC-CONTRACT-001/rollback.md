# Rollback

## Trigger

Focused review finds an ambiguity, contradiction, weaker privacy boundary,
unbounded resource path, or baseline closure mismatch.

## Reversible steps

Abandon the local repair branch/worktree. The original T-001 candidate worktree
and pre-reauthorization stash remain untouched. Do not reuse any proposal bound
to either superseded canonical state.

## Data compatibility

No data migration or runtime schema change occurs. The change is normative
documentation plus a content-addressed manifest only.

## Post-rollback verification

Validate the original baseline at its original commit and confirm the preserved
candidate inventory/stash still exists. A rollback does not restore authority
to an expired or consumed proposal.
