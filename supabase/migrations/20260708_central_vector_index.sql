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
        true as remote_read_enabled,
        false as remote_write_enabled,
        'derived_remote_read_cache'::text as index_role,
        'trusted_sync_host_reviewed_snapshots'::text as source_of_truth
    from public.vault_memory_embeddings;
$$;

comment on function public.vault_central_vector_index_status() is
    'Safe metadata-only status for the central vector index. Does not expose embedding values or memory content.';

grant execute on function public.vault_central_vector_index_status() to anon, authenticated, service_role;

drop function if exists public.vault_sensitivity_rank(text) cascade;

create or replace function public.vault_sensitivity_rank(p_sensitivity text)
returns integer
language sql
immutable
set search_path = public
as $$
    select case lower(coalesce(p_sensitivity, ''))
        when 'low' then 10
        when 'medium' then 20
        when 'high' then 30
        when 'restricted' then 40
        else 999
    end;
$$;

comment on function public.vault_sensitivity_rank(text) is
    'Small helper for Vault RPC policy filters. Lower numbers are less sensitive.';

grant execute on function public.vault_sensitivity_rank(text) to anon, authenticated, service_role;

create or replace function public.vault_match_readable_memory_embeddings(
    p_agent_id text,
    p_query_embedding vector(1536),
    p_project_id text default null,
    p_match_count integer default 10,
    p_max_sensitivity text default 'medium',
    p_min_similarity double precision default 0
)
returns table (
    memory_key text,
    revision integer,
    similarity double precision,
    title text,
    summary text,
    category text,
    tags text[],
    scope text,
    sensitivity text,
    read_handle text
)
language sql
security definer
set search_path = public, extensions
as $$
    with scored as (
        select
            e.memory_key,
            e.revision,
            1 - (e.embedding <=> p_query_embedding) as similarity,
            s.title,
            s.summary,
            s.category,
            s.tags,
            e.scope,
            e.sensitivity,
            e.memory_key as read_handle
        from public.vault_memory_embeddings e
        join public.vault_active_memory_snapshots s
          on s.memory_key = e.memory_key
         and s.revision = e.revision
        where e.is_latest
          and lower(coalesce(s.status, 'active')) = 'active'
          and (p_project_id is null or e.project_id = p_project_id)
          and public.vault_sensitivity_rank(e.sensitivity) <= public.vault_sensitivity_rank(p_max_sensitivity)
          and (
              lower(e.scope) = 'public'
              or (
                  lower(e.scope) in ('shared', 'project')
                  and p_project_id is not null
                  and e.project_id = p_project_id
              )
              or (
                  nullif(p_agent_id, '') is not null
                  and p_project_id is not null
                  and e.project_id = p_project_id
                  and (
                      e.owner_agent = p_agent_id
                      or p_agent_id = any(e.allowed_agents)
                  )
              )
          )
    )
    select
        scored.memory_key,
        scored.revision,
        scored.similarity,
        scored.title,
        scored.summary,
        scored.category,
        scored.tags,
        scored.scope,
        scored.sensitivity,
        scored.read_handle
    from scored
    where scored.similarity >= coalesce(p_min_similarity, 0)
    order by scored.similarity desc
    limit least(greatest(coalesce(p_match_count, 10), 1), 50);
$$;

comment on function public.vault_match_readable_memory_embeddings(text, vector, text, integer, text, double precision) is
    'Policy-aware semantic preview search over reviewed safe-summary embeddings. Returns safe metadata only; no raw memory content or embedding values.';

grant execute on function public.vault_match_readable_memory_embeddings(text, vector, text, integer, text, double precision)
    to anon, authenticated, service_role;

create or replace function public.vault_get_readable_memory_snapshot(
    p_agent_id text,
    p_read_handle text,
    p_project_id text default null,
    p_max_sensitivity text default 'medium',
    p_max_chars integer default 2000
)
returns table (
    memory_key text,
    revision integer,
    title text,
    summary text,
    content_preview text,
    content_source text,
    truncated boolean,
    max_chars integer,
    category text,
    tags text[],
    scope text,
    sensitivity text,
    content_hash text,
    updated_at timestamp with time zone
)
language sql
security definer
set search_path = public, extensions
as $$
    with bounded as (
        select least(greatest(coalesce(p_max_chars, 2000), 1), 8000) as max_chars
    ),
    readable as (
        select s.*
        from public.vault_active_memory_snapshots s
        where s.memory_key = p_read_handle
          and lower(coalesce(s.status, 'active')) = 'active'
          and public.vault_sensitivity_rank(s.sensitivity) <= public.vault_sensitivity_rank(p_max_sensitivity)
          and (
              lower(s.scope) = 'public'
              or (
                  lower(s.scope) in ('shared', 'project')
                  and p_project_id is not null
                  and split_part(s.memory_key, ':', 1) = p_project_id
              )
              or (
                  nullif(p_agent_id, '') is not null
                  and p_project_id is not null
                  and split_part(s.memory_key, ':', 1) = p_project_id
                  and s.owner_agent = p_agent_id
              )
          )
        order by s.revision desc
        limit 1
    )
    select
        r.memory_key,
        r.revision,
        r.title,
        r.summary,
        left(
            case when nullif(r.content, '') is not null then r.content else r.summary end,
            b.max_chars
        ) as content_preview,
        case when nullif(r.content, '') is not null then 'reviewed_snapshot_content' else 'reviewed_snapshot_summary' end as content_source,
        length(case when nullif(r.content, '') is not null then r.content else r.summary end) > b.max_chars as truncated,
        b.max_chars,
        r.category,
        r.tags,
        r.scope,
        r.sensitivity,
        r.content_hash,
        r.updated_at
    from readable r
    cross join bounded b;
$$;

comment on function public.vault_get_readable_memory_snapshot(text, text, text, text, integer) is
    'Policy-aware bounded read for reviewed central active memory snapshots. Returns a limited preview only; candidates and embeddings are never returned.';

grant execute on function public.vault_get_readable_memory_snapshot(text, text, text, text, integer)
    to anon, authenticated, service_role;
