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

## Builder focused repair finding

The first focused source revision passed seven of eight selected checks but the
new SDG-011 anchor assertion denied during historical SDG-004 replay. Static
diff inspection found the Builder had accidentally added
`tests/test_repo_hygiene_tools.py` to historical `SDG004_COMPATIBILITY_PATHS`
and `SDG007_COMPATIBILITY_MODIFIED_PATHS`. Those records describe immutable
merged deliveries, so expanding either set correctly caused fail-closed replay.
The bounded repair removes only those two contaminating entries while retaining
the hygiene path in the new SDG-012 closed set.

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
phase harness, exclude them from both remainders, keep production bytes
unchanged, and never mutate historical delivery path sets.
