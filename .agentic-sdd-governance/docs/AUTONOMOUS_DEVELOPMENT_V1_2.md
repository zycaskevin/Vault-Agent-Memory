# SDG Autonomous Development v1.2

> **AUTONOMY BY DEFAULT. ESCALATION BY EXCEPTION.**

Human judgment is a scarce resource. Do not use humans as checksum validators, CI runners, Git operators, test runners, diff reviewers, retry buttons, or approval buttons for reversible technical work.

## Hard policy

`NO_HUMAN_ESCALATION_IF_MACHINE_VERIFIABLE`

If an answer can be obtained from the Repository, approved SDD, Decision Log, ADR, Policy, CI, Tests, Tool output, or deterministic verification, the Agent must obtain it there and continue. Uncertainty first triggers investigation, evidence retrieval, a safe reversible default, and a recorded technical decision. It becomes `ACTION REQUIRED` only when an unresolved decision changes the product contract or crosses a genuine risk/authority boundary.

## Default execution state

The default state is `CONTINUE`. Issue creation, Branches, routine implementation, Commit, feature-branch Push, PR creation, Review, review fixes, Lint, Typecheck, Tests, E2E, Security scans, recoverable retry, routine conflicts, CI, integrity verification, and L0/L1 Merge are engineering operations rather than approval prompts.

Checkpoint records completed capabilities, SDD/Issue traceability, tests, Evidence, deviations, risk, Git/Release state, and next work. It defaults to `requires_response: false` and `next_state: CONTINUE`.

## Escalation classifier

Before stopping, the Agent evaluates in this order:

1. Existing SDD, Decision or ADR resolves the question: continue.
2. Tests, CI or Tools can verify it: verify and continue.
3. It is a reversible L0/L1 technical decision: decide, record and continue.
4. Only one Work Package is blocked: record the blocker and continue unrelated work.
5. It is an unresolved L2 product decision, concrete L3 operation, Operational Action, or Necessary UAT: emit a strict `ACTION REQUIRED` Decision Package.

Sub-agents route uncertainty to the Main Agent. The Main Agent performs the lookup, evidence gathering and classification; a sub-agent does not ask the product owner to make routine engineering choices.

## Decision memory and approval budget

`.sddgov/decisions.json` records an approved L2 decision, its scope, basis and explicit reopen condition. The classifier reuses it only when the requested scope matches exactly, assumptions are unchanged, and the reopen condition has not occurred.

- L0: zero approvals.
- L1: zero approvals.
- L2: one approval per independent decision.
- L3: one fresh, one-use approval per concrete operation.
- Milestone UAT: one necessary UAT request.

An old L3 decision does not authorize a new operation. Fresh approval must match the exact operation ID, remain unexpired, and be unused.

The v1.2 Hard Gates require an owner-signed Ed25519 receipt from a configured trusted public key. Caller-provided `approved_by` text is never authority. The first successful L3 evaluation consumes the exact receipt atomically; a second or concurrent consumer fails closed. See `HARD_GATES_V1_2.md`.

## Integrity is invisible infrastructure

`sddgov artifact lock` calculates SHA-256 and writes `release.lock`. `sddgov artifact verify` recalculates and compares it. A match continues. A mismatch blocks that artifact, records `human_action_required: false`, and starts investigation. The system never asks a human to copy, paste, calculate, or approve a digest.

The digest remains available in the machine lock and provenance records, but ordinary checkpoints report only `Integrity verified`.

## Production deploy policy

Production is external state, so an L0 deployment is not pre-authorized. A routine deployment may run autonomously as L1 only when a recorded Decision explicitly authorizes that exact deployment class, its assumptions remain unchanged, and every machine guard passes. A caller-supplied boolean is not authority:

- all required checks pass;
- rollback is available;
- no unresolved security findings;
- no destructive schema change;
- no Secret change;
- no permission-boundary change;
- health check passes;
- blast radius is within policy.

Missing machine evidence blocks the deployment and triggers investigation, not an approval request. An L2 product-impacting deployment reuses a recorded decision only while its assumptions remain true. Destructive, high-privilege, Secret, permission-boundary, irreversible, or non-recoverable operations remain L3 and require fresh approval.

Every known action request explicitly supplies `effects`, using `{}` when none apply. Omitted, null, unknown, or false-valued effect classifications fail closed. Unknown action categories and any action declaring Production, destructive, irreversible, Secret, permission-boundary, payment, or high-privilege effects fail closed when labeled L0/L1. The Agent must correct the classification; the mismatch does not become an owner approval prompt.

## Executable Merge gate

`sddgov merge verify` binds the exact executable change to Local Green, strict DEP, Redaction, Rollback, raw-Evidence exclusion, and protected-file independent Review. GitHub workflows must execute it, and repository rulesets should require the resulting check.

## ACTION REQUIRED contract

A genuine escalation must contain exactly one bounded decision or operation and include Decision ID, risk, why human judgment is required, what the Agent already verified, options, recommendation, rationale, impact of no decision, and approval scope. Vague questions such as “要不要繼續？” or “可以嗎？” are invalid.

If an Operational Action blocks only one Work Package, the Decision Package may be queued while the Agent continues unrelated work.

## Audit conclusion

The canonical pre-v1.2 Repository did not contain a Policy, CLI, Workflow, Guard, or Prompt that explicitly asked the owner to paste a SHA-256. Existing hash code already calculated digests automatically. The observed behavior was an Agent/prompt-layer failure enabled by missing executable escalation, decision-memory, checkpoint, integrity-lock, and deployment-gate contracts. v1.2 adds those contracts without removing SHA-256 or weakening Production, Secret, permission, data, redaction, testing, or rollback gates.
