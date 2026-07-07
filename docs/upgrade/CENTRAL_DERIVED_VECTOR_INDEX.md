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

Remote vector read remains disabled. The status surface exists so operators and
tests can verify index posture before later Gateway, Remote Server, or
Supabase/Postgres vector-read work.

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
