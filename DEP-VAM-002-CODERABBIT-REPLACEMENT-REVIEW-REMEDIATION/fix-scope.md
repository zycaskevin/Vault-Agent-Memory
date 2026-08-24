# Fix Scope

## Smallest sufficient change

Map `agent_id_required` to the existing HTTP 400 Memory API error contract;
add direct and real-HTTP regressions for the two affected read endpoints; make
the SDD mapping explicit; correct current DEP narratives and rollback guards;
add manifest-bound successor proof instead of silently rewriting historical
raw evidence; and add one regression that binds all 13 dispositions.

## Files or components in scope

- `vault/gateway_memory_api.py` and `vault/gateway_openapi.py`;
- `tests/test_gateway.py` and `tests/test_vault_boundary_freeze.py`;
- `docs/specs/vam-002-memory-change-envelope.md`;
- the cited VAM-002 reproduction, verification, rollback, manifest,
  redaction-report, and shareable derivative files;
- `DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md`;
- this successor DEP and final audit-only merge-gate rebind.

## Explicit non-scope

No memory schema, stored row, cursor encoding, authorization policy, content
filter, write path, identity/personality/relationship semantics, dependency,
live Hermes workspace, production data, receipt, Reviewer trust, merge,
release, or deployment.

## Blast radius

Malformed public requests that omit `agent_id` on `/memory/changes` or a
revision-bound `/memory/{id}` read change only from HTTP 200-with-error to HTTP
400-with-the-same-error. All valid-call results remain unchanged. The rest is
test, documentation, rollback, and evidence provenance.
