# Governed Memory Demo Packaging

Date: 2026-07-03

## Context

Vault-for-LLM's public positioning depends on proving that it is not another
RAG database or notes app. The strongest product proof is the three-agent
governed memory lifecycle:

```text
propose -> review -> promote -> search -> bounded read -> rollback -> audit
```

The repo already had `vault demo agent-governance`, a runbook, and evidence
artifacts. The gap was first-run clarity: after running the command, a new user
could still see several files and wonder which one to open first.

## Decision

The demo command now generates a `reports/demo/start-here.md` file. It is the
first artifact a person should open after running the demo. It explains the
30-second story, the file reading order, and the one-sentence close.

The demo also generates public talk tracks in three languages:

- English: `public-demo-script.md`
- Traditional Chinese: `public-demo-script.zh-Hant.md`
- Simplified Chinese: `public-demo-script.zh-CN.md`

The runbook and demo pack docs now point to `start-here.md` first.

## Consequences

- The demo is easier to hand to external users, reviewers, and agents.
- Future changes to the demo must keep the first-run path clear.
- Public demos should lead with memory governance, not embeddings, vector
  search, or benchmark numbers.
- Generated artifacts should remain public-safe and require no cloud service,
  private data, or hidden runtime state.
