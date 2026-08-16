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
- The corrected isolated-base focused capture passed all four exact activation
  topology nodes in 11.37 seconds with exit 0.
- Builder full Local Green is `NOT_RUN_PHASE_GATED`: the real Builder topic
  intentionally lacks both its final gate update and independent reviewer
  receipt, so candidate replay must deny until the review phase.

## Capture limitation

The first focused wrapper created the correct isolated base clone but omitted
changing its process working directory. Pytest therefore ran against the real
14-path Builder topic and produced four expected setup denials before any test
body. This is retained as operator/bootstrap telemetry, is not product RED, and
is not used as exit proof. Root authorized one corrected capture with exact
workdir; that capture is the focused evidence above.

## Unverified boundary

Independent pre-sign Local Green, fresh receipt, real candidate verification,
hosted CI, merge, and active post-merge readback remain unclaimed until the
reviewer phase.
