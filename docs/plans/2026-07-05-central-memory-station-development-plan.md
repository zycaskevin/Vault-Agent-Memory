# Central Memory Station Development Plan

## North Star

Vault should become the memory base for many agents and devices. A car, robot,
phone, laptop, local agent, and hosted agent can each have its own working
vault, while a trusted central memory station keeps shared memory reviewed,
searchable, synced, and recoverable.

## Simple Story

- Local vault = the agent's notebook.
- Central memory station = the family library.
- Gateway = the door guard.
- Candidate memory = a sticky note waiting for review.
- Dream = nightly cleaning and pattern finding.
- Forgetting = moving stale memory out of daily search, not destroying history.

## Phase 1: One Clear Command Surface

Goal: make the product easier to operate.

Deliverables:

- `vault start` as the orientation entry.
- `vault memory-sync` for status, push, pull, and one-shot sync.
- `vault memory-review` for candidates and conflicts.
- `vault memory-lifecycle` for Dream, forget, archive, and cold-store.
- `vault ops` for health, status, and security checks.
- Keep the older 40+ commands as advanced aliases.

Done when a new user can understand the memory system without reading the full
CLI reference.

## Phase 2: Central Store Schema

Goal: make Supabase and self-hosting share one memory model.

Deliverables:

- central event log;
- central candidate inbox;
- active memory snapshot table;
- revision table;
- conflict table;
- archive table;
- Dream report table;
- forgetting suggestion table;
- sync cursor table;
- agent/device registry table;
- policy rule table.

Done when a sync worker can use the same concepts on Supabase or a self-hosted
server.

Current groundwork:

- `supabase/migrations/20260705_central_memory_station.sql` defines the central
  tables.
- `vault memory-sync run-once` and `python -m scripts.central_memory_sync` write
  `reports/central-memory-sync-latest.json`.
- `setup-agent --features supabase --supabase-sync ...` writes cron,
  LaunchAgent, and n8n Central Memory Station schedule templates.
- Dry-run is the recommended first step before enabling central writes.

## Phase 3: Sync Worker

Goal: make many machines sync without pretending there are no conflicts.

Default rhythm:

- every 30-60 minutes for ordinary sync;
- manual `run-once` for debugging;
- near-realtime only on trusted machines that can hold privileged credentials.

Rules:

- local vault stays usable offline;
- candidates can move both ways;
- reviewed active memory is pushed as a controlled snapshot;
- conflicts go to review instead of overwriting truth;
- secrets and private memory do not leave the local vault unless policy allows
  reviewed summaries.

First worker command:

```bash
vault memory-sync run-once --push-read-copy --push-central-store --pull-candidates --dry-run --json
vault memory-sync run-once --push-read-copy --push-central-store --pull-candidates --apply --json
vault memory-sync run-once --central-backend self-host --pull-candidates --apply --json
```

Done when two hosts can exchange reviewed memory and candidate memory with a
visible conflict inbox.

## Phase 4: Review And Conflict Decisions

Goal: make memory trustworthy.

Deliverables:

- candidate ranking by source, trust, duplicate risk, privacy risk, and usage;
- conflict cards with old value, new value, source, and recommended action;
- explicit choices: keep current, accept candidate, merge, keep both, fork
  private, archive stale;
- audit trail for every decision;
- feedback loop so future automation learns from rejected candidates.

Done when the system can explain why a memory became trusted or stayed pending.

## Phase 5: Dream, Forget, Archive, Cold-Store

Goal: prevent the memory base from becoming a junk drawer.

Deliverables:

- nightly Dream report;
- duplicate and stale-memory detection;
- automatic archive previews;
- cold-store summaries for expired but still useful memory;
- forgetting suggestions that never hard-delete by default;
- weekly human-readable memory maintenance report.

Done when memory quality improves over time without requiring humans to inspect
every row.

## Phase 6: Devices And Roles

Goal: support different places where memory will live.

Example roles:

- phone: personal quick capture and search;
- laptop: primary work vault and review station;
- server: central sync and backup worker;
- car: trip, preference, and environment memory with strict privacy rules;
- robot: task, place, object, and safety memory;
- hosted agent: read-only or candidate-submit mode by default.

Done when each device class can have a role, sensitivity limit, sync interval,
and allowed actions.

## Phase 7: Operations

Goal: make the system dependable.

Deliverables:

- backup and restore runbook;
- health dashboard;
- sync freshness warnings;
- key rotation;
- RLS / Gateway policy tests;
- candidate inbox migration between Supabase and self-hosted central store;
- reviewed active-memory snapshot bundle export/verify/import as review candidates;
- later full audit-history import and active-restore disaster recovery test.

Done when a user can move from Supabase to self-hosted, or from self-hosted to
Supabase, without losing reviewed memory history.

The self-host implementation target is specified in
[Self-host Central Memory Host Specification](../specs/self_host_central_memory_host.md).
It defines the operator runbook, state model, security boundary, sync rhythm,
and acceptance tests for the self-host backend adapter.

## Command Consolidation Policy

The existing detailed commands should not disappear. They are useful for agents,
tests, and power users.

The product surface should be:

- 5 primary command groups for humans and operators;
- detailed commands remain documented as advanced tools;
- new features should first appear under the primary command group, then expose
  low-level commands only when needed.
