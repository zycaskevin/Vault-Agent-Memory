# Deployment Modes

Vault Agent Memory is a backend-agnostic memory governance layer. The product
contract is candidate-first, reviewable, auditable memory for agents; the
backend is replaceable.

```text
Agents / Apps
  -> MCP / Gateway / OpenAPI adapters
  -> Vault Governance Contract
  -> Backend adapter
  -> Local SQLite / Self-host central host / Supabase / future Vault Cloud
```

## Vault Governance Contract

Every deployment mode must preserve the same rules:

- approved memory is the durable read surface;
- remote writes enter as candidates, not active memory;
- promotion is done by a trusted reviewer or explicit policy gate;
- sensitive, conflicting, strategic, or freshness-sensitive memory remains
  review-visible;
- access policy metadata and audit events travel with memory;
- daily-loop status and reports explain what changed and what needs review.

Minimum operations:

```text
search_approved_memory(query, agent_id, policy)
read_approved_memory(handle, agent_id, policy)
submit_candidate(memory_candidate, agent_id, source)
review_candidate(candidate_id, decision, reviewer_or_policy)
promote_candidate(candidate_id, policy)
audit_memory_event(event)
daily_loop_status()
daily_loop_report()
```

Backends can store and index data differently, but they must not bypass the
candidate-first contract.

Runtime surfaces expose this contract as machine-readable JSON:

- `vault gateway health --json` includes `gateway.governance_contract`;
- `vault remote-server health --json` includes the same contract under the
  Remote Server metadata;
- `vault gateway openapi --json` and `vault remote-server openapi --json`
  include `x-vault-governance-contract`;
- `vault security doctor --json` includes `governance_contract` beside the
  Supabase and self-host boundary checks.

## Mode Matrix

| Mode | Best for | Cost | Main risk | Default recommendation |
|---|---|---:|---|---|
| Local Vault | one developer, one machine | free | local backup discipline | default start |
| Self-host Central Memory Host | clinics, teams, multi-agent workstations | hardware only | VPN/token/backup | recommended for privacy |
| Supabase Adapter | hosted agents, Coze, n8n, no always-on host | possible cloud cost | RLS/key/schema/provider setup | optional cloud path |
| Vault Cloud | teams that do not want to operate memory infrastructure | paid | vendor trust | future managed backend |

## Local Vault

Use local mode first when one machine can host the working memory.

Data flow:

```text
local agent -> local CLI/MCP -> local vault.db + Markdown
```

Permissions:

- local agents use local CLI or MCP profiles;
- writes still go through candidates unless the operator deliberately uses a
  direct maintenance command;
- private/high/restricted memory stays governed by access-policy metadata.

Sync and backup:

- no cloud service is required;
- back up `vault.db`, Markdown sources, and generated reports;
- run daily-loop reports locally.

Use this mode for first installs, solo developers, and the smallest reliable
setup.

## Self-host Central Memory Host

Use this mode when privacy, local embeddings, and operational control matter.
This is the **Trusted Local Central Memory Host** pattern: one trusted machine
owns the source-of-truth vault; other machines connect through Gateway, Remote
Server, or MCP-facing adapters.

For the implementation contract, state model, sync rhythm, and acceptance
tests, see [Self-host Central Memory Host Specification](specs/self_host_central_memory_host.md).

Data flow:

```text
remote agent
  -> authenticated Gateway / Remote Server
  -> search approved memory or submit candidate
  -> trusted central host reviews/promotes
  -> local vault.db remains source of truth
```

Recommended host responsibilities:

- keep `vault.db` and Markdown source files;
- run daily-loop reports;
- review, reject, defer, or promote candidates;
- run Dream, archive, forgetting, and rollback jobs;
- run local embedding providers when semantic search is needed;
- update derived semantic/vector indexes after promotion or on a schedule;
- back up the vault daily.

For backend moves, migrate central candidate inbox rows with
`vault memory-sync migrate-candidates` and bootstrap reviewed memory with
`vault memory-sync export-snapshots` / `vault memory-sync verify-snapshots` /
`vault memory-sync import-snapshots`. Snapshot verify checks the bundle manifest,
snapshot digest, content hashes, and missing-content state without writing
memory. Snapshot import writes local `memory_candidates` only; it does not write
active `knowledge` or bypass review.

Network and credential checklist:

- prefer Tailscale, ZeroTier, WireGuard, or a private VPN before exposing a
  public endpoint;
- require a Gateway token or Remote Server token;
- use one token per agent identity for remote semantic reads;
- use HTTPS or a trusted reverse proxy for public exposure;
- keep admin credentials on the central host only;
- do not give remote agents filesystem access to `vault.db`.

Before exposing the host, run:

```bash
vault security doctor --json
vault remote-server health --json
```

`vault security doctor` warns when a self-host deployment has no stable Gateway
token, exposes a public bind without TLS/private-network evidence, enables
Remote Semantic Search without token-agent binding, or has no local SQLite
backup under `backups/`.

Recommended sync rhythm:

- candidate submission: immediate;
- approved-memory search/read: immediate through the central host;
- semantic index refresh: after promotion or every 5-15 minutes;
- daily-loop report: once per day, commonly 09:00 local time;
- backup: daily, or more often for active teams;
- offline agents: store an outbox locally and submit candidates when online.

This mode is the recommended architecture for sensitive teams because query
embeddings can stay local and the active memory authority does not leave the
trusted machine.

## Supabase Adapter

Use Supabase when hosted agents or cloud workflows need remote access and the
team does not have an always-on central host.

This is a **Cloud Adapter** path: Supabase supplies hosted infrastructure around
the same Vault Governance Contract, not a separate memory truth model.

Data flow:

```text
trusted sync host -> reviewed read copy / candidate inbox in Supabase
hosted agent -> approved reads + candidate submissions
trusted sync host -> pulls candidates into local review
```

Permissions:

- normal hosted agents use anon, publishable, or scoped credentials;
- `SUPABASE_SERVICE_ROLE_KEY` belongs only on a trusted sync host;
- service-role keys must not be placed in Coze, browser clients, normal n8n
  workflows, or hosted agents unless that runtime is intentionally the trusted
  sync host;
- Supabase is a reviewed read copy plus candidate inbox, not active
  multi-master memory.

Run `vault security doctor --json` on agent hosts and sync hosts. It warns if a
service-role key is present without `VAULT_SUPABASE_TRUSTED_SYNC_HOST=1`.

Sync and review:

- push approved local memory to the reviewed read copy;
- pull remote candidate requests into local review;
- promote only after local review or narrow policy-gated automation;
- monitor sync reports for freshness and warnings.

Use this mode for Coze, n8n, hosted agents, OpenAPI connectors, and teams that
prefer managed cloud infrastructure over running a central host.

## Vault Cloud

Vault Cloud should be positioned as a future managed backend for the same Vault
Governance Contract.

It is also a **Cloud Adapter** path. It should manage operations for the same
contract rather than replacing local, self-hosted, or Supabase semantics.

It should provide:

- managed storage for approved memory and candidates;
- managed review dashboard;
- managed backups and health reports;
- API key and agent identity management;
- optional managed embeddings and derived indexes;
- the same candidate-first, reviewable, auditable behavior as local and
  self-hosted deployments.

It should not introduce a different memory model. The commercial message is:

> Run it yourself, connect Supabase, or use Vault Cloud when you do not want to
> operate memory infrastructure.

## Remote Semantic Search Privacy

Remote semantic search is disabled by default. If enabled, Vault creates a query
embedding before it searches the central derived vector index.

Important default:

- the default remote semantic query embedding provider is OpenAI;
- therefore search query text is sent to OpenAI unless the operator configures a
  local or otherwise trusted embedding provider;
- remote semantic search returns safe previews and read handles, not raw memory
  content or embedding values.

Sensitive deployments should either keep remote semantic search disabled or set
a local embedding provider on the trusted host. Do not place secrets, customer
records, medical data, or private identifiers in search queries sent to an
untrusted provider.

Before enabling remote semantic endpoints, run:

```bash
vault gateway health --json
vault remote-server health --json
```

The health payload reports the query embedding provider/model and includes a
privacy warning when enabled remote semantic queries would go to OpenAI or
another external provider.

## Backend Adapter Requirements

Every backend adapter must support:

- approved memory storage;
- candidate queue storage;
- access-policy metadata;
- audit trail;
- read/search operations;
- backup or export path;
- optional semantic index support;
- a hard boundary preventing remote agents from writing active memory directly.

The adapter may be local SQLite, self-hosted Gateway/Remote Server storage,
Supabase, Postgres, or future Vault Cloud. The governance semantics must remain
the same.

## Release Checklist

Before describing a deployment as production-like, verify:

- readers can search approved memory without seeing private or restricted rows;
- remote candidate submission does not create active memory;
- service-role or admin credentials are present only on trusted hosts;
- Remote Semantic Search, if enabled, discloses the active embedding provider;
- daily-loop status and reports show sync freshness and candidate counts;
- backup and restore have been tested for the chosen backend;
- benchmark claims are described as retrieval evidence unless final-answer QA
  evaluation has been run.

For the v0.9.0 memory foundation architecture score and remaining limitations,
see [Memory Foundation Architecture Review](reviews/2026-07-09-memory-foundation-architecture-review.md).
