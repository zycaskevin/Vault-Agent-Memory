# Vault-for-LLM Public Release Progress

Last updated: 2026-05-17 01:45 CST

## Current Task: Clarify public positioning and alpha roadmap — DONE

### Goal
Position Vault-for-LLM as a local-first agent memory layer with experimental quality tools, without overstating alpha-stage maturity. Public docs should explain that the project is evolving toward an agent memory QA layer while keeping the stable path centered on `vault init`, `vault add`, `vault compile`, `vault search`, and `vault-mcp`.

## Previous Task: Remove pre-Vault internal naming from public codebase — DONE

### Goal
Rename internal modules, file names, database names, CLI/MCP surfaces, docs, and tests to the public Vault-for-LLM naming. The repository should no longer tell users that old names are kept for compatibility.

### Scope
- Rename Python package/module path to the Vault-branded `vault` package.
- Rename internal module files to Vault-branded/generic file names such as `cli.py`, `mcp.py`, `db.py`, etc.
- Make console scripts point to Vault-branded modules.
- Make MCP public names use `vault_*` and `vault-mcp`; remove old public tool aliases unless a migration shim is strictly required internally.
- Prefer `vault.db` as the default generated database name.
- Update tests, docs, schema, audit report, and examples to stop presenting old names as the default.
- Keep changes surgical: do not redesign retrieval, schema, sync, or search behavior beyond renaming/migration compatibility.

### Public Repository Constraints
- Public-facing brand: **Vault-for-LLM**, `vault`, `vault-mcp`.
- Core promise: local-first SQLite knowledge vault for LLM agents.
- SQLite is the source of truth; Supabase is optional sync/read infrastructure.
- No private/internal context or user-specific paths in public docs.
- Any backward compatibility shim must be minimal, hidden from public docs, and covered by tests.

### Verification Checklist
- [ ] `vault --help` works and points at Vault-branded modules.
- [ ] `vault-mcp --help` works and points at Vault-branded modules.
- [ ] New projects create/use `vault.db` by default.
- [ ] New and existing Vault-branded projects consistently use `vault.db`.
- [ ] MCP `tools/list` exposes `vault_*` tools and no old public tool aliases.
- [ ] Full pytest passes in the project env.
- [ ] `git diff --check` and Python compile checks pass.
- [ ] Markdown/code scans show no public-facing old naming except deliberate historical audit notes.
- [ ] Graphify is rebuilt after code changes.
- [ ] Independent review passes before commit/PR.
