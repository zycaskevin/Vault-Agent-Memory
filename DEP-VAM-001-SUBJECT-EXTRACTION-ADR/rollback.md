# Rollback

## Trigger

The ADR misstates the owner decision, changes preserved task history, blurs the
Vault/DLI dependency direction, or any non-scope artifact appears in the diff.

## Reversible steps

Revert only the VAM-001 branch changes: its ADR, status paragraph, issue-comment
drafts, executable documentation test, Issue/SDD/Work Package, decision entry,
claim/event records, and DEP. Leave all frozen Subject artifacts untouched.

## Data compatibility

No schema, data, API, runtime, or external state changes exist. Rollback needs
no migration, backup restore, compatibility shim, or GitHub action.

## Post-rollback verification

Confirm the VAM-001 paths no longer differ from the selected base, rerun the
Subject contract tests and progress validator, and verify the frozen-artifact
diff remains empty.
