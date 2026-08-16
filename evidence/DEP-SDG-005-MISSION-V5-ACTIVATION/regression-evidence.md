# Regression Evidence

## Required checks

- External and repository proof bytes compare equal and retain exact SHA-256.
- Exact activation topic is preliminary and dispatcher remains inactive.
- Proof-only, incomplete, extra-path, wrong-action/mode, wrong parent/order,
  side-merge, merge-tree drift, gate drift, and receipt drift deny.
- Exact closed reviewed two-parent delivery activates only after merge.
- Static checks, focused activation regressions, strict DEP, full Local Green,
  independent review, hosted CI, and exact merge readback pass.

## Executed results

- External proof is canonical JSON, 3409 bytes, mode `0644`, and exact SHA-256
  `70113552d582f5f579a0c9d01a5206ff74df678801accca59173ff76bae6d528`.
- Repository copy compares byte-for-byte equal to the external proof.
- Static source inspection found no runner or test gap; the existing suite
  already exercises the required positive and negative activation topology.

## Unverified boundary

Focused execution, Builder Local Green, independent receipt, hosted CI, merge,
and active post-merge readback remain unclaimed until performed.
