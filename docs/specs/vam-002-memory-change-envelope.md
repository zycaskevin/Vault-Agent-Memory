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
  "count": 1,
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
uses the same format. `revision_id` is a deterministic digest of the canonical
knowledge-row snapshot fields surfaced by the current envelope. Repeating a
read of unchanged row state therefore returns the same revision id; a surfaced
content, lifecycle, provenance, confidence, status, or governance change
returns a different revision id. `audit_ref` is advisory metadata hydrated from
the latest audit event, not a canonical row field; an audit-only event does not
change revision_id or advance row-based change ordering. Consumers use
`/memory/audit` when they need audit-event progression.

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

Unknown non-empty `max_sensitivity` values fail closed and never remove the
caller's ceiling.

Ordering is ascending by `(recorded_at, memory row id)`. The cursor advances
only to the last change actually returned to the caller. Hidden rows do not
change the visible cursor, count, or `has_more` value. Reusing a cursor under a
different agent or sensitivity/private policy fails closed.

The SQLite adapter implements this with bounded keyset batches containing only
ordering and read-policy columns. It fetches `content_raw` and latest audit ids
only for the readable rows selected for the response page; it does not load the
entire knowledge or audit table before filtering.

The policy scan, selected-row hydration, and latest-audit lookup run inside one
explicit SQLite read transaction. They therefore observe one WAL snapshot.
Writes committed after the scan begins are visible on a later request, not
partially reflected in the current page's `changes`, `count`, `has_more`, or
`next_cursor`.

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
  response to a change envelope revision. For a revision-bound read, the
  Gateway preserves `{id}` as an opaque string and the selected provider alone
  validates or decodes it. The SQLite provider currently accepts its decimal
  row-id representation.
- `invalid_cursor`, `cursor_policy_mismatch`, and `max_sensitivity_invalid`
  return HTTP 400 with the documented Memory API error schema; they are never
  encoded as a successful change page or bounded read.

Existing Memory API routes and their default authorities remain unchanged.

## Compatibility and migration

This change adds provider methods, one read-only Gateway route, optional read
parameters, and OpenAPI metadata. It does not alter tables or write paths.
Rollback is removal of the new route/methods and documentation; stored data is
unchanged.
