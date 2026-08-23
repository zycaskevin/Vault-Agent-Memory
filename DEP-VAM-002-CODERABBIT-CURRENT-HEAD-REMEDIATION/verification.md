# Verification

## Green command and result

The exact repo-relative VAM-002 focused command recorded in
`shareable/artifacts/terminal--current-head-green.txt` passed 22 tests. The
real HTTP loopback candidate-first snapshot node passed 1 test. Ruff over all
ten PR-changed Python files and `git diff --check` both returned zero.

The single authorized non-sandbox Builder Local Green then passed at exact
committed head `5efde41f1a1846439f81a10c928687388b0f15fd`: Doctor, CI contract,
README smoke, and release parity returned zero; 446 identity-isolated Subject
nodes passed; repository pytest reported 2969 passed, 10 skipped, and one
existing warning. Post-run HEAD, clean worktree, 1443 tracked physical modes,
Frozen Subject diff, and `git diff --check` were exact.

## Before/after evidence

RED: the two-node command failed because whitespace returned the synthetic high
fixture and a one-row page performed two 100-row policy scans. Green: the same
boundaries pass after trim-before-default and one `limit + 1` policy query; an
additional matrix proves the SQL predicate matches the canonical read policy
for public/shared/private/restricted and owner/allowlist cases.

## Remaining limitations

The SQL result set is bounded to `limit + 1`; as with any ordered database
query, SQLite may inspect index/table pages internally. No public cursor or
error contract is changed. Gate rebind, public branch push, current-head
CodeRabbit review, and independent Reviewer receipt remain separate steps; this
proof authorizes none of them.
