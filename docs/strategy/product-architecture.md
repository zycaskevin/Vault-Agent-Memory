# Product Architecture

Vault Agent Memory should grow in layers. Each layer should preserve the
local-first trust boundary while adding more team and enterprise governance.
Vault's durable product boundary is the governance contract, not a specific
backend.

The backend-agnostic stack is:

```text
Agents / Apps / Memory Frameworks
  -> Vault Memory API plus MCP / Gateway / OpenAPI adapters
  -> Vault Gateway / Vault Governance Contract
  -> Memory Provider Interface / Backend adapter
  -> Local SQLite / Self-host central host / Supabase / Postgres / future Vault Cloud
```

This stack is additive, not a requirement to install another memory framework.
Vault must remain useful as a standalone local memory system through CLI, MCP,
Gateway, and SQLite. The same governance layer can also sit underneath other
agent or memory frameworks, such as Hermes, OpenClaw, Letta, mem0, Claude Code,
and Codex, when they need a reviewable and auditable shared memory backend.

The detailed draft contract for that next public interface lives in
[`docs/specs/vault_memory_api.md`](../specs/vault_memory_api.md). The first
implementation should be a compatibility facade over current governed behavior,
not a storage rewrite.

## P0 Trust Boundary

Vault's category distinction is:

> Single-host sharing, multi-host governed sync.

On one trusted machine, Codex, OpenClaw, Claude Code, Hermes, Coze connectors,
and other local agents can share the same Vault project. Across machines or
hosted runtimes, agents should use anon or scoped credentials to read approved
memory and submit candidates. Only a trusted sync host with service-role/admin
credentials reviews candidates, promotes official memory, runs Dream / archive /
forgetting, and pushes reviewed read copies or derived indexes back out.

This boundary should survive every adapter choice: local SQLite, self-hosted
Gateway / Remote Server, Supabase, Obsidian, local MCP, future vector search,
and future Vault Cloud are surfaces around the same governance model, not
alternate memory semantics.

## Layer 1: Open-Source Local Memory Engine

This layer should remain open source and simple enough to trust.

It includes:

- Markdown and SQLite source of truth
- CLI and MCP tools
- local search and bounded reads
- candidate memory and promotion flow
- privacy, duplicate, metadata, and quality gates
- Obsidian import/export and review-friendly Markdown
- backup, restore, and verification
- basic audit metadata
- optional local semantic search
- optional central derived vector index as a rebuildable retrieval cache, not a
  second source of truth

Primary users:

- solo developers
- agent-heavy builders
- open-source agent framework users
- local-first teams
- users of Hermes Agent, Claude Code, Codex, OpenClaw, OpenCode, n8n, or similar tools

This layer builds trust, adoption, and the shared protocol surface.

## Layer 2: Self-Host Team Edition

This is the first commercial or pilot-ready layer.

It should help small teams share memory without giving every agent the same
unbounded view.

Capabilities:

- shared project vault
- private plus shared memory layout
- multi-agent identity and access profiles
- review inbox for memory candidates
- promote / reject / delay workflow
- rollback and deprecation workflow
- team dashboard
- memory health reports
- optional backend adapters: self-hosted Gateway / Remote Server, Supabase, or
  Postgres-backed sharing
- trusted local central memory host deployment
- trusted-host vector read index for shared retrieval, after access-policy and
  stale-index safeguards are in place

The core promise:

> Multiple agents can share experience without polluting each other or leaking
> private memory.

## Layer 3: Vault Cloud / Hosted Backend

Vault Cloud should be delayed until self-host usage proves that teams want the
workflow but do not want to maintain the infrastructure. It should be a managed
backend for the same Vault Governance Contract, not a replacement product model.

Possible hosted features:

- managed memory gateway / backend adapter
- hosted review dashboard
- team API key management
- managed backups
- managed or customer-selected embeddings and derived vector indexes
- usage analytics
- integration templates
- memory health reports

Commercial framing:

> Run it yourself, connect Supabase, or use Vault Cloud when you do not want to
> operate memory infrastructure.

Cloud beta should require real traction signals:

- multiple teams already using self-host
- repeated requests for managed hosting
- clear integration path
- evidence that review dashboards are used weekly

## Layer 4: Enterprise Governance Platform

Enterprise should sell governance, not storage.

Capabilities:

- SSO / SAML
- advanced RBAC and agent roles
- audit log export
- retention and deletion policy
- PII and secret redaction
- BYOC, VPC, or on-prem deployment
- compliance review reports
- dedicated support
- custom agent integrations

The enterprise value proposition:

> The organization can control what its agents remember, who may use that
> memory, when it expires, and how mistakes are audited or rolled back.

## Open-Core Boundary

Keep open source:

- local vault
- SQLite and Markdown storage
- CLI and MCP basics
- search and bounded reads
- candidate-first review
- basic gates
- backup / restore
- import / export
- example adapters

Consider paid tiers for:

- hosted dashboards
- team review queues
- multi-agent fleet views
- managed gateway
- team analytics
- advanced policy engine
- SSO and enterprise RBAC
- retention and audit exports
- BYOC / VPC / on-prem support
