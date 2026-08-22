# Rollback

## Trigger

Rollback only if the placeholder or provenance breaks the evidence consumer.

## Reversible steps

From a clean checkout of the remediation commit, restore only the remediated
tracked files from exact pre-remediation head
`26519313d479b6bb240ec1f815dcac5f950f53b4`:

```bash
git restore --source=26519313d479b6bb240ec1f815dcac5f950f53b4 --staged --worktree -- \
  DEP-VAM-003-IDENTITY-ISOLATION-RECHECK/manifest.json \
  DEP-VAM-003-IDENTITY-ISOLATION-RECHECK/redaction-report.json \
  DEP-VAM-003-IDENTITY-ISOLATION-RECHECK/shareable/artifacts/exact-head-builder-local-green.txt \
  DEP-VAM-003-INDEPENDENT-REVIEW-REMEDIATION/manifest.json \
  DEP-VAM-003-INDEPENDENT-REVIEW-REMEDIATION/redaction-report.json \
  DEP-VAM-003-INDEPENDENT-REVIEW-REMEDIATION/regression-evidence.md \
  DEP-VAM-003-INDEPENDENT-REVIEW-REMEDIATION/shareable/artifacts/terminal--exact-head-builder-local-green.txt \
  DEP-VAM-003-INDEPENDENT-REVIEW-REMEDIATION/verification.md \
  DEP-VAM-003-L0-BOOTSTRAP-BOUNDARY/rollback.md \
  tests/test_vault_boundary_freeze.py
```

Preserve this DEP and all other VAM-003 governance history, then review the
resulting candidate.

## Data compatibility

No database, user memory, directory, or API data changes exist.

## Post-rollback verification

Verify the staged path set is exactly the ten paths above, run `git diff
--check`, strict verification of all preserved DEPs, the focused boundary
tests, and complete Local Green before publishing a rollback.
