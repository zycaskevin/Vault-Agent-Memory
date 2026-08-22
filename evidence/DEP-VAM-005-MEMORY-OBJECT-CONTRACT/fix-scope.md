# Fix Scope

## Smallest sufficient change

Add a Memory Object module, three provider adapters, additive create aliases,
provider/OpenAPI contract metadata, and canonical VAM-002 kind mapping.

## Files or components in scope

- `vault/memory_object.py`
- Memory Provider protocol/SQLite adapter
- Gateway Memory API create mapping
- Gateway OpenAPI contract
- VAM-002 envelope kind adapter
- Focused tests and VAM-005 records/DEP

## Explicit non-scope

Database/storage migration, L0 or broad docs cleanup, application-domain
runtime, new endpoint namespace, direct active writes, authority switch,
release, deployment, merge, or original dirty worktree mutation.

## Blast radius

Additive provider methods and request aliases. Existing `memory_type`, `trust`,
CLI, MCP, Gateway routes, storage rows, and default authorities remain valid.
