# Root Cause Hypothesis

## Hypothesis

The governance workflow deliberately checks out a pull request's exact linear
head, while the Mission V5 fixture unconditionally invoked the post-merge
delivery predicate. The predicate's denial is correct; the CI route selected
the wrong lifecycle predicate for the checked topology.

## Supporting evidence

- The failing head is linear and no GitHub merge commit exists before review.
- The active predicate requires exactly one two-parent delivery with the
  protocol base as first parent.
- The work package already declares unmerged activation topics inactive and
  expected pre-merge denial.

## Falsification

If a proof-present linear topic can pass candidate validation with an extra,
missing, replaced, pending, or non-linear path, the hypothesis is false. If a
two-parent delivery is no longer required for active validation, the fix is
invalid.

## Conclusion

Confirmed. The smallest safe repair is explicit candidate/active routing, not
relaxing the active delivery predicate.
