# Obsidian Import Dry-Run Contract

Date: 2026-07-03

## Decision

`vault import obsidian --dry-run` is a pure preview mode.

Even when combined with `--compile`, dry-run must not:

- write `raw/` files;
- write `.vault/obsidian-import-manifest.json`;
- write or update SQLite `knowledge` rows;
- run `vault compile`.

## Rationale

New users may point Vault at a large Obsidian vault before they understand the
import model. A dry-run flag should be safe to run repeatedly and should never
silently populate active memory.

## Behavior

- Human output states that dry-run does not write `raw/` and does not compile.
- JSON output includes `dry_run_semantics` and `next_action` so agents can
  explain the difference between preview and apply.
- A regression test verifies `--dry-run --compile --json` leaves `knowledge`
  empty and does not create raw import files or the Obsidian import manifest.

## Non-Goals

- This does not change normal `vault import obsidian --compile` behavior.
- This does not change conflict-resolution dry-run behavior.
- This does not make import automatically promote notes into trusted memory.
