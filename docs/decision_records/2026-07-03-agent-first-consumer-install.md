# Agent-First Consumer Install

## Context

Vault has many CLI commands because agents, scheduled jobs, MCP tools, sync
adapters, and maintenance workflows need precise operations. Ordinary users
should not need to understand that full surface before receiving value.

The consumer product direction is:

- humans choose intent,
- agents choose commands,
- daily use is a short memory report,
- low-risk sourced memories can be kept automatically,
- uncertain, sensitive, conflicting, strategic, or low-trust memories stay in
  the human review surface.

## Decision

The primary public onboarding path is now the agent-first install prompt exposed
by:

```bash
vault guide --intent install
```

That prompt tells the installing agent to use consumer governed-auto mode and
to ask only the small setup questions:

- language,
- independent or shared vault,
- optional Obsidian / Supabase connections,
- daily report time.

The agent should hide advanced flags unless the user asks, run the guided
installer, finish with a smoke check, and show the daily report or local GUI
link.

## Consequences

- README and agent-first documentation should point ordinary users to
  `vault guide --intent install`, not to the full CLI reference.
- `vault setup-agent --audience consumer` remains the implementation path.
- `governed-auto` remains the default consumer memory mode.
- The full CLI remains available for builders, scheduled jobs, and maintenance,
  but it is no longer the primary human mental model.

## Non-goals

- Do not remove advanced CLI or MCP controls.
- Do not silently promote high-impact or sensitive memories.
- Do not make ordinary users configure low-level MCP profiles, automation
  policy files, or sync templates by hand.
