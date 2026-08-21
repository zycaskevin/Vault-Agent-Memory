# Root Cause Hypothesis

## Hypothesis

The pinned Subject verifier treats metadata changes to every absolute ancestor
directory as repository-input replacement. Because the fresh Reviewer checkout
was directly below shared `/tmp`, unrelated system activity that changed
`/tmp`'s size or `mtime_ns` made the final fail-closed path-chain audit reject
unchanged pinned repository inputs.

## Supporting evidence

- `_identity` includes device, inode, mode, size, and `mtime_ns`.
- `_open_chain` records each absolute path component from `/`, including
  `/tmp`, and `_audit` later requires exact identity equality.
- The deterministic diagnostic changes only one unrelated `/tmp` sibling;
  the unchanged control passes and the perturbed call is denied.
- Read-only samples observed `/tmp` mtime advancing while the checkout-root
  mtime stayed fixed.
- The exact verifier bytes and all five manifest-bound files matched their
  pinned SHA-256 and byte sizes after the failure.

## Contradicting evidence

The production exception deliberately collapses all verifier subconditions to
`Denied`, so the original transcript cannot name the exact changed component.
This is resolved by the deterministic diagnostic, which proves the proposed
ancestor-only change is independently sufficient to produce the same boundary.

## Falsification test

Run the unchanged exact Local Green from a fresh Reviewer checkout whose
absolute ancestor chain is private and stable for the duration of the run. The
hypothesis is falsified if `_repo_inputs` still denies while the checkout,
ancestor identities, and all pinned inputs remain unchanged.

## Conclusion

Confirmed as an execution-location race. This DEP does not propose weakening
the fail-closed verifier or changing any frozen Subject source. The bounded fix
is to execute independent review from a fresh private, stable checkout rather
than directly below shared `/tmp`.
