# Rollback

## Trigger

Existing-client regression, noncanonical public kind, write-policy bypass,
stored-data reinterpretation, or migration requirement.

## Reversible steps

Revert the VAM-005 commit/PR after its VAM-002 dependency. Do not modify stored
rows or the preserved dirty VLT-001 worktree.

## Data compatibility

No schema or data migration. Legacy fields and rows are unchanged.

## Post-rollback verification

Run provider, Gateway, VAM-002, and full Local Green tests; confirm additive
Memory Object aliases/contract are absent and existing interfaces remain Green.
