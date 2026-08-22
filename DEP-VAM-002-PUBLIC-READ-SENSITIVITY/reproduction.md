# Reproduction

## Expected

Unknown non-empty sensitivity labels return `max_sensitivity_invalid` before
any Memory API adapter runs. The four VAM-002 provider reads require a
non-empty `agent_id`; list/evidence return `agent_id_required`, while
metadata/revision return no row.

## Actual

Both no-revision Memory API adapters returned bounded high-sensitivity content
for `max_sensitivity=typo`. Direct provider reads with an omitted agent returned
a private/high row, metadata, revision, and content.

## Deterministic steps

Run `/tmp/vam-python-path-vam001/python -m pytest -q
tests/test_gateway.py::test_memory_api_all_read_facades_reject_invalid_sensitivity_before_dispatch
tests/test_memory_change_envelope.py::test_provider_authorized_reads_require_nonempty_agent_identity`.

## Environment and preconditions

Exact branch head `d2bed8a66895691e6765498490902b123129724a`, SQLite fixture
with synthetic shared-high and private-high rows, CPython 3.11.
