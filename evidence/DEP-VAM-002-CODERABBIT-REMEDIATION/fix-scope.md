# Fix Scope

## Smallest sufficient change

Preserve opaque memory references on revision-bound Gateway reads, safely
decode them only inside the SQLite provider, replace list-all pagination with
bounded keyset policy scans and selected-row hydration, and strengthen the
range/OpenAPI/query regression tests.

## Files or components in scope

- `vault/memory_provider.py`
- `vault/gateway_memory_api.py`
- `vault/gateway_openapi.py`
- focused Gateway and memory-change tests
- VAM-002 documentation and governance evidence corrections

## Explicit non-scope

No schema migration, write-path change, historical snapshot support, provider
authority switch, identity/personality modeling, release, deployment, merge,
or remote issue/review mutation.

## Blast radius

Read-only change pagination and bounded-read request parsing. Existing numeric
SQLite ids and legacy non-revision reads must remain compatible.
