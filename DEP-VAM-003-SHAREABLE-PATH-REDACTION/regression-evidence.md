# Regression Evidence

## Regression test added or strengthened

The new test rejects `/home/`, requires `$BUILDER_WORKTREE`, recomputes the
shareable artifact SHA-256, verifies the manifest binding, and verifies the
redaction report's exact source/output hashes and `workstation_path` count.

## Related tests executed

- Red: 1 failed, 17 passed.
- Initial Green: 18 passed.
- Final Green after the all-VAM-003 shareable scan: 19 passed.
- New-DEP rollback preservation probe: Red failure, then 1 passed after fix.
- Proof-state wording probe: Red failure on the pending-Green contradiction,
  then Green after separating DEP Proof from the repository merge gate.
- Updated identity-isolation DEP strict verification: pass.

## Unaffected paths sampled

All runtime files and public behavior remain unchanged. Existing stable-root
redacted artifacts and their hashes remain byte-identical.
