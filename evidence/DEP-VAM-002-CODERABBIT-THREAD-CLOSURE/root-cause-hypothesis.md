# Root Cause Hypothesis

## Hypothesis

The prose was wrapped immediately before the issue number, leaving `#500` at
column one where Markdown treats it as heading syntax.

## Supporting evidence

- The deterministic RED probe identifies exactly line 13.
- The surrounding sentence already intends `PR #500 procedure` as prose.
- No runtime, API, storage, or authorization behavior participates.

## Contradicting evidence

The document renders acceptably in viewers that do not enforce MD018, which
explains why functional and governance tests remained Green.

## Falsification test

Move `PR` and `#500` onto the same physical line and add a regression that
rejects any future line beginning with `#500`. The hypothesis is false if the
same scan remains RED or normalized prose loses `PR #500 procedure`.

## Conclusion

Confirmed. The defect is a single unsafe Markdown line break, not a product or
rollback-behavior defect.
