# Fix Scope

## Smallest sufficient change

Add a Mission V5-only lifecycle audit wrapper. For ancestor directories it
binds device, inode, type, and mode through retained no-follow descriptors. For
the owned private directory and both private files it retains exact pathname
and descriptor identity, bytes, mode, link count, member closure, and cleanup.

Bind the post-SDG-004 compatibility delivery to one exact two-parent merge,
closed paths/actions/modes, and a linear topic without hidden add/delete.

## Files or components in scope

- `scripts/run_subject_development_mission_v5.py`.
- `tests/test_subject_development_mission_v5.py`.
- SDG-006 Work Package, strict DEP, gate records, and reviewer receipt.

## Explicit non-scope

- No edits to frozen v1-v4, canonical five, T-001 through T-003, sequence-6
  ledger, verifier/schema, task descriptors, or product semantics.
- No Mission activation or T-004 start.
- No private/live data, production, deployment, release, Billing, credential,
  provider-console, destructive, or L2/L3 action.

## Blast radius

Mission V5 proposal verification and its exact release checker only. Existing
v1 callers retain their frozen behavior. Security-relevant file replacement
and path substitution remain DENY.
