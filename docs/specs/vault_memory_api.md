# Vault Memory API Specification

Status: draft for the next architecture track after v0.9.0 public beta.

Vault Memory API is the stable public memory interface that lets Vault work in
two modes:

- standalone: agents use Vault directly through CLI, MCP, Gateway, OpenAPI, and
  the default local SQLite backend;
- foundation: other agent or memory frameworks use Vault as a governed memory
  backend while Vault preserves review, audit, lifecycle, and backend
  boundaries.

The API is additive. It must not remove or break the existing CLI, MCP tools,
Gateway `/search`, `/read-range`, `/submit-candidate`, Central Memory Station,
or local SQLite workflows.

## Architecture

```text
Agent / Framework
Hermes / OpenClaw / Letta / mem0 / Claude Code / Codex
        |
        v
Vault Memory API
        |
        v
Vault Gateway / Governance Layer
permissions, candidate-first writes, search, sync, audit, revisions, timeline
        |
        v
Memory Provider Interface
        |
        v
SQLite / Self-host host / Supabase / Postgres / Vault Cloud
```

Qdrant or other vector stores are semantic index providers, not default
source-of-truth memory providers. A backend can become a full memory provider
only when it preserves candidate queue storage, active memory storage, access
policy metadata, lifecycle status, audit trail, and backup/export semantics.

## HTTP Surface

The target namespace is:

```text
POST   /memory/create
POST   /memory/search
GET    /memory/{id}
PATCH  /memory/{id}
DELETE /memory/{id}
POST   /memory/promote
POST   /memory/link
GET    /memory/timeline
GET    /memory/audit
POST   /memory/sync
```

Compatibility rule: current Gateway endpoints remain valid adapters. The new
namespace should initially be a facade over the existing governed behavior, not
a rewrite of storage internals.

## Governance Semantics

The API must preserve the Vault Governance Contract:

- remote or untrusted `create` writes candidates, not active memory;
- official read surfaces return reviewed active memory subject to policy;
- `promote` requires a trusted reviewer or explicit policy gate;
- strategic, sensitive, conflicting, or freshness-sensitive memory remains
  review-visible;
- every mutating operation records an audit event;
- sync does not turn remote backends into active multi-master memory stores.

`DELETE /memory/{id}` is a soft tombstone by default. It marks memory as deleted
for normal recall while preserving audit and recovery metadata. Hard delete, if
added later, must be a separate admin-retention operation with explicit
credentials and documentation.

In the initial Gateway facade, untrusted or remote clients do not apply the
tombstone directly. `DELETE /memory/{id}` submits a soft-delete review candidate
that a trusted reviewer or policy gate can later apply. This keeps the new API
compatible with the existing candidate-first Gateway boundary.

## Lifecycle Status

The public lifecycle status set should stay small:

```text
candidate
active
archived
deprecated
deleted
```

`active` is the official readable state. `approved` should be represented as a
review decision or audit event, not as a long-lived memory row status, so users
do not have to guess whether `approved` or `active` is the current read surface.

## Identity Metadata

The public API should accept multi-agent identity metadata without forcing an
immediate storage migration:

```text
agent_id
created_by_agent
owner_user
workspace_id
source_app
source_device
permission_scope
scope
sensitivity
allowed_agents
```

Initial implementations can map these fields onto the existing governance
metadata (`owner_agent`, `scope`, `sensitivity`, and `allowed_agents`) while the
provider boundary matures.

## Provider Interface

The first internal provider contract should be minimal:

```text
create_candidate(...)
search_active(...)
get_memory(...)
update_memory(...)
soft_delete_memory(...)
promote_candidate(...)
list_timeline(...)
list_audit(...)
sync(...)
```

SQLite remains the default local-first provider. Supabase remains an optional
cloud adapter and reviewed read-copy plus candidate inbox. Postgres and Vault
Cloud can implement the same provider contract later without changing agent
integrations.

## Non-Goals

This architecture track should not make Vault depend on Letta, mem0, Qdrant,
Supabase, or Vault Cloud. It should not turn Vault into a full agent runtime,
large SaaS platform, billing system, or enterprise admin console.

The immediate goal is a stable memory interface and provider boundary while the
existing standalone local workflow keeps working.
