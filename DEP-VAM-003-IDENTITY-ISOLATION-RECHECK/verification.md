# Verification

## Green command and result

From `$STABLE_WORKTREE`,
`sddgov ci local-gate .` passed: 446 identity nodes followed by 2,935 passed
and 10 skipped in the disjoint suite.

## Before/after evidence

The shared `$TEMP_WORKTREE` failed closed at two different proposal-building
nodes. Moving the unchanged candidate to a stable dedicated root produced a
complete Green run, matching the repository's existing race evidence.

## Remaining limitations

The verifier deliberately provides fixed denial output, so the precise audit
branch is not exposed. The stable-root requirement remains mandatory for the
independent review and exact merge-gate verification.
