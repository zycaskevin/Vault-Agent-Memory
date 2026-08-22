# Reproduction

## Expected

Active public guidance describes Vault as governed memory infrastructure, and
the VAM-003 rollback both satisfies the installed merge verifier contract and
fails closed when CPython optimization is enabled.

## Actual

Three public guides contained identity/profile instructions. The rollback used
unsupported version `1.1`, omitted top-level `command` and `verify`, used two
optimization-sensitive assertions, and did not reject post-mutation untracked
paths.

## Deterministic steps

From exact head `8eec35c3b228efbdfc8707a11e2d31e885002562`, add the
boundary and rollback contract tests, then run:

`/tmp/vam-python-path-vam001/python -m pytest -q tests/test_vault_boundary_freeze.py`

The Red run produced 5 failures and 12 passes. Hosted governance run
`32548900312`, job `96972271288`, independently reported `rollback record is
missing or incomplete`.

## Environment and preconditions

Branch `codex/vam-003-l0-bootstrap-boundary`, clean pre-remediation head
`8eec35c3b228efbdfc8707a11e2d31e885002562`, CPython 3.11.15, pytest 9.1.1,
isolated Builder checkout, no private fixture or network dependency.
