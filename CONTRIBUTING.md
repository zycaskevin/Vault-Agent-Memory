# Contributing

Thanks for helping improve Vault Agent Memory.

Vault is aimed at Agent-assisted builders: people using Codex, Claude Code,
Hermes, OpenClaw, n8n, Coze, Obsidian, or similar tools who want governed
memory instead of another unmanaged RAG store. Contributions are most helpful
when they make that workflow safer, clearer, or easier to verify.

## Good First Contributions

You do not need to understand the whole system before helping. Good first
contributions usually fit one of these shapes:

- docs that make an install, MCP, Obsidian, Gateway, or daily-report workflow
  easier to follow;
- small CLI or JSON-contract consistency fixes;
- focused tests for an existing behavior;
- issue reproduction scripts for confusing setup, privacy, or sync behavior;
- examples for a specific Agent client such as Codex, Claude Code, Hermes,
  OpenClaw, Coze, n8n, Cursor, or Obsidian.

See [docs/contributing_good_first_issues.md](docs/contributing_good_first_issues.md)
for starter task ideas.

## Before You Start

- For small docs, tests, or bug fixes, opening a PR directly is fine.
- For larger behavior changes, schema changes, security changes, Gateway /
  remote-sync work, or new automation policy, please open an issue first.
- Do not include real API keys, tokens, customer data, medical data, private
  chat logs, or production vault exports in issues or PRs.
- If your report involves sensitive information, redact it and provide the
  smallest reproduction you can.

## Maintainer Response Expectations

Vault is currently maintained primarily by one maintainer with heavy Agent
assistance. That means reviews may not be instant, but the goal is:

- bug reports: initial response within about 7 days;
- small PRs: review within about 7 days;
- large design PRs: expect discussion before merge;
- security-sensitive reports: prioritize confirmation and safe reproduction
  before public detail.

If a PR is time-sensitive, say so clearly in the description.

## Install Paths

Vault keeps two supported local development paths:

- `pip` / `venv`: the common Python path and the main public install model.
- `uv`: the reproducible source-development path for maintainers, CI smoke
  checks, and coding agents.

Public users should still install releases with `pip install vault-for-llm`.
Use `uv` when working from a source checkout.

## pip Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,mcp]"
pytest -q
```

## uv Development Setup

```bash
uv sync --extra dev --extra mcp
uv run pytest -q
```

The checked-in `uv.lock` makes this path reproducible for agents and humans.

## Lockfile Policy

- Commit `uv.lock`.
- Run `uv lock` whenever `pyproject.toml` dependencies or optional extras
  change.
- Run `uv lock --check` before opening a PR that changes dependencies.
- Do not require `uv` for normal package users; keep `pip install
  vault-for-llm` working.
- Do not use the semantic extra in default CI smoke checks unless the PR is
  specifically testing semantic dependencies, because that stack is much
  heavier than core and MCP development.

## Useful Checks

Run the smallest relevant checks first, then broaden if the change touches
shared behavior.

```bash
pytest -q
python -m compileall -q vault scripts tests
python scripts/module_size_gate.py
python scripts/readme_command_smoke.py
uv lock --check
uv run python -m pytest -q tests/test_lite.py tests/test_cli_project_dir.py
```

For docs-only PRs, at least run:

```bash
python scripts/readme_command_smoke.py
git diff --check
```

For setup, CLI, MCP, Gateway, Obsidian, or sync changes, include the exact
command you used to smoke-test the user path.

## Pull Request Checklist

Before opening a PR:

- describe the user problem or bug being fixed;
- list the files or commands a reviewer should look at first;
- include validation commands and results;
- say whether the change affects CLI output, MCP tools, JSON contracts,
  database schema, security defaults, or docs only;
- keep unrelated formatting churn out of the PR.

The PR template will ask for the same information.

## Release Policy

Releases are maintainer-only and run through GitHub Actions. External
contributors do not need PyPI credentials.

## Community Standards

By participating, you agree to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).
