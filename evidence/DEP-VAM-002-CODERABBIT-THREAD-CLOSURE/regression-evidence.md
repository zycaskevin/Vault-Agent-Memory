# Regression Evidence

## Regression test added or strengthened

`test_vam002_review_rollback_keeps_pr_number_as_plain_text` rejects any line
beginning with `#500` and requires the normalized prose phrase. The existing
authoritative rollback contract also requires this DEP's preservation path.

## Related tests executed

At exact implementation commit `8847f94a58acc81a5e1b18357a6cbf50d00a35a7`,
the focused rollback selection passed 2 tests with 22 deselected; the direct
line scan returned `bad_lines=[]`; Ruff 0.16.4 and `git diff --check` passed.

## Unaffected paths sampled

Runtime Memory API modules, Gateway tests, database paths, Frozen Subject
paths, and live data are unaffected by this documentation-only correction.
Exact committed-head Local Green remains the proof-stage gate.
