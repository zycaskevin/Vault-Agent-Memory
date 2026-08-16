# Regression Evidence

## Required checks

- Preliminary exact linear topic PASS with inactive replay.
- Active single-parent topic DENY; active exact two-parent delivery PASS.
- Preliminary merge, extra path, pending artifact, proof mismatch, and invalid
  or abbreviated phase DENY.
- Identity collection remains closed and every Mission V5 node runs once under
  the explicit phase harness.
- Updater and task-action paths never receive a preliminary capability.

## Executed results

- Focused phase-routing suite: 92 passed.
- Builder Local Green: doctor, CI contract verification, README smoke, and
  release parity passed; the preliminary identity harness passed 431 nodes;
  the disjoint remainder passed 2869 tests with 12 skips.
- No skip, xfail, acceptance weakening, or updater/task-action preliminary
  capability was introduced.
