# Release Stabilization Checklist

Vault-for-LLM should merge focused maintenance PRs before publishing the next
external package release. Use this checklist when deciding whether `main` is
ready to become a new release.

## Stabilization Queue

| Area | Done when |
| --- | --- |
| Large-module paydown | Remaining near-limit modules have clear ownership boundaries or a documented reason to stay as-is. |
| README cleanup | README gives the short product path; detailed command and integration guidance lives in focused docs. |
| MCP profile guidance | Agent docs recommend `core` by default, explain when to use `review`, `maintenance`, `remote`, and `full`, and warn about token/tool-surface cost. |
| Automation review UX | `automation brief`, `inbox`, and `handoff` show compact, deduped review cards and hide raw candidate content by default. |
| Temporal memory | Search and docs explain how current, old, superseded, and valid-window facts are handled. |
| Supabase safety | Remote-reader, RLS/RPC, and multi-Agent access examples are tested with least-privilege keys; remote map/read stays on guarded RPCs instead of direct table reads. |
| Install smoke matrix | Source checkout and clean wheel install both validate CLI, MCP stdio, setup-agent, automation, migration, and key integrations. |

## Current Stabilization Evidence

This batch should be treated as stabilization work, not as a reason to publish a
new release by itself.

| Area | Evidence |
| --- | --- |
| Large-module paydown | PR #214 split runtime-template install and startup-contract doctor helpers into `vault.agent_setup_runtime`, with a decision record for the new boundary. Remaining near-limit modules stay under the module-size gate and should be split by ownership, not by line count alone. |
| README cleanup | README now keeps the daily path short and points detailed MCP/profile guidance to focused docs. |
| MCP profile guidance | PR #213 recommends `core` for daily agents, documents `review`, `remote`, `maintenance`, and `full`, and records the tool-schema/context tradeoff. |
| Automation review UX | PR #210 deduped automation brief review cards while keeping raw candidate content hidden by default. |
| Temporal memory | `tests/test_memory_pipeline_temporal_reflection.py` and `tests/test_mcp_memory.py::test_mcp_memory_pipeline_temporal_and_reflection` cover pipeline, temporal status/list, search state marking, and reflection surfaces. |
| Supabase safety | PR #215 verifies remote search/map/read stay on guarded Supabase RPCs and do not regress to direct `vault_knowledge*` table reads. |
| Install smoke matrix | PR #212 added `scripts/install_smoke_matrix.py`; source smoke validates CLI and actual core-profile MCP calls. |

## Required Local Gates

Run these before opening a release PR or tag:

```bash
PYTHONPATH=. pytest -q
PYTHONPATH=. python scripts/module_size_gate.py
PYTHONPATH=. python scripts/public_pr_gate.py
PYTHONPATH=. python scripts/check_release_parity.py
PYTHONPATH=. python scripts/readme_command_smoke.py
PYTHONPATH=. python scripts/history_privacy_scan.py
python -m build
twine check dist/*
```

## Required Install Smoke

The release should be checked from a clean environment, not only from the source
checkout.

Run the install smoke matrix after building the wheel:

```bash
python -m build
PYTHONPATH=. uv run --with mcp --with anthropic python scripts/install_smoke_matrix.py \
  --mode both \
  --wheel dist/vault_for_llm-*.whl \
  --venv-python python3.11
```

The matrix checks both source-checkout and clean wheel-install behavior. It
creates temporary projects and runs:

- `vault --version`
- `vault init`
- `vault add`
- `vault search`
- `vault list`
- `vault map build`
- `vault map read`
- `vault remember`
- `vault candidates`
- `vault capture session`
- `vault automation brief`
- `vault automation cycle --write-workspace`
- `vault automation handoff`
- `vault db status`
- `vault usage stats --json`
- `vault-mcp --tool-profile core`

The MCP step includes actual client calls to:

- `vault_search`
- `vault_read_range`

Use `--mode source` for fast PR validation and `--mode wheel` when checking only
the built package. The source-mode MCP client also needs MCP runtime
dependencies, so run it through the same dependency wrapper:

```bash
PYTHONPATH=. uv run --with mcp --with anthropic python scripts/install_smoke_matrix.py \
  --mode source \
  --json
```

If the current Python cannot create a venv on the release machine, pass an
explicit interpreter:

```bash
PYTHONPATH=. uv run --with mcp --with anthropic python scripts/install_smoke_matrix.py \
  --mode wheel \
  --wheel dist/vault_for_llm-*.whl \
  --venv-python python3.11
```

## Optional Advanced Smokes

Run these when the release touches the relevant area:

- `vault setup-agent` generated artifact validation.
- Obsidian import/export dry-run and one real import.
- Supabase remote reader and RLS/RPC validation.
- Semantic index smoke with hash provider and, when available, one real embedding provider.
- Migration smoke against an older `vault.db` fixture.

For Supabase-related changes, include the local no-network guard:

```bash
PYTHONPATH=. uv run pytest -q tests/test_cli_extended.py::TestRemoteCli
```

That test verifies `vault_remote_search`, `vault_remote_map_show`, and
`vault_remote_read_range` use guarded RPCs such as `vault_search_readable`,
`vault_get_readable`, `vault_nodes_readable`, and `vault_claims_readable`. It
should fail if remote readers regress to direct `vault_knowledge*` table reads.

## Release Cadence Rule

Do not release just because a maintenance PR merged.

Release when the batch is meaningful to external users, fixes a security or
privacy issue, or changes install/runtime behavior in a way users should receive.
