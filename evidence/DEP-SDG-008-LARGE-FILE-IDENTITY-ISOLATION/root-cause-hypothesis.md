# Root Cause Hypothesis

## Hypothesis

The T-001 large-file reader intentionally audits the full retained identity of
every path component. In a long shared pytest process, unrelated filesystem
activity can change size or mtime on a shared temporary ancestor, causing the
security check to deny even though the retained file bytes and inode are safe.

## Supporting evidence

- The failing read remained fail-closed; it did not accept hostile bytes.
- The exact baseline-control file passes 53/53 in a clean process.
- The complete closed per-node harness passes all previous nodes plus the 53
  baseline-control nodes, 430/430 total.
- The validator and baseline-control test hashes remain byte-identical to the
  T-001 terminal references.

## Contradicting evidence

No authorization acceptance changed, and no production input was read. The
defect is gate reliability under shared process/filesystem churn, not a bypass.

## Falsification test

Pin the baseline-control count at 53, execute every node through the existing
fresh-process harness, preserve the two frozen hashes, and require 430/430
PASS. Any drift, missing/duplicate node, or frozen-byte change falsifies the
hypothesis.

## Conclusion

Confirmed. Process isolation is the smallest safe fix. Editing the immutable
T-001 validator or tests would invalidate the terminal proof chain and remains
explicitly out of scope.
