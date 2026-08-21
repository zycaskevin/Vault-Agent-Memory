# Fix Scope

## Smallest sufficient change

Derive a canonical current-snapshot envelope from existing knowledge rows, add
policy-bound cursor helpers and provider methods, expose one read-only changes
route, and bind existing bounded reads to an optional expected revision.

## Files or components in scope

- Change envelope helper module
- Memory Provider protocol and SQLite provider
- Gateway Memory API routing and OpenAPI contract
- Focused provider/Gateway tests
- VAM-002 issue, SDD, Work Package, ADR, and DEP

## Explicit non-scope

Database migrations, historical content reconstruction, write-path authority,
remote sync, application-domain models/endpoints, external dependencies,
release, deployment, merge, or private/live data.

## Blast radius

Read-only and additive. Existing endpoints and default adapters remain intact.
The only runtime additions are envelope derivation, one GET route, optional
revision validation, and contract metadata.
