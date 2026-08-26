# Reproduction

## Expected

The focused contract test imports `vault.memory_change_envelope` and exercises
policy-filtered cursor pagination plus revision-bound bounded evidence.

## Actual

Pytest stops during collection with `ModuleNotFoundError`. The collection
failure proves only that `vault.memory_change_envelope` was absent on the
`origin/main` baseline; it does not independently prove the provider contract
was absent. Provider-interface behavior requires a separate deterministic
contract check.

## Deterministic steps

Run:

```text
python -m pytest -q tests/test_memory_change_envelope.py
```

The collection error is captured in the red-test shareable artifact.

## Environment and preconditions

- Branch: `codex/vam-002-memory-change-envelope`
- Baseline: `291d5595c9cb2208a6b74206acbba35a883eb918`
- Python: repository development virtual environment, Python 3.11
- Isolated worktree based exactly on `origin/main`
