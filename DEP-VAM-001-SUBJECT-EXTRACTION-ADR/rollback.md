# Rollback

## Trigger

The ADR misstates the owner decision, changes preserved task history, blurs the
Vault/DLI dependency direction, or any non-scope artifact appears in the diff.

## Reversible steps

Revert only the VAM-001 branch changes: its ADR
`docs/decision_records/2026-08-21-extract-subject-distillation.md`, status
paragraph, issue-disposition record, executable documentation test,
Issue/SDD/Work Package, `.sddgov/external-actions.json`, decision entry,
claim/event records, and DEP. Use `git diff --name-status <base>...HEAD` to
prove every VAM-001-owned repository path is reverted while leaving all frozen
Subject artifacts untouched. External Issue state is historical and must not
be silently reopened by repository rollback.

## Data compatibility

No schema, data, API, or runtime changes exist. The already completed GitHub
Issue disposition is external historical state; reversing it would be a new
separately authorized operation, not an automatic rollback step.

## Post-rollback verification

Confirm the VAM-001 paths no longer differ from the selected base, rerun the
Subject contract tests and progress validator, and verify the frozen-artifact
diff remains empty.
