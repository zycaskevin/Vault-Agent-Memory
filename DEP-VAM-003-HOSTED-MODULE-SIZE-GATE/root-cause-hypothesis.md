# Root Cause Hypothesis

## Hypothesis

VAM-003 centralized the memory-directory list correctly, but the new import
added one physical line while the replaced directory literal did not remove an
equivalent line. The legacy file therefore exceeded its frozen physical-line
baseline by exactly one. The local governance gate does not include the hosted
module-size script, so the overage first appeared after Ready-for-review.

## Supporting evidence

- The hosted check reports 1,232 lines against a 1,231-line allowance.
- The scoped diff adds one import and does not add a new function or branch in
  `vault/agent_setup.py`.
- The functional VAM-003 local suite was already Green.

## Contradicting evidence

No evidence indicates a functional regression or baseline drift. The exact
same hosted gate passes on VAM-001 and VAM-002, which do not add the import to
this module.

## Falsification test

Remove one non-semantic separator line, rerun
`python scripts/module_size_gate.py`, and confirm the file returns to 1,231
lines without changing the canonical-directory behavior tests.

## Conclusion

Confirmed. This is a one-line physical-size regression, not a need to raise the
baseline or change product behavior.
