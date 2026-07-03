# Memory Export Formats

Date: 2026-07-03

## Decision

Vault supports three read-only active-memory export formats:

- `vault export markdown --bundle DIR` for human-readable batch review.
- `vault export okf --bundle DIR` for OKF-style agent/tool exchange.
- `vault export json --bundle DIR` for machine-readable backup, migration, or
  custom transformation work.

Each exporter reads from `vault.db` and does not mutate SQLite, `raw/`,
`compiled/`, sync state, or remote targets. Each exporter supports `--dry-run`
and excludes `scope: private` plus `sensitivity: restricted` by default.

## Rationale

Markdown, OKF, and JSON serve different user jobs:

- Markdown is easiest to inspect, diff, and selectively re-import.
- OKF keeps the portable knowledge-bundle contract for agents and tools.
- JSON preserves the full row-shaped memory data for backup and migration
  workflows.

Combining these into one overloaded format would make onboarding harder and
would blur safety expectations around private or restricted memory.

## Operational Notes

`--include-private` and `--include-restricted` must stay explicit because export
bundles are easy to copy outside the original Vault boundary. Product docs
should describe exported bundles as sensitive artifacts whenever those flags are
used.
