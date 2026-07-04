# Repository Rename Migration

Date: 2026-07-04

## Decision

When the repository is renamed, use **Vault-Agent-Memory** as the GitHub
repository slug.

Keep the compatibility identifiers from the product display-name decision:

- Product display name: **Vault Agent Memory**
- GitHub repository slug after rename: `Vault-Agent-Memory`
- Python package: `vault-for-llm`
- CLI command: `vault`
- MCP command: `vault-mcp`

The repository rename must be treated as an operational migration, not as a
normal wording cleanup. Do not change install URLs to the new slug until the
GitHub repository has actually been renamed and the new raw URLs have been
validated.

## Rationale

`Vault-Agent-Memory` aligns the public repository name with the new product
display name while preserving the existing package and runtime contracts.

Keeping `vault-for-llm` as the package name avoids breaking PyPI installs,
dependency pins, local automation, MCP server configuration, and one-click
installer scripts. The repository slug can change with GitHub redirects, but
raw installer URLs, GitHub Pages, badges, issue templates, release links, and
Trusted Publishing configuration need explicit checks.

## Migration Order

1. Merge the display-name change first.
2. Publish this migration plan and checklist.
3. Choose a quiet release window with no active publish job.
4. Rename the GitHub repository from `Vault-for-LLM` to `Vault-Agent-Memory`.
5. Immediately update repository URLs and raw installer URLs in source docs.
6. Verify old redirects and new canonical URLs.
7. Run release readiness CI and installer smoke checks.
8. Only then announce the canonical repository URL.

## Compatibility Rules

- Keep install commands using `vault-for-llm`.
- Keep runtime paths, import paths, CLI names, MCP command names, local database
  names, and package metadata compatible.
- Keep historical announcements and review notes unchanged unless they are
  actively used as current installation instructions.
- Update current entry surfaces and templates after the repo rename:
  `README.md`, localized READMEs, install scripts, issue templates, release
  publishing docs, integration docs, and GitHub Pages references.

## Non-Goals

- This does not rename the PyPI package.
- This does not rename the CLI command.
- This does not rename MCP tools.
- This does not change database schema, local project directory names, or
  generated vault data.
- This does not execute the GitHub repository rename by itself.
