# Root Cause Hypothesis

## Hypothesis

The two independently correct phase contracts define mutually exclusive final
Git trees: Mission V5 accepts only the proof path, while SDG requires refreshed
gate and receipt bytes committed for the exact reviewed head.

## Supporting evidence

The proof-only commit returns Mission `ACTIVE/PASS` and SDG base mismatch. The
Mission activation replay currently compares the base-to-delivery path set to a
single proof path. Hosted CI always invokes the SDG merge verifier for a ready
Pull Request.

## Contradicting evidence

No evidence contradicts the conflict. Both gates are fail closed as designed;
the missing piece is an explicit compatibility phase, not a parser or CI flake.

## Falsification test

Create a temp-Git activation containing the proof plus a closed SDG record set.
If Mission V5 can validate that exact linear topic/merge while denying proof-only
and extra paths, the hypothesis is confirmed.

## Conclusion

Confirmed. A bounded compatibility layer is required. Bypassing either gate or
loosening activation to arbitrary governance paths is not acceptable.
