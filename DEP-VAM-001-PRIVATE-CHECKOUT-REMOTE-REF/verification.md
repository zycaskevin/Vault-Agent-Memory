# Verification

## Green command and result

After fetching `origin/main` and proving it equals exact PR base
`291d5595c9cb2208a6b74206acbba35a883eb918`, the exact failed node ran with
the pinned candidate-phase environment and returned `1 passed in 4.57s`, exit
0. The full command is preserved in the shareable terminal artifact.

## Before/after evidence

- Before: `git rev-parse origin/main` exited 128 during Local Green.
- After: the explicit remote-tracking ref resolved to the exact PR base and the
  named node passed without a tracked-file change.

## Remaining limitations

The consumed Builder full gate remains a valid FAIL and is not retried under
the existing authorization. Push and independent review remain blocked until
a separately authorized exact Builder Local Green passes at the new final
audit head.
