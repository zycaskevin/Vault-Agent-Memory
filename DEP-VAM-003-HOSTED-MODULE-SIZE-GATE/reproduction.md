# Reproduction

## Expected

The hosted `python scripts/module_size_gate.py` check accepts VAM-003 without
increasing any legacy module beyond its recorded baseline.

## Actual

Release Readiness CI run `32473949789`, job `96746338443`, failed because
`vault/agent_setup.py` had 1,232 physical lines while the recorded allowance is
1,231.

## Deterministic steps

1. Check out exact head `0539ae33f36a290a4e853630bacbe6ef7749382b`.
2. Install the repository development dependencies.
3. Run `python scripts/module_size_gate.py`.
4. Observe exit status 1 and the one-line overage.

## Environment and preconditions

GitHub Actions Release Readiness CI on Ubuntu 24.04, branch
`codex/vam-003-l0-bootstrap-boundary`, exact head
`0539ae33f36a290a4e853630bacbe6ef7749382b`.
