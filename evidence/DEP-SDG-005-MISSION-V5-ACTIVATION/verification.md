# Verification

## Green command and result

Phase-correct focused gate in a clean detached protocol-base clone:

```text
python -m pytest -q \
  tests/test_subject_development_mission_v5.py::test_mission_activation_requires_exact_two_parent_merge_before_active \
  tests/test_subject_development_mission_v5.py::test_mission_activation_accepts_only_exact_two_parent_merge_delivery \
  tests/test_subject_development_mission_v5.py::test_mission_activation_accepts_exact_sdg_review_records_only \
  tests/test_subject_development_mission_v5.py::test_mission_activation_denies_proof_without_sdg_review_records
```

Result: `4 passed in 5.82s`.

## Before/after evidence

Before activation delivery: proof exists, pending is absent, T-004 has not
started, and the live unmerged topic is correctly INACTIVE/DENY. The synthetic
exact merge is GREEN. After delivery, protected review, hosted CI, exact merge,
and current-main ACTIVE readback must all pass before T-004 starts.

## Remaining limitations

This DEP does not claim activation or hosted verification yet. The final
protected receipt, Local Green, hosted checks, merge commit, and post-merge
ACTIVE result are appended only when each gate actually completes. The Mission
expires at `2026-11-14T02:53:59Z` and remains subject to irreversible owner
revocation and the frozen L2/L3 prohibitions.

The live-worktree control invocation was denied by the expected pre-merge
activation fixture. The phase-correct detached protocol-base invocation above
is the authoritative focused result. SDG-007 isolates all 75 Mission V5 test
nodes from the shared remainder for the later protected Local Green gate.
