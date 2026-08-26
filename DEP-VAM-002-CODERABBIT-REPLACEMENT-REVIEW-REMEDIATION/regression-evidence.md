# Regression Evidence

## Regression test added or strengthened

- `test_memory_change_http_errors_use_non_success_status_and_openapi_contract`
  now binds `agent_id_required` to HTTP 400 and the OpenAPI error enum.
- `test_gateway_http_memory_api_facade_routes` proves missing identity on both
  `/memory/changes` and revision-bound `/memory/{id}` returns HTTP 400 with no
  rows or content.
- `test_vam002_replacement_review_findings_have_current_reproducible_records`
  binds every evidence, rollback, command, manifest, redaction, strict-proof,
  audit-descendant, authorization, and SDD disposition from the 13-item
  review.
- The existing rollback contract test now requires the successor DEP to remain
  preserved by the guarded PR rollback.

## Related tests executed

- Original RED selection: 2 failed.
- Exact focused Green including real loopback HTTP: 26 passed in 1.21s.
- Immutable `a3be45e...` follow-up revalidation: 43 passed in 9.12s.
- Ruff on all four changed Python files: PASS.
- Module size gate: PASS, 159 modules scanned.
- All ten predecessor VAM-002 DEPs: strict PASS with the hosted verifier
  version `0.2.0-experimental.6`.
- Governance Doctor and CI contract: PASS with no warning/error.

## Unaffected paths sampled

No storage schema, migration, write path, cursor encoding, content policy,
Frozen Subject contract, dependency declaration, live Hermes workspace,
production database, Reviewer receipt, or trust file changed. `git diff
--check` passed.
