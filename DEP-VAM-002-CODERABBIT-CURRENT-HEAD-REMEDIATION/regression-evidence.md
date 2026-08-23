# Regression Evidence

## Regression test added or strengthened

Two RED nodes cover whitespace fail-closed behavior across both adapters and
the one-query `limit + 1` change-page selection. The HTTP facade test snapshots
stable content, governance, temporal, and lifecycle fields for every knowledge
row before candidate-first operations and compares the exact snapshot after.

## Related tests executed

RED: 2 failed at exact public head plus test-only RED changes. Targeted Green:
the reproducible VAM-002 selection passed 22/22, the real HTTP loopback
candidate-first snapshot node passed 1/1, the exact two RED boundaries plus SQL
policy-equivalence regression passed, and changed-file Ruff passed. Full-suite
proof remains a separate exact-committed-head gate.

## Unaffected paths sampled

Existing invalid-label, malformed stored-label, private/restricted policy,
cursor, WAL snapshot, hydration, OpenAPI, and revision-bound tests remain in
the focused selection.
