# Fix Scope

## Smallest sufficient change

- Record the knowledge-row count after HTTP test fixture setup and assert the
  same count after all candidate-first requests.
- Keep unknown stored labels fail-closed, but do not append generic
  `unauthorized` after the precise unknown-label codes.
- Run the two failing nodes plus adjacent authorization diagnostics before a
  separately authorized exact-head complete Local Green.

## Files or components in scope

- `tests/test_gateway.py`
- `vault/governance_read_guard.py`
- `tests/test_memory_foundation_compare.py` as the existing regression oracle
- this DEP

## Explicit non-scope

No write-path semantics, API payload schema, database migration, live Hermes
configuration or data, trust, signing, push, merge, or deployment.

## Blast radius

The production change affects only reason-code reporting for already-denied
rows with malformed stored governance labels. All known-label authorization
paths and the deny decision remain unchanged.
