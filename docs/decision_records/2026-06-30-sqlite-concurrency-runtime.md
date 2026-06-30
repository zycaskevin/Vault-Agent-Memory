# SQLite Concurrency Runtime

Date: 2026-06-30

## Decision

Keep SQLite as the local source of truth, and harden the local runtime before
adding heavier queue or service infrastructure.

Vault now makes SQLite concurrency behavior explicit:

- connections use WAL mode, `synchronous=NORMAL`, and a configurable busy
  timeout;
- high-frequency local write paths retry common locked-database failures with
  rollback before retry;
- multi-agent docs recommend `vault-mcp` or a local write worker for sustained
  write traffic instead of many short-lived CLI subprocess writers.

## Why

The local-first design should stay simple: one portable `vault.db` should remain
usable by individual users, small teams, and agent runtimes without a required
server. At the same time, multi-agent setups can create lock contention when
many processes write at once.

The first response should make the current SQLite architecture more predictable
and observable, not replace it with a distributed system.

## Boundaries

- WAL and retry improve reliability; they do not remove SQLite's single-writer
  constraint.
- CLI subprocesses are safe for low-frequency writes, but they are not the
  preferred high-throughput write queue.
- MCP/server-style runtimes should be preferred for repeated agent operations.
- Candidate-first writes remain the default policy for shared vaults.

## Future Work

If real deployments need sustained concurrent writes, add an optional local
write worker that accepts candidate proposals and serializes them into the
vault. That worker should be optional and should not be required for core local
use.
