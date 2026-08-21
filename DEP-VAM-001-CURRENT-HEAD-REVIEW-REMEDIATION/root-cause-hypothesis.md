# Root Cause Hypothesis

## Hypothesis

The prior fix bound the local target but did not separately bind the change's
PR-parent provenance or every evidence/rollback identity needed for replay.

## Supporting evidence

Current-head review showed the target could be inherited from the base parent;
the Green artifact omitted checkout state; warning disposition and mutation
wording were implicit; historical rollback targets were unnamed.

## Contradicting evidence

The local `main` and exact HEAD guards themselves were correctly ordered and
the functional tests passed.

## Falsification test

Bind exactly two merge parents and exclusive head-parent ancestry; add immutable
reverse-order rollback selectors and supplemental evidence records.

## Conclusion

Confirmed. These are evidence and fail-closed provenance gaps, not product
runtime defects.
