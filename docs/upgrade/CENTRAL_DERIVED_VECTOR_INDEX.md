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
