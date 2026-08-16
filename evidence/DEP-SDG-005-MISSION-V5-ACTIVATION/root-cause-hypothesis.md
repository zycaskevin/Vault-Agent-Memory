# Root Cause Hypothesis

## Hypothesis

There is no product defect. Mission V5 is intentionally inactive because its
owner-confirmed proof has not yet been delivered through the closed,
independently reviewed two-parent activation merge.

## Supporting evidence

- Exact main lacks `MISSION-V5-T004-T033.json` and dispatches inactive.
- The proof binds protocol base `9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0`.
- Existing validators distinguish preliminary topic from active delivery and
  require exact parent order, tree equality, paths, actions, modes, gate,
  receipt, and proof bytes.
- Existing genuine tests cover proof-only denial, preliminary topic, active
  merge, topology drift, extra/pending paths, and governance-path closure.

## Contradicting evidence

None. No runner/test gap was found by static inspection, so source changes
would enlarge scope without evidence.

## Falsification

The hypothesis is false if the exact candidate becomes active before merge,
if the exact reviewed merge remains inactive, or if any drift case passes.

## Conclusion

Deliver only the frozen activation package and preserve existing executable
semantics.
