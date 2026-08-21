# Rollback

## Trigger

Rollback only if the stable-root verification process changes repository bytes
or weakens an identity/security check.

## Reversible steps

No product fix exists to revert. Discard this verification-only DEP if its
evidence is invalid; retain the unchanged frozen Subject implementation.

## Data compatibility

No data, schema, migration, or runtime behavior changed.

## Post-rollback verification

Re-run Local Green from a fresh stable dedicated root and require all 446
identity nodes to pass.
