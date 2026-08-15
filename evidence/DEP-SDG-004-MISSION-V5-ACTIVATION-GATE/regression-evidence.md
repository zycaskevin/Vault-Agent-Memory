# Regression Evidence

## Regression test added or strengthened

`test_sdg004_release_accepts_only_exact_linear_reviewed_merge` proves the
hotfix release boundary. Activation tests prove the exact SDG record chain and
deny proof-only and extra-path deliveries.

`test_mission_activation_requires_exact_two_parent_merge_before_active`
proves that an otherwise exact linear activation topic remains inactive until
the exact two-parent delivery merge exists. The same test proves that the
byte-identical merged tree is accepted and an intervening rogue commit remains
denied.

Six complete authorization/progress identity-sensitive files run in dedicated
processes before a disjoint remainder. Each file remains fully collected; no
test is skipped or xfailed by the routing change. Final proof must compare the
union of isolated and remainder node IDs with ordinary full collection.

Final collection proof: `expected=3302`, `selected=3302`, with zero duplicate,
missing, or extra nodes. The executed result is 3290 passed plus 12 declared
skips, exactly 3302.

## Related tests executed

Focused Mission V5 and dispatcher suites, Ruff, Python 3.10 grammar, diff check,
doctor, CI Cost Guard, strict DEP, full Local Green, and hosted required CI.

Protected review revision 1 failed closed before full Local Green because the
activation validator accepted an unmerged topic, rollback contained a merge
placeholder, and the frozen review metadata did not match the reviewer's
independent digest. Revision 2 removes topic-head activation, uses a fixed
repository and exact head-branch GitHub merge query for rollback, and rebuilds
the review gate from the repaired source commit.

## Unaffected paths sampled

Canonical five, v1-v4, T-001 through T-003 trust roots, sequence-6 ledger,
registry/contract/schema, private gate, and product runtime remain byte-identical.
