# Regression Evidence

## Regression test added or strengthened

`tests/test_vault_boundary_freeze.py` now rejects the exact stale phrases in
the three active guides, requires neutral positive wording, enforces rollback
contract version 1.0 and required scalar fields, rejects every Python `assert`
inside the guarded command, and requires pre/post untracked-path inspection.
It executes both embedded Python guards under `python -O`, proving invalid
approval and mismatched path input exit nonzero while valid inputs exit zero.

## Related tests executed

- Red: 5 failed, 12 passed.
- Green boundary/rollback file: 17 passed.
- Green VAM-003 focused suite: 230 passed.
- Exact committed/gate-bound Builder Local Green at `26519313`: 446 isolated
  Subject nodes passed, then 2,946 passed and 10 skipped with one already
  dispositioned warning.

## Unaffected paths sampled

Runtime code is unchanged. The focused suite samples project initialization,
legacy path inference, generated setup output, CLI setup flows, and the public
boundary contract.
