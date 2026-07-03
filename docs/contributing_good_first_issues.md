# Good First Issue Ideas

This list helps new contributors find work that does not require understanding
the whole Vault-for-LLM architecture.

Before starting, read [CONTRIBUTING.md](../CONTRIBUTING.md). If a task changes
schema, security defaults, Gateway behavior, sync behavior, or automation
policy, open an issue first.

## Documentation

### Add one Agent client quickstart

Pick one client and add a short "minimum viable setup" example:

- Codex
- Claude Code
- Hermes
- OpenClaw / OpenCode
- Coze
- n8n
- Cursor

Keep it practical:

1. what the user asks the Agent to do;
2. which Vault command or MCP config is generated;
3. how to smoke-test that search or daily report works;
4. what not to claim.

### Add one Obsidian-as-GUI example

Write a small example showing:

- folder structure;
- frontmatter fields;
- one note imported into Vault;
- one Vault memory exported back to Obsidian;
- how conflicts should be reviewed.

### Improve one multilingual page

Pick one English, Traditional Chinese, or Simplified Chinese doc and make it
shorter, warmer, and more precise. Avoid changing technical meaning.

## Tests

### Add a README or guide smoke assertion

Add a focused test that protects one documented command, prompt, or generated
guide from drifting.

Good candidates:

- `vault guide --intent install`
- `vault daily-report --json`
- `vault setup-agent --memory-mode governed-auto`
- generated Obsidian conflict text

### Add a privacy regression fixture

Add a test that proves sensitive content is detected and does not auto-promote.
Use fake data only.

Good candidates:

- fake API key;
- fake bearer token;
- fake Taiwan mobile number;
- fake Taiwan ID-like string.

## CLI / JSON Contract

### Normalize one JSON output

Find one Agent-used command that has partial JSON output and make it match the
standard shape:

```json
{
  "ok": true,
  "status": "completed",
  "next_action": "..."
}
```

Keep this small. Update tests and docs for that command only.

### Improve one error message

Find one confusing CLI error and make it actionable. Good errors should say:

- what failed;
- why it likely failed;
- what the user or Agent should do next.

## Examples

### Add a migration sample

Create a small sanitized sample for importing memory from another tool as
candidates, not active knowledge.

Useful examples:

- Chatbox export;
- generic JSON conversation summary;
- Markdown notes folder.

### Add a daily report sample

Create a tiny example daily report showing:

- auto-kept low-risk memories;
- review-needed decisions;
- rejected or delayed noisy candidates;
- no more than five human decisions.

## Not Good First Issues

These are important, but should start with an issue or design discussion:

- database schema migration;
- Gateway security model;
- remote sync conflict resolution;
- agent identity or HMAC changes;
- auto-promote policy changes;
- encryption, SSO, RBAC, or enterprise controls;
- replacing the storage backend.
