# Regression Evidence

## Regression test added or strengthened

`tests/test_memory_object_contract.py` covers the exact kind/capability boundary,
legacy mapping, provider candidate-first adapters, Gateway aliases, invalid-kind
pre-write rejection, OpenAPI/provider parity, and VAM-002 canonical mapping.

## Related tests executed

- MemoryObject/provider/Gateway/VAM-002 focused suite: 45 passed.
- Deployment-positioning docs: 12 passed.
- Changed-Python Ruff: passed.
- Full Local Green: 446 identity-isolated nodes plus 2933 passed / 10 skipped.

## Unaffected paths sampled

The full gate exercised existing CLI, MCP, Gateway, installer, sync, search,
candidate, governance, release parity, README smoke, and frozen Subject paths.
Existing `memory_type` / `trust` clients and VAM-002 cursor/evidence tests remain
Green.
