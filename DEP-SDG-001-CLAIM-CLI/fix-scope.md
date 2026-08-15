# Fix Scope

## Smallest sufficient change

Use `--path .` so the initialized repository is the state root. Keep
`SDG-001` as the positional Work Package identifier.

## Files or components in scope

Only `.sddgov/work-claims.json` and the local DEP documenting the corrected
invocation.

## Explicit non-scope

No change to the `sddgov` package, repository product code, tests, CI, policy,
or Work Package content.

## Blast radius

One local governance claim record with a four-hour TTL.
