# Verification

Current phase: Proof.

Historical preflight at exact head
`983c48036a585eaecced5a56b7dcbb98dacb67ed` remained clean and established
the interpreter-selection failure: the governance Python could not import
pytest, the Vault test Python imported pytest `9.1.1`, and the failed run
emitted no named Subject node or repository pytest result. That preflight is
not the final proof candidate.

Authoritative final proof candidate
`1a346913563f5437b7815f655393f0eee5a0da52` is the single manifest-bound
success record: 1429 tracked physical modes matched the Git index, Doctor and
CI contract passed, all 446 identity-isolated nodes passed, and repository
pytest completed with 2967 passed, 10 skipped, and one existing warning. The
gate exited zero and no push, receipt, trust mutation, merge, deployment, or
live-data change occurred.

## Green command and result

The unchanged `sddgov ci local-gate .` used Vault Python/pytest `9.1.1` and
merged governance `0.2.0-experimental.9`. The former PATH failure did not
recur; 446 identity nodes passed and repository pytest ran.

## Before/after evidence

Before: collection failed before any node because selected Python lacked
pytest. After: identity nodes completed and repository pytest returned its own
bounded result. Both artifacts are hash-bound in the manifest.

## Remaining limitations

Proof is bound to the exact committed candidate. Any later implementation or
evidence mutation requires rebinding and a new exact-head gate under the CI
cost contract.
