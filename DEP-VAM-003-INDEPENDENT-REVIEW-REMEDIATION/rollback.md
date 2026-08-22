# Rollback

## Trigger

Use this rollback only if the neutral wording is inaccurate, the tests are
non-portable, or the hardened record is rejected by the installed verifier for
a reason introduced by this remediation.

## Reversible steps

From a clean checkout of the remediation commit, restore only these tracked
files from pre-remediation head
`8eec35c3b228efbdfc8707a11e2d31e885002562`:

```bash
git restore --source=8eec35c3b228efbdfc8707a11e2d31e885002562 --staged --worktree -- \
  DEP-VAM-003-L0-BOOTSTRAP-BOUNDARY/rollback.md \
  docs/agent_install.md \
  docs/memory_governance.md \
  docs/vision.md \
  tests/test_vault_boundary_freeze.py
```

Preserve this DEP and all other VAM-003 governance history. Review and commit
the resulting candidate through the ordinary governed workflow.

## Data compatibility

No database, stored memory, user directory, or public identifier migration is
part of the remediation or its rollback.

## Post-rollback verification

Verify the staged path set is exactly the five paths above, run
`git diff --check`, the pre-remediation focused suite, strict verification of
this preserved DEP, and the complete Local Green before publishing a rollback.
