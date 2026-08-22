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

## Expected

TODO

## Actual

TODO

## Deterministic steps

TODO

## Environment and preconditions

TODO
