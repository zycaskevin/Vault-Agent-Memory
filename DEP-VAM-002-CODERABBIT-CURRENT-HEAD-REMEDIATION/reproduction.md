# Reproduction

## Expected

Every `/memory/*` read treats an omitted or whitespace-only
`max_sensitivity` as `low`. The change feed obtains at most `limit + 1`
policy-readable metadata rows in one query, without a Python loop whose work
scales with hidden rows. Candidate-first HTTP operations leave the complete
active-memory content and governance snapshot unchanged.

## Actual

At exact public head `15eb5583d7fdf02358c4978cd22ab28ebd796ee4`,
whitespace is truthy before normalization, so the Gateway forwards an empty
ceiling and can return high-sensitivity content. A hidden-row fixture produces
two policy scans even for `limit=1`; no cumulative scan bound exists. The HTTP
facade regression compares only `count(*)`, so replacement of one active row
could pass vacuously.

The authorized current-head CodeRabbit review raised 12 findings. Local
verification classified eight as actionable and four as non-actionable:

- action: whitespace sensitivity, unbounded Python scan loop, full-snapshot
  oracle, final-proof commit provenance, bounded PATH reproduction, truthful
  blast radius, complete Ruff rollback command, and stale Local Green wording;
- disposition: SQLite connection close already ends the read transaction;
  historical RED artifacts must not be rewritten; Red and Green legitimately
  bind different commits; and reviewed-head equality would reject valid
  audit-only receipt descendants.

## Deterministic steps

From exact head plus only the two RED regression edits:

```text
env PYTHONPATH=. $VAULT_TEST_PYTHON -m pytest -q \
  tests/test_memory_change_envelope.py::test_change_page_uses_one_bounded_policy_query_and_selected_row_hydration \
  tests/test_gateway.py::test_memory_api_all_read_facades_reject_invalid_sensitivity_before_dispatch
```

Result: `2 failed`. The scan assertion observed two 100-row queries instead of
one `limit + 1` query. The Gateway read returned `status=ok` for a whitespace
ceiling and exposed the synthetic high-sensitivity fixture.

## Environment and preconditions

- base commit: `c284e1c7bedf288a10009b98e5f2da525c3ee4bc`
- public RED head: `15eb5583d7fdf02358c4978cd22ab28ebd796ee4`
- branch: `codex/vam-002-memory-change-envelope-ready`
- test runtime: CPython 3.11.15 and pytest 9.1.1
- fixtures are synthetic and temporary; no Hermes or live database is read or
  changed
