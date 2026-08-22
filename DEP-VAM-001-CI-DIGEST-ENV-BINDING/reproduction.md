# Reproduction

## Expected

Interactive and hosted-equivalent digest calculation must produce the gate's
declared value, or the environment difference must be explicitly pinned before
the audit binding is created.

## Actual

At `b2c8378`, default calculation produced `e155240b...`; the repository CI
contract environment produced `1ba66ab1...`, causing hosted governance failure.

## Deterministic steps

Run `sddgov merge digest . --base-ref 291d559...` first normally and then with
the CI contract's `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=core.abbrev`, and
`GIT_CONFIG_VALUE_0=40`; compare `change_digest`.

## Environment and preconditions

Exact PR base `291d5595c9cb2208a6b74206acbba35a883eb918`, exact head
`b2c8378db44079080d1d9bbd418febf93e527ec9`, governance version
`0.2.0-experimental.6`.
