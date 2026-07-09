# Self-host Central Memory Host Specification

Status: draft implementation spec for the self-host backend adapter.

This specification defines the **Trusted Local Central Memory Host** pattern.
Network posture: Tailscale / VPN first, token second, HTTPS or a trusted reverse
proxy before any public exposure.

This spec turns the self-host deployment mode into an implementation target.
It does not replace the broader Deployment Modes guide. It defines the
contracts an operator, adapter, and test suite should be able to rely on.

## Goal

A Self-host Central Memory Host is one trusted machine that owns the governed
Vault project for a team or group of agents.

It should provide:

- approved-memory search and read access for remote agents;
- candidate submission for remote agents and devices;
- local review, reject, defer, promote, Dream, archive, forgetting, and daily
  reporting on the trusted host;
- optional local embedding and semantic/vector index refresh;
- backup, restore, audit, and sync freshness evidence.

It should not become an unreviewed multi-master active memory database.

## Non-goals

- Remote agents do not write active `knowledge` rows directly.
- Offline devices do not merge active memory into the host without review.
- `vault-central.db` is not a second source of truth for active memory.
- Semantic/vector indexes are derived read caches, not memory authorities.
- Public internet exposure without VPN or HTTPS plus token auth is not a
  supported production posture.

## Architecture

```text
Remote agents / apps / devices
  -> VPN or HTTPS
  -> Gateway / Remote Server / OpenAPI adapter
  -> Vault Governance Contract
  -> self-host backend adapter
  -> vault.db + Markdown + reports + backups
```

The central host owns:

- `vault.db` as the source of truth for approved memory;
- Markdown or imported source files, when present;
- `memory_candidates` as the local review queue;
- `vault-central.db` as the self-host central candidate inbox;
- `reports/` for daily-loop, sync, Gateway audit, and automation evidence;
- `backups/` for tested SQLite backups.

## Roles

| Role | Credential | Allowed actions | Must not do |
|---|---|---|---|
| Remote reader | scoped Gateway token | search/read approved memory within policy | read private/restricted memory outside policy |
| Remote contributor | scoped Gateway token | submit candidate memory | promote or edit active memory |
| Remote semantic reader | token bound to one `agent_id` | query semantic preview for approved memory | receive raw memory content or embedding values |
| Trusted reviewer | local host account or admin token | review, reject, defer, promote candidates | bypass audit for remote submissions |
| Operator | local host account | backup, restore, rotate tokens, run reports | share admin secrets with hosted agents |

## Required Contract

The host must preserve the same Vault Governance Contract as other backends:

```text
search_approved_memory(query, agent_id, policy)
read_approved_memory(handle, agent_id, policy)
submit_candidate(memory_candidate, agent_id, source)
review_candidate(candidate_id, decision, reviewer_or_policy)
promote_candidate(candidate_id, policy)
audit_memory_event(event)
daily_loop_status()
daily_loop_report()
```

Implementation surfaces may differ, but behavior must not:

- approved reads are policy-filtered;
- remote writes create candidates only;
- promotion requires a trusted reviewer or explicit policy gate;
- sensitive, conflicting, strategic, or stale memory remains review-visible;
- every decision leaves audit evidence.

## HTTP Surface

`vault remote-server` reuses the Gateway contract. A self-host deployment must
support these read/write classes:

| Class | Example endpoint | Behavior |
|---|---|---|
| Health | `/health` | return readiness, security, and governance metadata |
| Contract | `/openapi.json` | return machine-readable adapter contract |
| Approved read | `/search`, `/read-range` | return policy-filtered approved memory only |
| Candidate write | `/submit-candidate` | write candidate, never active memory |
| Central inbox | `/central-candidates/status` | inspect self-host candidate inbox counts |
| Central submit | `/central-candidates/submit` | submit to `vault-central.db` |
| Central pull | `/central-candidates/pull` | import central candidates into local review |

Remote Semantic Search, when enabled, must add these constraints:

- disabled by default;
- token-agent binding is required;
- project scope is required unless explicitly configured as public/global;
- raw memory content and embedding values are not returned;
- health output discloses the active query embedding provider and privacy risk.

## State Model

The self-host adapter has three different stores. Keeping them separate is the
main safety boundary.

| Store | Purpose | Authority |
|---|---|---|
| `vault.db` / `knowledge` | approved active memory | source of truth |
| `vault.db` / `memory_candidates` | local review queue | pending decisions only |
| `vault-central.db` / `vault_memory_candidates_central` | network-facing candidate inbox | pending import only |

Derived stores:

- local FTS, semantic, or vector indexes are read caches;
- exported Markdown and Obsidian notes are human review surfaces;
- sync reports are evidence, not authority.

## Data Flow

Approved read:

```text
remote agent
  -> authenticated search/read request
  -> access policy filter
  -> approved memory handle or safe preview
```

Candidate submission:

```text
remote agent
  -> authenticated candidate request
  -> central candidate inbox or local candidate queue
  -> daily-loop/review inbox
  -> reject, defer, merge, or promote
```

Promotion:

```text
reviewer or narrow policy gate
  -> candidate decision
  -> active memory update
  -> audit event
  -> derived index refresh
  -> daily report
```

## Sync Rhythm

Recommended default:

| Job | Timing | Notes |
|---|---:|---|
| Candidate submit | immediate | remote agents can submit while online |
| Approved read | immediate | central host remains the online read path |
| Pull central candidates | every 5-15 minutes or before review | imports to local review only |
| Semantic/vector refresh | after promotion or every 5-15 minutes | derived cache only |
| Daily-loop report | daily, commonly 09:00 local time | human-readable status |
| Backup | daily minimum | verify restore periodically |
| Security doctor | before exposure and after config changes | catches weak token/TLS/backup posture |
| Audit review | weekly | inspect Gateway and review decisions |

Plain-language defaults:

- candidate submission: immediate;
- approved-memory search/read: immediate;
- daily-loop report: once per day;
- backup: daily.

Offline agents should keep a local outbox and submit candidates when they can
reach the host. They should not attempt to replay active-memory mutations.

## Security Requirements

Minimum:

- use Tailscale, ZeroTier, WireGuard, or another private network when possible;
- if exposed publicly, use HTTPS or a trusted reverse proxy;
- require `VAULT_GATEWAY_TOKEN` or `--auth-token` before serving;
- issue separate tokens per agent or agent class;
- keep admin tokens and filesystem access on the central host only;
- do not place service-role, admin, or host filesystem credentials in hosted
  agents, browser clients, Coze, or ordinary n8n workflows;
- run `vault security doctor --json` before opening access;
- keep a tested backup under `backups/`.

Recommended:

- rotate tokens after team/member changes;
- bind Remote Semantic tokens to exactly one `agent_id`;
- keep Remote Semantic disabled for sensitive deployments unless the embedding
  provider is local or contractually trusted;
- rate-limit Gateway requests and review lockout/audit summaries.

## Operator Runbook

Bootstrap:

```bash
vault setup-agent --features core,mcp --agent-project-dir ~/Vaults/team-memory
vault --project-dir ~/Vaults/team-memory security doctor --json
vault remote-server health --project-dir ~/Vaults/team-memory --json
vault remote-server openapi --project-dir ~/Vaults/team-memory --json
```

Serve:

```bash
export VAULT_GATEWAY_TOKEN="set-from-secret-manager"
vault remote-server serve --project-dir ~/Vaults/team-memory --host 0.0.0.0
```

Daily operation:

```bash
vault memory-sync run-once --project-dir ~/Vaults/team-memory --central-backend self-host --pull-candidates --dry-run --json
vault memory-review inbox --project-dir ~/Vaults/team-memory --json
vault daily-loop report --project-dir ~/Vaults/team-memory --refresh --write-report --json
vault db backup --db-path ~/Vaults/team-memory/vault.db --verify --json
```

Only use `--apply` after the dry-run result shows the expected candidate
imports and no safety warnings.

`vault setup-agent` writes `vault-remote-server-operator.cron`, macOS
LaunchAgent plists, systemd service/timer pairs, and
`README-remote-server-operator-schedule.md` for the trusted host. The generated
schedule templates cover candidate pull, daily report refresh, verified backup,
weekly Gateway audit summary, and weekly security doctor.

## Acceptance Tests

Release or deployment validation should prove:

- `vault remote-server serve` refuses to start without a stable token;
- `/health` reports the governance contract and self-host metadata;
- `/openapi.json` includes the self-host central candidate endpoints;
- remote search excludes private/restricted memory outside policy;
- remote candidate submission does not create active `knowledge`;
- central candidate pull imports to `memory_candidates`, not active memory;
- promotion records a review decision and audit evidence;
- daily-loop status reports candidate counts and sync freshness;
- `vault security doctor --json` warns on missing token, missing backup, public
  bind without TLS/private-network evidence, or unbound Remote Semantic tokens;
- Remote Semantic health discloses provider/model and query-text privacy risk;
- backup and restore have been exercised on a copy of the project.

## Migration And Interop

Self-host, Supabase, and future Vault Cloud are backend adapters around the
same governance contract. A team should be able to move between them by:

- exporting approved memory and audit evidence from the current backend;
- importing remote submissions as candidates, not active memory;
- preserving access-policy metadata where possible;
- rebuilding derived search/vector indexes from reviewed memory;
- validating daily-loop and security doctor output before opening access.

Candidate inbox migration is available as a bounded first step:

```bash
vault memory-sync migrate-candidates --direction supabase-to-self-host --json
vault memory-sync migrate-candidates --direction supabase-to-self-host --apply --json
vault memory-sync migrate-candidates --direction self-host-to-supabase --json
vault memory-sync migrate-candidates --direction self-host-to-supabase --apply --json
```

This command copies only pending Central Memory Station candidate inbox rows. It
does not migrate active `knowledge`, does not write local `memory_candidates`,
and does not promote memory.

Reviewed snapshot bundle migration is available for host bootstrap and backend
moves:

```bash
vault memory-sync export-snapshots --bundle ./vault-snapshots.json --json
vault memory-sync export-snapshots --bundle ./vault-snapshots.json --include-content --json
vault memory-sync verify-snapshots --bundle ./vault-snapshots.json --json
vault memory-sync verify-snapshots --bundle ./vault-snapshots.json --require-content --json
vault memory-sync import-snapshots --bundle ./vault-snapshots.json --json
vault memory-sync import-snapshots --bundle ./vault-snapshots.json --apply --json
```

Snapshot export uses the same reviewed active-memory snapshot schema as the
Central Memory Station read copy. The default bundle excludes raw memory
content. `--include-content` should be used only when the bundle is stored and
transferred on a trusted, encrypted path. The bundle manifest records snapshot
count, snapshot digest, content policy, and metadata-only local revision/audit
counts. `verify-snapshots` checks the manifest and content hashes without
writing memory; use `--require-content` before a disaster-recovery candidate
import. Snapshot import is deliberately candidate-first: `--apply` writes local
`memory_candidates` for review, not active `knowledge`, and it never promotes
candidates.
In short, snapshot import writes local `memory_candidates` for review, not active `knowledge`.

## Roadmap

Follow-up implementation work:

- full audit-history import and disaster recovery active-restore tests;
- a small operator dashboard for health, candidates, and backup age;
- policy bundles for clinic/team deployments;
- optional local embedding provider presets for privacy-sensitive deployments.
