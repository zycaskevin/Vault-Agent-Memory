# Decision Record: Agent-Assisted Builder Positioning

Date: 2026-07-03

## Context

The v0.7.27 public path made Vault much easier to approach:

- a trilingual landing page,
- rendered three-agent demo,
- `vault guide --intent install`,
- governed-auto setup,
- daily memory report,
- candidate-first memory governance.

However, the phrase "ordinary users" can over-promise. Vault still has a real
system underneath it: MCP profiles, Gateway, Obsidian, Supabase, automation
policy, agent access, daily reports, and many optional setup files. Calling the
product a general consumer app implies an app-store level of simplicity that
does not yet match the current package.

The better public audience is narrower and more honest:

> people who already use agents, or are beginning to build with agents, and want
> one governed memory layer without studying every internal command.

## Decision

Use **Agent-assisted builders** as the primary public audience.

This includes:

- Codex users,
- Claude Code users,
- Hermes / OpenClaw / OpenCode users,
- n8n / Coze builders,
- AI-heavy developers,
- small teams building multi-agent workflows,
- Obsidian / Markdown users who want their notes to become agent-readable.

Do not position Vault as a zero-learning app for people who do not use agents.

## Public Language

Use:

- Agent-assisted onboarding
- Agent-assisted builders
- people already working with agents
- guided setup
- daily memory report
- governed-auto memory
- memory governance, not just RAG

Avoid or qualify:

- ordinary consumers
- general public
- no setup
- four questions and everything is done
- fully automatic memory
- realtime distributed database

The four-question setup remains useful, but it should be described as the
human-facing part of an agent-led install, not the full complexity of the
system.

## Product Boundary

Vault should still hide unnecessary complexity from humans:

1. The human tells an agent to install Vault.
2. The agent handles Python, package install, project directory, and smoke test.
3. The human answers a few setup questions.
4. The human reads a short daily memory report.
5. Builders can opt into advanced CLI, MCP, Gateway, Supabase, and Obsidian
   controls when needed.

This is not a retreat from ease of use. It is a more honest wedge:

> people who have entered the agent world should be able to use Vault through
> their agents, without becoming Vault experts.

## Consequences

- README and landing copy should say "Agent-assisted" or "builders" instead of
  implying a fully general consumer audience.
- `--audience consumer` can remain an internal CLI compatibility term, but docs
  should explain it as the guided, agent-assisted setup path.
- The demo should continue to show Codex / Claude Code / Hermes sharing governed
  memory because that is the strongest proof of the product category.
- Future GUI work should serve the daily report, conflict inbox, and review
  queue first, not attempt to become a general note app.
