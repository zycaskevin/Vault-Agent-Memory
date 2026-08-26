# Regression Evidence

## Regression test added or strengthened

`test_vam002_current_head_coderabbit_findings_have_current_records` binds the
canonical list to the exact executable rollback and reproduction details.

## Related tests executed

Run the focused binding node, then Ruff on the changed test file and `git diff
--check`. A repository Local Green run is recorded only when it is actually
performed; historical full-suite counts are not relabeled as this run.

## Unaffected paths sampled

VAM-002 provider and Gateway source files are intentionally unchanged. The
existing focused VAM-002 tests remain the product-contract boundary.
