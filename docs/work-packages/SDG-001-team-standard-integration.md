# Work Package: SDG-001 team-standard integration

## References

- Issue: #470
- Bootstrap dependency: #471 and
  `zycaskevin/Agentic-SDD-Governance#8`
- SDD: `.agentic-sdd-governance/core/POLICY_KERNEL.md`,
  `.agentic-sdd-governance/profiles/team-standard.yaml`, and
  `.agents/skills/agentic-sdd-governance/references/ci-cost-guard.md`
- Risk: L1

## Objective Contract

- Outcome: Install and verify Agentic SDD Governance
  `0.2.0-experimental.6` for Codex with the `team-standard` profile.
- Success metric: `doctor`, CI Cost Guard static verification, and the
  repository-specific Local Green Gate all pass from the same revision.
- Guardrails: Preserve existing required tests and acceptance criteria; keep
  raw evidence, private keys, credentials, production data, deployment,
  release, Billing, and provider-console operations out of scope.
- Keep condition: Managed governance assets are deterministic, public-safe,
  reviewable, and compatible with the existing Release Readiness CI.
- Rollback condition: Any governance validation failure, required-test
  weakening, unexpected secret/private-path retention, or hosted-CI regression.

## Scope

- In scope: Managed SDG assets, Codex Skill, project state, CI Cost Guard,
  `AGENTS.md`/`.gitignore` managed blocks, and the minimum CI controls required
  by `team-standard`.
- Non-scope: Vault product behavior, Subject Distillation task implementation,
  database migrations, private/live data, deployment, release, and Billing.
- Dependencies: Existing repository test commands and GitHub Release Readiness
  CI; the merged consumer-root protected-file policy from #471; Python
  development dependencies installed only in the local ignored
  `.venv-sddgov` environment.
- Evidence requirement: Targeted setup/doctor proof plus full Local Green Gate,
  independent review, and one hosted CI run for the final revision.
- Verification plan: Run `sddgov doctor .`, `sddgov ci verify .`,
  `sddgov ci local-gate .`, repository smoke/parity checks, and
  `git diff --check`. The package-source-only `sddgov validate` command is not
  a consumer-repository gate; `doctor` validates installed managed assets.

## Claim

- Agent: codex
- Claimed at: 2026-08-15T01:59:29Z
- Expires at: 2026-08-15T05:59:29Z
