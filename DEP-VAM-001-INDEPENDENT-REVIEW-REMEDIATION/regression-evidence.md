# Regression Evidence

## Required checks

- Focused VAM-001 extraction-boundary tests.
- Subject baseline and contract tests, the exact production progress validator
  against the canonical manifest/schema/tasks/ledger, and the complete
  446-node identity-isolation suite for current progress/authorization nodes.
- Both prior VAM-001 DEPs plus this DEP under strict verification.
- Full repository Local Green and hosted CI on the exact remediation head.

## Unaffected paths

Frozen Subject specification, runtime modules, database schema, APIs, and
external GitHub Issue state remain unchanged.

## Regression test added or strengthened

`tests/test_subject_extraction_boundary_docs.py` now extracts each required H2
section and proves that every Issue outcome appears only in its matching
section. It also binds the #410 future-draft condition and the ADR ownership and
forbidden-boundary statements to their respective sections.

## Related tests executed

The focused remediation suite passed 56 tests. The canonical Subject progress
validator returned the expected baseline, sequence 8, and PASS. The repository
Local Green then passed all 446 identity-isolated Subject nodes and 2,926 tests
with 10 skips.

## Unaffected paths sampled

The frozen `specs/subject-distillation` tree, `vault/subject_contracts.py`, and
`tests/test_subject_contracts.py` were compared against the PR base and remain
unchanged. Runtime and database paths are outside the remediation diff.
