# Regression Evidence

## Regression test added or strengthened

`test_vam002_final_review_records_keep_red_and_green_semantics_distinct`
binds the defect categories, expected-RED rollback language, separate Green
acceptance commands, and full snapshot evidence wording. The existing normative
revision-material test now normalizes both the specification and decision text
before every field or phrase assertion.

## Related tests executed

The original four-condition static probe changed from four failures to four
passes. The complete VAM-002 focused selection then passed 24 tests, including
the executable rollback contract and new semantic evidence regression. Ruff on
both changed Python tests, `git diff --check`, governance Doctor, and CI contract
verification all passed.

## Unaffected paths sampled

No production Python module changed. The focused selection sampled the complete
memory-change envelope and provider suites plus invalid sensitivity, opaque
identifier, candidate-first metadata, HTTP error, rollback, and boundary-freeze
contracts. Exact committed-head Local Green remains the proof-stage gate.

That proof-stage gate is now complete at exact implementation commit
`c004c04cd1c1ed471ba39d6d4ad0f5e565dfea5a`: 446 identity-isolated Subject
nodes passed, followed by 2,970 repository tests passing with 10 skips and one
pre-existing deprecation warning.
