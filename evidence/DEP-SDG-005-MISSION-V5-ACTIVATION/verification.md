# Verification

## Builder verification

- Exact clean protocol base and canonical origin confirmed before publication.
- Proof canonicality, mode, size, SHA-256, and verifier stdout equality pass.
- Public-safe owner binding uses proposal ID, receipt SHA-256, and confirmation
  reference; no private transcript is retained.
- Existing activation validator and genuine regression coverage remain
  byte-identical.
- Focused activation selection: four exact topology nodes passed in 11.70
  seconds with exit 0 under the pinned experimental.6 runtime.
- The initial system-Python wrapper lacked pytest and exited before collection;
  it is retained as bootstrap telemetry and is not Green evidence.
- Builder full Local Green: NOT_RUN_PHASE_GATED until the exact review topology
  supplies the gate update and independent receipt required by candidate mode.

## Required final proof

- Closed 16-path action/mode and protected-file audit.
- Candidate preliminary replay with zero authority.
- Independent reviewer pre-sign Local Green using governed synthetic topology,
  then real candidate verification after fresh signature.
- Strict DEP/redaction verification and exact change digest.
- Independent reviewer receipt with zero P0/P1 findings.
- Hosted CI, normal two-parent merge, tree equality, and active readback.

No independent review, hosted result, merge, task start, or production outcome
is claimed by this fix-phase Builder evidence.
