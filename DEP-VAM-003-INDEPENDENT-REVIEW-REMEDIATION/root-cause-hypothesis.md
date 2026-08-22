# Root Cause Hypothesis

## Hypothesis

The first VAM-003 implementation updated the primary boundary statements but
did not inventory all active guidance. Its rollback was written as an
operator-oriented procedure without exercising the installed merge verifier or
running its embedded Python checks under optimized mode.

## Supporting evidence

- The focused regression recorded five deterministic failures at exact head
  `8eec35c3b228efbdfc8707a11e2d31e885002562`.
- The three named guides contained the stale profile/identity phrases reported
  by the independent Reviewer.
- Hosted governance job `96972271288` rejected the rollback record as missing
  or incomplete.
- Both rollback checks used `assert`, which CPython removes under `-O`.
- The post-mutation guard checked only tracked, unstaged differences.

## Contradicting evidence

- The runtime boundary, canonical `L0-bootstrap` path, and compatibility alias
  were already implemented and passed focused tests.
- All hosted functional jobs passed, so the finding is limited to active
  guidance, rollback governance, and evidence binding rather than runtime
  behavior.

## Falsification test

Replace the stale phrases and strengthen the rollback contract, then run the
new tests under ordinary and optimized Python. The hypothesis is false if the
tests remain red or if merge verification still rejects the record.

## Conclusion

Confirmed. The missing guidance inventory and non-executable rollback contract
fully explain the observed review and hosted-governance failures.
