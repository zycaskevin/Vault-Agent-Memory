# Chinese README Consumer-First Rewrite

Date: 2026-07-03

## Decision

The Traditional Chinese and Simplified Chinese README pages should lead with the
ordinary Agent user experience, not with a feature inventory.

The first screen should answer:

- What is Vault-for-LLM in plain language?
- Why would a non-expert Agent user care?
- What should the user paste to an Agent to install it?
- What happens every day after installation?

Technical details such as SQLite, MCP, Supabase, bounded read, governance
metadata, temporal fields, and CLI command variants remain important, but they
belong after the product story and the agent-first install path.

## Rationale

The earlier Chinese README pages were accurate but too dense for the target
consumer flow. They introduced too many implementation details before the reader
understood the everyday outcome:

> Let my Agents share a governed memory vault, while I only review a small daily
> report and keep control over uncertain memory.

For general Agent users, the primary interface is not a command list. The
primary interface is:

1. Copy an install prompt to an Agent.
2. Answer four setup questions.
3. Receive a daily memory report.
4. Approve, reject, delay, or keep both sides for ambiguous memory decisions.

The README should match that shape.

## Writing Rules

- Prefer "記憶金庫" / "记忆金库" over abstract infrastructure phrasing in the
  opening.
- Avoid leading with SQLite, MCP, Supabase, vector search, or implementation
  internals.
- Keep the agent install prompt near the top.
- Explain governed-auto as a daily memory loop:
  - safe low-risk memories can enter the vault;
  - uncertain, sensitive, conflicting, or strategic memories go to the report.
- Keep advanced CLI and integration details, but move them below the general
  user flow.
- Keep Traditional Chinese and Simplified Chinese pages structurally aligned.

## Non-Goals

- This does not replace the English README.
- This does not remove developer documentation.
- This does not claim that all remote sync paths are fully automatic or
  conflict-free; remote and Obsidian workflows should continue to describe
  review and resolver boundaries clearly.

## Expected Outcome

The Chinese README pages should feel less like a technical specification and
more like a clear product doorway:

> I can give this to my Agent, let it install Vault, and then review only the
> important memory decisions.
