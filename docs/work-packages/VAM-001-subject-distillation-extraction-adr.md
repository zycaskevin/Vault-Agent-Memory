# Work Package: VAM-001 Subject Distillation Extraction ADR

## References

- Issue: `docs/issues/VAM-001-subject-distillation-extraction-adr.md`
- SDD: `docs/specs/vam-001-subject-distillation-extraction.md`
- Owner decision: Digital Life Identity Runtime v0.1 SDD, 2026-08-21
- Risk: L1 implementation under approved L2 architecture direction

## Objective Contract

- Outcome: record the Vault/Digital Life Identity extraction boundary without
  changing runtime behavior or frozen Subject history.
- Success metric: the ADR, status page, and four issue-comment drafts satisfy
  the executable documentation contract; all protected historical artifacts
  remain unchanged.
- Guardrails: no Mission V6, T-005 implementation, progress mutation, frozen
  artifact change, API/runtime change, new repository, push, merge, release,
  or deployment. This implementation package originally excluded remote Issue
  writes; the owner later issued a separate concrete instruction to execute the
  bounded disposition, recorded as `VAM-001-ISSUE-DISPOSITION`.
- Keep condition: focused checks, relevant regressions, frozen-artifact diff,
  and strict redacted evidence verification pass.
- Rollback condition: documentation misstates preserved task status, blurs the
  Memory/Identity boundary, or touches any non-scope artifact.

## Scope

- In scope: extraction ADR; non-frozen Subject status; local issue-comment
  drafts; executable documentation check; local governance and evidence.
- Non-scope: VAM-002/VAM-003, DLI repo work, additional online Issue/PR
  mutation, and all runtime/database/API changes.
- Dependencies: owner architecture directive, PR #494 merge commit
  `291d5595c9cb2208a6b74206acbba35a883eb918`, and the frozen Subject baseline.
- Evidence requirement: full local L1 DEP with redacted Red/Green output.
- Verification plan: focused test, relevant Subject tests, README/parity smoke,
  frozen-file diff, `git diff --check`, governance doctor, and strict DEP verify.

## Claim

- Agent: codex
- Claimed at: 2026-08-21T03:57:18Z
- Expires at: 2026-08-21T11:57:18Z
