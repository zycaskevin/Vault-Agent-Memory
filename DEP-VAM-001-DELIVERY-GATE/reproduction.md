# Reproduction

## Expected

The VAM-001 branch passes the repository CI Cost Guard without weakening the
frozen Subject controls or the existing agent-setup behavior.

## Actual

The identity-isolated suite passed all 446 nodes, then the disjoint remainder
reported one documentation compatibility failure, environment-dependent
agent-setup command rendering failures, and a fail-closed source-mode denial.

## Deterministic steps

Run `sddgov ci local-gate .` with the repository virtual-environment Python
available as `python`. The documentation failure is reproduced by
`tests/test_subject_baseline.py::test_public_package_has_no_stale_private_governance_metadata`.

## Environment and preconditions

Clean `codex/vam-001-subject-extraction-adr` worktree, Python 3.11.15,
repository governance 0.2.0-experimental.6, CLI 0.2.0-experimental.3. The
isolated worktree was created on a host whose default directory mode is 0775.
