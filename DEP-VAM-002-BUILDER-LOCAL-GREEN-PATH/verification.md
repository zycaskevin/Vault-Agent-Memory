# Verification

Current phase: Proof.

Historical preflight at exact head
`983c48036a585eaecced5a56b7dcbb98dacb67ed` remained clean and established
the interpreter-selection failure: the governance Python could not import
pytest, the Vault test Python imported pytest `9.1.1`, and the failed run
emitted no named Subject node or repository pytest result. That preflight is
not the final proof candidate.

The intermediate command-provider Green at
`7a64938bdc1e5aa483db013e4de4c8e78952fa20` closed only the PATH/interpreter
defect: all 446 identity nodes passed and repository pytest started, then two
separately governed compatibility tests failed. The artifact name
`terminal--local-green-path-green.txt` refers to the PATH subproblem, not to an
overall Local Green PASS.

Authoritative final proof candidate
`1a346913563f5437b7815f655393f0eee5a0da52` is the single manifest-bound
success record: 1429 tracked physical modes matched the Git index, Doctor and
CI contract passed, all 446 identity-isolated nodes passed, and repository
pytest completed with 2967 passed, 10 skipped, and one existing warning. The
gate exited zero and no push, receipt, trust mutation, merge, deployment, or
live-data change occurred.

These are three ordered, non-conflicting candidates: `983c4803` is the
interpreter-selection RED, `7a64938b` is PATH Green but overall product RED,
and `1a346913` is the manifest-bound overall proof after the compatibility fix.

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
