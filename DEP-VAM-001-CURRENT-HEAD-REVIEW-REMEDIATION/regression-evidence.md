# Regression Evidence

## Regression test added or strengthened

The rollback-order test now checks exactly two parents, target ancestry from
parent 2, non-ancestry from parent 1, and all later mutation guards in order.

## Related tests executed

The focused suite passed 58 tests; the canonical progress validator, Ruff, diff
check, and strict supplemented-DEP verification passed. Complete Local Green
passed all 446 isolated Subject nodes and 2,928 repository tests with 10 skips.

## Unaffected paths sampled

Frozen Subject/runtime, product API/database, Issue state, and stored data remain
unchanged.
