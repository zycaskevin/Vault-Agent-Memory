# Verification

## Green command and result

The exact targeted command below passed 2 tests in 0.09 seconds:

`python -m pytest -q tests/test_vault_boundary_freeze.py::test_vam002_replacement_review_findings_have_current_reproducible_records tests/test_vault_boundary_freeze.py::test_vam002_rollback_is_executable_and_fail_closed_under_optimized_python`

Ruff on `tests/test_vault_boundary_freeze.py`, non-strict DEP verification,
and `git diff --check` also passed. Exact implementation-commit Local Green is
required before Proof.

## Before/after evidence

Before: exact equality rejected governed audit descendants. After: the guard
requires ancestry and proves the residual path set is empty after excluding
only the merge gate and exact VAM-002 receipt.

## Remaining limitations

Execution still requires the fresh L3 authorization and every other guard in
the authoritative rollback. This DEP does not authorize rollback execution.
TODO
