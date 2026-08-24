# Reproduction

## Expected

The PR #500 current head must describe historical evidence truthfully, keep
timestamped source evidence distinguishable from later corrections, expose
reproducible focused commands, use fail-closed rollback guards, and implement
the approved HTTP authorization contract. Missing `agent_id` on
`/memory/changes` or a revision-bound `/memory/{id}` read must return the
documented non-success error without rows or content.

## Actual

The completed replacement CodeRabbit review reported 13 findings. A bounded
RED regression confirmed all 12 documentation/evidence/rollback gaps and the
runtime contract defect: `agent_id_required` produced an error payload but
`gateway_memory_http_status` mapped it to HTTP 200. The static regression
reported the exact unclosed finding identifiers rather than treating every
third-party suggestion as automatically valid.

## Deterministic steps

From exact candidate `26df3c8693900ac4b734b342293a892df6560cb2`, add only
the two RED regression changes in `tests/test_gateway.py` and
`tests/test_vault_boundary_freeze.py`, then run:

```text
env PYTHONPATH=. $VAULT_TEST_PYTHON -m pytest -q \
  tests/test_gateway.py::test_memory_change_http_errors_use_non_success_status_and_openapi_contract \
  tests/test_vault_boundary_freeze.py::test_vam002_replacement_review_findings_have_current_reproducible_records
```

Expected RED: two failures. The Gateway test reports HTTP 200 instead of 400
for `agent_id_required`; the evidence-contract test lists the unclosed finding
IDs. The bounded transcript is collected as
`private/raw/terminal--replacement-review-red.txt`.

## Environment and preconditions

- Branch: `codex/vam-002-memory-change-envelope`
- Exact baseline: `c284e1c7bedf288a10009b98e5f2da525c3ee4bc`
- Exact candidate: `26df3c8693900ac4b734b342293a892df6560cb2`
- Runtime: CPython 3.11, pytest 9.1.1, repository source via `PYTHONPATH=.`
- Synthetic fixtures only; no live Hermes, production database, secrets,
  signing, trust mutation, merge, or deployment
