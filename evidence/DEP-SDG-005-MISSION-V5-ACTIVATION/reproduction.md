# Reproduction

## Expected

An exact owner-confirmed Mission V5 proof remains inactive on an unmerged
topic, then becomes ACTIVE only after the exact SDG-005 protected-review tree
is delivered by one direct two-parent merge on current main.

## Actual

The proof is atomically published and private cleanup has passed. The live
pre-merge validator returns DENY because no qualifying delivery merge exists;
this is the required phase boundary, not a product regression.

## Deterministic steps

1. Start from clean merged main `46690372e532c50761f9232ff5b2e20e18779d28`.
2. Reconstruct proposal
   `8acdc645348e625cdfacf1f42ca0185c787d042654d18c31fd541c966447b2c9`
   and verify the exact owner-confirmed receipt digest.
3. Run the retained private verifier and publish the canonical Mission proof.
4. Confirm proof SHA-256 `69afd990e5d7d9bdf7fde4a1f7fe97183c909855371445e49eebe50dadbab681`,
   mode `0644`, single link, and both pending paths absent.
5. Run the current Mission validator on the unmerged topic and observe DENY.
6. In a clean detached protocol-base clone, run the four exact activation
   topology and SDG-record controls; observe `4 passed in 8.25s`.
7. Require protected review, Local Green, hosted required CI, exact merge, and
   post-merge ACTIVE readback before any T-task start.

## Environment and preconditions

macOS; CPython 3; SDG `0.2.0-experimental.6`; branch
`agent/mission-v5-activation-post-sdg008`; sequence-6 ledger with T-001 through
T-003 COMPLETED and T-004 through T-033 PENDING. No private packet or secret is
stored in Git.
