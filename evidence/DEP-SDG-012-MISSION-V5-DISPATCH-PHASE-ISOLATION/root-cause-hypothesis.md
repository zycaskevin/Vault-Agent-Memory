# Root Cause Hypothesis

## Hypothesis

The dispatcher test file remained in the generic Local Green remainder after
Mission V5 introduced explicit candidate/active replay. Because it was absent
from the identity harness, its two assertions always inspected live checkout
topology and therefore required an active merge even on an exact preliminary PR
head.

## Supporting evidence

- Hosted candidate Mission V5 identity controls passed before the remainder.
- The remainder alone reported exactly the two dispatcher V5 failures.
- The identity harness lists eight files and omits dispatcher V5.
- Both local and hosted remainder commands omit only Mission V5, not dispatcher
  V5.
- Production dispatcher correctly denied the preliminary topic; its fail-closed
  behavior is evidence against changing production code.

## Contradicting evidence

No evidence shows a production dispatcher, validator, updater, activation, or
authority defect. The ordinary test job's synthetic merge topology already
passes the unconditional production dispatch replay.

## Falsification

The hypothesis is false if the same two failures remain after the dispatcher
nodes run from phase-neutral snapshots exactly once, or if active phase no
longer returns ACTIVE.

## Conclusion

Move test ownership, not authority semantics: add the two nodes to the explicit
phase harness, exclude them from both remainders, and keep production bytes
unchanged.
