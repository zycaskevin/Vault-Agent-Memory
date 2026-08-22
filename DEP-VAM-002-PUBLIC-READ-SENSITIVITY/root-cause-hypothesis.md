# Root Cause Hypothesis

## Hypothesis

The provider policy is inactive when `agent_id` is empty, and the Memory API
validates sensitivity only in revision/change provider branches rather than at
the common public facade entry.

## Supporting evidence

The RED provider page returns private/high changes with omitted identity. The
RED default legacy Memory API read returns `status=ok` and synthetic
`SECRET-HIGH` content when the ceiling is `typo`.

## Contradicting evidence

Gateway HTTP requires an agent for changes/revision reads, and the earlier
provider-bound strict sensitivity helper correctly rejects invalid labels once
it is reached. Those protections do not cover no-revision adapter dispatch or
direct provider calls without identity.

## Falsification test

Validate agent identity before constructing all four VAM-002 provider policies,
and validate sensitivity before get/search/timeline adapter selection. Both RED
nodes must become Green without changing legacy `/search` or `/read-range`.

## Conclusion

Confirmed. Authorization inputs are validated too late or not at all on the
affected public/provider read entry points.
