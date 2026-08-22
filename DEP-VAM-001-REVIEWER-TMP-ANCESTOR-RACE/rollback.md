# Rollback

## Trigger

The owner-private checkout is not clean and exact, its origin or permissions do
not match this DEP, an ancestor changes during verification, or any Local Green
or independent-review gate fails.

## Reversible steps

1. Do not sign, push a receipt, or merge.
2. Record the failure in a successor DEP without rewriting this evidence.
3. Stop using the affected checkout and remove only that explicitly resolved
   temporary checkout after confirming it contains neither Reviewer private
   identity nor unrelated files.
4. Keep the protected PR blocked until a new bounded remediation reaches Proof.

## Data compatibility

No product data, schema, API, Vault database, frozen Subject input, or shipped
artifact changes. Reviewer identity and trust files live outside temporary
checkouts and are not rollback targets.

## Post-rollback verification

Confirm the PR head and remote branch are unchanged, no Review receipt or trust
variable was created by the failed run, the Builder/main worktrees are
untouched, and the explicitly resolved temporary checkout path no longer
exists if cleanup was performed.
