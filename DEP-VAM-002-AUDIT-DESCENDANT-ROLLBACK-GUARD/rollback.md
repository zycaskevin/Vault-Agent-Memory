# Rollback

rollback_version: 3.0
target: exact VAM-002 audit-descendant rollback-guard correction; preserve this DEP and all prior VAM-002 provenance
rollback_action: git_revert
rollback_ref: 18ef12446c638d3c59db728a48c66924ae8a1836
reconcile_action: setup_agent_from_reverted_source
reconcile_agent: codex
reconcile_profile: team-standard
verify_action: doctor_and_python_module
verify_module: unittest

## Trigger

Rollback only if the corrected guard accepts a non-audit descendant or rejects
the exact legitimate gate/receipt descendant shape.

## Reversible steps

Before merge, prepare an uncommitted revert of exact implementation commit
`18ef12446c638d3c59db728a48c66924ae8a1836` and compare the staged paths to
Fix Scope. After merge, use only
the fresh-approval procedure in
`DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md` and preserve this DEP.

## Data compatibility

No stored data or runtime response changes. Rollback affects only the
post-merge rollback precondition and its regression/provenance records.

## Post-rollback verification

Require the expected targeted RED, all other rollback contract tests Green,
strict verification of preserved DEPs, clean staged/untracked allowlists,
Doctor, CI verify, `git diff --check`, and repository Local Green.
