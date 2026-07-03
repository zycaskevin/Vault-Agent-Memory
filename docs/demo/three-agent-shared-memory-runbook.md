# Three-Agent Shared Memory Runbook

This runbook turns the local governance demo into a real integration shape for
three agent surfaces:

- Codex
- Claude Code
- Hermes Agent

The goal is not to prove that Vault can search text. The goal is to prove that
multiple agents can share a governed project memory without losing review,
source, rollback, and audit.

## Principle

Use one shared project vault for reviewed project knowledge:

```text
~/Vaults/demo-shared-memory/vault.db
```

Each agent keeps its own identity and runtime-specific private memory outside
the shared vault. The shared vault is for reviewed project lessons, SOPs,
decisions, bug roots, and task handoffs that another agent should be able to
reuse.

## Step 1: Create The Shared Vault

```bash
vault init ~/Vaults/demo-shared-memory
vault demo agent-governance --project-dir ~/Vaults/demo-shared-memory --json
```

Open the generated files:

```text
~/Vaults/demo-shared-memory/reports/demo/start-here.md
~/Vaults/demo-shared-memory/reports/demo/demo-report.md
~/Vaults/demo-shared-memory/reports/demo/public-demo-script.md
~/Vaults/demo-shared-memory/reports/demo/public-demo-script.zh-Hant.md
~/Vaults/demo-shared-memory/reports/demo/public-demo-script.zh-CN.md
~/Vaults/demo-shared-memory/reports/demo/acceptance-checklist.md
~/Vaults/demo-shared-memory/agent-config-snippets/
```

Start with `start-here.md`. It tells a new user which proof file to open first,
which talk track to use, and what the demo is supposed to prove before any real
agent runtime is configured.

## Step 2: Pick One Access Mode

### Option A: Local MCP

Use this when all agents can start a local stdio MCP server.

```bash
vault-mcp --project-dir ~/Vaults/demo-shared-memory --tool-profile core
```

Each agent should use the same `project-dir` and a different `agent_id`.

### Option B: Local Gateway

Use this when agents, scripts, n8n, or browser-based connectors should share
one small HTTP contract instead of a full MCP tool surface.

Set the Gateway auth token in your shell, then run:

```bash
vault gateway serve --project-dir ~/Vaults/demo-shared-memory
```

Then verify:

```bash
curl -s http://127.0.0.1:8789/health \
  -H "Authorization: Bearer <demo-token>"
```

For a public demo, local MCP is simpler. Gateway is better when showing Coze,
n8n, or cross-runtime HTTP adapters.

## Step 3: Configure Agent Identities

Use stable, public-safe agent IDs:

| Agent surface | Suggested `agent_id` | Role in demo |
|---|---|---|
| Codex | `codex` | proposes a reusable lesson |
| Claude Code | `claude-code` | reviews/promotes candidate memory |
| Hermes Agent | `hermes` | recalls promoted memory with bounded citation |

Do not put personal names, private personas, API keys, or local-only paths into
public demo startup files.

## Step 4: Agent Startup Contract

Each agent should follow this startup contract:

```text
1. Search before answering project-memory questions.
2. Use Document Map or bounded read before citing.
3. Treat candidates as unreviewed until promoted.
4. Propose durable lessons as candidates.
5. Do not write private identity or care memory into the shared project vault.
```

The generated snippets under `agent-config-snippets/` are intentionally short.
They are suitable for project instructions such as `AGENTS.md`, `CLAUDE.md`, or
a Hermes profile bootstrap.

## Step 5: Run The Live Story

### Codex Proposes

Codex discovers a durable project lesson and proposes it as a candidate:

```text
This repo requires a specific test setup before pytest results are trusted.
```

The important point is that this does not become active shared memory
immediately.

### Claude Code Reviews

Claude Code or a human reviewer checks source evidence and promotes the
candidate only when gates pass.

The important point is that shared memory has a review boundary.

### Hermes Recalls

Hermes searches the shared vault, reads the bounded evidence range, and cites
the promoted memory.

The important point is that another agent can reuse the lesson without reading
raw private notes or unreviewed chat history.

## Step 6: Show Rollback

After promotion, show that the system has:

- a backup path
- audit events
- a candidate ID
- a promoted knowledge ID
- a bounded citation

Then explain that a stale or wrong memory should be deprecated or replaced
instead of silently lingering forever.

## What This Proves

This demo proves four things:

1. A shared Vault can be the same memory layer across agent tools.
2. Agents can propose memory without polluting active knowledge.
3. Review and promotion make shared memory trustworthy.
4. Rollback and audit keep memory accountable.

## What It Does Not Claim

This demo does not claim:

- enterprise SSO is complete
- cloud sync is required
- all memory should be shared
- agents should silently auto-promote everything
- vector search alone is the product

The product is governed continuity across agent workflows.

## Publishable Close

Use this sentence at the end of the demo:

> Vault-for-LLM is a local-first memory governance layer for agent teams. It
> helps agents remember together without turning shared memory into a garbage
> pile.
