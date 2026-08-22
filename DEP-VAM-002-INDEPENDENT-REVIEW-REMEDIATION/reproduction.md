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

At exact reviewed head `67e38bbce4f978a23453117a91d6b53bf1180948`, add the
three independent-review regression nodes in `tests/test_memory_change_envelope.py`
and `tests/test_gateway.py`, then run them together. The result is `3 failed`:
an OK invalid-sensitivity page, missing revision-contract wording, and a missing
Gateway error/status mapper. The redacted proof is
`shareable/artifacts/terminal--independent-review-red.txt`.

## Environment and preconditions

CPython 3.11, VAM-002 branch exact audit head, local SQLite fixture, no network,
and no private/live memory data.
