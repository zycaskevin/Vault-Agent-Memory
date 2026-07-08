# Single-Host Sharing and Multi-Host Governed Sync

Date: 2026-07-08

## Context

Vault's core differentiation is not only local storage, search, or embeddings.
The important boundary is how several agents can share memory without turning
the shared vault into a polluted multi-writer database.

There are two different operating modes:

1. **Single-host sharing**: several agents on the same machine can use the same
   local Vault project through CLI, MCP, Obsidian, or local Gateway surfaces.
2. **Multi-host governed sync**: agents on other machines or hosted runtimes can
   read approved memory and submit candidates, but they do not write active
   memory directly.

These modes must stay distinct. A remote adapter, Supabase deployment, Gateway,
or future vector index must not blur candidate submission with active-memory
promotion.

## Decision

Vault uses the following P0 architecture rule:

> Single-host agents may share one local Vault. Multi-host agents may contribute
> candidates, but only a trusted sync host can review, promote, archive, dream,
> and write official shared memory.

The product wording is:

> Single-host sharing, multi-host governed sync.

In practical terms:

- local agents on one trusted machine may share the same Vault project;
- hosted or different-machine agents use least-privilege credentials such as
  anon or scoped reader keys;
- remote agents may submit memory candidates to Supabase, Gateway, or Remote
  Server;
- remote agents must not receive service-role keys;
- remote agents must not write active memory snapshots, active revisions,
  derived vector indexes, lifecycle state, or archive decisions directly;
- a trusted sync host with service-role credentials pulls candidates, imports
  them into local review queues, promotes only policy-approved memory, runs
  Dream / archive / forgetting, and pushes reviewed read copies back out.

## Trust Roles

| Role | Typical credential | Allowed actions | Explicitly forbidden |
|---|---|---|---|
| Local agent on the trusted host | local CLI / MCP profile / local Gateway token | Search, bounded read, propose candidates, and use the shared local project according to local policy. | Bypassing review or writing restricted memory without the configured local profile. |
| Remote or hosted agent | anon key, scoped reader token, or Gateway client token | Read approved memory allowed by policy; submit memory candidates. | Service-role access, active-memory writes, direct revision writes, direct vector-index writes, Dream, archive, forgetting, rollback. |
| Trusted sync host / reviewer agent | service-role key plus trusted-host marker or self-host admin credential | Pull candidates, verify signatures, review, promote, sync approved read copies, run lifecycle jobs, write reports. | Treating unreviewed remote submissions as active truth. |
| Human reviewer | local review UI, CLI, or trusted review agent | Approve, reject, defer, keep both, change sensitivity, and resolve conflicts. | Silent background deletion of official memory without audit. |

## Data Flow

```text
remote / hosted agents
  -> read approved memory through policy-aware RPC or Gateway
  -> submit candidate memory with anon/scoped credentials
  -> candidate inbox in Supabase, Gateway, or Remote Server
  -> trusted sync host pulls candidates with service-role/admin credentials
  -> local memory_candidates queue
  -> review, gates, conflict handling, promote/reject/defer
  -> official local Vault memory and revision/audit log
  -> Dream, archive, forgetting, cold-store, report
  -> approved read copy and derived indexes pushed back to remote surfaces
```

Candidate inboxes are ingress surfaces. They are not official memory stores.

Approved read copies and derived vector indexes are egress surfaces. They are
rebuilt from reviewed memory and must be safe to delete and regenerate.

## Supabase and Gateway Contract

Supabase and Gateway should expose the same trust contract even when their
deployment details differ:

- remote read APIs return only policy-allowed approved memory;
- remote submit APIs create candidates only;
- candidate payloads can be HMAC-signed and idempotency-keyed;
- service-role operations are reserved for the trusted sync host;
- `VAULT_SUPABASE_TRUSTED_SYNC_HOST=1` or the equivalent self-host marker
  distinguishes an operator machine from a normal remote-reader environment;
- Gateway remote semantic reads require endpoint opt-in and per-agent token
  binding; a shared unscoped Gateway token must not be used for central semantic
  search;
- status and doctor commands must report when service-role credentials are
  missing, misplaced, or present without the trusted-host marker.

## Derived Semantic Search

Central semantic search must follow the same rule.

The central vector index is allowed only as a derived read index:

- index reviewed active memory, safe summaries, and policy-approved metadata;
- do not index unreviewed candidates in the active shared retrieval index;
- do not index high/restricted memory in shared remote indexes by default;
- let the trusted sync host generate or approve indexable text and embeddings;
- return compact references first, then require bounded read for content;
- re-check Vault access policy after vector retrieval.

This means pgvector, Qdrant, SQLite vectors, or any future hosted vector layer
is a searchable card catalog for approved memory. It is not the library shelf,
not the librarian, and not a second authority for memory truth.

## Release Gate

Any release that changes Supabase, Gateway, Remote Server, central sync, remote
candidate submission, or remote semantic search must verify:

- anon/scoped remote credentials can submit candidates;
- anon/scoped remote credentials cannot write active memory, revisions, archive
  state, lifecycle decisions, or vector-index rows;
- the trusted sync host can pull remote candidates into the local candidate
  queue;
- promotion happens only through local review/policy gates;
- approved read copies are pushed only after review;
- candidate content does not appear in normal remote search or shared vector
  search before promotion;
- service-role credentials are reported as unsafe unless the runtime is marked
  as a trusted sync host;
- Gateway remote semantic endpoints are off by default, token-bound to one
  `agent_id`, project-scoped by default, and documented as sending query text to
  the configured embedding provider;
- daily-loop or memory-sync reports show candidate pull, review, sync, and
  lifecycle status separately.

## Consequences

This gives Vault a sharper product category than a generic memory SDK or vector
database:

- one machine can run a shared local memory foundation for many agents;
- many machines can contribute safely without polluting the official memory;
- remote services improve reach and retrieval, but do not become the source of
  truth;
- governance, review, rollback, report, and audit remain the durable center of
  the product.

The cost is that multi-host memory writes are intentionally slower than direct
multi-master writes. That is a design tradeoff: Vault optimizes for governed
shared memory, not fastest possible unreviewed replication.
