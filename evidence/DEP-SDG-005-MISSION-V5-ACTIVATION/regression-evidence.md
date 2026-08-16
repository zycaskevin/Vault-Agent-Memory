# Regression Evidence

## Regression test added or strengthened

No test bytes changed. Existing controls prove that an unmerged topic cannot
activate Mission V5, an exact two-parent merge can, exact SDG review records are
required, and a proof without those records is denied.

## Related tests executed

In a clean exact two-parent synthetic delivery checkout, the four activation
controls passed `4/4` in `8.25s`. The first attempted invocation ran from the
live proof worktree and therefore hit the intended pre-merge session guard;
the phase-correct isolated invocation changed cwd to the detached clone and
passed without modifying the proof or weakening the guard.

The merged SDG-007 phase-isolation release keeps the 75 Mission V5 nodes in
their own process before the disjoint remainder. Doctor, CI Cost Guard, strict
DEP, phase-correct Local Green, protected review,
hosted required CI, and post-merge Mission validation remain delivery gates.

## Unaffected paths sampled

Canonical five, v1-v4, T-001 through T-003 trust roots and completion records,
sequence-6 progress, V5 implementation/contract/registry/schema, task outputs,
private/live data, and product runtime remain byte-unchanged.
