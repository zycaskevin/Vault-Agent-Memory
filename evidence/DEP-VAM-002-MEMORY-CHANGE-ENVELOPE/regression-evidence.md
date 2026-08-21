# Regression Evidence

## Regression test added or strengthened

`tests/test_memory_change_envelope.py` covers deterministic full hashes and
revision ids, policy-filtered pagination, hidden-row non-disclosure, policy-bound
cursors, bounded evidence, stale revision denial, and delete tombstones.

`tests/test_gateway.py` now covers the direct and localhost HTTP changes route,
revision-bound reads, health endpoint discovery, and the OpenAPI schema.

## Related tests executed

- Provider/Gateway/change-envelope suite: 40 passed.
- Deployment-positioning docs: 12 passed.
- Changed-Python Ruff check: passed.
- Full Local Green: 446 identity-isolated nodes plus 2928 passed / 10 skipped.

## Unaffected paths sampled

The Local Green gate exercised existing CLI, MCP, Gateway, installer, sync,
search, governance, release parity, README command smoke, and frozen Subject
authorization paths. No default Gateway adapter authority changed.
