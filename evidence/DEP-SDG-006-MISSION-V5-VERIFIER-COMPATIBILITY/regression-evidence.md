# Regression Evidence

## Regression test added or strengthened

- Unrelated external sibling create/delete is accepted by the Mission V5
  compatibility audit and the shared verifier still returns PASS.
- Private receipt inode replacement is DENY.
- External directory inode replacement is DENY.
- Exact SDG-006 two-parent linear reviewed merge is PASS; a hidden add/delete
  topic is DENY.

## Related tests executed

Focused Mission V5 tests, authorization lifecycle regression slices, full
Local Green, independent protected review, and hosted CI are required before
merge. Results are recorded in `verification.md` and the shareable artifacts.

## Unaffected paths sampled

Frozen v1-v4 hashes, canonical five, sequence-6 progress, no private artifact,
Ruff, Python 3.10 grammar, diff check, doctor, CI Cost Guard, README smoke, and
release parity.
