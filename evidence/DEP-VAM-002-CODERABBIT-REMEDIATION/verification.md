# Verification

## Green command and result

`python -m pytest -q tests/test_memory_change_envelope.py
tests/test_memory_provider.py tests/test_gateway.py` passed 42 tests. Ruff and
the repository module-size gate also passed. `sddgov ci local-gate .` passed:
446 identity-isolated nodes, then 2,930 repository tests with 10 skips and one
pre-existing deprecation warning.

## Before/after evidence

Before: three focused assertions failed for the unbounded policy scan, integer
OpenAPI contract, and Gateway coercion. After: the same assertions pass; the
81-line request continues to fail closed at `max_lines=80`.

## Remaining limitations

- SQLite still decodes only its documented decimal opaque-id representation.
- The envelope represents current state, not historical content snapshots.
- Hosted CI and independent re-review remain required for the corrected exact
  head before merge.
