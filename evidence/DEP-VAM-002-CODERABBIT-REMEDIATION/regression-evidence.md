# Regression Evidence

## Regression test added or strengthened

`tests/test_memory_change_envelope.py` now requests 81 lines, traces the SQLite
statements across more than one policy batch, and proves that content/audit
hydration is restricted to selected ids. `tests/test_gateway.py` verifies both
the OpenAPI string contract and HTTP-path preservation of an opaque reference.

## Related tests executed

- At commit `5dd09ef8e2c15800fc8ff750afb51a5e542feb2e`, `python -m
  pytest -q tests/test_memory_change_envelope.py tests/test_memory_provider.py
  tests/test_gateway.py`: 42 passed, up from 40 because remediation added two
  test nodes.
- `python -m pytest -q tests/test_deployment_positioning_docs.py`: 12 passed;
  these documentation tests are also part of the complete repository suite.
- Ruff on all changed Python files: passed.
- Module size gate: passed without raising a baseline.
- At the same commit, the complete gate command was `umask 022 &&
  PATH=$PYTHON_SHIM:$USER_BIN:/usr/local/bin:/usr/bin:/bin sddgov ci local-gate
  .`; 446 identity-isolated nodes passed, followed by 2,930 repository tests
  passed with 10 skips and one pre-existing warning. Focused and
  deployment-positioning counts are subsets, not additive; the full count
  increased from 2,928 when the two remediation tests were added.

## Unaffected paths sampled

Existing numeric SQLite ids, legacy non-revision reads, policy-denied private
rows, cursor policy binding, stale revision denial, candidate-first writes,
HTTP routing, and the unchanged 80-line provider ceiling remain covered by the
focused suite.

Follow-up commit `a3be45e272f126a96d519cffc6ea59027055a3e5` added one
concurrent-writer snapshot test and strengthened the existing OpenAPI test. The
focused suite passed 43 tests, and full Local Green passed 446 isolated identity
nodes plus 2,931 repository tests / 10 skips / 1 pre-existing warning. The one
node increase from 2,930 is the new snapshot test; the OpenAPI assertion does
not add a node.
