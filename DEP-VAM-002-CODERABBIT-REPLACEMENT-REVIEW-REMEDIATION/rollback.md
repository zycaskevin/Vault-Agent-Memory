# Rollback

rollback_version: 3.0
target: exact remediation implementation commit recorded before Proof; preserve this DEP and every prior VAM-002 evidence package
rollback_action: git_revert
rollback_ref: REPLACE_WITH_FULL_CANDIDATE_SHA
reconcile_action: setup_agent_from_reverted_source
reconcile_agent: codex
reconcile_profile: team-standard
verify_action: doctor_and_python_module
verify_module: unittest

## Trigger

Rollback this remediation only if valid identity-bearing callers regress, the
HTTP contract returns content or rows on missing identity, a historical source
hash is no longer preserved, or an exact-parent rollback guard rejects the
actual protected receipt head.

## Reversible steps

Before Proof, no rollback command is authorized from this record. The exact
remediation implementation commit replaces `REPLACE_WITH_FULL_CANDIDATE_SHA`
after it exists. Before merge, an uncommitted local revert of only that commit
may be prepared and mechanically checked against Fix Scope. After merge, use
only the fresh-L3-approval guarded PR procedure in
`DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md`; restore this successor
DEP so its audit trail remains available.

## Data compatibility

No schema or stored-data rewrite exists. Rollback changes the missing-identity
HTTP status from 400 back to the prior 200-with-error behavior and removes only
the successor tests, documentation, and evidence corrections. Valid-call
payloads and stored rows remain byte-compatible.

## Post-rollback verification

Require an exact staged-path allowlist, no untracked files, the expected RED
for the two targeted regressions, Green valid-caller/provider tests, strict
verification of every preserved DEP, Ruff, module-size, `git diff --check`,
Doctor, the declared unittest module, and repository Local Green. Any
post-merge commit or push remains governed by the authoritative
approval-consuming rollback, not this local preparation.
