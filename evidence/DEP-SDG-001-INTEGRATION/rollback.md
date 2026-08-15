# Rollback

rollback_version: 1.0
target: merged SDG-001 team-standard integration HEAD
command: git revert --no-edit HEAD
verify: git diff --check

## Trigger

Any managed-file mismatch, CI Cost Guard regression, required-test weakening,
secret/private-path retention, independent-review rejection, or hosted-CI
failure attributable to this integration.

## Reversible steps

Revert the SDG-001 integration commit as one unit. This removes the installed
managed assets, Work Package/evidence records, CI Cost Guard contract, and the
bounded workflow control additions while preserving unrelated repository
history and user files.

## Data compatibility

No product data or schema changes are involved. Rollback does not rewrite the
Subject Distillation ledger or completed task artifacts.

## Post-rollback verification

Run the prior repository test commands, README smoke, release parity, and
`git diff --check`; confirm no private/raw DEP content is tracked.
