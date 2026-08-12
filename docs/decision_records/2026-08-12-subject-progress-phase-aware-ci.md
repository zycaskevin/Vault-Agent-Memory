# Subject progress phase-aware CI

Date: 2026-08-12
Status: Accepted
Risk: L0 test and CI routing repair

## Context

The T-001 completion review binds `tests/test_subject_progress.py` byte-for-byte.
That historical test also asserts the exact T-001 delivery ledger phase: sequence
2, `T-001=COMPLETED`, and every later task still `PENDING`. Once T-002 starts,
the live ledger correctly advances to sequence 3 and `T-002=IN_PROGRESS`; rerunning
the historical repository-phase assertion against that newer ledger is therefore
a phase mismatch, not a product regression.

Changing the historical test would invalidate T-001's content-addressed evidence.
Weakening or disabling it would remove a delivery control. Neither is acceptable.

## Decision

Release Readiness CI separates the two valid phases:

1. The current checkout runs the complete current-state suite except the exact
   immutable `tests/test_subject_progress.py` file.
2. A detached temporary worktree at the post-bridge, pre-T-002 checkpoint
   `8ec045a7b39c5aa9684f61d9099eb62b3142983d` verifies the pinned test, progress
   validator, and sequence-2 ledger SHA-256 values, then runs the entire immutable
   historical test file.
3. The current checkout independently runs the v1 progress validator and the v2
   authorization overlay, so current ledger state remains fail-closed.
4. T-002 v2 unit tests derive their sequence-2 prestart fixture from the
   hash-bound T-001 activation events instead of appending a second sequence-3
   event to the live ledger.

The routing is locked by `tests/test_repo_hygiene_tools.py`: no broad ignore,
`-k`, xfail, `continue-on-error`, or deselection is allowed.

## Consequences

- No T-001 source or evidence byte changes.
- No test is discarded: the immutable T-001 test runs in its reviewed historical
  phase, while current validation runs against the live phase.
- The hotfix changes the Git base, so any earlier T-002 proposal, receipt, proof,
  and sequence-3 start are obsolete. T-002 must restart from the merged clean main
  with a fresh exact proposal and owner confirmation.

## Reopen conditions

Reopen this decision if the T-001 pinned hashes or completion commit change, the
v1/v2 progress validation interfaces change, or a later authorization protocol
provides a mechanically stronger phase-replay mechanism.
