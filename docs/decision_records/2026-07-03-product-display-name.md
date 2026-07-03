# Product Display Name

Date: 2026-07-03

## Decision

Use **Vault Agent Memory** as the product display name.

Keep the existing technical identifiers unchanged for compatibility:

- Python package: `vault-for-llm`
- CLI command: `vault`
- MCP command: `vault-mcp`
- repository slug: `Vault-for-LLM`

Public entry surfaces should introduce the product as Vault Agent Memory and
explain that it is installed through `vault-for-llm`.

## Rationale

The old display name, Vault-for-LLM, worked as a package and repository slug,
but it reads like an implementation-era project name. The current product
position is broader and clearer:

> Local-first memory governance for AI agents.

Vault Agent Memory better communicates that the product is for agent memory
workflows, not a generic LLM utility, vector database, note app, or secrets
vault.

Keeping the package and command names stable avoids unnecessary breakage for
published PyPI installs, existing docs, MCP configs, automation templates, and
agent install prompts.

## Writing Rules

- Use "Vault Agent Memory" for product-facing headings, landing pages, README
  introductions, guide titles, and marketplace-style descriptions.
- Use `vault-for-llm` when referring to the Python package, install command,
  pinned dependency, or compatibility slug.
- Use `vault` when referring to the CLI command.
- Do not rewrite historical release notes only to rename the product.
- When both names appear, prefer this wording:

  > Vault Agent Memory is installed as `vault-for-llm`.

## Non-Goals

- This does not rename the PyPI package.
- This does not rename the repository.
- This does not change import paths, CLI commands, MCP tool names, database
  names, or existing automation contracts.
- This does not require rewriting old announcements or archived review notes.
