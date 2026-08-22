# Reproduction

## Expected

New Vault projects create `L0-bootstrap`; legacy `L0-identity` paths remain
readable; and generated setup guidance stays within generic memory curation and
lifecycle governance.

## Actual

New projects create `L0-identity`, the compiler does not recognize
`L0-bootstrap`, active public docs call L0 Identity, and generated guidance
instructs Profile agents to create user profiles and care summaries.

## Deterministic steps

Run `python -m pytest -q tests/test_vault_boundary_freeze.py` from the clean
VAM-003 worktree. The initial run produced 11 failures and one pass; the pass
confirms the legacy `L0-identity` path still maps to L0.

## Environment and preconditions

Branch `codex/vam-003-l0-bootstrap-boundary`, base commit
`291d5595c9cb2208a6b74206acbba35a883eb918`, CPython 3.11.15, pytest 9.1.1,
isolated worktree, no private fixture or network dependency.

## Evidence completeness audit

### Actual

The observed pre-fix behavior is fully recorded in the `Actual` section above.

### Deterministic steps

The focused pytest command above is sufficient to reproduce the boundary failure.

### Environment and preconditions

The branch, exact base, runtime, isolation, and dependency conditions are recorded above.
