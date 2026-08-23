# Rollback

## Trigger

The Markdown line again begins with `#500`, the regression fails, or the
authoritative rollback stops preserving this DEP.

## Reversible steps

Revert only immutable implementation commit
`8847f94a58acc81a5e1b18357a6cbf50d00a35a7`, without committing; restore this
DEP from the proof head so the audit record remains available.

## Data compatibility

No schema, API, runtime, or stored-data change exists. Rollback affects only
documentation rendering and its regression assertion.

## Post-rollback verification

Rerun the focused regression, `git diff --check`, strict DEP verification, and
the repository Local Green Gate at the exact rollback candidate.
