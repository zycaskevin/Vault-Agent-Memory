# Regression Evidence

## Hosted merge-gate reproduction (revision 2)

The first ready-for-review hosted run failed closed in the Agentic SDD Governance merge gate with:

```text
[ERROR] merge verification requires a clean exact-HEAD worktree
```

The job had created `.venv-sddgov` inside the checkout. Python virtual environments include a local `.gitignore`; that untracked file made the exact-HEAD worktree dirty. The repair creates the pinned governance environment under `RUNNER_TEMP` and invokes the runtime from that external path. No merge-gate cleanliness rule was weakened.

## Revision-2 Local Green transient control

The first full Local Green attempt reached 3,282 passing tests and one known fail-closed filesystem-identity failure in the T-003 real-Git pending recovery case. An immediate isolated rerun of the exact parameterized case passed (`1 passed`). This class had already been observed as an ancestor-directory metadata race and does not exercise the CI workflow edit. The permitted single full rerun is therefore used as the transient control; any repeated failure remains blocking.

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
