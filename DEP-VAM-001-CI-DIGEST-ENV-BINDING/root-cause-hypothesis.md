# Root Cause Hypothesis

## Hypothesis

The change digest hashes textual `git diff --binary` output whose `index` lines
inherit Git's configured object abbreviation length.

## Supporting evidence

At exact head `b2c8378`, the default environment returns digest `e155240b...`,
while the CI contract's `core.abbrev=40` returns `1ba66ab1...`. Hosted merge
verification rejects the default-environment value.

## Contradicting evidence

Both calculations resolve the same full base and head SHAs, so commit identity
drift does not explain the mismatch.

## Falsification test

Calculate and bind the final gate only under the CI contract environment, then
run hosted-equivalent merge verification and GitHub CI against that exact head.

## Conclusion

Confirmed. The bounded repository fix is an audit binding generated under the
pinned CI Git environment; the upstream digest implementation remains outside
this Work Package.
