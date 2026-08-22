# Fix Scope

## Smallest sufficient change

Replace the two invalid `$schema` selectors with the canonical root-level path
and add one exhaustive test that resolves every VAM-001 root DEP selector,
requires exact Governance Root equality, and requires the schema file to exist.

## Files or components in scope

- `DEP-VAM-001-REVIEWER-TMP-ANCESTOR-RACE/summary.yaml`
- `DEP-VAM-001-PRIVATE-CHECKOUT-REMOTE-REF/summary.yaml`
- `tests/test_subject_extraction_boundary_docs.py`
- This DEP and the VAM-001 merge-gate binding

## Explicit non-scope

- No change to DEP semantic evidence, artifacts, workflow history, product
  source, frozen Subject/Memory Layer, API, schema content, or acceptance
  criteria
- No modification to the external `sddgov` package in this Vault PR
- No Reviewer Local Green or signature until a new exact final head exists

## Blast radius

Repository governance evidence and its focused test only. Runtime behavior and
shipped product artifacts are unchanged.
