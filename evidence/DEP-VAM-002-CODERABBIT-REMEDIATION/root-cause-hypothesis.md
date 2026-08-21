# Root Cause Hypothesis

## Hypothesis

The first implementation reused integer-oriented legacy Gateway helpers and a
simple load-filter-slice provider path. The tests verified returned values but
not provider-boundary type preservation, a span above the hard ceiling, or SQL
query scope.

## Supporting evidence

`gateway_memory_get` calls `int(memory_id)` before the revision-bound provider
call. `SQLiteMemoryProvider.list_changes` selects every knowledge column and
all audit groups without a keyset predicate or SQL limit. The range test asks
for L1-L4 while the ceiling is 80.

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

Confirmed. The RED tests reproduced the unbounded query and both integer
coercions, while the 81-line test confirmed the provider ceiling already worked.
The bounded keyset scan and provider-owned identifier validation made the same
focused checks Green without a schema or write-path change.
