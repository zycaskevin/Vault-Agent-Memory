# VAM-001 Subject Distillation Extraction SDD Slice

Status: owner-approved architecture transition; implementation scope is L1
documentation only.

## Problem

Vault's frozen Subject Distillation package contains valuable Generic Subject
contracts and research, but its broader runtime domain includes identity,
belief, relationship, and Context Pack behavior that is outside Vault's memory
infrastructure responsibility. Without an explicit transition record, open
issues can continue the superseded T-005 through T-033 implementation path.

## Required outcome

- Record why Subject Distillation crossed the Memory/Identity boundary.
- Preserve T-001 through T-004 as completed origin provenance.
- Keep T-005 through T-033 in their historical `PENDING` state while recording
  that Vault will not continue them.
- State the intended disposition of Issues #410, #495, #496, and #497.
- Define the one-way future integration: Digital Life Identity consumes the
  generic Vault Memory API; neither product imports the other's internal store.
- Prepare issue-comment drafts without changing GitHub state.

## Acceptance criteria

1. The extraction ADR contains Context, Decision, boundary rationale,
   ownership, task status, issue disposition, origin, compatibility, rollback,
   and future-integration sections.
2. `docs/subject-distillation.md` identifies the package as preserved origin,
   not an active Vault runtime roadmap.
3. T-001 through T-004 remain `COMPLETED`; T-005 through T-033 remain `PENDING`.
4. Frozen canonical files, task authorization, evidence, and progress history
   are byte-for-byte unchanged from `origin/main`.
5. Comment drafts exist for Issues #410, #495, #496, and #497, with no remote
   write performed.

## Guardrails

- Do not create Mission V6 or Subject v15 runtime/database behavior.
- Do not modify the frozen five-file baseline, progress ledger, authorization,
  review, or evidence records.
- Do not add DLI-specific Vault endpoints or dependencies.
- Do not create the new DLI repository in this Work Package.
- Do not close or comment on GitHub issues in this Work Package.

## Rollback

Revert only the VAM-001 documentation, test, and local governance records. No
data or runtime rollback is required.
