# Verification

## Green command and result

`/tmp/vam-python-path-vam001/python -m pytest -q
tests/test_vault_boundary_freeze.py` passed the initial 18-test fix proof, then
the final 19-test suite after adding the all-VAM-003 shareable scan. All five
VAM-003 DEPs pass strict verification. The focused rollback preservation probe
also passes after adding this DEP to the guarded restore list.

## Before/after evidence

Before: the regression exposed the owner-home path and failed. After: the
artifact contains `$BUILDER_WORKTREE`; its SHA-256 is
`c21e45f1acf0abdc52bab64b36f5acdb8020d761624a882967b119eaffb822b0`,
and both manifest and redaction provenance bind that output.

## Remaining limitations

Local Green is enforced separately by the merge gate; this DEP's Proof is the
completed focused Red/Green evidence above and does not treat a pending
repository gate as Proof. Independent review and receipt signing remain
separate protected-file gates.
