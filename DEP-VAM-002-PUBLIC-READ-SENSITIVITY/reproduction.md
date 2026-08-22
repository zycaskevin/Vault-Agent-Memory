# Reproduction

## Expected

Unknown non-empty sensitivity labels return `max_sensitivity_invalid` before
any Memory API adapter runs. The four VAM-002 provider reads require a
non-empty `agent_id`; list/evidence return `agent_id_required`, while
metadata/revision return no row.
Unknown stored scope or sensitivity labels fail closed under every active read
policy, valid governance updates are stored canonically, and `Deleted` is
emitted as a delete tombstone.

## Actual

Both no-revision Memory API adapters returned bounded high-sensitivity content
for `max_sensitivity=typo`. Direct provider reads with an omitted agent returned
a private/high row, metadata, revision, and content.
An unknown stored sensitivity was treated as low, an unknown stored scope was
treated as readable shared data, and a mixed-case accepted lifecycle status was
stored verbatim and emitted as an upsert.

## Deterministic steps

Run `/tmp/vam-python-path-vam001/python -m pytest -q
tests/test_gateway.py::test_memory_api_all_read_facades_reject_invalid_sensitivity_before_dispatch
tests/test_memory_change_envelope.py::test_provider_authorized_reads_require_nonempty_agent_identity`.

The follow-up RED command and bounded results are retained in
`shareable/artifacts/terminal--stored-labels-and-tombstone-red.txt`. The
independent Reviewer separately reproduced the unknown-scope path through
`update_memory(scope="private-ish")` before the defensive test was added.
After capture, the stored-label RED node was expanded and renamed to
`test_invalid_governance_updates_and_malformed_rows_fail_closed`; the final
Green artifact records the current executable node set.

## Environment and preconditions

The initial public-facade and missing-agent RED was captured at exact branch
head `d2bed8a66895691e6765498490902b123129724a` with synthetic shared-high and
private-high rows. The stored-label/tombstone RED was captured later at exact
committed head `b7326b344ef4bbf42e64691859fa6aaf396fb9f3` plus uncommitted
test-only RED changes, using malformed governance rows. Both used CPython 3.11.
