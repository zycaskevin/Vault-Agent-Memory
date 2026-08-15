# Agentic SDD Governance consumer policy bootstrap

## Status

Accepted as the one-time consumer bootstrap for the owner-directed installation
of Agentic SDD Governance `0.2.0-experimental.6` with the `team-standard`
profile.

## Context

`setup-agent` installs its managed policy under
`.agentic-sdd-governance/policies/protected-files.yaml`. The experimental.6
merge verifier instead reads `policies/protected-files.yaml` from the exact
trusted Pull Request base. A first-time consumer installation therefore cannot
make that base-anchored file appear retroactively. The upstream defect is
tracked as `zycaskevin/Agentic-SDD-Governance#8`.

## Decision

Add one consumer-root protected-file policy before the managed installation PR.
The bootstrap policy protects installed governance roots, all workflows and
SDG state, agent instructions, its own policy root, packaging metadata,
scripts, and tests. It requires independent review and forbids acceptance
weakening or security-gate deletion.

This record does not claim that the new policy can authenticate its own
bootstrap. Trust in this one-time commit comes from the owner's explicit SDG
installation direction, exact two-path review, local verification, hosted CI,
and independent GitHub review. Once merged, every later governed PR must use
the executable base-anchored merge gate; this exception cannot be reused.

## Boundaries

- No product behavior, Subject Distillation task, ledger, migration, private or
  live data, deployment, release, Billing, credential, or provider-console
  action is authorized.
- The managed `.agentic-sdd-governance/` bytes remain supplied by the released
  package and are not copied into this bootstrap.
- Any future weakening or replacement of this policy requires the independent
  protected-file review that the policy establishes.

## Verification and rollback

Parse the YAML, verify the exact two-path diff, run the existing current-state
test command, and require hosted CI plus independent GitHub review before
merge. Rollback is a normal revert of this two-path commit; it has no product or
data compatibility effect.
