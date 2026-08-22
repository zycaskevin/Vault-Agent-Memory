# Fix Scope

## Smallest sufficient change

Strictly validate `max_sensitivity` for all four VAM-002 provider operations;
return a bounded `max_sensitivity_invalid` error from page/evidence operations;
map the exact three Memory API client errors to HTTP 400 and document them in
OpenAPI; clarify row-revision versus advisory-audit semantics; strengthen the
SQL trace assertion; and add an executable PR #500 rollback guard.

## Files or components in scope

- read-policy/provider/Gateway/OpenAPI implementation modules;
- VAM-002 focused provider and real-HTTP tests;
- VAM-002 SDD, ADR, public Memory API documentation, and existing DEP cleanup;
- sequential-integration rollback and this remediation DEP.

## Explicit non-scope

No database/schema/migration change, cursor format change, historical snapshot
feature, audit ordering change, legacy MCP/search strictness change, identity or
personality semantics, release, deployment, or merge.

## Blast radius

L1 remediation within the already approved L2 VAM-002 contract. Valid callers
are unchanged; only malformed sensitivity/cursor requests gain a non-success
response. Rollback remains approval-gated and is documentation-only until a
future explicitly authorized incident.
