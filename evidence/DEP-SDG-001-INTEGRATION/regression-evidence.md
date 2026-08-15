# Regression Evidence

## Regression test added or strengthened

The CI Cost Guard itself is the machine-readable regression contract. It now
enumerates every automatic workflow/job, enforces timeouts, read-only default
permissions, concurrency cancellation, and draft-PR skip controls. CI path and
secret-scan coverage now include the installed governance and evidence roots.
The exact-head governance job also executes the signed merge gate with public
reviewer trust materialized outside the repository.

## Related tests executed

`sddgov doctor .`, `sddgov ci verify .`, README command smoke, release parity,
the current-state pytest suite, workflow YAML/contract JSON parsing, and
`git diff --check`.

## Unaffected paths sampled

The current-state suite passed with 3,283 tests and 12 skips. Deployment and
release workflows remain byte-preserved and are explicitly exempt from this L1
cost-control change. No Subject Distillation implementation or canonical
Mission artifact was modified.
