# Verification

## Green command and result

```text
env PYTHONPATH=. /tmp/vam-python-path-vam001/python -m pytest -q -p no:cacheprovider tests/test_subject_extraction_boundary_docs.py::test_vam001_root_dep_schema_references_resolve_exactly
```

Result: `1 passed in 0.01s`, exit 0.

## Before/after evidence

- Before: two committed summaries and the newly initialized root DEP resolved
  their schema selectors outside the Governance Root.
- After: every enumerated VAM-001 root DEP resolves exactly to the existing
  governed schema, and the focused check passes.

## Remaining limitations

The Vault repository regression test closes this PR's coverage gap. The
external `sddgov evidence init/verify` implementation still does not normalize
or validate repository-placement-specific `$schema` selectors; correcting that
tool is outside VAM-001 and should be handled in the governance repository.
