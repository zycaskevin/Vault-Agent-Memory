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

## Hypothesis

TODO

## Supporting evidence

TODO

## Contradicting evidence

TODO

## Falsification test

TODO

## Conclusion

TODO
