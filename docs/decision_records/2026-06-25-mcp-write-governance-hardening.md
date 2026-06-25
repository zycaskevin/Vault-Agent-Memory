# MCP Write Governance Hardening

Date: 2026-06-25

## Context

Vault-for-LLM has moved from a local project memory tool into a multi-runtime Agent memory layer. Claude Code, Codex, OpenClaw, Hermes, n8n, Coze, and other runtimes can all point at the same vault or a Supabase-synced remote reader.

That is useful, but it changes the threat model. A shared vault should be easy to read through bounded tools, while writes into official memory should stay deliberate.

## Decision

Add write-side MCP governance without changing the existing local CLI path.

- Low-sensitivity `project` writes remain compatible.
- `shared` and `public` writes require `allow_shared=true`.
- `private` writes require `agent_id` and `allow_private=true`.
- `high` writes require `agent_id` and `allow_high_sensitivity=true`.
- `restricted` writes require `agent_id`, `allow_restricted=true`, and owner/allow-list alignment.
- MCP tool calls get a simple in-process rate limiter with environment-variable controls.
- The privacy gate warns on prompt-injection-like content and encoded sensitive content.

## Consequences

Autonomous agents can still propose normal project memories. Broader writes now need explicit capability flags, which makes shared-vault installs safer and easier to audit.

This is intentionally not a full authentication system. It is a local governance boundary for MCP tools. Hosted or cross-host deployments still need network isolation, scoped tokens, Supabase RLS/RPC, and service-role key separation.

## Follow-Ups

- Add a deeper remote doctor check for deployed Supabase policy drift.
- Split MCP tools into smaller modules.
- Add module-size gates so future security work does not disappear inside large files.
