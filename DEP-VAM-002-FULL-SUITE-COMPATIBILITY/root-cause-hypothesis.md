# Root Cause Hypothesis

## Hypothesis

The two failures have independent, confirmed causes:

1. The HTTP test added a high-sensitivity fixture after `_project` created two
   rows, but retained the old literal final count of two.
2. `evaluate_governed_read` correctly records `unknown_scope` and
   `unknown_sensitivity`, then its generic authorization branch records
   `unauthorized` for the same fail-closed decision.

## Supporting evidence

The database contained exactly three rows before the HTTP server started, and
the failure reported three afterward. The focused read-guard reproduction
returned the two precise codes plus only the redundant generic code.

## Contradicting evidence

No active-row write or authorization bypass was observed. The read decision
remained denied, so this is diagnostic precision rather than a fail-open
security defect.

## Falsification test

Capture the active-row count after all fixtures and assert it is unchanged
after all HTTP requests. For unknown stored labels, assert denial with exactly
the two typed codes and run the surrounding governance-read tests.

## Conclusion

Confirmed. The smallest fix is one stable before/after test oracle and one
guard branch that suppresses generic authorization only when unknown stored
labels already explain the denial.
