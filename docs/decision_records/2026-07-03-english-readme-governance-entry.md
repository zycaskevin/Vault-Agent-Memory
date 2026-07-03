# English README Governance Entry

Date: 2026-07-03

## Decision

The English README should become a product entry plus developer trust page.

It should not be as short and consumer-only as the Chinese README pages, because
GitHub and PyPI readers often need to evaluate technical credibility quickly.
However, it should still lead with the product category:

> Local-first memory governance for AI agents.

The first screen should explain the outcome before introducing implementation
details:

- agents share one governed memory vault;
- memory moves through propose, review, promote, bounded read, rollback, and
  audit;
- ordinary users can ask an agent to install Vault and then review a short
  daily report;
- developers can still find MCP, CLI, SQLite, Supabase, Gateway, Obsidian, and
  Search QA details below.

## Rationale

The previous English README was accurate but too broad. It mixed product
positioning, consumer setup, generated installer details, MCP profile guidance,
automation internals, remote server templates, and long lifecycle explanations
in one long page.

That made the project look powerful, but also made the core message easier to
miss:

> Vault-for-LLM is not another RAG database. It is a memory governance layer for
> multi-agent workflows.

The English README should still preserve enough technical proof for developer
adoption, but advanced command surfaces belong in linked docs.

## Writing Rules

- Put "memory governance" near the top.
- Keep the agent-first install prompt near the top.
- Keep the daily report / governed-auto loop visible.
- Move long non-interactive setup examples and generated-template details to
  `docs/agent_install.md` and integration docs.
- Keep MCP profiles, quickstart commands, Gateway/Supabase, Obsidian, Search QA,
  and maturity sections, but make them short.
- Avoid framing Vault as just "local project memory" or just "RAG".

## Non-Goals

- This does not remove developer documentation.
- This does not claim remote sharing is full offline multi-master sync.
- This does not change the Chinese README pages, which remain more
  consumer-first and less technical.

## Expected Outcome

An English-speaking GitHub reader should understand within one minute:

1. why Vault is different from RAG and note apps;
2. how a normal user can let an agent install it;
3. why developers can trust the implementation enough to inspect deeper docs.
