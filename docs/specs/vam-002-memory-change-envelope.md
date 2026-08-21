# VAM-002 Memory Change Envelope Specification

Status: implementation target

## Contract

`MemoryProvider.list_changes(...)` returns a page with this shape:

```json
{
  "status": "ok",
  "changes": [
    {
      "schema_version": "vault.memory-change.v1",
      "memory_id": "42",
      "revision_id": "rev_<sha256>",
      "change_type": "upsert",
      "content_sha256": "<64 lowercase hex characters>",
      "occurred_at": "<ISO-8601 timestamp or empty>",
      "recorded_at": "<ISO-8601 timestamp>",
      "valid_from": "<ISO-8601 timestamp or empty>",
      "valid_until": "<ISO-8601 timestamp or empty>",
      "audit_ref": "audit:<event-id> or empty",
      "evidence_ref": {
        "memory_id": "42",
        "revision_id": "rev_<sha256>",
        "operation": "read_bounded_evidence"
      }
    }
  ],
  "next_cursor": "<opaque cursor or empty>",
  "has_more": false
}
```

The envelope may include generic memory metadata such as title, kind,
confidence, provenance, lifecycle status, scope, and sensitivity. It never
contains raw memory content, a content snippet, an allowlist, or a hidden-row
count.

For the SQLite provider, `memory_id` is the decimal knowledge-row id serialized
as an opaque string. Consumers must not parse it or assume another provider
uses the same format. `revision_id` is a deterministic digest of every field
surfaced by the current envelope. Repeating a read of unchanged state therefore
returns the same revision id; a surfaced content, lifecycle, provenance,
confidence, status, or governance change returns a different revision id.

`content_sha256` is the full SHA-256 of the exact current `content_raw` bytes
encoded as UTF-8. It is separate from legacy short hashes and document-node
range hashes.

## Time semantics

- `occurred_at`: `valid_from` when supplied, otherwise the memory's creation
  time. Vault does not invent an event time from the latest edit time.
- `recorded_at`: latest storage update time, falling back to creation time.
- `valid_from` / `valid_until`: the existing temporal fact window, unchanged.

## Cursor and privacy semantics

The cursor is an opaque base64url token containing a version, the last returned
readable ordering key, and a hash of the read-policy inputs. It is not an
authorization token. Every page independently applies Vault policy.

Ordering is ascending by `(recorded_at, memory row id)`. The cursor advances
only to the last change actually returned to the caller. Hidden rows do not
change the visible cursor, count, or `has_more` value. Reusing a cursor under a
different agent or sensitivity/private policy fails closed.

## Bounded evidence

`MemoryProvider.read_bounded_evidence(...)` accepts `memory_id`,
`revision_id`, `line_start`, and `line_end`. It:

1. applies the normal Vault read policy;
2. requires the requested revision to equal the current revision;
3. delegates line extraction to the existing read-range implementation;
4. enforces a provider-side maximum of 80 lines even if a caller requests a
   larger maximum;
5. rechecks the revision after reading and returns no content if the memory
   changed during the read.

The first version intentionally reads only the current revision. Vault does
not claim historical evidence availability when no historical content snapshot
exists.

## HTTP mapping

- `GET /memory/changes`: list readable changes using `agent_id`, `cursor`,
  `limit`, `include_private`, and `max_sensitivity` query parameters.
- `GET /memory/{id}`: existing bounded read; an optional `revision_id` binds the
  response to a change envelope revision.

Existing Memory API routes and their default authorities remain unchanged.

## Compatibility and migration

This change adds provider methods, one read-only Gateway route, optional read
parameters, and OpenAPI metadata. It does not alter tables or write paths.
Rollback is removal of the new route/methods and documentation; stored data is
unchanged.
