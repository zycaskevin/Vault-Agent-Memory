# Regression Evidence

## Regression test added or strengthened

The VAM-001 documentation contract now asserts remote merge resolution,
compatibility ancestry, local `main`, exact local HEAD, approval evaluation, and
revert appear exactly once in fail-closed order.

## Related tests executed

The focused suite passed 57 tests; the canonical progress validator, Ruff, and
`git diff --check` also passed. Complete Local Green passed all 446 isolated
Subject nodes and 2,927 repository tests with 10 skips. The single pre-existing
`DeprecationWarning` is the invalid escape sequence in
`tests/test_semantic_chunk_coverage.py`; it does not affect this documentation
boundary and remains separately visible rather than being suppressed.

Supplemental redacted artifacts bind the final run to branch
`codex/vam-001-subject-extraction-adr`, exact head `b2c8378`, tracked-clean
state, the known untracked attach file, and clarify that the pre-fix risk was
mutation of the wrong checkout's index and working tree rather than a branch
reference mutation.

## Unaffected paths sampled

Frozen Subject specs/contracts/runtime, database, Memory API, and public Issue
state remain outside the diff.
