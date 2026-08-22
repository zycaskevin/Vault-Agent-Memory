# Verification

## Green command and result

The focused rollback/boundary, Subject contract, and exact baseline suite passed
57 tests. The canonical progress validator returned baseline
`0dc10cfc4a429662`, sequence 8, and PASS. Ruff and `git diff --check` passed.
Complete Local Green then passed: all 446 identity-isolated Subject nodes passed,
followed by 2,927 passed and 10 skipped in the repository suite. A fresh
independent review and hosted CI remain required after the exact gate is rebound.

## Before/after evidence

Before: remote merge identity and ancestry were bound, but local mutation
identity was not. After: local branch and HEAD must match `main` and the exact
resolved merge commit before approval consumption and revert.

## Remaining limitations

This change does not authorize or execute rollback. A future rollback still
requires a fresh strict DEP and consumed L3 approval. Independent Reviewer Local
Green remains subject to its separate clean-host execution boundary.
