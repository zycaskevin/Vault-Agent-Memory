# Regression Evidence

## Required checks

- Proof remains canonical, mode `0644`, and byte-identical to verifier output.
- Exact activation topic is preliminary and dispatcher grants zero authority.
- Proof-only, incomplete, extra-path, wrong-action/mode, wrong parent/order,
  side-merge, tree drift, gate drift, and receipt drift deny.
- Exact closed reviewed two-parent delivery activates only after merge.
- Static checks, focused regressions, strict DEP, Local Green, independent
  review, hosted CI, and exact merge readback pass.

## Current result

- Canonical proof publication succeeded inside the proposal window and stdout
  compares byte-for-byte with the repository proof.
- Proof SHA-256 is `f1c38461dd4639c50f82bd9ddc39029d8a8a02f63fbbedc6cce2df9461ec2465`.
- Four exact activation topology nodes passed in 11.70 seconds with exit 0.
- Full Local Green remains phase-gated until the review topology supplies the
  gate and independent receipt required by candidate validation.

## Bootstrap limitation

The first wrapper used a system Python installation without pytest and exited
before collection. It is retained as bootstrap telemetry, not test evidence.
The corrected capture used the pinned experimental.6 runtime and passed once.

## Unverified boundary

Candidate topology, Local Green, independent review, hosted CI, merge, and
active post-merge readback remain unclaimed until their exact phases complete.
