# Fix Scope

## Smallest sufficient change

Remove one redundant separator blank line adjacent to the new import. Keep the
centralized directory contract and all functional behavior unchanged.

## Files or components in scope

- `vault/agent_setup.py`
- focused module-size and VAM-003 boundary checks
- this DEP

## Explicit non-scope

No baseline increase, module-size policy change, API change, directory contract
change, broad refactor, or CI configuration change.

## Blast radius

Formatting-only source change plus evidence records. Runtime behavior is
unchanged.
