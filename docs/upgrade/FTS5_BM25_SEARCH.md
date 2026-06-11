# FTS5 / BM25 keyword search upgrade

This PR upgrades keyword search from a pure `LIKE` scan to an optional SQLite FTS5 index with BM25 ranking.

## Behavior

- `VaultDB.connect()` attempts to create `knowledge_fts` using SQLite FTS5.
- If FTS5 is available, `VaultSearch.search_keyword()` queries `knowledge_fts MATCH ...` and orders by `bm25(knowledge_fts)`.
- If FTS5 is unavailable, has a malformed query, or returns no rows for a CJK/mixed-token query, search falls back to the existing `LIKE` keyword path.
- The result `_mode` is:
  - `keyword_fts` when the FTS5/BM25 path returns rows.
  - `keyword` when the fallback path is used.

## Index synchronization

The FTS index is maintained on normal knowledge CRUD:

- `add_knowledge()` inserts the row into `knowledge_fts`.
- `update_knowledge()` replaces the FTS row for that knowledge id.
- `delete_knowledge()` removes the FTS row before deleting the knowledge row.
- Existing databases are backfilled on first connect when the FTS table is empty.

## Fallback policy

FTS5 is an acceleration layer, not a hard dependency. Base installs must still support keyword search on SQLite builds without FTS5.

Fallback is intentionally conservative for Traditional Chinese/CJK and mixed technical queries. SQLite's default `unicode61` tokenizer does not provide full CJK segmentation, so zero-hit FTS queries are retried with the prior `LIKE` search behavior.

## Verification

Use Search QA before and after retrieval changes:

```bash
python -m vault.cli search-qa run \
  --db-path path/to/vault.db \
  --qa-file benchmarks/search_qa/basic.en.json \
  --mode keyword \
  --limit 3
```

Quality metrics should not regress. Latency metrics are directional and should only be compared on the same machine with the same fixture size.

On the PR B development machine, the tiny public Search QA fixtures kept the same quality metrics (`top1_hits=2`, `topk_hits=2`, `MRR=0.6666666666666666`, `citation_policy_violations=0`). A larger synthetic single-token benchmark with 20,000 rows showed the intended indexed lookup behavior:

| Search path | Top result | Mode | mean latency |
|---|---|---|---:|
| pre-FTS `LIKE` | `Unique Needle Retrieval` | `keyword` | 8.358 ms |
| FTS5/BM25 | `Unique Needle Retrieval` | `keyword_fts` | 0.136 ms |
