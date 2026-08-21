# Regression Evidence

## Regression test added or strengthened

The VAM-001 documentation contract now asserts remote merge resolution,
compatibility ancestry, local `main`, exact local HEAD, approval evaluation, and
revert appear exactly once in fail-closed order.

## Related tests executed

The focused suite passed 57 tests; the canonical progress validator, Ruff, and
`git diff --check` also passed. Complete Local Green passed all 446 isolated
Subject nodes and 2,927 repository tests with 10 skips.

## Unaffected paths sampled

Frozen Subject specs/contracts/runtime, database, Memory API, and public Issue
state remain outside the diff.
