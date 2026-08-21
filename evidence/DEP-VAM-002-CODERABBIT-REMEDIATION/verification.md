# Verification

## Green command and result

At remediation commit `5dd09ef8e2c15800fc8ff750afb51a5e542feb2e`,
`python -m pytest -q tests/test_memory_change_envelope.py
tests/test_memory_provider.py tests/test_gateway.py` passed 42 focused tests.
The two remediation tests account for the increase from the original 40-test
focused run. Ruff and `python scripts/module_size_gate.py` also passed.

`umask 022 && PATH=$PYTHON_SHIM:$USER_BIN:/usr/local/bin:/usr/bin:/bin sddgov
ci local-gate .` passed at the same commit: 446 identity-isolated nodes, then
2,930 repository tests with 10 skips and one pre-existing deprecation warning.
The focused tests and the separately reported 12-test
`tests/test_deployment_positioning_docs.py` run are subsets of this full suite;
they are not added to 2,930. The full-suite count increased from 2,928 to 2,930
because the remediation added two test nodes.

## Before/after evidence

Before: three focused assertions failed for the unbounded policy scan, integer
OpenAPI contract, and Gateway coercion. After: the same assertions pass; the
81-line request continues to fail closed at `max_lines=80`.

## Remaining limitations

- SQLite still decodes only its documented decimal opaque-id representation.
- The envelope represents current state, not historical content snapshots.
- Hosted CI and independent re-review remain required for the corrected exact
  head before merge.
