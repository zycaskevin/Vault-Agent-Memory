# Supabase and Docker Collectors

## Supabase (`supabase-log`)

Default to the local development stack. Record the command, local project reference, migration snapshot, API status, and narrow service log window.

```bash
supabase status
supabase functions serve <name> --debug > supabase-function.log 2>&1
evidence collect <DEP> --collector supabase-log --input supabase-function.log
```

Fail closed when a command may target production. Do not apply, repair, reset, or replay a production migration as evidence collection. Do not export tables or auth records. Remove JWTs, service-role keys, emails, user IDs, database URLs, and webhook signatures.

## Docker (`docker-log`)

Use explicit container/service names and a bounded time window:

```bash
docker logs --since 10m <test-container> > docker-failure.log 2>&1
evidence collect <DEP> --collector docker-log --input docker-failure.log
```

Do not collect every container or environment dump. `docker inspect` may reveal environment secrets; prefer a manually written configuration summary unless exact non-secret metadata is required.
