# Root Cause Hypothesis

## Hypothesis

`_check_protocol_release_commit()` conflates the frozen V5 bridge change set
with every later commit that may legally precede activation. It compares the
cumulative `BRIDGE_BASE..selected_base` path set to `BRIDGE_PATHS`, so any
reviewed governance-only descendant necessarily denies.

## Supporting evidence

- The exact clean main at `4c4c29a16decfeedda59b685886801f65b9fd878`
  has canonical repository identity, equals `origin/main`, descends from the
  V5 bridge, and has no Mission V5 proof.
- The proposal command still exits 2 with the fixed DENY marker.
- The only newly changed paths are the reviewed policy-bootstrap and SDG
  integrations; adding them to the cumulative comparison explains the deny.

## Contradicting evidence

The fail-closed result is internally consistent with the current function: an
arbitrary extra path also denies. The problem is therefore not that the old
check stopped working, but that it cannot distinguish an exact reviewed
governance anchor from an unauthorized descendant.

## Falsification test

Model a frozen reviewed post-SDG anchor followed by a closed compatibility
topic and exact two-parent merge. The hypothesis is falsified if the old code
accepts that merge, or if the repaired code accepts a single-parent descendant,
an extra path, a deletion/rename, a wrong mode, non-linear topic history, or a
merge whose tree differs from its reviewed topic parent.

## Conclusion

Confirmed. The genuine RED fails before any authority mutation because the
module has no post-SDG compatibility boundary, while the production proposal
reproduction denies for the same cumulative-diff design.
