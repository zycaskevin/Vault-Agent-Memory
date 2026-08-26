# Reproduction

## Expected

At exact PR #500 repair head
`983c48036a585eaecced5a56b7dcbb98dacb67ed`, the complete repository Local
Green should run with the Vault test interpreter and the newly merged global
Local Green serialization lock.

## Actual

The authorized command put the isolated governance virtual environment first
on `PATH`. Doctor, CI-contract validation, README smoke, and release parity
passed. Identity-isolated Subject collection then returned exit `1` with only
the fail-closed message `identity-isolated subject tests failed`; the outer
gate returned exit `3`. No named Subject node and no repository-wide pytest
result were emitted.

Read-only diagnosis proved the governance environment's `python` cannot import
`pytest`, while the established Vault test interpreter resolves to the project
development environment and imports pytest `9.1.1`.

## Reproduction boundary

This is a Builder runtime-composition failure. It is not evidence that a Vault
product test failed. The failed non-sandbox run is not retried without a fresh
explicit authorization.

## Deterministic steps

The preflight resolves both providers from the same bounded PATH, then the
unchanged complete gate is invoked. `$VAULT_PYTHON_SHIM` is the private shim
directory containing the Vault test interpreter, and `$SDDGOV_RUNTIME` is the
private governance virtual environment root:

```text
PATH=$VAULT_PYTHON_SHIM:$SDDGOV_RUNTIME/bin:/usr/local/bin:/usr/bin:/bin \
  python -c 'import pytest; print(pytest.__version__)'
PATH=$VAULT_PYTHON_SHIM:$SDDGOV_RUNTIME/bin:/usr/local/bin:/usr/bin:/bin \
  sddgov --version
PATH=$VAULT_PYTHON_SHIM:$SDDGOV_RUNTIME/bin:/usr/local/bin:/usr/bin:/bin \
  sddgov ci local-gate .
```

## Environment and preconditions

- private clean checkout at exact committed candidate
- Vault test-python shim first; merged governance runtime second
- current-user home read/write and local loopback only under explicit approval
- no push, sign, trust, merge, deployment, or live-data permission
