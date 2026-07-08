-- Central Memory Station schema groundwork.
-- Local SQLite remains the working vault and offline buffer.
-- Supabase is a central reviewed store, candidate inbox, and sync ledger.

create extension if not exists pgcrypto;

create table if not exists public.vault_memory_events (
    id uuid primary key default gen_random_uuid(),
    event_type text not null,
    actor_agent_id text not null default '',
    device_id text not null default '',
    memory_key text not null default '',
    source_ref text not null default '',
    payload jsonb not null default '{}'::jsonb,
    created_at timestamp with time zone not null default now()
);

comment on table public.vault_memory_events is
    'Append-only central event log for sync, review, lifecycle, and audit events.';

create index if not exists idx_vault_memory_events_type_time
    on public.vault_memory_events (event_type, created_at desc);
create index if not exists idx_vault_memory_events_memory_key
    on public.vault_memory_events (memory_key);
create index if not exists idx_vault_memory_events_actor
    on public.vault_memory_events (actor_agent_id, created_at desc);

create table if not exists public.vault_memory_candidates_central (
    id uuid primary key default gen_random_uuid(),
    candidate_key text not null,
    title text not null default '',
    content text not null default '',
    reason text not null default '',
    category text not null default 'general',
    tags text[] not null default array[]::text[],
    trust double precision not null default 0,
    scope text not null default 'project',
    sensitivity text not null default 'low',
    owner_agent text not null default '',
    allowed_agents text[] not null default array[]::text[],
    from_agent text not null default '',
    source_ref text not null default '',
    memory_type text not null default 'remote_candidate',
    status text not null default 'candidate',
    gate_status jsonb not null default '{}'::jsonb,
    idempotency_key text not null default '',
    hmac_key_id text not null default '',
    hmac_algorithm text not null default '',
    payload_hash text not null default '',
    hmac_signature text not null default '',
    local_candidate_id text not null default '',
    error text not null default '',
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),
    constraint vault_memory_candidates_central_key unique (candidate_key)
);

comment on table public.vault_memory_candidates_central is
    'Central candidate inbox. Remote agents submit here; trusted workers pull into local memory_candidates.';

create index if not exists idx_vault_memory_candidates_central_status
    on public.vault_memory_candidates_central (status, created_at desc);
create index if not exists idx_vault_memory_candidates_central_from_agent
    on public.vault_memory_candidates_central (from_agent, created_at desc);
create index if not exists idx_vault_memory_candidates_central_scope_sensitivity
    on public.vault_memory_candidates_central (scope, sensitivity);
create unique index if not exists idx_vault_memory_candidates_central_idempotency
    on public.vault_memory_candidates_central (idempotency_key)
    where idempotency_key <> '';
create index if not exists idx_vault_memory_candidates_central_payload_hash
    on public.vault_memory_candidates_central (payload_hash)
    where payload_hash <> '';

create table if not exists public.vault_active_memory_snapshots (
    id uuid primary key default gen_random_uuid(),
    memory_key text not null,
    local_knowledge_id bigint,
    title text not null default '',
    content text not null default '',
    summary text not null default '',
    category text not null default 'general',
    tags text[] not null default array[]::text[],
    scope text not null default 'project',
    sensitivity text not null default 'low',
    owner_agent text not null default '',
    allowed_agents text[] not null default array[]::text[],
    status text not null default 'active',
    content_hash text not null default '',
    revision integer not null default 1,
    reviewed_at timestamp with time zone,
    updated_at timestamp with time zone not null default now(),
    constraint vault_active_memory_snapshots_key unique (memory_key)
);

comment on table public.vault_active_memory_snapshots is
    'Reviewed active memory read copy. It is synced from trusted workers, not edited by arbitrary remote agents.';

create index if not exists idx_vault_active_memory_snapshots_status
    on public.vault_active_memory_snapshots (status, updated_at desc);
create index if not exists idx_vault_active_memory_snapshots_scope_sensitivity
    on public.vault_active_memory_snapshots (scope, sensitivity);
create index if not exists idx_vault_active_memory_snapshots_content_hash
    on public.vault_active_memory_snapshots (content_hash);

create table if not exists public.vault_memory_revisions (
    id uuid primary key default gen_random_uuid(),
    memory_key text not null,
    revision integer not null,
    parent_revision integer,
    actor_agent_id text not null default '',
    operation text not null default '',
    content_hash text not null default '',
    payload jsonb not null default '{}'::jsonb,
    created_at timestamp with time zone not null default now(),
    constraint vault_memory_revisions_key unique (memory_key, revision)
);

create index if not exists idx_vault_memory_revisions_memory_key
    on public.vault_memory_revisions (memory_key, revision desc);
create index if not exists idx_vault_memory_revisions_actor
    on public.vault_memory_revisions (actor_agent_id, created_at desc);

create table if not exists public.vault_memory_conflicts (
    id uuid primary key default gen_random_uuid(),
    conflict_key text not null,
    memory_key text not null default '',
    candidate_id uuid,
    active_snapshot_id uuid,
    conflict_type text not null default 'content_mismatch',
    status text not null default 'open',
    resolution text not null default '',
    reason text not null default '',
    actor_agent_id text not null default '',
    payload jsonb not null default '{}'::jsonb,
    created_at timestamp with time zone not null default now(),
    resolved_at timestamp with time zone,
    constraint vault_memory_conflicts_key unique (conflict_key)
);

create index if not exists idx_vault_memory_conflicts_status
    on public.vault_memory_conflicts (status, created_at desc);
create index if not exists idx_vault_memory_conflicts_memory_key
    on public.vault_memory_conflicts (memory_key);

create table if not exists public.vault_memory_archive (
    id uuid primary key default gen_random_uuid(),
    memory_key text not null,
    title text not null default '',
    summary text not null default '',
    archive_reason text not null default '',
    original_hash text not null default '',
    payload jsonb not null default '{}'::jsonb,
    archived_at timestamp with time zone not null default now()
);

create index if not exists idx_vault_memory_archive_key
    on public.vault_memory_archive (memory_key, archived_at desc);

create table if not exists public.vault_dream_reports (
    id uuid primary key default gen_random_uuid(),
    report_key text not null,
    mode text not null default 'report',
    summary text not null default '',
    findings jsonb not null default '[]'::jsonb,
    candidate_count integer not null default 0,
    created_at timestamp with time zone not null default now(),
    constraint vault_dream_reports_key unique (report_key)
);

create index if not exists idx_vault_dream_reports_created
    on public.vault_dream_reports (created_at desc);

create table if not exists public.vault_forgetting_suggestions (
    id uuid primary key default gen_random_uuid(),
    memory_key text not null default '',
    suggestion_type text not null default 'review',
    reason text not null default '',
    score double precision not null default 0,
    status text not null default 'candidate',
    payload jsonb not null default '{}'::jsonb,
    created_at timestamp with time zone not null default now(),
    resolved_at timestamp with time zone
);

create index if not exists idx_vault_forgetting_suggestions_status
    on public.vault_forgetting_suggestions (status, created_at desc);
create index if not exists idx_vault_forgetting_suggestions_memory_key
    on public.vault_forgetting_suggestions (memory_key);

create table if not exists public.vault_sync_cursors (
    id uuid primary key default gen_random_uuid(),
    agent_id text not null,
    device_id text not null default '',
    cursor_name text not null,
    cursor_value text not null default '',
    last_synced_at timestamp with time zone,
    payload jsonb not null default '{}'::jsonb,
    updated_at timestamp with time zone not null default now(),
    constraint vault_sync_cursors_key unique (agent_id, device_id, cursor_name)
);

create index if not exists idx_vault_sync_cursors_updated
    on public.vault_sync_cursors (updated_at desc);

create table if not exists public.vault_agent_registry_central (
    id uuid primary key default gen_random_uuid(),
    agent_id text not null,
    device_id text not null default '',
    role text not null default 'work',
    max_sensitivity text not null default 'medium',
    sync_interval_minutes integer not null default 60,
    can_read boolean not null default true,
    can_submit_candidates boolean not null default true,
    can_promote boolean not null default false,
    can_run_lifecycle boolean not null default false,
    last_seen_at timestamp with time zone,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),
    constraint vault_agent_registry_central_key unique (agent_id, device_id)
);

create index if not exists idx_vault_agent_registry_central_role
    on public.vault_agent_registry_central (role);
create index if not exists idx_vault_agent_registry_central_last_seen
    on public.vault_agent_registry_central (last_seen_at desc);

create table if not exists public.vault_policy_rules (
    id uuid primary key default gen_random_uuid(),
    rule_key text not null,
    rule_type text not null,
    enabled boolean not null default true,
    priority integer not null default 100,
    rule jsonb not null default '{}'::jsonb,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),
    constraint vault_policy_rules_key unique (rule_key)
);

create index if not exists idx_vault_policy_rules_type
    on public.vault_policy_rules (rule_type, enabled, priority);

alter table public.vault_memory_events enable row level security;
alter table public.vault_memory_candidates_central enable row level security;
alter table public.vault_active_memory_snapshots enable row level security;
alter table public.vault_memory_revisions enable row level security;
alter table public.vault_memory_conflicts enable row level security;
alter table public.vault_memory_archive enable row level security;
alter table public.vault_dream_reports enable row level security;
alter table public.vault_forgetting_suggestions enable row level security;
alter table public.vault_sync_cursors enable row level security;
alter table public.vault_agent_registry_central enable row level security;
alter table public.vault_policy_rules enable row level security;

-- Development policy only. Production deployments should replace this with
-- role-aware read/write policies or route writes through Gateway service roles.
drop policy if exists agents_rw on public.vault_memory_events;
create policy agents_rw on public.vault_memory_events for all using (true) with check (true);
drop policy if exists agents_rw on public.vault_memory_candidates_central;
create policy agents_rw on public.vault_memory_candidates_central for all using (true) with check (true);
drop policy if exists agents_rw on public.vault_active_memory_snapshots;
create policy agents_rw on public.vault_active_memory_snapshots for all using (true) with check (true);
drop policy if exists agents_rw on public.vault_memory_revisions;
create policy agents_rw on public.vault_memory_revisions for all using (true) with check (true);
drop policy if exists agents_rw on public.vault_memory_conflicts;
create policy agents_rw on public.vault_memory_conflicts for all using (true) with check (true);
drop policy if exists agents_rw on public.vault_memory_archive;
create policy agents_rw on public.vault_memory_archive for all using (true) with check (true);
drop policy if exists agents_rw on public.vault_dream_reports;
create policy agents_rw on public.vault_dream_reports for all using (true) with check (true);
drop policy if exists agents_rw on public.vault_forgetting_suggestions;
create policy agents_rw on public.vault_forgetting_suggestions for all using (true) with check (true);
drop policy if exists agents_rw on public.vault_sync_cursors;
create policy agents_rw on public.vault_sync_cursors for all using (true) with check (true);
drop policy if exists agents_rw on public.vault_agent_registry_central;
create policy agents_rw on public.vault_agent_registry_central for all using (true) with check (true);
drop policy if exists agents_rw on public.vault_policy_rules;
create policy agents_rw on public.vault_policy_rules for all using (true) with check (true);
