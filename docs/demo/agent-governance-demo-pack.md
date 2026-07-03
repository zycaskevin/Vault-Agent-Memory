# Agent Governance Demo Pack

This pack is the public proof for Vault-for-LLM's positioning:

> Agents need memory governance, not just RAG.

It shows three agent identities sharing one Vault through a reviewable memory
lifecycle:

```text
propose -> review -> promote -> search -> bounded read -> rollback -> audit
```

## Run The Demo

```bash
vault demo agent-governance --json
```

For a persistent demo folder:

```bash
vault demo agent-governance --project-dir ./vault-governance-demo --json
```

The command creates:

- `reports/demo/demo-report.md`
- `reports/demo/demo-report.json`
- `reports/demo/public-demo-script.md`
- `reports/demo/acceptance-checklist.md`
- `reports/demo/evidence-summary.md`
- `reports/demo/evidence-summary.json`
- `agent-config-snippets/codex-startup.md`
- `agent-config-snippets/claude-code-startup.md`
- `agent-config-snippets/hermes-startup.md`

## What To Show

Show these artifacts in order:

1. `demo-report.md`: the lifecycle proof.
2. `public-demo-script.md`: the external talk track.
3. `evidence-summary.md`: the generated pass/fail evidence for the proof.
4. `acceptance-checklist.md`: the proof criteria.
5. `agent-config-snippets/`: the shortest setup snippets for each agent.

Do not lead with embeddings, vector search, or benchmark numbers. Lead with the
governed lifecycle.

## Recording Script

1. Start with the problem: multiple agents work on one project, but hidden or
   unreviewed memory becomes risky.
2. Run the demo command.
3. Open the report and point to the candidate, promotion, bounded citation,
   backup, and audit sections.
4. Open the startup snippets and explain that each agent can connect to the
   same shared memory while keeping its own identity and permissions.
5. Close with the product sentence:

> Vault controls what agents remember, trust, share, forget, and roll back.

## Acceptance Criteria

The demo is ready to publish only if:

- the memory starts as a candidate
- review and promotion are explicit
- a different agent can recall the promoted memory
- the answer path uses bounded read and citation
- rollback or deprecation is visible
- audit events exist
- no private data, cloud service, or hidden runtime is required

If the demo only proves search, it is not the right demo.

## Evidence Summary

`evidence-summary.json` is the machine-readable proof that the run completed the
governed memory lifecycle. It checks:

- candidate creation
- promotion into active knowledge
- search recall by another agent
- bounded read citation
- verified rollback backup
- audit event recording

Use `evidence-summary.md` in screenshots, release notes, or demo writeups when
you need a concise human-readable proof.

## Follow-Up Integrations

After the local proof works, connect the same shared vault to real agent
surfaces:

- Codex
- Claude Code
- Hermes Agent
- OpenClaw / OpenCode
- n8n or Coze through Gateway or MCP

The integration should keep the same principle: agents may propose memory, but
shared active memory should remain reviewed, source-grounded, and reversible.

For a concrete Codex + Claude Code + Hermes setup, use
[Three-Agent Shared Memory Runbook](three-agent-shared-memory-runbook.md).
