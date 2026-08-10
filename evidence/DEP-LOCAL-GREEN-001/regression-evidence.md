# Regression Evidence

## Regression test added or strengthened

Upstream commit `536934c` strengthens the test to assert the exact three
B-000-owned paths, regular-file/no-symlink status, and modes 0755/0644.

## Related tests executed

The original focused test passed: `1 passed in 0.04s`. The full Local Green
pytest command passed with `3093 passed, 12 skipped in 95.14s`. CI Cost Guard
static verification returned `ok: true` with no errors.

## Unaffected paths sampled

The unchanged gate also passed compileall, README command smoke, release parity,
and the OpenClaw adapter verification. No T-001 candidate file was edited by
the lifecycle repair.
