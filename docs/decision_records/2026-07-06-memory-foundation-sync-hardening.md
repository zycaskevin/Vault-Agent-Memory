# Memory Foundation Sync Hardening

Date: 2026-07-06

## Status

Accepted for the next larger release. Do not publish this as a narrow patch-only
release unless a downstream release process explicitly requires it.

## Context

The Codex private-memory runtime was usable as an agent memory foundation, but
the scheduled Supabase sync exposed two operational gaps:

- Document Map sync sent local SQLite integer `knowledge_id` values into remote
  Supabase Document Map tables whose `knowledge_id` references remote UUIDs.
- `remote status` could treat a dry-run sync report as a fresh sync report,
  masking whether a trusted host had actually pushed the reviewed read copy.

The daily human report schedule was working, and the live MCP/read path was
current, but release readiness needs truthful sync freshness and clean remote
Document Map writes.

## Decision

Document Map sync must resolve local knowledge rows to remote read-copy UUIDs
before upserting remote nodes or claims. Resolution prefers `content_hash` and
falls back to exact title matching.

Remote sync freshness must ignore pure dry-run reports. A dry-run report can be
shown as diagnostic evidence, but it must not count as `last_synced_at`; status
surfaces should warn with `sync_report_dry_run` until a trusted sync host writes
a real report.

The scheduled trusted-host sync should run the Central Memory Station worker
with `--push-read-copy` and write `reports/remote-sync-latest.json`, rather than
calling the low-level Supabase script directly. This keeps the operational
freshness surface aligned with what agents and MCP tools read.

## Validation

- Targeted regression tests passed for Document Map sync, remote status,
  Central Memory Station sync, CLI surfaces, and daily-loop status.
- A trusted Supabase sync from the local runtime completed successfully:
  knowledge inserted 3, Document Map nodes inserted 3, Document Map claims
  inserted 4, failed 0, skipped 0.
- `vault daily-loop status` reported empty sync warnings after the trusted sync
  refreshed `reports/remote-sync-latest.json` with `dry_run=false`.

## Consequences

The local agent memory foundation is operational for Codex private-memory.
Before a public/larger release, keep this hardening bundled with the daily-loop
runtime foundation and rerun the standard release-quality checks.
