# Root Cause Hypothesis

## Hypothesis

The stable branch was specified from the receipt outward: the receipt MAC and
child handoff were closed, but the operator-private key source was left as an
abstract mapping. That omission made the independent attester check impossible
to implement deterministically and encouraged treating child PASS as authority.

## Supporting evidence

- The receipt HMAC message/domain and child output are exact.
- The config was described only as `key_id` to key/config input.
- No normative serialization, key encoding, resource bound, or canonical byte
  contract existed.
- Independent review found no attester-owned HMAC comparison in the candidate.

## Contradicting evidence

The operator-private verifier was already required to recompute the HMAC. That
protects the child-internal path, but does not satisfy the separately stated
attester independence requirement or defend against a substituted/misbehaving
child.

## Falsification test

Add one closed config grammar and require the repository validator to select the
key and recompute the exact MAC. If independent implementations can derive the
same bytes and the hostile synthetic child-PASS control is required to DENY,
the hypothesis is confirmed.

## Conclusion

Confirmed. The smallest sufficient repair is normative config closure plus an
attester-owned HMAC check. Bounded child I/O closes the adjacent availability
gap without changing product scope.
