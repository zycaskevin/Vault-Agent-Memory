# Root Cause Hypothesis

## Hypothesis

The final evidence pass updated behavior and tests without applying one
cross-document semantic consistency check to rollback expectations, defect
categories, snapshot-oracle wording, and normalized Markdown assertions.

## Supporting evidence

- `rollback.md` simultaneously invokes the known RED command and says every
  command must exit zero.
- The reverted parent lacks the new bounded-query test node, mechanically
  proving the exact command cannot pass after rollback.
- The compatibility evidence says row count while the current HTTP regression
  compares full projected row snapshots.
- The test creates `normalized_spec` but still uses raw `spec` and raw
  `decision` for some assertions.

## Contradicting evidence

All hosted functional jobs and the bounded remediation checks are Green. The
exact committed-head Builder Local Green has not completed because two attempts
failed on private-clone identity setup before repository-wide pytest. This is
not evidence of a Memory API runtime regression, and the affected production
implementation remains unchanged by the proposed fix.

The second checkout defect is now mechanically resolved: the formal
`origin/main` ref exists at the exact PR base and the private clone remains
clean. No additional gate was run, so this preparation does not change the
proof state.

## Falsification test

Apply only the four bounded corrections and rerun the same static probe. The
hypothesis is false if any check remains RED or if the focused contract tests
regress without changing production code.

## Conclusion

Confirmed. The four failures arise from stale or internally contradictory proof
text and one brittle test implementation, not from the approved VAM-002 public
behavior.
