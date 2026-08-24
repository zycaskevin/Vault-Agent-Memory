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
TODO
