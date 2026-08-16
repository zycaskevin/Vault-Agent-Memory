# Regression Evidence

## Regression test added or strengthened

`test_sdg008_release_accepts_only_exact_linear_reviewed_merge` accepts only the
closed two-parent hotfix release and denies hidden add/delete history. The
Local Green routing test requires baseline control in the harness and the
disjoint remainder ignore list while asserting its immutable file is not in the
modified-path set.

## Related tests executed

- Baseline-control collection: 53 unique nodes.
- Complete immutable baseline-control file: 53 passed.
- SDG-008 release checker and routing contract: 2 passed.
- Identity-isolated harness: 430 nodes passed.
- Disjoint remainder: 2867 passed, 12 skipped, one pre-existing warning.
- No test, acceptance condition, skip, or xfail was removed or weakened.

## Unaffected paths sampled

The T-001 evidence validator and baseline-control test, canonical five, v1-v4,
T-001 through T-003 artifacts, sequence-6 progress, Mission contract/schema/
registry, updater/validator/dispatcher, private/live data, and product runtime.
