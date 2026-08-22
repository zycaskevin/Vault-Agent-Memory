# Verification

## Green command and result

`/tmp/vam-python-path-vam001/python -m pytest -q
tests/test_vault_boundary_freeze.py tests/test_agent_setup.py
tests/test_cli_extended.py` passed: 230 tests in 5.70 seconds.

## Before/after evidence

Before: 5 focused failures identified all three stale documents, the verifier
record mismatch, and fail-open rollback guards. After: 17 boundary/rollback
tests and the 230-test VAM-003 focused suite pass, including optimized-Python
negative probes.

## Remaining limitations

The complete Builder Local Green passed at exact committed and gate-bound head
`26519313d479b6bb240ec1f815dcac5f950f53b4` before its push: 446 isolated
Subject nodes passed, followed by 2,946 passed, 10 skipped, and one already
dispositioned warning. Independent review and receipt signing remain separate
protected-file gates.
