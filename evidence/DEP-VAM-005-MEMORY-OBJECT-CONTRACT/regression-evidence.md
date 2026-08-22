# Regression Evidence

## Regression test added or strengthened

`tests/test_memory_object_contract.py` covers the exact kind/capability boundary,
legacy mapping, provider candidate-first adapters, Gateway aliases, invalid-kind
pre-write rejection, OpenAPI/provider parity, and VAM-002 canonical mapping.

## Related tests executed

- MemoryObject/provider/Gateway/VAM-002 focused suite: 45 passed at the
  implementation commit; 48 passed after integrating VAM-002 follow-up commit
  `68ddbe6`.
- Deployment-positioning docs: 12 passed.
- Full Local Green at stacked integration commit `119cf38`: 446
  identity-isolated nodes plus 2936 passed / 10 skipped / 1 pre-existing
  warning.
- Changed-Python Ruff and the module-size gate both passed after dependency
  integration.

## Unaffected paths sampled

The full gate exercised existing CLI, MCP, Gateway, installer, sync, search,
candidate, governance, release parity, README smoke, and frozen Subject paths.
Existing `memory_type` / `trust` clients and VAM-002 cursor/evidence tests remain
Green.
