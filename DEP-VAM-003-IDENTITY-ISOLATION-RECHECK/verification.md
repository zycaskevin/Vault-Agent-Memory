# Verification

## Green command and result

From `$STABLE_WORKTREE`,
`sddgov ci local-gate .` passed: 446 identity nodes followed by 2,935 passed
and 10 skipped in the disjoint suite.

The later exact committed audit head
`8eec35c3b228efbdfc8707a11e2d31e885002562` was then verified from the
owner-private Builder checkout with the hosted-equivalent command: 446 identity
nodes passed, followed by 2,941 passed, 10 skipped, and the already
dispositioned warning. The checkout remained clean at the same exact head.

## Before/after evidence

The shared `$TEMP_WORKTREE` failed closed at two different proposal-building
nodes. Moving the unchanged candidate to a stable dedicated root produced a
complete Green run, matching the repository's existing race evidence. The
subsequent exact committed-head proof confirms that the mitigation persisted
after the module-size and merge-gate commits, without an uncommitted qualifier.

## Remaining limitations

The verifier deliberately provides fixed denial output, so the precise audit
branch is not exposed. The stable-root requirement remains mandatory for the
independent review and exact merge-gate verification.
