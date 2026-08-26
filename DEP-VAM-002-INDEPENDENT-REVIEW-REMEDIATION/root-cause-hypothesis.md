# Root Cause Hypothesis

## Hypothesis

VAM-002 reused the legacy permissive read-policy normalizer at a new public
provider boundary. That normalizer intentionally converts unknown sensitivity
labels to an empty ceiling for older local callers, but the change-envelope
operations require strict client-input validation. Separately, the Gateway
transport treated every Memory API payload as HTTP 200, the SDD conflated
canonical row fields with advisory audit metadata, and review evidence did not
mechanically prove its audit-query and rollback claims.

## Supporting evidence

- The RED probe exposes a high-sensitivity shared row only when the ceiling is
  misspelled; the same row is hidden under `low`.
- `normalize_read_policy` erases an unknown non-empty label, after which no
  sensitivity ceiling is applied.
- Provider cursor errors already have stable error payloads, but the HTTP
  handler sends all Memory API GET payloads with the default 200 status.
- Changing only `audit_ref` leaves the row-based revision material unchanged.
- The rollback document has no executable guard, and `all([])` makes the SQL
  trace assertion pass without an audit query.

## Contradicting evidence

Valid sensitivity labels, row-based revisions, bounded keyset scanning, and
the production selected-row audit query all behave correctly. The defect is
the strictness and proof at the new boundary, not the storage/query design.

## Falsification test

The hypothesis is false if strict validation still permits rows/content under
an invalid label, if HTTP cursor errors remain 200, if audit-only metadata
changes alter the row revision, or if the guarded rollback can reach `git
revert` without exact merge/base/head/approval/cleanliness checks.

## Conclusion

Confirmed. Introduce one strict provider-boundary policy helper while
preserving legacy permissive normalization, map the exact client-error set to
HTTP 400, clarify advisory audit metadata, strengthen the SQL oracle, and
replace prose rollback with an executable fail-closed procedure.
