# SQLite schema migrations

Vault Agent Memory keeps SQLite schema metadata in two compatible places:

- `config.schema_version` remains the public compatibility value used by existing tools.
- `schema_migrations(version, name, applied_at)` records explicit migration metadata.
- `PRAGMA user_version` is also kept in sync with the current schema version.

The current schema target is defined by `VaultDB.SCHEMA_VERSION`.

## CLI workflow

Check schema status:

```bash
vault db status --pretty
```

Run the idempotent migration workflow:

```bash
vault db migrate --pretty
```

Both commands accept an explicit database path:

```bash
vault db status --db-path /path/to/vault.db --pretty
vault db migrate --db-path /path/to/vault.db --pretty
```

`status` emits a JSON object with the current version, target version, whether migration is needed, applied migrations, database path, and required-table presence. `migrate` emits a JSON summary including before/after status and any newly recorded migration versions.

## Compatibility notes

Existing databases that only contain `config.schema_version` are supported. Opening or migrating a database runs idempotent table/column creation, records migration metadata, and preserves existing knowledge rows. The `config.schema_version` value remains updated to the current schema version for older tests and integrations.

Backup and restore are intentionally separate operator workflows and are not implemented by this migration/status command set.
