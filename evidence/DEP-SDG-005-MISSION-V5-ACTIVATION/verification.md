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

Result: `4 passed in 8.25s` on the refreshed SDG-008 protocol base.

Phase-correct full Local Green on an exact synthetic two-parent delivery:

```text
identity-isolated subject tests passed: 430 nodes
2867 passed, 12 skipped, 1 warning in 101.52s
local-gate return code: 0
```

The synthetic delivery reported `ACTIVE`, sequence `6`, and the exact Mission
ID. Its tree differed from the reviewed topic only by the test-only placeholder
`REV-SDG-005`; that placeholder is never copied into the candidate branch.

## Before/after evidence

Before activation delivery: proof exists, pending is absent, T-004 has not
started, and the live unmerged topic is correctly INACTIVE/DENY. The synthetic
exact merge is GREEN. After delivery, protected review, hosted CI, exact merge,
and current-main ACTIVE readback must all pass before T-004 starts.

## Remaining limitations

This DEP does not claim activation or hosted verification yet. The final
protected receipt, hosted checks, merge commit, and post-merge ACTIVE result
are appended only when each gate actually completes. The Mission
expires at `2026-11-14T05:35:57Z` and remains subject to irreversible owner
revocation and the frozen L2/L3 prohibitions.

The refreshed pre-sign Local Green ran once with all six configured commands
returning `0`; identity isolation took `428.184s` and the disjoint remainder
took `101.921s`. The live-worktree control invocation was denied by the expected pre-merge
activation fixture. The phase-correct exact two-parent invocation above is the
authoritative focused result. SDG-007 isolates all 76 Mission V5 test nodes and
SDG-008 expands the identity-isolated boundary for the later protected Local
Green gate.

Protected review revision 1 passed pre-sign Local Green but the mandatory
post-sign verifier stopped before tests because the rollback command contained
the literal shell redirection token `>`, which experimental.6 reserves for
unresolved placeholders. Revision 2 removes that token while preserving the
same detached-base INACTIVE verification. The revision-1 receipt is invalid
and is not present in this candidate history.

The first refreshed protected-review attempt after SDG-008 correctly rejected
three stale `75`-node claims; those claims now use the independently collected
`76` Mission V5 nodes. Its next revision was run concurrently with a separate
same-repository RC Local Green. Both identity harnesses create and remove
private test roots under the same user home, so the concurrent sibling mutation
changed retained ancestor metadata and one `linked-linked` lifecycle case
failed closed in `_audit_lifecycle`. The receipt was not signed. This is an
execution-scheduling artifact, not permission to weaken full identity checks.
The next protected review must hold an external exclusive same-repository test
lease for the entire identity harness and Local Green; no other pytest,
identity harness, or Local Green may run until the lease is released.
