# Root Cause Hypothesis

## Hypothesis

Mission V5 intentionally separates proof publication from activation. The
unmerged topic is not authority; activation is derived only from a reviewed,
closed, two-parent delivery merge on exact current main.

## Supporting evidence

- `verify-confirmed` returned the canonical proof only after the retained
  private verifier passed and cleanup completed.
- The proof and pending topology are exact, but the live unmerged checkout
  remains DENY.
- Four synthetic controls accept only the exact two-parent merge and exact SDG
  record set, while denying incomplete activation records.

## Contradicting evidence

No evidence contradicts the phase model. Treating the unmerged DENY as a test
failure would weaken the activation contract by allowing a branch to
self-authorize.

## Falsification test

Construct an exact synthetic topic and direct two-parent merge from the
protocol base. If the merged tree is accepted, the linear topic is denied, and
missing SDG review records are denied, the hypothesis is confirmed.

## Conclusion

Confirmed. No production-code fix is required. The smallest safe delivery is
the closed activation proof plus governance evidence, independent review,
hosted CI, and exact merge readback.
