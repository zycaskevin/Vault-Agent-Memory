# Regression Evidence

## Red

The first complete gate stopped before node execution. The governance Python
raised `ModuleNotFoundError: No module named 'pytest'`; the Vault test Python
reported pytest `9.1.1`.

## Required Green

Before a second full gate, assert both command providers independently:

```text
PATH=$VAULT_PYTHON_SHIM:$SDDGOV_RUNTIME/bin:... python -c 'import pytest'
PATH=$VAULT_PYTHON_SHIM:$SDDGOV_RUNTIME/bin:... sddgov --version
```

Then run the unchanged repository `sddgov ci local-gate .` exactly once. Green
requires identity-isolated nodes and repository-wide pytest to complete, a
clean worktree, unchanged exact head, and no retry.

## Regression test added or strengthened

No repository test was needed because the defect was outside repository bytes.
The executable-provider preflight is the regression guard.

## Related tests executed

Doctor, CI contract, README smoke, release parity, and all 446 identity-isolated
Subject nodes passed. Repository pytest started and reported its own two
separately governed findings.

## Unaffected paths sampled

The exact head stayed clean, tracked physical modes remained index-consistent,
and the frozen Subject contract was unchanged.
