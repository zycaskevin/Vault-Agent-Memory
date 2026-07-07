# Central Derived Vector Index

Date: 2026-07-07

## Context

Vault already supports local keyword search, optional semantic search, bounded
reads, Supabase read copies, Gateway / Remote Server reads, and candidate-first
remote writes. External architecture review also identified a real P1 gap: a
shared memory foundation needs better cross-agent retrieval and eventually
remote vector read paths.

The risky interpretation is to add a second central "memory database" that
agents can write to directly. That would weaken Vault's core contract:

- local SQLite and Markdown are the source of truth;
- active memory is governed, reviewed, auditable, and recoverable;
- remote writes are candidates first;
- Supabase and Remote Server are sharing/read surfaces, not active multi-master
  memory stores.

Vector search can improve retrieval quality and latency, but only if it remains
a derived search layer instead of a new source of truth.

## Decision

Vault should add a **central derived vector index** as a P1 optimization and
sharing layer.

The vector index is:

- a rebuildable cache derived from reviewed Vault memory;
- scoped by vault, agent access policy, sensitivity, lifecycle state, source
  range, embedding provider, model, and dimension;
- used for retrieval candidate generation and reranking;
- always checked again against Vault access policy before results are returned;
- never the authority for whether a memory exists, is current, is private, or
  can be shown to an agent.

The vector index is not:

- a second memory store;
- a multi-master sync layer;
- a place for hosted agents to write active memory;
- a bypass around candidate review;
- a substitute for SQLite / Markdown backup, restore, and audit.

## Source Of Truth

The source of truth remains the local Vault database and human-readable memory
files. The index can be deleted and rebuilt from reviewed memory plus metadata.

Index rows must carry enough metadata to prove what they came from:

- `vault_id` or project identity;
- `knowledge_id` or stable memory id;
- `source` and optional source range;
- `layer`, `scope`, `sensitivity`, `owner_agent`, and `allowed_agents`;
- lifecycle state such as active, archived, expired, or cold-stored;
- content hash or memory revision id;
- embedding provider id, model id, dimension, and index version;
- indexed timestamp and invalidation timestamp when relevant.

If any metadata needed for access filtering is missing, the result should be
treated as unsafe and omitted.

## Indexing Policy

Default indexing should include reviewed active memory only.

Candidates, rejected candidates, private memory, high/restricted sensitivity
memory, archived memory, expired temporal memory, and cold-store originals need
explicit policies before they are indexed. The conservative defaults are:

| Memory state | Default vector-index behavior |
|---|---|
| Reviewed active low/normal sensitivity memory | Indexable. |
| Private memory | Local-only indexing unless an agent access policy explicitly allows it. |
| High or restricted sensitivity memory | Not indexed in shared or remote indexes by default. |
| Memory candidates | Not indexed in the active retrieval index. Candidate-review search may use a separate local-only candidate index later. |
| Rejected or blocked candidates | Not indexed. |
| Archived memory | Not included in normal search index; may use a separate audit index later. |
| Expired temporal memory | Excluded from current-memory search by default. |
| Cold-store summaries | Indexable only as summaries, not raw originals, unless audit mode explicitly allows it. |

Promotion, rejection, archive, restore, temporal expiry, sensitivity change,
access-policy change, source edit, and sync pull must invalidate or refresh the
affected vectors.

## Query Policy

Vector retrieval should be one stage in a governed search pipeline:

```text
query
  -> keyword / FTS / BM25 candidate generation
  -> optional vector candidate generation
  -> hybrid merge or rerank
  -> Vault access-policy filter
  -> bounded result payload
  -> optional read-range for authorized source ranges
```

The final result must be filtered by Vault rules, even if the vector store
already supports metadata filters. Metadata filters in the vector store are a
performance optimization, not the security boundary.

Remote vector search should return compact references first: ids, source
ranges, scores, and safe metadata. Full content should still go through bounded
read APIs.

## Deployment Model

Implement in stages:

1. **Local shared index**: one machine, one shared Vault project, many local
   agents. The index is stored beside `vault.db` or under the project install
   directory and can be rebuilt from local memory.
2. **Hybrid retrieval**: search uses keyword/FTS/BM25 plus vector retrieval,
   then measures Search QA, LoCoMo / LongMemEval retrieval-only source hits,
   latency, and stale-index behavior.
3. **Trusted remote read index**: a trusted sync host can serve remote vector
   search through Gateway / Remote Server or a Supabase/Postgres-backed read
   copy. Remote writes remain candidate-first.
4. **Managed/team option**: only after the local and trusted-host paths prove
   useful, expose managed embedding/index operations for teams.

## Engineering Requirements

The first implementation should provide:

- explicit index status and health output;
- rebuild command;
- stale-vector detection by content hash or revision id;
- provider/model/dimension metadata;
- per-query latency and index-build latency reporting;
- Search QA support for hybrid/vector modes;
- benchmark integration for retrieval-only evidence recall;
- tests for access-policy filtering after vector retrieval;
- tests for invalidation after promote/reject/archive/sensitivity changes.

## Security Requirements

Hosted or remote agents must not receive direct credentials to write the central
vector index. They should call Gateway, Remote Server, or approved read RPCs.

Remote vector search must not expose:

- service-role keys;
- raw private memory;
- raw high/restricted memory;
- unreviewed candidate content;
- stale memory that has been archived, expired, or rejected.

When in doubt, the index should fail closed and fall back to keyword search.

## Consequences

This preserves Vault's governance model while improving retrieval quality and
multi-agent shared-memory ergonomics. It also creates a fair path for external
memory benchmarks: central vector search can be measured as retrieval-only
source-hit performance before any final-answer claims are made.

The cost is operational complexity. Vault needs index health, invalidation,
model metadata, and access-policy tests before remote vector search is safe to
ship.

## Deferred

- Choosing the storage backend: SQLite vectors, pgvector, Qdrant, LanceDB, or
  another local-first option.
- Candidate-review vector index.
- Audit/archive vector index.
- Remote vector read API schema.
- Managed embedding and hosted team index operations.
- Cross-device index replication.
