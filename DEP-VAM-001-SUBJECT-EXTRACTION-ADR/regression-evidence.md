# Regression Evidence

## Regression test added or strengthened

`tests/test_subject_extraction_boundary_docs.py` adds three deterministic
checks for the complete ADR contract, preserved historical task states, and
bounded issue-comment drafts. It uses no network, database, or private fixture.

## Related tests executed

- Focused documentation, Subject contract, and positioning suite: 67 passed.
- Subject progress validator: PASS at baseline `0dc10cfc4a429662`, sequence 8.
- README command smoke: passed.
- Release parity: passed at version 0.10.2.
- Ruff for the new test: passed.
- `git diff --check`: passed.
- Governance doctor and CI contract verification: passed.

## Unaffected paths sampled

The frozen five-file Subject baseline, progress ledger, authorization/evidence
trees, `vault/subject_contracts.py`, and `tests/test_subject_contracts.py` have
no diff from `origin/main`. No runtime, API, database, CLI, MCP, Gateway, CI,
or package file is changed by VAM-001.
