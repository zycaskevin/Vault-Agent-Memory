# Fix Scope

## Smallest sufficient change

Add exact local `main` and `HEAD == merge_oid` preconditions before approval is
consumed, document the condition, and strengthen the VAM-001 rollback test.

## Files or components in scope

`DEP-VAM-001-DELIVERY-GATE/rollback.md`, the VAM-001 extraction boundary test,
this DEP, and the audit-only merge gate.

## Explicit non-scope

No runtime, Subject artifact, API, database, Issue state, deployment, ADR
decision, compatibility wording, or rollback execution.

## Blast radius

One future rollback command and one documentation contract test. No production
path changes.
