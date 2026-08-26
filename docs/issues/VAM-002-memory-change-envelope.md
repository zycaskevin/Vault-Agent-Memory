# VAM-002: Stable Memory Change Envelope

Status: in progress

## Problem

Vault has governed search, bounded reads, lifecycle metadata, revisions, and an
audit log, but an external memory consumer cannot incrementally ask which
readable memories changed. Without a stable change envelope, each consumer
would have to depend on Vault's SQLite schema or invent its own cursor,
revision, and evidence semantics.

## Outcome

Add an additive, provider-independent change envelope to the Memory Provider
Interface and expose it through the existing Gateway Memory API. A consumer can
list policy-filtered changes by opaque cursor, identify an exact current
revision, and request bounded evidence for that revision.

## Acceptance criteria

- Every returned change has a stable `memory_id`, deterministic `revision_id`,
  full `content_sha256`, temporal fields, bounded-evidence reference, and
  metadata-only audit reference.
- Pagination cursors are opaque, policy-bound, and advance only across readable
  changes. Responses do not expose hidden totals or hidden identifiers.
- Bounded evidence enforces Vault read policy and a fixed server-side line cap.
- A stale revision request fails without returning content.
- The implementation is additive and requires no database migration.
- Existing CLI, MCP, Gateway, and provider behavior remains compatible.

## Non-scope

- Application-level subject, identity, personality, relationship, life-phase,
  or human-model semantics.
- New application databases or dependencies.
- Historical full-content reconstruction for revisions Vault did not preserve.
- Default provider-authority promotion, remote sync, release, deployment, or
  merge.
