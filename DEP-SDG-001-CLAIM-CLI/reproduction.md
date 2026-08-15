# Reproduction

## Expected

The claim command records Work Package `SDG-001` in the repository's
`.sddgov/work-claims.json`.

## Actual

The command exited 1 with `NotADirectoryError` while attempting to resolve
`.sddgov` below the Markdown Work Package path.

## Deterministic steps

Run:

```text
.venv-sddgov/bin/sddgov claim SDG-001 --agent codex --ttl-minutes 240 --path docs/work-packages/SDG-001-team-standard-integration.md
```

## Environment and preconditions

Agentic SDD Governance `0.2.0-experimental.6`, Python 3.14, branch
`agent/mission-v5-reactivation-post-hotfix`, base commit
`ab0637b55f3202c57bd0a11ee28386abe566c84d`. The Work Package file exists and
the repository governance state is initialized.
