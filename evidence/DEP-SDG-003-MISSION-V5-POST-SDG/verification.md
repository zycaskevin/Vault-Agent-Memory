# Verification

## Green command and result

Focused implementation gate:

```text
python -m pytest -q tests/test_subject_development_mission_v5.py tests/test_subject_task_authorization_dispatch_v5.py
```

Result: PASS, 67 passed. Ruff, Python compile, and `git diff --check` also pass.
Dedicated stable-checkout Local Green on source
`2c47002b59644eb1c367dfef41e8a6454ff17bf3`: PASS, 3286 passed, 12 skipped,
1 warning. The canonical origin preflight passed and `git status --porcelain`
was empty before and after the gate.

## Before/after evidence

- Before: exact clean main proposal exited 2 with
  `SUBJECT_DEVELOPMENT_MISSION_V5_DENY`.
- After: the temp-Git exact compatibility merge passes; extra descendant,
  hidden add-and-revert history, wrong mode, parent/tree/path drift all deny.
- The active-runtime full gate fail-closed evidence is preserved separately and
  is not relabelled as Green.
- The rejected v4 protected review is likewise preserved as fail-closed. Its
  two identity-sensitive V3 cases motivated process isolation rather than a
  test skip, xfail, retry, or frozen verifier change; the isolated complete V3
  progress file passed 29 tests.

## Remaining limitations

- The current branch is not activation authority. A fresh proposal can be
  generated only after independent review, hosted CI, merge, and exact main
  readback.
- The package-source-only `sddgov validate .` layout limitation remains outside
  the consumer-repository gate; `doctor` validates the installed managed
  assets.
- A protected independent review receipt, hosted CI, and merge readback are
  still required before generating the fresh proposal.
