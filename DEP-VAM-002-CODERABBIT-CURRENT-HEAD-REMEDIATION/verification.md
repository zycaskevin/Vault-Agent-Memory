# Verification

## Green command and result

The exact repo-relative VAM-002 focused command recorded in
`shareable/artifacts/terminal--current-head-green.txt` passed 22 tests. The
real HTTP loopback candidate-first snapshot node passed 1 test. Ruff over all
ten PR-changed Python files and `git diff --check` both returned zero.

## Before/after evidence

RED: the two-node command failed because whitespace returned the synthetic high
fixture and a one-row page performed two 100-row policy scans. Green: the same
boundaries pass after trim-before-default and one `limit + 1` policy query; an
additional matrix proves the SQL predicate matches the canonical read policy
for public/shared/private/restricted and owner/allowlist cases.

## Remaining limitations

The SQL result set is bounded to `limit + 1`; as with any ordered database
query, SQLite may inspect index/table pages internally. No public cursor or
error contract is changed. A new exact-committed-head Builder Local Green is
still required before Proof, followed by gate rebind and current-head
CodeRabbit review.
