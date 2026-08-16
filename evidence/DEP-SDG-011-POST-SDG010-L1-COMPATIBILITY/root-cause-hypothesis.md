# Root Cause Hypothesis

## Hypothesis

The Mission V5 checker encoded SDG-008 as the terminal compatibility release.
SDG-010 was safely merged afterward, but the chain never gained a verifier for
that new exact delivery. Separately, the SDG-010 rollback record froze an
earlier branch name instead of the reviewed v4 PR head.

## Supporting evidence

- `_check_protocol_release_commit()` calls
  `_check_sdg008_compatibility_release(repo_root, base)` directly.
- `efa43a4` is a two-parent merge of exact `46690372` and exact `7e155ca`, not a
  direct SDG-008 delivery from `6d499e41`.
- Merge tree and topic tree are both exact `781beb6d`.
- Exact gate and receipt SHA-256 values recompute to `bd7b1935...` and
  `07ee1f58...`.
- PR #484 metadata names the v4 source branch, while the rollback text omits
  `-v4`.
- Source `db4f142ab` added 13 genuine Mission V5 regression nodes but retained
  the pre-SDG-011 identity-harness count of 77; collection therefore denied
  before node execution.

## Contradicting evidence

No evidence shows activation, owner-proof, progress, updater, or dispatcher
semantics changed. The defect is confined to release ancestry recognition and
the executable rollback locator.

## Falsification

The hypothesis is false if exact SDG-010 cannot be validated independently, if
the current anchor must itself become an eligible proposal base, or if a closed
future merge still fails after the chain advances. Any acceptance of wrong
parent/order/tree, hidden history, path/action/mode drift, or gate/receipt drift
also invalidates the fix.

## Conclusion

Confirmed from source and exact Git topology. Add a fixed SDG-010 anchor
validator followed by a closed SDG-011 delivery validator, and correct only the
current rollback bytes without rewriting history.

The collection failure has the same bounded cause: update the closed count to
90, include the harness in SDG-011's allowed/modified paths, and refresh its CI
byte pin. No identity predicate or test is skipped.
