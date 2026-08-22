# Fix Scope

## Smallest sufficient change

Make H2 extraction fence-aware; add the two missing integration assertions;
capture autonomy output only after evaluator success; assert the revert changes
only the compatibility document; and bind remediation rollback provenance.

## Files or components in scope

VAM-001 extraction documentation test, delivery rollback, independent-review
remediation rollback, this DEP, and audit-only merge gate.

## Explicit non-scope

No Vault runtime, database, API, frozen Subject artifact, Issue mutation,
compatibility text, deployment, release, or concrete rollback execution.

## Blast radius

Documentation/test governance only. Production behavior and stored data are
unchanged.
