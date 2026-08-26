# Rollback

## Trigger

Any policy bypass, hidden-row metadata leak, stale revision returning content,
cursor cross-policy reuse, existing API regression, or migration requirement.

## Reversible steps

Revert the VAM-002 commit/PR. No table or stored-row rollback is needed.

## Data compatibility

No schema or data mutation is introduced. Existing databases remain readable
before, during, and after rollback.

## Post-rollback verification

Run the existing provider and Gateway suites plus the repository Local Green
gate; confirm `/memory/changes` is absent from OpenAPI after rollback.
