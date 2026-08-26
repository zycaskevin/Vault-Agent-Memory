# Root Cause Hypothesis

## Hypothesis

The whitespace leak is caused by applying the default before trimming. The
scan-cost defect is caused by filtering policy rows in a repeated Python batch
loop instead of one policy-filtered, result-bounded SQL query. The remaining
actionable findings are evidence/oracle drift accumulated across remediation
heads, not additional production causes.

## Supporting evidence

- `value or "low"` preserves a whitespace-only value; strict normalization then
  turns it into an empty ceiling.
- The exact RED fixture records two 100-row policy queries for a one-row page.
- The existing HTTP regression stores only a pre-request row count.
- The named evidence documents contain the stale text at the exact public head.

## Contradicting evidence

Known non-empty invalid labels already return `max_sensitivity_invalid`, and
normal low/high policies already filter ordinary rows correctly. SQLite closes
the connection at the context boundary, so the explicit read snapshot is not a
leaked transaction.

## Falsification test

Trim before applying the Gateway default, replace the batch loop with one SQL
policy predicate limited to `limit + 1`, and rerun the exact two-node RED. The
hypothesis is false if whitespace can still return the high fixture or more
than one policy-selection query executes.

## Conclusion

Confirmed by source inspection and deterministic RED.
