# Regression Evidence

## Regression test added or strengthened

Tests cover both no-revision get adapters, both Memory API search adapters,
timeline, range overflow, OpenAPI/HTTP 400, all four provider reads without
identity, exact revision material, tombstones, and rollback preservation.
They also cover rejected unknown provider updates, defensive denial of unknown
stored scope/sensitivity across all four provider reads, and canonical
mixed-case tombstone emission.

## Related tests executed

Two initial and two follow-up RED nodes failed deterministically. The final
exact Green command passed 21 nodes; the exact all-changed-Python Ruff command
and 159-module size gate also passed. Exact commands and bounded outputs are
retained in the shareable artifacts.

## Unaffected paths sampled

Existing valid sensitivity, cursor, revision, candidate-first writes, and
legacy adapter behavior remain in the later focused regression set.
