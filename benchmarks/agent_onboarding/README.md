# Agent onboarding benchmark fixtures

This directory contains public-safe fixtures for comparing exported agent
sessions with governed Vault project memory.

The fixtures intentionally do not include real Hermes, Codex, Claude, or user
session exports. Bring those from your own machine at run time and keep reports
outside the repository.

- `project_onboarding.repo.json` - Search QA cases for the repository-doc
  onboarding benchmark.
- `session_candidates.example.json` - candidate-memory examples for the
  candidate-first gate check.

## Build the repository-doc Vault

Create a temporary Vault database from the current source checkout:

```bash
python scripts/build_agent_onboarding_vault.py \
  --output-dir /tmp/vault-agent-onboarding
```

The builder writes a local SQLite database and manifest under the output
directory. It parses the selected README/docs files into Document Map nodes so
Search QA can measure `read_range` guidance.

## Run with a real exported session

Pass one or more exported session files:

```bash
python scripts/agent_onboarding_benchmark.py \
  --provider codex \
  --session-file /path/to/codex-session.jsonl \
  --qa-file benchmarks/agent_onboarding/project_onboarding.repo.json \
  --db-path /tmp/vault-agent-onboarding/repo-docs-vault.db \
  --candidate-file benchmarks/agent_onboarding/session_candidates.example.json \
  --output /tmp/vault-agent-onboarding/report.json
```

This compares what the exported session text contains against what the governed
Vault can retrieve from project source-of-truth documents. It is not a test of
hidden runtime memory internals.
