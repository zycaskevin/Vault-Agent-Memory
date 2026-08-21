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

## Trigger

TODO

## Reversible steps

TODO

## Data compatibility

TODO

## Post-rollback verification

TODO
