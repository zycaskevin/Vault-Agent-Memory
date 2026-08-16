# Reproduction

## Expected

The protocol-release checker must first validate exact merged SDG-010 and then
require one exact closed SDG-011 two-parent delivery. The merged SDG-010 anchor
alone must remain ineligible as a fresh proposal base.

## Actual

At exact `origin/main` `efa43a4dfb305cd51d8a57a20838be6123ccb514`,
`_check_protocol_release_commit()` passes that merge to
`_check_sdg008_compatibility_release()`. The latter requires first parent
`6d499e41ac41b8cd0f560146b0f18939b55a5f3f`, while `efa43a4` correctly has
first parent `46690372e532c50761f9232ff5b2e20e18779d28`, so a fresh Mission proposal
is denied.

The merged SDG-010 rollback record also queries source branch
`agent/sdg010-mission-v5-ci-phase-routing`, but merged PR #484 used actual head
`agent/sdg010-mission-v5-ci-phase-routing-v4`. Its rollback command therefore
cannot resolve the delivery it claims to reverse.

The first code-bearing Builder Local Green on source `db4f142ab` completed
doctor, CI verification, README smoke, and release parity, then stopped during
identity collection. Thirteen new Mission V5 regression nodes raised that
file's exact collection from 77 to 90 while the closed identity harness still
pinned 77. No identity node or disjoint remainder test started.

## Deterministic steps

1. Read `efa43a4` parents and require exact base `46690372` then topic
   `7e155ca`.
2. Compare merge and topic trees; both are exact `781beb6d`.
3. Invoke the pre-fix release chain with `efa43a4`; observe the SDG-008 parent
   mismatch denial.
4. Evaluate the merged rollback query against exact PR #484 metadata; observe
   the branch mismatch.
5. After the fix, retain denial for `efa43a4`, create a closed SDG-011 topic and
   exact two-parent merge, and require acceptance only for that merge.
6. Collect the closed identity suite and require exactly 90 Mission V5 nodes
   before running each node once.

## Environment and preconditions

Issue #485; clean isolated branch
`agent/sdg011-post-sdg010-l1-compatibility`; CPython 3; local Git objects from
the exact public repository. No proof, private data, credential, ledger,
deployment, production, or external live action is involved.
