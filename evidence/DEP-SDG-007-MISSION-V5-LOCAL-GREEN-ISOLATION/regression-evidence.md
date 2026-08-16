# Regression Evidence

## Regression test added or strengthened

`test_sdg007_release_accepts_only_exact_linear_reviewed_merge` accepts only the
closed two-parent hotfix release and denies hidden add/delete history. The
existing Local Green routing test now requires Mission V5 in the harness and
the disjoint remainder ignore list.

## Related tests executed

- Mission V5 collection: 75 unique nodes.
- Release checker, routing contract, and original failing node: 3 passed.
- Identity-isolated harness: 376 nodes passed.
- Disjoint remainder: 2920 passed, 12 skipped, one pre-existing warning.
- No test, acceptance condition, skip, or xfail was removed or weakened.

## Unaffected paths sampled

Canonical five, v1-v4, T-001 through T-003 artifacts, sequence-6 progress,
Mission contract/schema/registry, updater/validator/dispatcher, task outputs,
private/live data, and product runtime.
