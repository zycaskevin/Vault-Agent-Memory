# Gateway Graceful Shutdown

Date: 2026-07-03

## Decision

Vault Gateway and Vault Remote Server support graceful shutdown for `SIGINT`,
`SIGTERM`, and `Ctrl+C`.

Shutdown enters drain mode:

- stop accepting new requests;
- return `503 gateway_draining` to clients that connect during drain;
- wait for active requests to complete;
- respect `--shutdown-timeout-seconds` or
  `VAULT_GATEWAY_SHUTDOWN_TIMEOUT_SECONDS`.

The default drain timeout is 10 seconds.

## Rationale

Gateway is the shared HTTP entrypoint for local and cross-host agents. Abrupt
termination can interrupt memory searches, bounded reads, or candidate
submissions in ways that are hard for agents to distinguish from network
failures.

Drain mode gives supervisors, LaunchAgents, containers, and operators a
deterministic shutdown path without adding a new dependency or changing the
Gateway HTTP contract.

## Scope

This is not a distributed load balancer or queue. Public deployments should
still place Gateway behind a reverse proxy or supervisor with compatible
timeouts. Reverse proxy stop timeouts should be longer than the Gateway drain
timeout so in-flight requests can finish.
