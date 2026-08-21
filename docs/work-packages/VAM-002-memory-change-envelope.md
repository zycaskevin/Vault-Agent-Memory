# Work Package: VAM-002 Stable Memory Change Envelope

## References

- Issue: `docs/issues/VAM-002-memory-change-envelope.md`
- SDD: `docs/specs/vam-002-memory-change-envelope.md`
- Decision: `docs/decision_records/2026-08-21-memory-change-envelope.md`
- Risk: L2

## Objective Contract

- Outcome: give external memory consumers a stable, governed incremental-read
  contract without exposing Vault storage internals.
- Success metric: provider and HTTP contract tests prove stable revisions,
  policy-bound cursor pagination, no hidden-row counts, full content SHA-256,
  revision-bound bounded evidence, and compatibility with existing routes.
- Guardrails: no application-domain endpoints or dependencies; no schema
  migration; no direct active-memory writes; no raw content in change pages;
  no hidden-count leakage; no authority switch; no merge, release, or deploy.
- Keep condition: focused and full local tests are Green, strict DEP evidence is
  complete, and an independent focused architecture review is obtained before
  merge.
- Rollback condition: access-policy mismatch, stale revision returning content,
  cursor reuse across policies, hidden-row metadata leakage, existing API
  regression, or database migration requirement.

## Scope

- In scope: provider-independent envelope helpers; SQLite provider methods;
  `GET /memory/changes`; revision binding on bounded reads; OpenAPI and Memory
  API documentation; focused regression tests; DEP proof; Draft PR.
- Non-scope: application identity/personality/subject modeling; historical
  snapshot storage; Digital Life package/database code; provider-authority
  promotion; remote synchronization; private/live datasets; production,
  release, deployment, merge, or destructive actions.
- Dependencies: current Memory Provider Interface, Gateway Memory API facade,
  access-policy helpers, bounded read-range implementation, audit metadata, and
  the approved 2026-08-21 Vault boundary-freeze direction.
- Evidence requirement: RED failures for missing contract behavior, focused
  Green, API/privacy regression Green, full Local Green, strict DEP, and focused
  architecture review before merge.
- Verification plan: memory-change unit tests; provider tests; Gateway direct
  and HTTP tests; OpenAPI assertions; Ruff for changed Python; repository Local
  Green; strict DEP verification.

## Claim

- Agent: codex
- Claimed at: 2026-08-21T10:01:36Z
- Expires at: 2026-08-21T18:01:36Z
