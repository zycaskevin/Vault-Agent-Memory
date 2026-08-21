# Root Cause Hypothesis

## Hypothesis

The owner architecture decision was issued after PR #494 merged, so the
repository has correct T-004 origin artifacts but no later record that transfers
future Subject runtime ownership out of Vault.

## Supporting evidence

- PR #494 and the progress ledger correctly complete T-004.
- T-005 through T-033 remain pending.
- Issues #495, #496, and #497 remain open and describe the superseded path.
- The deterministic test fails only on the missing extraction record, status,
  and drafts.

## Contradicting evidence

The existing page already states that the runtime is not implemented and keeps
candidate-first safety language. Those facts are compatible with extraction,
but they do not establish the new ownership or issue disposition.

## Falsification test

Add only the approved ADR, non-frozen status paragraph, and local issue-comment
drafts. The original test must pass while a scoped diff proves that frozen
specifications and the progress ledger remain unchanged.

## Conclusion

Confirmed. The gap is a missing transition record, not a runtime defect or a
need to modify frozen history.
