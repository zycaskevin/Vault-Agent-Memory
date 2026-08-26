# Regression Evidence

## Regression test added or strengthened

`test_vam002_replacement_review_findings_have_current_reproducible_records`
now requires reviewed-head ancestry, an audit-only diff, both exact exclusions,
and rejects exact-parent equality.

## Related tests executed

The targeted RED failed with all five finding-11 markers. After the bounded
fix, the same test and the executable rollback contract test passed together:
2 passed in 0.09 seconds. Ruff on the changed test file and `git diff --check`
also passed. Exact-head full Local Green at `18ef124...` then passed 446
identity-isolated Subject nodes and repository pytest with 2972 passed, 10
skipped, and one existing warning; the manifest-bound transcript is
`shareable/artifacts/terminal--artifact-2.txt`.

The final stable exact-head run at
`f28843b1777f002b342d35449e9ce7aaf4bfc83c` passed the same 446 isolated
nodes and repository pytest with 2972 passed, 10 skipped, and one existing
warning. It checked 1496 tracked physical modes with zero mismatches. The
manifest-bound transcript is `shareable/artifacts/terminal--artifact-4.txt`.

## Unaffected paths sampled

Frozen Subject contracts, memory runtime/API implementation, stored data,
dependency declarations, and all live environments remain unchanged.
