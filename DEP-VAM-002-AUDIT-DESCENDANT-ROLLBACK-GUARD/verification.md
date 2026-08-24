# Verification

## Green command and result

The exact targeted command below passed 2 tests in 0.09 seconds:

`python -m pytest -q tests/test_vault_boundary_freeze.py::test_vam002_replacement_review_findings_have_current_reproducible_records tests/test_vault_boundary_freeze.py::test_vam002_rollback_is_executable_and_fail_closed_under_optimized_python`

Ruff on `tests/test_vault_boundary_freeze.py`, non-strict DEP verification,
and `git diff --check` also passed. One owner-approved exact-head Local Green
at `18ef12446c638d3c59db728a48c66924ae8a1836` passed Doctor, CI contract,
README smoke, release parity, 446 identity-isolated Subject nodes, and
repository pytest with 2972 passed, 10 skipped, and one existing warning.
Post-run HEAD, clean status, 1494 physical modes, Frozen Subject diff, and
`git diff --check` remained exact. The manifest-bound proof is
`shareable/artifacts/terminal--artifact-2.txt`.

## Before/after evidence

Before: exact equality rejected governed audit descendants. After: the guard
requires ancestry and proves the residual path set is empty after excluding
only the merge gate and exact VAM-002 receipt.

## Remaining limitations

Execution still requires the fresh L3 authorization and every other guard in
the authoritative rollback. This DEP does not authorize rollback execution.
It also does not authorize push, Reviewer trust/signing, merge, deployment, or
live Hermes/production-data changes.

## Final candidate gate disposition

The subsequent candidate `962ebf8b4d8c6a1b74a488ca4b8da2e77c09ee34`
adds only the required preservation of this DEP to the authoritative rollback
and its regression. Its single authorized Local Green was consumed and failed
closed before repository pytest at
`test_mission_activation_requires_exact_two_parent_merge_before_active` while
reading the unchanged, hash-valid, mode-0644 Frozen Subject `design.md`.

Post-run HEAD, worktree, Frozen Subject diff, and file identity remained exact.
Read-only evidence showed the identity verifier audits every absolute checkout
ancestor by device, inode, mode, size, and mtime, while a direct Codex state
file changed the `$CODEX_STATE_ROOT` ancestor during the failing-node window.
The runner erases the exact `Denied` subcondition, so the evidence is
time-aligned and strongly explanatory but not a retried reproduction. The
manifest-bound failure record is `shareable/artifacts/terminal--artifact-3.txt`.
Per that run's explicit no-retry condition, no second run was performed under
the exhausted authorization.

## Final stable exact-head proof

Under a later, separate owner authorization, a fresh 0700 clone outside the
volatile `$CODEX_STATE_ROOT` ancestor was prepared with formal GitHub origin,
exact `origin/main` base
`c284e1c7bedf288a10009b98e5f2da525c3ee4bc`, exact candidate
`f28843b1777f002b342d35449e9ce7aaf4bfc83c`, clean status, and 1496 tracked
physical modes with zero mismatches.

Its single non-sandbox repository-controlled Local Green passed Doctor, CI
contract, README smoke, release parity, all 446 identity-isolated Subject
nodes, and repository pytest with 2972 passed, 10 skipped, and one existing
warning. Post-run HEAD, clean worktree, physical modes, Frozen Subject diff,
and `git diff --check` remained exact. This closes the prior environment-only
ancestor-volatility limitation. The manifest-bound proof is
`shareable/artifacts/terminal--artifact-4.txt`.

No push, Reviewer signing, trust mutation, merge, deployment, live Hermes, or
production-data action was performed by this proof run.
