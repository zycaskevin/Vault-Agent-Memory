# Rollback

## Trigger

Rollback this documentation-only remediation if its new binding test creates a
false constraint or a corrected rollback command is shown inaccurate.

## Reversible steps

From the exact successor commit, prepare an uncommitted local revert of only
the remediation commit. Run `git diff --cached --check`, confirm the staged
allowlist contains only the files in this DEP plus the listed documentation and
binding test, then discard the uncommitted revert if verification fails.

## Data compatibility

No database, stored memory, API route, or user data changes.

## Post-rollback verification

Run the focused binding node, Ruff on `tests/test_vault_boundary_freeze.py`,
and `git diff --cached --check` against the uncommitted rollback candidate.
