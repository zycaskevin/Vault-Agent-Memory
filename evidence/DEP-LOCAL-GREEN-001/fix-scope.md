# Fix Scope

## Smallest sufficient change

Fast-forward the local branch from `3e30a99` to `origin/main` at `599bba4`,
thereby incorporating the already reviewed single-file repair `536934c`.

## Files or components in scope

`tests/test_subject_authorization_bootstrap.py` and Git ancestry only.

## Explicit non-scope

No T-001 candidate bytes, product runtime, schemas, dependencies, CI workflows,
remote branches, PRs, deployments, releases, or billing operations.

## Blast radius

Test-only authorization lifecycle boundary. The new HEAD invalidates the old
T-001 exact-base delivery authority; the existing proof remains historical and
must not authorize delivery from the new base.
