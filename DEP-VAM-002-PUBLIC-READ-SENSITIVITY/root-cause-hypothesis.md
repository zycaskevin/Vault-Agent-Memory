# Root Cause Hypothesis

## Hypothesis

The provider policy is inactive when `agent_id` is empty; the Memory API
validates sensitivity too late; active row policy assigns unknown sensitivity
rank zero and treats every unknown scope as non-private; and provider updates
validate status transitions without canonicalizing governance labels.

## Supporting evidence

The RED provider page returns private/high changes with omitted identity. The
RED default legacy Memory API read returns `status=ok` and synthetic
`SECRET-HIGH` content when the ceiling is `typo`.
Follow-up RED evidence shows a malformed stored sensitivity in a low-ceiling
change page and a mixed-case tombstone status persisted verbatim. Independent
Reviewer probes confirmed the companion unknown-scope content path.

## Contradicting evidence

Gateway HTTP requires an agent for changes/revision reads, and the earlier
provider-bound strict sensitivity helper correctly rejects invalid labels once
it is reached. Those protections do not cover no-revision adapter dispatch or
direct provider calls without identity.

## Falsification test

Validate agent identity before constructing all four VAM-002 provider policies,
validate sensitivity before get/search/timeline adapter selection, reject
unknown governance updates, canonicalize accepted labels, and deny malformed
stored labels whenever policy is active. All RED nodes must become Green
without changing legacy `/search` or `/read-range`.

## Conclusion

Confirmed. Authorization inputs and stored governance labels were either
validated too late, not validated, or assigned permissive fallbacks.
