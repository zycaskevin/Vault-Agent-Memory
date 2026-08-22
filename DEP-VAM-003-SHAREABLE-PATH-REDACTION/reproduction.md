# Reproduction

## Expected

The exact-head Builder proof uses a stable checkout placeholder and has matching
manifest and redaction-report hashes.

## Actual

The shareable artifact exposed `/home/.../PR499-builder-20260822/repo`, its
manifest bound those bytes, and no redaction-report record existed.

## Deterministic steps

From exact head `26519313d479b6bb240ec1f815dcac5f950f53b4`, add the
shareable-path regression and run
`/tmp/vam-python-path-vam001/python -m pytest -q
tests/test_vault_boundary_freeze.py`. The Red result is 1 failed and 17 passed.

## Environment and preconditions

Branch `codex/vam-003-l0-bootstrap-boundary`, exact committed head above,
CPython 3.11.15, pytest 9.1.1, isolated Builder checkout, no network or private
fixture dependency.
