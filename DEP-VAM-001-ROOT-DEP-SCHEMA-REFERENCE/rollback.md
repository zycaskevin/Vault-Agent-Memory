# Rollback

## Trigger

The corrected selectors fail to resolve in a fresh clone, the exhaustive test
rejects a legitimate governed layout, any strict DEP regresses, or the change
touches product/frozen paths.

## Reversible steps

Revert only the schema-reference remediation implementation commit and its
following merge-gate audit commit before receipt signing. Preserve this DEP's
evidence; do not restore the invalid selectors without a replacement selector
that resolves to an existing governed schema.

## Data compatibility

Documentation metadata and a focused test only. No product data, database,
schema content, API, runtime, or Reviewer identity compatibility impact.

## Post-rollback verification

Run the exhaustive schema-reference test, all bound strict DEP checks,
`sddgov ci verify`, frozen-diff assertion, and `git diff --check`; keep Merge
blocked if any selector is unresolved.
