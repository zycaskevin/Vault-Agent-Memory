# Root Cause Hypothesis

## Hypothesis

The Local Green failure is caused only by the branch being behind the already
reviewed B-000 lifecycle repair at commit
`536934c369082568f01a86413cf7e346aaecfd2c`, not by a malformed T-001 artifact.

## Supporting evidence

`git diff HEAD..origin/main -- tests/test_subject_authorization_bootstrap.py`
shows that the upstream repair replaces phase-absence assertions with exact
B-000 ownership, file-kind, and mode assertions. `origin/main` is a direct
descendant of the current HEAD and contains no other content change beyond that
single-file repair merge.

## Contradicting evidence

No other test failed in the 3,105-result run. The T-001 artifacts are required
by the current Subject SDD and therefore cannot be removed as a valid fix.

## Falsification test

Fast-forward locally to `origin/main`, rerun the original failing test, and then
rerun the unchanged Local Green Gate. Any remaining failure falsifies the claim
that the stale lifecycle assertion is the sole blocker.

## Conclusion

Confirmed. After the exact upstream fast-forward, the focused lifecycle test
passed and the unchanged Local Green Gate completed with no failures.
