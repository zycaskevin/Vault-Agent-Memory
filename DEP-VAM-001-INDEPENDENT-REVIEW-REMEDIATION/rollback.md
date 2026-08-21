# Rollback

## Trigger

The section extractor misparses a valid Issue heading, the strengthened tests
reject the approved document, or the rollback contract becomes less bounded.

## Reversible steps

The only provenance anchors eligible for semantic rollback are remediation
commit `d792cf21b6959a5a3990ba2fc2e5a04034481d00` and its audit-only gate revision
`92bd0d28f36b9da401c57d08cd7ebd57d972c36e`. Before any rollback execution,
create a new rollback DEP through Red -> Evidence -> Fix -> Green -> Proof,
strictly verify it, and consume a fresh, exact, unexpired owner-signed L3
approval.

Because successor remediation and gate commits now depend on those anchors, do
not directly revert either commit. Prepare a bounded compensating change against
their exact diff, preserve all DEP/provenance files, and rebuild current
merge-gate metadata in a separate audit-only commit. No broader commit, whole-PR
revert, extraction ADR, frozen Subject artifact, completed Issue disposition,
or existing governance history is an allowed target.

## Data compatibility

No runtime, schema, or stored-data change exists.

## Post-rollback verification

Retain redacted outputs in the new rollback DEP and prove: its complete phase
sequence and strict verification; the restored change and gate digests; an empty
diff from the approved base for frozen `specs/subject-distillation`,
`vault/subject_contracts.py`, and `tests/test_subject_contracts.py`; `git diff
--check`; focused VAM-001 tests; every current strict VAM-001 DEP; complete Local
Green; hosted CI; and a fresh independent Reviewer receipt. The PR or follow-up
rollback PR remains blocked until all results pass.
