# Regression Evidence

## Regression test added or strengthened

Tests cover both no-revision get adapters, both Memory API search adapters,
timeline, range overflow, OpenAPI/HTTP 400, all four provider reads without
identity, exact revision material, tombstones, and rollback preservation.

## Related tests executed

Two focused RED nodes failed deterministically at exact pre-fix head. The exact
Green command passed 19 nodes; the exact all-changed-Python Ruff command and
159-module size gate also passed. Both exact commands and outputs are retained
in the shareable Green artifact.

## Unaffected paths sampled

Existing valid sensitivity, cursor, revision, candidate-first writes, and
legacy adapter behavior remain in the later focused regression set.
