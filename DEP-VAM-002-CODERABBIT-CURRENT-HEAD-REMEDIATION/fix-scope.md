# Fix Scope

## Smallest sufficient change

Trim the Gateway sensitivity input before applying the low default. Translate
the existing active read policy into a single SQLite predicate and fetch only
`limit + 1` readable metadata rows. Strengthen the candidate-first regression
to compare stable active-row fields. The eight verified defects comprise two implementation defects
(whitespace sensitivity and the unbounded Python scan loop) plus six test,
evidence, or documentation defects.

## Files or components in scope

- `vault/gateway_memory_api.py`
- `vault/memory_provider.py`
- focused Memory Provider and Gateway regressions
- the four named existing DEP documents and this remediation DEP

## Explicit non-scope

No schema or stored-data migration, new endpoint/error code, cursor-format
change, write-authority change, remote provider change, live Hermes operation,
release, deployment, merge, trust change, or Reviewer receipt.

## Blast radius

Read-side only. The Gateway becomes stricter only for blank sensitivity input,
matching its documented default. Change-page ordering, cursor semantics,
response shape, and selected-row hydration remain unchanged; policy selection
moves from repeated Python batches to one bounded SQLite result set.
