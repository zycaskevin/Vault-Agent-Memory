# Root Cause Hypothesis

## Hypothesis

The first implementation reused integer-oriented legacy Gateway helpers and a
simple load-filter-slice provider path. The tests verified returned values but
not provider-boundary type preservation, a span above the hard ceiling, or SQL
query scope.

## Supporting evidence

`gateway_memory_http_get` decodes `{id}` through the integer-only
`_memory_id_from_path`, then `gateway_memory_get` calls `int(memory_id)` before
the revision-bound provider call. The HTTP-path regression test exercises both
sites from route parsing through the provider boundary.
`SQLiteMemoryProvider.list_changes` selects every knowledge column and all
audit groups without a keyset predicate or SQL limit. The range test asks for
L1-L4 while the ceiling is 80.

## Contradicting evidence

SQLite intentionally decodes its opaque decimal string internally, and the
existing read-range function already rejects spans larger than its effective
maximum. The defects are at the adapter boundary, regression coverage, and
query strategy; the public envelope shape and database schema remain valid.

## Falsification test

Make the Gateway pass an unchanged string into the provider, request 81 lines,
and trace list-change SQL. The hypothesis is falsified if any Gateway coercion
remains, an over-limit read succeeds, or an unbounded knowledge/audit query is
observed.

## Conclusion

Confirmed. The RED tests reproduced the unbounded query and both Gateway
integer-coercion sites through the HTTP-path test, while the 81-line test
confirmed the provider ceiling already worked. The bounded keyset scan and
provider-owned identifier validation made the same focused checks Green without
a schema or write-path change.

## Follow-up review findings

The next review found two independent contract gaps. `list_changes` performed
its bounded scan and selected-row hydration as separate autocommit reads, so a
concurrent commit could change a row between those phases. The PATCH operation
for `/memory/{id}` also omitted the path parameter required by its route
template. Commit `a3be45e272f126a96d519cffc6ea59027055a3e5` fixes both with
one explicit read transaction and a required positive-integer PATCH parameter;
the concurrent-writer and generated-OpenAPI tests make both claims falsifiable.
