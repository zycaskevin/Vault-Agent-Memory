# Root Cause Hypothesis

## Hypothesis

`setup-agent` intentionally installs managed governance assets but does not
invent a repository-specific Local Green contract or retrofit repository
workflows. The missing contract and controls are the cause of the deterministic
static verification failure.

## Supporting evidence

`doctor .` passes with all 59 managed files, while `ci verify .` exits 2 and
names only the missing contract. The existing automatic workflows also lack the
team-standard timeout and draft-PR controls required by the guard.

## Contradicting evidence

The repository's tests and product code were not implicated. A separate
repository-wide Ruff run reports pre-existing lint debt, but Ruff is not an
existing required gate and does not explain the missing SDG contract error.

## Falsification test

Add a schema-valid `.sddgov/ci-cost-guard.json`, retrofit only the bounded
workflow controls it declares, and rerun static verification. If the same error
persists, the hypothesis is false.

## Conclusion

Confirmed: after adding the repo-specific contract and bounded workflow
controls, `sddgov ci verify .` returns `ok: true` and enumerates every governed
workflow/job with no errors.
