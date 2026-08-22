# VAM-001: Record Subject Distillation extraction decision

## Evidence ID

`DEP-VAM-001-SUBJECT-EXTRACTION-ADR`

## Expected

Vault documentation records the owner-approved decision that Subject
Distillation runtime work moves to the separate Digital Life Identity product,
while Vault preserves T-001 through T-004 as immutable origin history and does
not continue T-005 through T-033.

## Actual

The repository preserves the completed Subject contracts and frozen
specification, but `docs/subject-distillation.md` still presents Issue #410 as
the current owner and no extraction ADR records the new product boundary or the
disposition of Issues #410, #495, #496, and #497.

## Reproduction

Run:

```bash
python -m pytest -q tests/test_subject_extraction_boundary_docs.py
```

Before the change, collection fails because
`docs/decision_records/2026-08-21-extract-subject-distillation.md` does not
exist.

## SDD reference

`docs/specs/vam-001-subject-distillation-extraction.md`

## Risk

L1. This is a reversible documentation and governance-record change under an
owner-approved L2 architecture decision. It changes no runtime behavior,
database, API, or external system.

## Non-scope

- Memory Change Envelope or any VAM-002 implementation
- Mission V6, T-005 through T-033 implementation, or progress-ledger mutation
- Changes to frozen Subject Distillation specifications or T-001 through T-004 evidence
- Digital Life Identity repository creation
- GitHub Issue, PR, release, merge, or deployment mutation

## Verification plan

- Run the executable boundary-document test.
- Verify frozen canonical artifacts and the progress ledger have no diff from
  `origin/main`.
- Run README command smoke, release parity, `git diff --check`, and the relevant
  Subject contract/progress tests.
- Complete and strictly verify the local redacted DEP.
