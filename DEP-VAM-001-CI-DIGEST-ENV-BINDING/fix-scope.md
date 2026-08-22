# Fix Scope

## Smallest sufficient change

Record the divergence, require all final VAM-001 digest/gate calculations to use
`GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=core.abbrev`, and
`GIT_CONFIG_VALUE_0=40`, and bind the audit-only gate to that result.

## Files or components in scope

This DEP and the final audit-only `.sddgov/merge-gate.json` revision.

## Explicit non-scope

No governance CLI source change, product runtime, Subject artifact, API,
database, documentation decision, Issue mutation, rollback, or deployment.

## Blast radius

Merge-gate verification only. Executable product behavior is unchanged.
