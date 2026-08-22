# Fix Scope

## Smallest sufficient change

Require a normalized non-empty agent on all four VAM-002 provider reads. Add
one shared strict Memory API sensitivity check before legacy/provider dispatch
for get, search, changes, and timeline; map POST search errors to HTTP 400.
Reject unknown scope/sensitivity provider updates, canonicalize valid
scope/sensitivity/status labels, and deny legacy/corrupt rows with unknown
stored scope or sensitivity under active read policy.

## Files or components in scope

`vault/access_policy.py`, `vault/memory_provider.py`, `vault/gateway_memory_api.py`,
`vault/gateway.py`, `vault/gateway_openapi.py`, focused provider/Gateway tests,
VAM-002 revision/tombstone/range contract wording, exact locked-Ruff evidence,
this DEP, and the authoritative rollback allowlist.

## Explicit non-scope

No database migration, cursor encoding, legacy `/search` or `/read-range`
behavior, Subject/Identity surface, or dependency change.

## Blast radius

Bounded to authorization validation, governance-label canonicalization, and
transport contracts on the new VAM-002 interfaces. Valid callers retain
existing result shapes; invalid trusted updates now fail closed.
