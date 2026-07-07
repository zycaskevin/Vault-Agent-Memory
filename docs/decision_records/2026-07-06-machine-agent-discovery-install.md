# Decision Record: Machine Agent Discovery During Setup

Date: 2026-07-06

## Context

Vault Agent Memory can serve multiple local and hosted Agents, but a packaged
runtime install is not the same thing as connecting every Agent to the same
Vault project. A machine can already contain Codex, OpenClaw, Claude Code,
Hermes, n8n, Coze templates, and older Vault projects. If setup silently creates
another project directory, the user may believe they installed a shared memory
foundation while each Agent is still reading a different vault.

## Decision

`vault setup-agent` should perform read-only machine discovery before choosing
the project directory in interactive builder setup. Discovery reports:

- registered Agents from the local agent registry
- likely Vault project directories under standard local paths
- Codex MCP Vault project hints from `~/.codex/config.toml`
- OpenClaw Vault plugin and default project hints from `~/.openclaw`

When existing Vault projects are found and the user has not supplied
`--agent-project-dir`, interactive setup asks whether this Agent should connect
to an existing Vault project or create a new one. The generated setup payload
also includes `machine_discovery` so non-interactive operators and Agents can
detect accidental split-brain installs.

The same read-only discovery is exposed as:

```bash
vault agent discover --json
```

Use this before repointing runtimes or debugging why two Agents appear to have
different memory.

## Product Rule

Installing Vault installs the runtime. Connecting an Agent selects which Vault
project that Agent reads and writes. Multiple Agents share memory only when
their local adapters point at the same `--project-dir` or their hosted adapters
point at the same reviewed remote read layer.

## Boundary

Discovery is read-only. It does not rewrite Codex, OpenClaw, Claude Code, Coze,
n8n, or Gateway configuration by itself. Repointing runtime configs remains an
explicit apply step so setup cannot silently move an Agent onto a different
memory source.

## Runtime Repointing

OpenClaw can be safely repointed with a dry-run-first command:

```bash
vault agent connect-runtime --runtime openclaw --project ~/Vaults/project-memory --json
vault agent connect-runtime --runtime openclaw --project ~/Vaults/project-memory --apply --json
```

The command updates only the Vault plugin entry, preserves unrelated OpenClaw
plugin config, and backs up existing `openclaw.json` by default.

## Hosted Reader Validation

Hosted-reader templates are not considered connected just because files exist.
`vault remote status --json` inspects Coze OpenAPI `servers.url` values and
emits a high-severity `remote_reader_openapi_placeholder_url` warning when a
template still points at placeholders such as `YOUR_PROJECT` or
`vault.example.internal`. The Coze validation checklist now requires that
warning to be absent before calling Coze connected.

## Follow-Up

- Extend explicit repoint/apply support beyond OpenClaw to Codex, Claude Code,
  and Hermes where each runtime has a stable config-file contract.
- Add live validation that checks each selected Agent can search the same
  sentinel memory through its configured adapter.
- Extend n8n hosted-reader validation beyond CLI template presence once an HTTP
  connector form is generated.
