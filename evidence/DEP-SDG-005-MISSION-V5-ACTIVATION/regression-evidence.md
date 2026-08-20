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

As of `2026-08-20T05:43:13Z`, this is the pre-review Builder evidence snapshot.
The final independent receipt is deliberately out of scope for this snapshot;
candidate topology, Local Green, independent review, hosted CI, merge, and
active post-merge readback were therefore unclaimed at that time.

## Hosted review follow-up

- Exact hosted run `32341186509` completed all 16 jobs successfully on receipt
  head `4e8fb09d9e6391e9e25c79e1bd0e86ce4967b581`.
- CodeRabbit then identified a valid rollback P1: the executable record did not
  require a clean canonical `main`, a fresh `origin/main` fetch, or exact
  `HEAD == origin/main == delivery` immediately before `git revert`.
- Delivery stopped before merge. The receipt and its hosted result are stale
  for the corrected source and are retained only as RED evidence; the corrected
  lineage requires a fresh gate digest, independent receipt, and hosted run.
- The v2 lineage then passed independent review and hosted run `32344829627`,
  but delivery again stopped before merge when review showed that event count
  plus maximum sequence did not prove the exact ledger sequence `1..6`.
- The final rollback assertion now requires the sorted event sequence to equal
  `list(range(1,7))` both before and after revert. The v2 receipt and hosted
  result are stale for this exact-sequence correction.
