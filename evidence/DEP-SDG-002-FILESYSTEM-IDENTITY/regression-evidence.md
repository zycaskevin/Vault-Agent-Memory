# Regression Evidence

## RED

The deterministic synthetic probe retained one regular file, verified its
bytes and inode were unchanged, created one unrelated sibling, and observed
`legacy_full_directory_metadata_audit=DENY`.

## GREEN control

The exact SDG candidate revision was checked out under a dedicated stable root
outside both the active Codex runtime tree and shared OS temporary roots.
`sddgov ci local-gate .` completed with:

- doctor: PASS;
- CI Cost Guard: PASS;
- README documented-command smoke: PASS;
- release parity: PASS;
- pytest: 3,283 passed, 12 skipped, zero failed.

No test was skipped beyond the existing phase-neutral exclusions already
declared by the checked-in CI Cost Guard. No retry was used for this stable-root
control.

## Security preservation

The frozen Subject files were not edited. Existing symlink, inode/type/mode,
file-byte, replacement, cleanup, no-echo, and historical replay tests remain in
the full gate. The mitigation changes where the reviewer runs, not what the
authorization code accepts.

The related full gate also sampled the unaffected README, release-parity,
governance-doctor, CI-contract, and non-Subject test paths.

## Bundle-origin negative control

The first bundle-based v9 review intentionally remained fail closed: its clone
retained the local bundle pathname as `origin`, and two Mission V5 repository
identity checks denied it. The reviewer did not retry or sign. This proves the
identity gate cannot be bypassed by moving an exact tree through a local
transport. The v10 preflight therefore sets the canonical GitHub origin before
the first gate while retaining the bundle as read-only object provenance.
