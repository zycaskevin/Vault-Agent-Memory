# Promotion Contract

Promotion is strict by default. `confirm=true` confirms the requested action;
it does not accept quality or duplicate warnings.

## Outcomes

- `promoted`: privacy, metadata, quality, and duplicate gates pass.
- `review_required`: quality or duplicate warnings remain. Vault writes no raw
  file and creates no active knowledge row.
- `blocked`: privacy or required metadata fails.

Candidate creation recommends direct promotion only when every gate passes.
Otherwise it recommends review.

## Reviewed conflict selection

A reviewed multi-host conflict may select one remote candidate as canonical and
archive the previous active row. That runtime path may accept duplicate findings
only when every finding points to the exact active knowledge row selected by the
conflict. Quality must still pass.

The review result is created inside the conflict runtime after it validates a
conflict reference, actor reference, non-empty reason, and canonical knowledge
id. CLI, MCP, GUI request payloads cannot construct or forward this internal
review value. Supplying fields such as `reviewer`, `promotion_mode`, or
`canonical_knowledge_id` in a public request has no authority.

Only an `open` conflict may be resolved. A resolved conflict ID cannot be reused
to promote or archive memory again, even if a caller repeats the confirmation.

Vault stores memory and review provenance; it does not model human identity,
personality, or relationships. Authentication of the runtime actor remains an
integration responsibility outside the Memory Object domain.
