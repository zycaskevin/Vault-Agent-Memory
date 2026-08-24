# Regression Evidence

## Regression test added or strengthened

`test_vam002_replacement_review_findings_have_current_reproducible_records`
now requires reviewed-head ancestry, an audit-only diff, both exact exclusions,
and rejects exact-parent equality.

## Related tests executed

The targeted RED failed with all five finding-11 markers. After the bounded
fix, the same test and the executable rollback contract test passed together:
2 passed in 0.09 seconds. Ruff on the changed test file and `git diff --check`
also passed.

## Unaffected paths sampled

Frozen Subject contracts, memory runtime/API implementation, stored data,
dependency declarations, and all live environments remain unchanged.
