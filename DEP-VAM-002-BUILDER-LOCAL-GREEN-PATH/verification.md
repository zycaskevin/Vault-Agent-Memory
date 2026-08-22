# Verification

Current phase: Proof.

Verified read-only facts:

- exact head `983c48036a585eaecced5a56b7dcbb98dacb67ed` remained clean;
- all 1,407 tracked physical modes matched the Git index;
- Doctor and CI-contract validation passed under the merged governance CLI;
- the governance Python cannot import pytest;
- the Vault test Python imports pytest `9.1.1`;
- the failed run emitted no named Subject node or repository pytest result;
- no push, receipt, trust mutation, merge, deployment, or live-data change
  occurred.

The corrected ordering passed collection and all 446 identity-isolated nodes.
After the separately governed compatibility repair, exact head
`1a346913563f5437b7815f655393f0eee5a0da52` completed the repository suite
with 2967 passed, 10 skipped, and one existing warning; the gate exited zero.

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
