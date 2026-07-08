-- Central vector index schema.
-- This is a derived remote read cache for reviewed memory only.
-- Local SQLite/Markdown remains the memory source of truth.

create extension if not exists pgcrypto;
create extension if not exists vector;

set search_path = public, extensions;

create table if not exists public.vault_memory_embeddings (
    id uuid primary key default gen_random_uuid(),

    memory_key text not null,
    revision integer not null default 1,
    project_id text not null default '',

    embedding_model text not null,
    embedding_dimension integer not null default 1536,
    vector_kind text not null default 'safe_summary',
    embedding vector(1536) not null,

    remote_search_text text not null default '',
    remote_search_text_hash text not null default '',
    content_hash text not null default '',
    embedding_hash text not null default '',

    scope text not null default 'project',
    sensitivity text not null default 'low',
    owner_agent text not null default '',
    allowed_agents text[] not null default array[]::text[],

    source_table text not null default 'vault_active_memory_snapshots',
    index_policy text not null default 'shared_reviewed_safe_summary_v1',
    is_latest boolean not null default true,
    superseded_at timestamp with time zone,

    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),

    constraint vault_memory_embeddings_key
        unique (memory_key, revision, embedding_model, vector_kind),
    constraint vault_memory_embeddings_reviewed_source
        check (source_table = 'vault_active_memory_snapshots'),
    constraint vault_memory_embeddings_shared_sensitivity
        check (lower(sensitivity) in ('low', 'medium')),
    constraint vault_memory_embeddings_shared_scope
        check (lower(scope) in ('public', 'shared', 'project')),
    constraint vault_memory_embeddings_dimension
        check (embedding_dimension = 1536),
    constraint vault_memory_embeddings_text_hash_required
        check (remote_search_text_hash <> ''),
    constraint vault_memory_embeddings_embedding_hash_required
        check (embedding_hash <> '')
);

comment on table public.vault_memory_embeddings is
    'Policy-aware derived vector read cache for reviewed active memory safe summaries. Remote agents must not write this table directly.';

comment on column public.vault_memory_embeddings.remote_search_text is
    'Safe index text approved by the trusted sync host, not raw unrestricted memory content.';

create index if not exists idx_vault_memory_embeddings_latest
    on public.vault_memory_embeddings (memory_key, is_latest, revision desc);
create index if not exists idx_vault_memory_embeddings_project
    on public.vault_memory_embeddings (project_id)
    where is_latest;
create index if not exists idx_vault_memory_embeddings_scope_sensitivity
    on public.vault_memory_embeddings (scope, sensitivity)
    where is_latest;
create index if not exists idx_vault_memory_embeddings_owner
    on public.vault_memory_embeddings (owner_agent)
    where is_latest and owner_agent <> '';
create index if not exists idx_vault_memory_embeddings_content_hash
    on public.vault_memory_embeddings (content_hash);
create index if not exists idx_vault_memory_embeddings_vector
    on public.vault_memory_embeddings
    using hnsw (embedding vector_cosine_ops);

alter table public.vault_memory_embeddings enable row level security;

-- No direct anon/authenticated table policy is created here.
-- Remote readers should use guarded RPC/Gateway paths. The service-role trusted
-- sync host can upsert this derived cache while normal agents remain candidate-first.

create or replace function public.vault_central_vector_index_status()
returns table (
    installed boolean,
    vector_rows bigint,
    latest_vector_rows bigint,
    embedding_models bigint,
    project_count bigint,
    oldest_updated_at timestamp with time zone,
    newest_updated_at timestamp with time zone,
    remote_read_enabled boolean,
    remote_write_enabled boolean,
    index_role text,
    source_of_truth text
)
language sql
security definer
set search_path = public, extensions
as $$
    select
        true as installed,
        count(*) as vector_rows,
        count(*) filter (where is_latest) as latest_vector_rows,
        count(distinct embedding_model) as embedding_models,
        count(distinct nullif(project_id, '')) as project_count,
        min(updated_at) as oldest_updated_at,
        max(updated_at) as newest_updated_at,
        false as remote_read_enabled,
        false as remote_write_enabled,
        'derived_remote_read_cache'::text as index_role,
        'trusted_sync_host_reviewed_snapshots'::text as source_of_truth
    from public.vault_memory_embeddings;
$$;

comment on function public.vault_central_vector_index_status() is
    'Safe metadata-only status for the central vector index. Does not expose embedding values or memory content.';

grant execute on function public.vault_central_vector_index_status() to anon, authenticated, service_role;
