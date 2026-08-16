# Verification

## Builder verification

- Exact clean base and isolated branch confirmed.
- Proof canonicality, mode, size, SHA-256, and external byte equality confirmed.
- Public-safe owner binding confirmed by proposal ID, receipt SHA-256, and
  confirmation reference; no private transcript is retained.
- Existing activation validator and genuine regression coverage inspected;
  no source or test mutation is justified.
- Corrected isolated-base focused activation selection: 4 passed in 11.37
  seconds, exact exit 0.
- Builder full Local Green: `NOT_RUN_PHASE_GATED`; running it on the incomplete
  real topic would violate the candidate phase contract, so it is assigned to
  the independent review phase after a reviewer-only pre-sign simulation.

## Required final proof

- Closed 16-path action/mode and protected-file audit.
- Candidate preliminary replay with inactive dispatcher state.
- Independent reviewer pre-sign Local Green using the governed synthetic
  placeholder, followed by real candidate verification after fresh signature.
- Strict DEP/redaction verification and exact change digest.
- Independent reviewer receipt with zero P0/P1 findings.
- Hosted CI, normal two-parent merge, tree equality, and active readback.

No independent review, hosted result, merge, task start, or production outcome
is claimed by Builder evidence.
