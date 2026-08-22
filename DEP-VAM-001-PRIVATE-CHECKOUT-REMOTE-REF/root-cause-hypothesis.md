# Root Cause Hypothesis

## Hypothesis

Replacing a local clone's origin URL does not synthesize remote-tracking refs.
The review setup validated the URL and head but omitted an explicit fetch and
exact-base assertion for `refs/remotes/origin/main`, which Mission V5 requires.

## Supporting evidence

- The failing traceback is exactly `git rev-parse origin/main` exit 128.
- `git remote get-url origin` already returned the formal GitHub URL.
- The checkout was created from a local source and had no `origin/main` ref.
- An explicit fetch created the ref at the exact PR base, after which the exact
  failing node passed in 4.57 seconds.

## Contradicting evidence

None. No repository content, frozen baseline, or test assertion changed between
Red and targeted Green; only the missing remote-tracking ref was added.

## Falsification test

Delete or misbind `refs/remotes/origin/main` in a disposable clone and confirm
the named node fails; restore it to the exact PR base and confirm the node
passes without changing tracked files.

## Conclusion

Confirmed checkout-preparation defect. The bounded fix is an explicit formal
origin fetch plus exact base/head/clean assertions before Local Green.
