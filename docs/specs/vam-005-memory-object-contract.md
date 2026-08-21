# VAM-005 Memory Object Contract

Status: implementation target

## Mission contract

Vault is governed memory infrastructure for AI agents. Its generic Memory
Layer contract has exactly five canonical content kinds:

```text
event
experience
decision
knowledge
interaction
```

`MemoryObject` is the envelope and is not a sixth kind. Vault supplies exactly
these infrastructure capabilities:

```text
storage
retrieval
provenance
confidence
lifecycle
governance
```

Application semantics remain opaque. Storing application-owned content does
not transfer semantic ownership to Vault.

## Envelope

```json
{
  "schema_version": "1.0",
  "id": "42",
  "kind": "interaction",
  "title": "Reviewed interaction",
  "content": "...",
  "provenance": {},
  "confidence": 0.8,
  "lifecycle": {},
  "governance": {},
  "application_metadata": {}
}
```

The adapter maps current storage fields without changing stored data:

- `memory_type` -> canonical `kind`;
- `trust` -> `confidence`;
- source and timestamps -> `provenance`;
- status and temporal fields -> `lifecycle`;
- scope, sensitivity, ownership, and allowlist -> `governance`.

An unknown legacy `memory_type` maps to `kind=knowledge` and is preserved in
`application_metadata.legacy_memory_type`. Vault does not interpret the legacy
label.

## Provider operations

The Memory Provider Interface adds:

```text
create_memory_object_candidate(...)
search_memory_objects(...)
get_memory_object(...)
```

Creation remains candidate-first. Search/get retain the existing provider read
policy. No new direct active-memory write is introduced.

## HTTP aliases

`POST /memory/create` accepts:

- `memory_kind`: one of the five canonical values;
- `confidence`: a 0..1 alias for legacy `trust`.

The aliases are additive. Existing `memory_type` and `trust` clients continue
to work. An invalid explicit `memory_kind` fails with
`unsupported_memory_kind` before a candidate is created.

## Change-envelope integration

`vault.memory-change.v1` continues to own cursor/revision/evidence semantics.
VAM-005 makes its `kind` canonical. Unknown legacy types remain available only
as opaque `application_metadata`, not as new Vault-owned kinds.

## Migration and rollback

No database migration is required. Rollback reverts the adapter, aliases, and
published contract; stored rows and existing interfaces remain unchanged.
