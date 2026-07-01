# Low-Risk Remote Candidate Auto-Merge

Date: 2026-07-01

## Decision

Vault may auto-promote remote candidate requests only after they have been
pulled into the local `memory_candidates` queue by a trusted host and only when
the local `automation_policy.yaml` explicitly allows it.

The command boundary is:

```bash
vault remote pull-candidates --apply --auto-promote-low-risk
```

## Safety Conditions

Remote auto-merge is never enabled by default. A candidate must satisfy all of
these local checks:

- imported in the current pull run
- source is allowed, for example `remote_write_request`
- memory type is allowed, for example `remote_candidate`
- scope is allowed, usually `shared`
- sensitivity is allowed, usually `low`
- trust is at or above the configured threshold
- source reference exists
- privacy, duplicate, metadata, and quality gates all pass
- learning policy does not require review

Low-trust, duplicate, sensitive, private, high/restricted, weak-quality, or
learning-downgraded candidates remain in the review queue.

## Why

This is the second phase after safe bidirectional candidate sync. It reduces
daily review load without letting remote hosts directly write active knowledge.
The trusted local host remains the place where gates, policy, raw Markdown
creation, compile, Document Map build, and audit feedback happen.

## Non-Goals

- No remote direct writes to `vault_knowledge`.
- No automatic merge without local policy.
- No multi-host active-memory direct overwrite.
- No full revision-graph rollback protocol yet.

## Next Phase

True multi-host co-writing still requires distributed revision exchange,
stronger rollback policy, and append-only audit enforcement.

Status update: the next PR added a local revision/conflict/audit surface and a
guarded conflict resolver. `accept_remote --apply-memory-change` promotes the
remote candidate and archives the conflicting local row instead of overwriting
it.
