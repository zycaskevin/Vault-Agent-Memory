# Reproduction

## Expected

An opaque memory reference crosses the Gateway unchanged until the selected
provider validates it. A request for 81 lines fails with `range_too_large` and
reports the provider ceiling of 80. Change listing scans bounded metadata-only
batches, then fetches raw content and audit ids only for selected readable rows.

## Actual

The Gateway converts the reference with `int(memory_id)`. The evidence test
requests only four lines, so it does not prove the 80-line limit. The provider
executes an unbounded `SELECT * FROM knowledge` and groups audits for every row
before applying the read policy and page limit.

## Deterministic steps

Run `python -m pytest -q --tb=no tests/test_memory_change_envelope.py
tests/test_gateway.py -k 'bounded_policy_scans or revision_bound_bounded or
openapi_contract_documents or preserves_opaque'` before changing production
code.

## Environment and preconditions

Branch `codex/vam-002-memory-change-envelope`, reviewed head
`48cea2cb60c1d90dc6e4eeef92e2d1f604623cb7`, CPython 3.11.15, pytest 9.1.1,
local SQLite fixture only, no network or private dataset.
