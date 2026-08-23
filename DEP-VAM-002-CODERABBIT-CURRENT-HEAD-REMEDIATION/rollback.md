# Rollback

## Trigger

Rollback if the policy SQL differs from `can_read_memory`, cursor ordering or
privacy changes, blank ceilings no longer default to low, selected hydration
widens, or the full repository gate regresses.

## Reversible steps

Revert immutable implementation commit
`cbbf2d1c174e432313654e0260450af37a766f71`, preserve all earlier VAM-002
evidence and reviewed heads, and verify the staged path set contains only this
DEP, the named source and test files, the authoritative rollback regression,
and the corrected historical evidence documents.

## Data compatibility

No table, migration, stored row, candidate, audit event, cursor version, or
live data is changed. Rollback is code/test/document only.

## Post-rollback verification

Run the exact targeted command from `reproduction.md`, the complete VAM-002
focused selection recorded in `verification.md`, Ruff over every changed
Python file, `git diff --check`, strict DEP verification, and the repository
Local Green. Every command must exit zero at the rollback candidate.
