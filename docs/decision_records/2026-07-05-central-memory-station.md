# Decision Record: Central Memory Station

Date: 2026-07-05

## Context

Vault already has local SQLite memory, candidate-first writes, Supabase read
copies, Gateway / Remote Server, local revision audit, conflicts, Dream reports,
archive, and cold-store. The next product step is to make those parts feel like
one memory system for many agents, machines, and devices.

The target user flow is simple:

- each agent or device keeps a local vault for fast work and offline use;
- a trusted central store receives active memory snapshots, candidate memory,
  sync events, and review decisions;
- a Gateway controls who can read, submit candidates, pull updates, promote, or
  run maintenance;
- scheduled sync runs every 30-60 minutes by default, with manual sync available;
- daily review, Dream, forgetting, archive, and cold-store keep the central
  memory useful instead of endlessly growing.

## Decision

Vault will present this as a **Central Memory Station**.

The first implementation keeps the existing safety boundary:

- local SQLite remains the fast working vault and offline buffer;
- Supabase is the hosted central option;
- Vault Remote Server / Gateway is the self-hosted central option;
- remote writes enter as candidates first;
- active memory is not edited as free-form multi-master state;
- conflict handling is explicit and auditable.

The CLI should expose fewer primary commands while preserving the detailed
commands as advanced aliases:

| Human intent | Primary command |
|---|---|
| Start or orient | `vault start` |
| Push, pull, or inspect central sync | `vault memory-sync ...` |
| Review candidates and conflicts | `vault memory-review ...` |
| Dream, forget, archive, cold-store | `vault memory-lifecycle ...` |
| Maintain the system | `vault ops ...` |

## Product Model

Think of the system as three boxes:

1. Local vault: the notebook each agent or device can use immediately.
2. Central memory station: the trusted library where shared memory is reviewed,
   synced, archived, and redistributed.
3. Gateway: the door guard that decides who can read, suggest, approve, or run
   maintenance.

Supabase and self-hosted server should share the same behavior contract even if
the deployment differs. Supabase is the default hosted path. Self-hosting is for
users who need stronger ownership, LAN/device deployments, or custom policy.

## Conflict Policy

Conflicts are expected. They should not block ordinary memory use.

The default behavior is:

- facts from agents become candidates, not immediate truth;
- low-risk, sourced candidates may be auto-promoted only under policy;
- conflicting candidates stay in the review inbox;
- every resolve action records actor, reason, source, and old content;
- forgotten memory is decayed, archived, or cold-stored, not silently deleted.

## Lifecycle Policy

Dream and forgetting are part of the core system, not decorative extras.

- Dream finds duplicates, stale facts, missing metadata, orphaned claims, and
  convergence opportunities.
- Forgetting means demote, expire, archive, or cold-store by policy.
- Archive keeps auditability while removing stale rows from normal search.
- Cold-store compresses expired but still useful memory into summaries.

## Current Implementation

This decision starts the consolidation layer:

- `vault start`
- `vault memory-sync status|doctor|push|pull|run-once`
- `vault memory-review run|inbox|preview|resolve`
- `vault memory-lifecycle status|dream|archive|forget|cold-store`
- `vault ops status|doctor|security`
- `python -m scripts.central_memory_sync` for scheduled or cron-style sync
- `reports/central-memory-sync-latest.json` for machine-readable sync freshness
- `vault_active_memory_snapshots`, `vault_memory_revisions`,
  `vault_memory_events`, and `vault_sync_cursors` writes through
  `--push-central-store`
- `vault memory-sync push --central-store` writes new candidate submissions
  directly to `vault_memory_candidates_central`
- `vault memory-sync pull` reads both the older `vault_memory_write_requests`
  inbox and the new central candidate inbox, then imports rows into local
  `memory_candidates` before any promotion
- Gateway / Remote Server now exposes `/central-candidates/status`,
  `/central-candidates/submit`, and `/central-candidates/pull` backed by a
  self-hosted SQLite `vault-central.db` inbox
- `vault memory-sync push|pull|run-once --central-backend self-host` uses that
  self-hosted inbox through the same Central Memory Station CLI surface

The commands wrap existing modules instead of creating a parallel system.

## Deferred

- Per-memory vector-clock or CRDT-style merge metadata for selected memory
  types.
- Central policy editor and UI review inbox.
- Device classes such as car, robot, phone, laptop with role-specific sync
  rules.
- End-to-end self-host deployment template with auth, TLS, backups, and
  monitoring.
