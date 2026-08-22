# Governance Bootstrap Evidence — 2026-08-03

## Evidence identity

- Repository: `zycaskevin/Vault-Agent-Memory`
- Bootstrap base: `cfee9429c64a1dfa86bc14b126666979a6ce2611`
- Work Package: `WP-GOV-001`
- Issue: `#427`
- Collected: `2026-08-03 Asia/Taipei`

## Repository and delivery readback

- Local status, branches and recent commits were inspected before changes.
- Remote `main` resolved to the exact Bootstrap base above.
- GitHub Issues, open PRs, CI runs, releases, environments, deployments,
  branch protection and rulesets were read back independently.
- Latest main Release Readiness run at Bootstrap was `30755710976` and passed.
- Latest release was `v0.10.2`; repository evidence did not prove an active
  Development or Staging deployment.
- The Pages workflow has a docs-triggered public deployment. It was not changed;
  its post-merge publication remains an operation-specific risk:L3 gate.

## Duplicate-work and SDD readback

- Product, architecture, Subject SDD, schema, baseline, traceability, roadmap,
  security/privacy and test documents were indexed and reconciled.
- A preserved B-001 runner/test candidate was inspected in its original dirty
  worktree. It was not modified or represented as accepted evidence.
- Open PRs `#401` and `#426`, stale Subject issues and drifted branches were
  recorded without destructive cleanup.

## Executable verification

Run from repository root:

```text
.venv/bin/python scripts/validate_agent_governance.py
.venv/bin/python -m pytest -q tests/test_agent_governance_bootstrap.py
.venv/bin/ruff check scripts/validate_agent_governance.py tests/test_agent_governance_bootstrap.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/validate_subject_baseline.py
```

Most recent pre-PR focused result: `20 passed in 1.39s`. Most recent pre-PR
full-suite result: `2910 passed, 12 skipped in 84.94s`. Final PR/CI evidence
supersedes this local snapshot when available.
