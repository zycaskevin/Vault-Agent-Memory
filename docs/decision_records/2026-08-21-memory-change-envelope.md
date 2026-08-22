# Stable Memory Change Envelope

Date: 2026-08-21
Decision ID: VAM-002-memory-change-envelope
Risk: L2
Status: approved for implementation; focused architecture review required before merge

## Context

Vault already owns governed memory storage, retrieval, provenance, confidence,
lifecycle, and audit metadata. It does not yet expose a stable incremental
change contract. An external consumer would otherwise need to read `vault.db`,
depend on SQLite row shapes, or duplicate Vault's access-policy logic.

## Decision

Add a provider-independent `vault.memory-change.v1` envelope and four additive
Memory Provider operations: `list_changes`, `get_metadata`, `get_revision`, and
`read_bounded_evidence`.

Expose policy-filtered change listing through `GET /memory/changes`. Continue to
use `GET /memory/{id}` for bounded content, with an optional `revision_id` that
fails closed when the current memory no longer matches the requested revision.

Use the current knowledge row as the first version's canonical snapshot. The
SQLite provider emits the row id as an opaque string memory id, a deterministic
revision digest, a full raw-content SHA-256, distinct occurrence/recording and
validity times, a bounded-evidence reference, and the latest available
metadata-only audit reference.

The revision digest binds canonical knowledge-row snapshot fields using the
exact normative revision-material definition in
`docs/specs/vam-002-memory-change-envelope.md`; this ADR does not maintain a
second field list. `audit_ref` is advisory metadata resolved from the latest
audit event and does not change revision_id when the row itself is unchanged.
Audit-only progression belongs to `/memory/audit`, not the row-based change
cursor.

Cursors are opaque, read-policy-bound pagination hints. They are not
credentials. Authorization is reevaluated on every call and requires a
non-empty agent identity. Cursor progress, counts, and `has_more` are calculated
only from readable rows.

The SDD's canonical scope and sensitivity sets are also authorization
boundaries. Trusted provider updates reject unknown labels, canonicalize valid
governance labels to lowercase, and active reads fail closed on malformed
stored labels rather than interpreting them as public or low sensitivity.

The Gateway preserves revision-bound memory ids as provider-owned opaque
strings. The SQLite adapter uses bounded keyset policy scans and hydrates raw
content plus audit references only for selected readable rows.

## Alternatives considered

1. Let consumers read SQLite directly. Rejected because it bypasses policy and
   couples consumers to Vault internals.
2. Add a new revision-history schema. Deferred because the required current
   change feed can be derived safely from existing rows; a migration would add
   risk without providing reliable historical content for old rows.
3. Put application-domain contracts in Vault. Rejected because Vault's frozen
   responsibility is generic governed memory infrastructure.

## Consequences

- External adapters can incrementally consume authorized current memory state
  without importing Vault internals.
- The same unchanged snapshot yields the same revision id, enabling downstream
  deduplication.
- A consumer cannot retrieve an older revision's content unless Vault preserves
  that snapshot through a future separately governed feature.
- No data migration is required; trusted provider updates gain bounded
  validation and canonicalization for governance labels.
- The API/privacy contract is L2 and cannot merge without a focused
  architecture review. Draft-PR publication is allowed; merge is not.

## Reopen conditions

Reopen this decision if consumers require complete historical event replay,
cross-vault globally unique identifiers, cryptographically authenticated
cursors, or an access-policy model that cannot be represented by the current
provider interface.
