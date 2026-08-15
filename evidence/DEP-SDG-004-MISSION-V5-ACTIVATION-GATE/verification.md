# Verification

## Green command and result

Focused gate:

```text
python -m pytest -q tests/test_subject_development_mission_v5.py tests/test_subject_task_authorization_dispatch_v5.py
```

Result: PASS, 71 passed. Ruff, Python 3.10 grammar, `git diff --check`,
`sddgov doctor .`, and `sddgov ci verify .` also pass. Full Local Green and
independent review remain pending until the exact candidate is frozen.

Final Local Green routing revision: PASS. Six identity-sensitive files passed
301 tests in dedicated processes; the disjoint remainder passed 2989 tests with
12 skipped. Total executed nodes are therefore 3290 passed and 12 skipped.
Independent collection parity reports `full=3473`, historical-adjusted
`expected=3302`, `selected=3302`, `duplicates=0`, `missing=0`, and `extra=0`.

The first combined Local Green correctly failed closed at one unchanged
authorization-bootstrap identity test (3260 passed, 12 skipped). The exact case
passed in isolation. The next revision runs the complete 96-test file in one
dedicated process and removes only that already-executed file from the disjoint
remainder; it is not a retry of the failed revision.

A second revision exposed the same filesystem-identity class in an unchanged
T-002 authorization test (3164 passed, 12 skipped); the exact case passed in
isolation. The final routing revision isolates the six complete lifecycle-heavy
files and requires node-set equality with ordinary full collection.

## Before/after evidence

RED: proof-only Mission V5 PASS combined with SDG exact-base mismatch DENY.
GREEN: the exact SDG-004 linear merge and SDG-005 activation-record tests pass;
proof-only and extra-path activation controls deny.

## Remaining limitations

The earlier proof is intentionally unusable after trust-root changes. A fresh
proposal and exact owner confirmation remain required after the hotfix merge.
Independent protected review, hosted CI, and merge readback are still pending.
