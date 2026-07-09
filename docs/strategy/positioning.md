# Positioning

Vault Agent Memory is not trying to win by storing more text than a RAG database or
recalling more chat facts than a hosted memory provider.

Its strongest category is:

> Local-first, self-hostable, auditable Agent Memory Governance.

The operating model that makes the category concrete:

> Single-host sharing, multi-host governed sync.

On one trusted machine, several agents can share one Vault. Across machines,
remote agents can read approved memory and submit candidates, but only a
trusted sync host promotes official memory and runs lifecycle jobs. That is the
line between governed shared memory and a polluted multi-writer memory store.

The user-facing sentence:

> Vault Agent Memory is the memory governance layer for multi-agent teams. It lets
> organizations safely manage what AI agents remember, trust, share, forget,
> and roll back.

The product boundary sentence:

> Vault works standalone, but can also become the governed memory backend for
> other agent and memory frameworks.

`vault-for-llm` remains the Python package and compatibility install path. The
canonical repository slug is `Vault-Agent-Memory`. Use Vault Agent Memory as the
product display name.

The sharper product claim:

> Agent memory is not about remembering more. It is about remembering with
> trust, review, rollback, and audit.

## Why This Is Not Just RAG

RAG usually asks whether an agent can retrieve the right chunk.

Agent memory governance asks a wider set of questions:

- Who proposed this memory?
- What source or evidence supports it?
- Did it pass privacy, duplicate, metadata, and quality gates?
- Who promoted it into active shared knowledge?
- Which agents can read it?
- When does it expire?
- What replaced it if it became stale?
- Can a bad memory be rolled back and audited?

Vault should demonstrate this lifecycle repeatedly:

```text
raw note
  -> memory candidate
  -> privacy / duplicate / metadata / quality gates
  -> human or policy review
  -> promoted memory
  -> searchable shared memory
  -> expire / deprecate / rollback / audit
```

This is the boundary between a memory dump and a governed memory system.

## Dangerous Failure Modes

### Category Confusion

People may mistake Vault for:

- a vector database
- a note app
- an Obsidian plugin
- a generic project RAG tool

The answer is to keep showing the memory lifecycle demo:

```text
propose -> review -> promote -> search -> bounded read -> rollback -> audit
```

### Cloud Too Early

Cloud hosting adds auth, billing, tenant isolation, uptime, security, support,
and incident response before the core workflow may be proven.

Cloud should come after self-host traction, not before it.

### No Agent Integration Wedge

A good governance model is not enough if it does not sit inside daily agent
workflows.

The first wedge should be a shared-memory demo across common agent surfaces:

- Hermes Agent
- Claude Code
- Codex

### Memory Pollution

Silent auto-promote can destroy trust. Low-quality notes, repeated status
updates, and private observations should not flood active shared memory.

Default behavior should stay candidate-first and review-first. Low-risk
automation may help triage, but it should not silently publish sensitive or
uncertain memories.

### Enterprise Feature Trap

SSO, advanced RBAC, compliance exports, and procurement features are expensive
to build before product value is proven.

Do not build enterprise weight only because it sounds strategic. Build it after
committed pilots reveal repeated requirements.

## Messaging Rules

Prefer:

- "memory governance"
- "candidate-first memory"
- "reviewable shared memory"
- "rollback and audit"
- "local-first and self-hostable"

Avoid leading with:

- "vector memory"
- "AI notes"
- "Obsidian plugin"
- "RAG database"
- "chatbot memory"

Those features exist, but they are not the category.
