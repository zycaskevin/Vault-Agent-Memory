# Fix Scope

## Smallest sufficient change

Correct the rollback success criteria, make both remediation evidence records
match the implemented defects and snapshot oracle, and use normalized Markdown
strings consistently in the existing normative contract test.

## Files or components in scope

- `DEP-VAM-002-CODERABBIT-CURRENT-HEAD-REMEDIATION/fix-scope.md`
- `DEP-VAM-002-CODERABBIT-CURRENT-HEAD-REMEDIATION/rollback.md`
- `DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md`
- `DEP-VAM-002-FULL-SUITE-COMPATIBILITY/regression-evidence.md`
- `tests/test_memory_change_envelope.py`
- `tests/test_vault_boundary_freeze.py`
- this bounded DEP and the audit-only merge-gate rebind

## Explicit non-scope

No production module, API schema, cursor, authorization policy, write path,
database, migration, package dependency, release, deployment, Reviewer trust,
receipt, merge, or live Hermes operation.

## Blast radius

Test-and-evidence only. Runtime Memory API behavior and persisted data are
byte-for-byte unchanged. The authoritative rollback gains the new DEP
preservation path and the already-in-scope boundary-test path; rollback of this
remediation removes only the semantic proof/test corrections while retaining
all prior VAM-002 implementation and evidence.
