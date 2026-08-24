# Root Cause Hypothesis

## Hypothesis

VAM-002 accumulated several successor evidence packages after the original
implementation, but no final regression bound historical source claims,
later exact-head proof, portable commands, and rollback authority in one
cross-package oracle. Separately, the later non-empty `agent_id` provider
requirement was not added to the Gateway HTTP client-error allowlist.

## Supporting evidence

- The RED contract test enumerates all 12 record gaps from current repository
  bytes rather than relying on the third-party review text alone.
- `gateway_memory_changes` and revision-bound `gateway_memory_get` already
  return `agent_id_required`, but `_MEMORY_API_BAD_REQUEST_ERRORS` omits it, so
  the same bounded error payload is sent with HTTP 200.
- The authoritative rollback originally accepted any second-parent ancestor
  without proving that the descendant bytes were limited to the merge gate and
  the exact VAM-002 receipt. CodeRabbit's literal exact-parent proposal would
  instead reject the governance contract's legitimate gate-only and
  receipt-only descendants, so the repair binds ancestry plus an audit-only
  path allowlist.
- Multiple historical proof documents name different commits and counts
  without explicitly separating failed preflight, intermediate Green, and the
  manifest-bound final proof.

## Contradicting evidence

- The final-remediation rollback already targets remediation commit
  `c004c04...`, not the original VAM-002 product implementation. That finding
  is a wording/scope ambiguity, not a destructive product rollback defect;
  the repair makes this explicit and keeps implementation rollback separate.
- Historical raw and shareable transcripts are timestamped evidence. They
  must not be rewritten to claim commands or runs that did not occur. When a
  derivative needs clarification, retain the original source hash and record
  the transformation, or add a new successor proof artifact.

## Falsification test

The hypothesis is false if the same two targeted RED tests do not become
Green after only the bounded HTTP-map, contract-test, documentation, DEP,
rollback, and evidence-provenance changes, or if any change to memory storage,
cursor semantics, content filtering, identity modeling, or live data is
required.

## Conclusion

Confirmed with one bounded disposition. The runtime defect is one missing
client-error enum member. The exact-parent suggestion is non-actionable as
written because governed audit descendants are required; its underlying
fail-closed concern is closed by ancestry plus an exact audit-only path guard.
The remaining findings are reproducibility, provenance, scope, or rollback
corrections within the approved VAM-002 contract.
