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

1. Start from clean merged main `6d499e41ac41b8cd0f560146b0f18939b55a5f3f`.
2. Reconstruct proposal
   `6c10560ab4addc7c185a2247895cd409a447afb5200b318b08752632d0bccd56`
   and verify the exact owner-confirmed receipt digest.
3. Run the retained private verifier and publish the canonical Mission proof.
4. Confirm proof SHA-256 `81762961548312e69823a097911000ac4b15756a7e403f022dd3fec789f8ff97`,
   mode `0644`, single link, and both pending paths absent.
5. Run the current Mission validator on the unmerged topic and observe DENY.
6. In a clean detached protocol-base clone, run the four exact activation
   topology and SDG-record controls; observe `4 passed in 5.82s`.
7. Require protected review, Local Green, hosted required CI, exact merge, and
   post-merge ACTIVE readback before any T-task start.

## Environment and preconditions

macOS; CPython 3; SDG `0.2.0-experimental.6`; branch
`agent/mission-v5-activation-post-sdg007`; sequence-6 ledger with T-001 through
T-003 COMPLETED and T-004 through T-033 PENDING. No private packet or secret is
stored in Git.
