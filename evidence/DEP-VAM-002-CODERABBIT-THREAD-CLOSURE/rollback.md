# Rollback

## Trigger

The Markdown line again begins with `#500`, the regression fails, or the
authoritative rollback stops preserving this DEP.

## Reversible steps

For an unmerged, local diagnostic only, require a fresh exact owner
authorization before any additional non-sandbox Local Green; the CI cost guard
still forbids an unsupported same-revision retry. Revert only immutable
documentation/test commit `8847f94a58acc81a5e1b18357a6cbf50d00a35a7`
without committing, then restore this DEP from the proof head so the audit
record remains available. Do not commit or push that candidate under this
procedure. After merge, do not use this local procedure: use only the
approval-consuming guarded implementation rollback in
`DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md`.

## Data compatibility

No schema, API, runtime, or stored-data change exists. Rollback affects only
documentation rendering and its regression assertion.

## Post-rollback verification

Rerun the focused regression, `git diff --check`, strict DEP verification, and
the repository Local Green Gate at the exact rollback candidate.
