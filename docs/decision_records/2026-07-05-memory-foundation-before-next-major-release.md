# Memory Foundation Before Next Major Release

Date: 2026-07-05

## Decision

Do not cut a small patch release only for the daily-loop review queue fix.

The next release should wait until the memory foundation is operationally
coherent, then ship as a larger version with the daily-loop, Central Memory
Station, review queue, live runtime, and sync surfaces validated together.

## Why

The current work moved daily-loop from repo feature work into the live Codex
runtime and exposed several foundation-level issues:

- reviewed `rejected` candidates could reappear in the human review queue
- `promoted` candidates could still appear in review surfaces
- `daily-loop run --write-report` is not a pure report refresh because it can
  capture new artifacts into the candidate inbox
- stale agent registry entries could keep fleet health red even when the live
  Codex runtime was current
- live runtime, Git-backed source, and shared update status can drift unless
  each surface is checked explicitly

These are not just release-note bugs. They affect whether Vault Agent Memory can
serve as a reliable memory foundation for agents.

## Current State

Completed:

- Codex live runtime is on Vault Agent Memory `0.7.31`.
- `vault_daily_loop_status` and `vault_daily_loop_report` are visible in the
  live MCP tool surface.
- Supabase remote search works through RPC `vault_search_readable`.
- Candidate review queue is cleared in the live Codex vault.
- Stale shared registry entries were removed; fleet update health is green with
  only `codex` registered.
- The automation inbox fix was committed locally as
  `d3982fa Fix automation inbox reviewed candidate queue`.
- The Git-backed repo now has `vault daily-loop report --refresh --write-report`,
  a read-only refresh path that rebuilds the latest daily-loop report without
  capture, reflection, sync writes, or new candidate writes.
- The live Codex private-memory vault regenerated a clean
  `reports/daily-loop/daily-loop-latest.*` through that refresh path; candidate
  counts stayed unchanged and no pending review queue remained.
- Supabase service-role status now has an explicit trusted-host marker:
  `VAULT_SUPABASE_TRUSTED_SYNC_HOST=1`. Without the marker, remote status keeps
  warning about service-role credentials; with it, trusted sync hosts can be
  distinguished from remote-reader environments.

Still required before the next release:

1. Merge or otherwise land the automation inbox queue fix in the canonical
   upstream path.
2. Restart the live MCP session after env-marker updates so MCP status reads
   the trusted-host marker from process startup.
3. Reinstall or repoint the live runtime from the final release artifact rather
   than relying on a temporary editable checkout.
4. Run release-quality checks across daily-loop, automation inbox, MCP tools,
   update-status, Supabase remote search, and clean install/import behavior.

## Release Gate

The next release can proceed only when all of the following are true:

- `vault automation inbox` reports no already-reviewed candidates in the review
  queue.
- `vault daily-loop status` and MCP `vault_daily_loop_status` agree on the
  latest report state.
- `vault daily-loop report --refresh --write-report` does not create candidate
  noise.
- `mcp__vault.vault_update_status` reports `ok=true` for the live Codex runtime.
- Supabase read-only search works without exposing service-role keys to reader
  agents, and trusted sync hosts explicitly set
  `VAULT_SUPABASE_TRUSTED_SYNC_HOST=1`.
- A clean environment install can run the key CLI/MCP smoke paths.

## Non-Goals

- No emergency patch release for this single queue fix.
- No direct remote writes into active knowledge.
- No multi-master active-memory merge before candidate-first sync is stable.
- No broad registry deletion beyond unregistering confirmed stale entries.

## Operator Guidance

Treat the current local commit as foundation hardening, not as a release trigger.
Finish the remaining foundation gates first, then publish a larger version with
the whole memory-foundation story validated end to end.
