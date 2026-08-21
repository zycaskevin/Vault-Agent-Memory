# Regression Evidence

## Regression test added or strengthened

No test or frozen Subject byte changed. Existing SDG-002/SDG-008 controls
already define the stable-root mitigation for this fail-closed availability
race.

## Related tests executed

- Original failed node alone: 1 passed.
- Original failed node under a fresh isolated home/temp root: 1 passed.
- Shared-`/tmp` complete recheck: failed closed on a different node.
- Stable dedicated root complete isolation: 446 nodes passed.
- Stable-root disjoint repository suite: 2,935 passed, 10 skipped.

## Unaffected paths sampled

Frozen Subject runner, verifier, manifest, schema, tests, authorization scope,
and fixed-deny behavior remained byte-unchanged.
