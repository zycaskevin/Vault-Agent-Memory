# Rollback

## Trigger

Rollback if a supported legacy project stops resolving L0 content, a new
project cannot initialize, or generated setup output violates the approved
memory/identity boundary.

## Reversible steps

Revert the VAM-003 commit. Do not rename or delete either canonical or legacy
user directories. If rollback occurs after new projects were created, their
`L0-bootstrap` directory remains ordinary user data and must not be moved
automatically.

## Data compatibility

The database layer value remains `L0`; no schema or stored row changes occur.
Both directory spellings are source-path inference labels, so the implementation
requires no migration or backup/restore operation.

## Post-rollback verification

Run project initialization, both source-inference cases, setup-agent guidance,
README smoke, and the complete local governance gate. Confirm no user data was
renamed or removed.

## Rollback completeness audit

### Trigger

The compatibility, initialization, and boundary violations above are the rollback triggers.

### Reversible steps

Revert only the VAM-003 change and preserve user directories exactly as stated above.

### Data compatibility

No stored data or schema migration exists; both input spellings remain readable.

### Post-rollback verification

Run the focused compatibility checks and complete local governance gate described above.
