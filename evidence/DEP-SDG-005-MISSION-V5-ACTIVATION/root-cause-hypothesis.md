# Root Cause Hypothesis

## Hypothesis

There is no product defect. Mission V5 is intentionally inactive because its
owner-confirmed proof has not crossed the closed independently reviewed
two-parent activation merge.

## Supporting evidence

- Exact main lacks the Mission V5 proof and dispatches inactive.
- The proof binds protocol base `327ebe1b557fc30cbc5482a1de87e1757b8873da`.
- Validators require exact parent order, tree equality, paths, actions, modes,
  gate, receipt, and proof bytes.
- Genuine tests cover preliminary and active topology plus drift cases.

## Contradicting evidence

None. No runner or test gap is presently evidenced.

## Falsification

False if the candidate grants authority before merge, the exact reviewed merge
remains inactive, or any drift case passes.

## Conclusion

Deliver only the frozen activation package and preserve executable semantics.
