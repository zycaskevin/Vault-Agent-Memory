# Reproduction

## Expected

All VAM-002 HTTP methods use the documented error status, active reads treat
present invalid governance labels as unreadable, rollback instructions are
executable and exact, and historical evidence is described without inventing
timestamps or rebinding the current gate to an obsolete head.

## Actual

At exact public head `acb6de412587d614086d4ae824abc2c2db277153`, PATCH
and DELETE returned an error payload with HTTP 200 when `agent_id` was missing.
An active read treated present empty/null scope or sensitivity as
`project`/`low`, which could expose malformed rows. Twelve review findings
required implementation or evidence clarification; two findings described
conditions already fixed in the current bytes and were dispositioned rather
than reintroduced.

## Deterministic RED

With `VAULT_TEST_PYTHON` bound to the repository-pinned Python, the added RED
selection was:

```bash
env PYTHONPATH=. "$VAULT_TEST_PYTHON" -m pytest -q \
  tests/test_access_policy.py::test_active_read_policy_defaults_only_absent_governance_labels \
  tests/test_memory_change_envelope.py::test_present_empty_governance_labels_fail_closed_across_provider_reads \
  tests/test_gateway.py::test_memory_change_http_errors_use_non_success_status_and_openapi_contract
```

It returned three failures: blank labels were readable in the canonical policy,
the SQLite change page exposed a blank-label row, and PATCH/DELETE had no
OpenAPI 400 response.

## Environment

- base: `c284e1c7bedf288a10009b98e5f2da525c3ee4bc`
- reviewed public head: `acb6de412587d614086d4ae824abc2c2db277153`
- synthetic local SQLite fixtures only
- no live Hermes, production data, signing, trust, push, merge, or deployment
