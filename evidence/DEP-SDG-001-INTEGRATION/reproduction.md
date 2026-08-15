# Reproduction

## Expected

`sddgov ci verify .` accepts a project-specific team-standard contract and
verifies bounded automatic workflows without weakening the repository's
existing tests.

## Actual

The command exits 2 because `.sddgov/ci-cost-guard.json` is absent. Inspection
also shows automatic workflow jobs without timeouts or draft-PR gating.

## Deterministic steps

1. Check out commit `ab0637b55f3202c57bd0a11ee28386abe566c84d`.
2. Install Agentic SDD Governance `0.2.0-experimental.6` with the
   `team-standard` profile.
3. Run `.venv-sddgov/bin/sddgov ci verify .`.
4. Observe exit 2 and the missing-contract error in the collected terminal
   artifact.

## Environment and preconditions

The worktree preserves pre-existing changes. The local SDG virtual environment
contains the repository development dependencies. No hosted CI, deployment,
release, private input, or Billing operation is part of this reproduction.
