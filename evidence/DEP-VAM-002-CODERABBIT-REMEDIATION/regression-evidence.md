# Regression Evidence

## Regression test added or strengthened

`tests/test_memory_change_envelope.py` now requests 81 lines, traces the SQLite
statements across more than one policy batch, and proves that content/audit
hydration is restricted to selected ids. `tests/test_gateway.py` verifies both
the OpenAPI string contract and HTTP-path preservation of an opaque reference.

## Related tests executed

- Provider, Gateway, and Change Envelope suite: 42 passed.
- Ruff on all changed Python files: passed.
- Module size gate: passed without raising a baseline.
- Complete local governance gate: 446 identity-isolated nodes passed, followed
  by 2,930 repository tests passed with 10 skips and one pre-existing warning.

## Unaffected paths sampled

Existing numeric SQLite ids, legacy non-revision reads, policy-denied private
rows, cursor policy binding, stale revision denial, candidate-first writes,
HTTP routing, and the unchanged 80-line provider ceiling remain covered by the
focused suite.
