# Verification

Current phase: Green for Builder runtime composition; full repository Proof is
not claimed.

Verified read-only facts:

- exact head `983c48036a585eaecced5a56b7dcbb98dacb67ed` remained clean;
- all 1,407 tracked physical modes matched the Git index;
- Doctor and CI-contract validation passed under the merged governance CLI;
- the governance Python cannot import pytest;
- the Vault test Python imports pytest `9.1.1`;
- the failed run emitted no named Subject node or repository pytest result;
- no push, receipt, trust mutation, merge, deployment, or live-data change
  occurred.

The corrected ordering passed collection and all 446 identity-isolated nodes,
then executed the repository suite. That suite exposed two independent
compatibility findings governed by `DEP-VAM-002-FULL-SUITE-COMPATIBILITY`.

## Green command and result

The unchanged `sddgov ci local-gate .` used Vault Python/pytest `9.1.1` and
merged governance `0.2.0-experimental.9`. The former PATH failure did not
recur; 446 identity nodes passed and repository pytest ran.

## Before/after evidence

Before: collection failed before any node because selected Python lacked
pytest. After: identity nodes completed and repository pytest returned its own
bounded result. Both artifacts are hash-bound in the manifest.

## Remaining limitations

Overall Local Green remains red until the separate compatibility DEP is fixed
and a new exact committed candidate passes the complete gate.
