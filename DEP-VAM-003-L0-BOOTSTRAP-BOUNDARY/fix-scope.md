# Fix Scope

## Smallest sufficient change

Define `L0-bootstrap` as the canonical new-project directory, keep
`L0-identity` as a read-only inference alias, and rewrite active setup/public
guidance to describe generic memory maintenance instead of human modeling.

## Files or components in scope

- Project creation and layer inference
- Generated memory-maintenance and access wording
- Primary README/core/governance/install/integration/CLI documentation
- `agent_manifest.json`
- Focused compatibility tests and VAM-003 governance records

## Explicit non-scope

No data rename/delete, schema or layer-value change, permission change, removal
of legacy public identifiers, historical-record rewrite, Subject change,
VAM-002 change, DLI dependency, release, deploy, or merge.

## Blast radius

New project directory names and generated documentation change. Existing
projects continue to compile and read with their current paths and database
values.

## Scope completeness audit

### Smallest sufficient change

The canonical-output and legacy-read compatibility change above is sufficient.

### Files or components in scope

All code, generated guidance, active documentation, tests, and governance records are listed above.

### Explicit non-scope

The exclusions above remain binding, including no migration, release, deploy, or merge.

### Blast radius

The blast radius is limited to new directory output and generated documentation as recorded above.
