# Gateway Security Checklist

Vault Gateway is a small HTTP adapter for agent memory. Treat it like a local
service by default. Expose it across hosts only when you control the network and
token storage.

## Startup Token

`vault gateway serve` prints a token when auth is enabled. Copy it only into
trusted local agent configuration.

For long-lived or remote deployments, set a stable token through the environment
instead of copying it into prompts:

```bash
export VAULT_GATEWAY_TOKEN="replace-with-a-long-random-secret"
vault remote-server serve --project-dir ~/Vaults/my-project --host 0.0.0.0
```

Do not commit tokens to source control, workflow JSON, public prompts, or
generated docs.

## Remote Deployment Checklist

- [ ] Keep token auth enabled. Do not use `--no-auth` outside localhost tests.
- [ ] Use TLS directly with `--tls-cert/--tls-key`, or put Gateway behind a
      trusted TLS reverse proxy.
- [ ] Restrict firewall, VPN, or IP allowlist access to known clients.
- [ ] Store `VAULT_GATEWAY_TOKEN` in environment variables or a secret manager.
- [ ] Run `vault remote-server health --json` before opening client access.
- [ ] Check `reports/gateway/audit.jsonl` during the first rollout week.
- [ ] Rotate the token if it was pasted into an unsafe place.

## Graceful Shutdown

`vault gateway serve` and `vault remote-server serve` drain on `Ctrl+C`,
`SIGINT`, or `SIGTERM`:

- stop accepting new requests;
- return `503 gateway_draining` to new clients during shutdown;
- wait for in-flight requests to finish.

The default drain timeout is 10 seconds. Tune it with:

```bash
vault remote-server serve --shutdown-timeout-seconds 30
export VAULT_GATEWAY_SHUTDOWN_TIMEOUT_SECONDS=30
```

Use a higher value when trusted clients may run long bounded-read or candidate
submission requests. Keep reverse proxy and supervisor timeouts longer than the
Gateway drain timeout so the process can finish its own cleanup.

## Central Candidate Inbox

Self-hosted `vault remote-server` exposes a Central Memory Station candidate
inbox without Supabase:

- `GET /central-candidates/status`
- `POST /central-candidates/submit`
- `POST /central-candidates/pull`

Submitted rows are stored in `vault-central.db` under
`vault_memory_candidates_central`. Pulling candidates imports them into the
local `memory_candidates` review queue; it still does not write active
knowledge. Use token auth, TLS or a trusted reverse proxy, and audit
`central_candidate_submit` / `central_candidate_pull` events before opening
this endpoint to many devices.

## HTTP Safety Headers

Gateway JSON responses include:

- `Cache-Control: no-store`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`

When Gateway serves TLS directly, it also sends:

- `Strict-Transport-Security: max-age=31536000; includeSubDomains`

If TLS is terminated by a reverse proxy, configure HSTS at that proxy.

## Troubleshooting

- `401`: send `Authorization: Bearer $VAULT_GATEWAY_TOKEN` or
  `X-Vault-Gateway-Token: $VAULT_GATEWAY_TOKEN`.
- `429`: wait and retry, or raise rate limits for trusted local clients.
- `vault.db missing`: run `vault init --project-dir <project>` or pass the
  correct `--project-dir`.
- Empty search results: run `vault compile --no-embed`, then retry a shorter
  search query.
