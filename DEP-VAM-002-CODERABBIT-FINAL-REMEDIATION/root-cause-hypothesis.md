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

All hosted functional jobs and the bounded remediation checks are Green. Two
historical attempts at exact implementation commit
`c004c04cd1c1ed471ba39d6d4ad0f5e565dfea5a` failed during private-checkout
identity setup before repository-wide pytest; neither failure was a Memory API
runtime regression. After the formal GitHub origin and exact `origin/main` ref
were prepared, the separately authorized run at the same exact commit passed:
446 identity-isolated Subject nodes, then 2970 passed, 10 skipped, 1 warning.
This successful exact-head proof supersedes the earlier pending statement while
retaining both failed setup attempts as historical evidence.

## Falsification test

Apply only the four bounded corrections and rerun the same static probe. The
hypothesis is false if any check remains RED or if the focused contract tests
regress without changing production code.

## Conclusion

Confirmed. The four failures arise from stale or internally contradictory proof
text and one brittle test implementation, not from the approved VAM-002 public
behavior.
