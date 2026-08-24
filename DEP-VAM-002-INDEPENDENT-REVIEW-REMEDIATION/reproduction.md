# Reproduction

## Expected

Invalid sensitivity labels fail closed without rows or content; invalid cursor
inputs receive a documented non-success HTTP response; revision documentation
matches canonical row-snapshot behavior; the SQL trace test proves an audit
query ran; and rollback preparation is executable and fail closed.

## Actual

An invalid non-empty sensitivity label becomes an empty ceiling and exposes
otherwise capped rows. Memory GET errors are sent as HTTP 200. Public revision
wording includes advisory `audit_ref` even though it is intentionally outside
the row revision. One audit-query assertion is vacuous, and rollback contains
only prose.

## Deterministic steps

At exact reviewed head `67e38bbce4f978a23453117a91d6b53bf1180948`, apply the
Minimal RED patch: add provider assertions that invalid non-empty sensitivity
returns no row/content, add the audit-only revision wording assertion, and add
the Gateway HTTP error/status/OpenAPI assertion. The exact nodes are:

```text
tests/test_memory_change_envelope.py::test_invalid_max_sensitivity_fails_closed_for_changes_and_revision_reads
tests/test_memory_change_envelope.py::test_audit_reference_is_advisory_and_not_part_of_the_row_revision_contract
tests/test_gateway.py::test_memory_change_http_errors_use_non_success_status_and_openapi_contract
```

With `VAULT_TEST_PYTHON` bound to the repository-pinned interpreter, run the
exact command:

```bash
env PYTHONPATH=. "$VAULT_TEST_PYTHON" -m pytest -q \
  tests/test_memory_change_envelope.py::test_invalid_max_sensitivity_fails_closed_for_changes_and_revision_reads \
  tests/test_memory_change_envelope.py::test_audit_reference_is_advisory_and_not_part_of_the_row_revision_contract \
  tests/test_gateway.py::test_memory_change_http_errors_use_non_success_status_and_openapi_contract
```

The full command is the focused three-node RED selection, not a complete
repository Local Green. It returned `3 failed`: an OK invalid-sensitivity page,
missing revision-contract wording, and a missing Gateway error/status mapper.
The redacted proof is
`shareable/artifacts/terminal--independent-review-red.txt`.

## Environment and preconditions

CPython 3.11, VAM-002 branch exact audit head, local SQLite fixture, no network,
and no private/live memory data.
