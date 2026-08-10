# Verification

## Green command and result

```bash
SDDGOV_SOURCE=/path/to/agentic-sdd-governance-source
PYTHONPATH="$SDDGOV_SOURCE/src" \
  python3 -m sddgov.cli ci local-gate .
```

Result: exit 0, `ok: true`. Pytest passed `3093` tests and skipped `12`; all
five configured Local Green commands returned zero.

## Before/after evidence

Before: `1 failed, 3092 passed, 12 skipped`; sole failure was the stale
B-000 lifecycle absence assertion. After: the focused replacement test passed,
then the full suite passed `3093 passed, 12 skipped`.

## Remaining limitations

Changing HEAD requires a fresh exact T-001 delivery authorization before those
candidate bytes may be delivered. This local verification does not grant it.
