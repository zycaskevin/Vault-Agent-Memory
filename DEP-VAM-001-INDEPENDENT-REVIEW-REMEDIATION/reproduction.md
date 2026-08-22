# Reproduction

## Expected

`tests/test_subject_extraction_boundary_docs.py` binds each disposition to the
matching `## Issue #...` section. The merge-gate rollback has one target and
preserves the extraction ADR, frozen Subject artifacts, and evidence history.

## Actual

The assertions searched the entire draft, so a phrase moved under the wrong
Issue heading still passed. The rollback command reverted PR #498 as a whole,
while its prose allowed only the compatibility sentence and prohibited removal
of the extraction ADR.

## Deterministic steps

Review `test_issue_disposition_record_is_bounded_and_exact` at reviewed head
`f46325de069be3fc9c18983bb49f0664be1a32b2`: headings and states are asserted
independently against the full text. Compare the first command in
`DEP-VAM-001-DELIVERY-GATE/rollback.md` with its `Reversible steps` section.
The independent review record is linked in the red artifact.

## Environment

Exact PR base `291d5595c9cb2208a6b74206acbba35a883eb918`; exact reviewed head
`f46325de069be3fc9c18983bb49f0664be1a32b2`; no review receipt was issued.
