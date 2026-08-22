# Root Cause Hypothesis

Confirmed: placing the Agentic SDD Governance virtual environment first on
`PATH` unintentionally selected its dependency-minimal `python` for every
repository-controlled command. The identity runner uses that interpreter for
collection; because it has no pytest module, collection exits before node
execution and the runner intentionally reports only its generic fail-closed
message.

Falsifier: with the Vault test-python shim first on `PATH` and the governance
runtime second, `python -c 'import pytest'` must resolve pytest `9.1.1`,
`sddgov --version` must resolve `0.2.0-experimental.9`, and the complete Local
Green must advance beyond identity collection. If it fails at the same stage,
this hypothesis is incomplete and no Green may be claimed.

## Supporting evidence

The first run selected a Python without pytest and stopped during collection.
The corrected run selected pytest `9.1.1`, passed all 446 identity nodes, and
entered repository-wide pytest.

## Contradicting evidence

The corrected run later found two separately governed compatibility failures.
Those failures occurred after collection and do not contradict the PATH cause.

## Falsification test

Resolve both executable providers, import pytest, and require the identity
runner to proceed through node execution into the repository suite.

## Conclusion

Confirmed and Green for command composition. Overall repository Green remains
separately blocked by `DEP-VAM-002-FULL-SUITE-COMPATIBILITY`.
