# Fix Scope

## In scope

- Use the established Vault test-python shim before the new governance runtime
  on `PATH`.
- Assert the selected Python imports pytest and the selected `sddgov` is the
  merged serialization version before consuming another full gate.
- Rerun exactly one complete non-sandbox Local Green only after fresh owner
  authorization, then bind the exact committed result.

## Non-scope

- No Vault production code, tests, acceptance criteria, HOME, TMPDIR, identity
  policy, retries, live Hermes configuration, database, push, merge, signing,
  or trust change.

## Blast radius

The correction changes only Builder command resolution for the deployment
preflight. Repository bytes and runtime product behavior are unchanged.

## Smallest sufficient change

TODO

## Files or components in scope

TODO

## Explicit non-scope

TODO

## Blast radius

TODO
