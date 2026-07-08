# Central Derived Vector Index Status

Vault treats vector indexes as derived retrieval caches. They are not a second
memory source of truth.

Use the read-only status command to inspect the current local derived index:

```bash
vault vector-index status --json
```

For a stricter health check:

```bash
vault vector-index doctor --json
```

To generate a metadata-only dry-run repair plan:

```bash
vault vector-index plan --json
```

To inspect the safe repair wrapper without changing the index:

```bash
vault vector-index repair --json
```

To apply the wrapper, pass `--apply`. It uses the existing semantic rebuild
workflow and defaults to a changed-only pass:

```bash
vault vector-index repair --apply --write-report --json
```

For local tests only, deterministic hash vectors can validate the wrapper:

```bash
vault vector-index repair --apply --allow-hash --hash-dim 8 --write-report --json
```

To persist the latest status or dry-run plan for cron, release audit, or the
next agent handoff:

```bash
vault vector-index status --write-report --json
vault vector-index plan --write-report --json
```

These write:

- `reports/vector-index/status-latest.json`
- `reports/vector-index/status-latest.md`
- `reports/vector-index/plan-latest.json`
- `reports/vector-index/plan-latest.md`

To check whether the Supabase central vector schema has been applied:

```bash
vault vector-index central-status --json
```

With `--write-report`, this writes:

- `reports/vector-index/central-status-latest.json`
- `reports/vector-index/central-status-latest.md`

The same metadata-only observability is included in the daily-loop report path:

```bash
vault daily-loop report --refresh --write-report
```

That refresh writes the daily-loop report and refreshes the vector-index status
and dry-run plan artifacts without ingesting transcripts, creating candidates,
rebuilding vectors, or cleaning up index rows.

The current implementation reads the existing local `semantic_vectors` table and
reports:

- whether the index is empty, partial, stale, or locally ready;
- provider, dimension, and vector-kind breakdown;
- how many reviewed active rows are indexable under the default shared-read
  policy;
- stale vectors whose stored content hash no longer matches the source memory;
- vectors tied to private, high/restricted, archived, or otherwise non-default
  shared-read memory;
- whether the index is safe for local vector search and whether it is ready for
  future shared remote vector read.

The `plan` action groups metadata rows into:

- missing default-policy vectors;
- stale vectors;
- shared remote-read risk vectors;
- orphan vectors.

It does not include raw memory content or vector source text. Treat it as a
dry-run repair and cleanup plan before running rebuilds or designing remote
vector read.

The report artifacts follow the same safety boundary: metadata, counts,
recommended commands, and sampled row identifiers only. They are intended for
scheduled observability and release review, not as a memory export.

The Supabase central vector schema is installed by applying:

```sql
supabase/migrations/20260708_central_vector_index.sql
```

That migration creates `public.vault_memory_embeddings`, a pgvector/HNSW index,
a metadata-only `vault_central_vector_index_status()` RPC, a guarded
`vault_match_readable_memory_embeddings()` preview RPC, and a bounded
`vault_get_readable_memory_snapshot()` read RPC. It is a derived remote read
cache for reviewed safe summaries. It does not let remote agents write vectors
and does not index candidates.

After the active snapshot read copy is synced, a trusted sync host can push
reviewed safe-summary embeddings:

```bash
vault memory-sync run-once --push-central-store --push-central-vectors --json
```

The writer requires a 1536-dimensional provider, defaults to OpenAI
`text-embedding-3-small`, skips private/high/restricted memory, skips
candidates, requires `VAULT_SUPABASE_TRUSTED_SYNC_HOST=1` when using env
credentials, and builds `remote_search_text` from title, summary, category, and
tags instead of raw memory content.

Remote semantic read is available through the policy-aware RPC, MCP, and
Gateway/Remote Server HTTP paths:

1. `vault_remote_semantic_search` creates a query embedding, calls
   `vault_match_readable_memory_embeddings()`, and returns safe preview rows.
2. Each preview row includes a `read_handle` and `next_action.tool` pointing to
   `vault_remote_snapshot_read`.
3. `vault_remote_snapshot_read` calls `vault_get_readable_memory_snapshot()` and
   returns a bounded central snapshot preview.
4. Non-MCP agents can use `POST /remote-semantic-search` followed by
   `POST /remote-snapshot-read` through the Gateway contract.

The preview path returns safe metadata such as title, summary, tags, scope,
sensitivity, similarity, and `read_handle`; it does not return
`remote_search_text` or embedding values. The bounded read returns a capped
`content_preview` from reviewed snapshot content when available, otherwise the
reviewed summary. It does not read candidates and does not expose the vector
table.

Verified live on 2026-07-08 against the Codex private-memory central read copy:
three latest central vector rows returned safe semantic previews, each preview
contained a `read_handle`, each `next_action.tool` was
`vault_remote_snapshot_read`, and each bounded snapshot read returned
`bounded_central_snapshot_preview` with `returns_embedding_values=false`,
`returns_raw_memory_content=false` on semantic preview, `candidate_first=true`,
and `bounded_preview=true`.

Rebuild vectors through the existing semantic workflow:

```bash
vault semantic rebuild
```

For local tests only, deterministic hash vectors can validate plumbing:

```bash
vault semantic rebuild --allow-hash --hash-dim 8
```

Hash vectors are not semantic-quality evidence and should not be used for public
retrieval-quality claims.
