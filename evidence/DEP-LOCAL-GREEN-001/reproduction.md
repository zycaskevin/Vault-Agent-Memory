# Reproduction

## Expected

`tests/test_subject_authorization_bootstrap.py` must verify that the three
B-000-owned artifacts remain regular files with their exact modes while later
authorized task artifacts may coexist.

## Actual

The stale branch-local test `test_only_b000_paths_are_present` asserted that
`scripts/read_subject_baseline_id.py` and
`specs/subject-distillation/implementation-progress.json` must not exist. The
first assertion failed in the active T-001 worktree.

## Deterministic steps

From repository root, run:

```bash
.venv/bin/python -m pytest -q
```

Observed result: `1 failed, 3092 passed, 12 skipped`; the sole failure was
`tests/test_subject_authorization_bootstrap.py::test_only_b000_paths_are_present`.

## Environment and preconditions

Branch `agent/t001-control-plane`, commit
`3e30a99c46cdd3cb0982f1332efa0e7dc2442438`, CPython 3.14.3, pytest 9.1.1.
The T-001 candidate paths pre-existed this repair and must be preserved.
