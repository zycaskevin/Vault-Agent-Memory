# Rollback

## Trigger

Rollback only if the compatibility sentence is shown to misstate the approved
Subject extraction decision or causes a new documentation regression.

## Reversible steps

Revert the bounded documentation compatibility commit only after another
approved sentence preserves the exact case-sensitive phrase `Runtime is not
implemented`. Do not alter or remove the frozen Subject artifacts or the
original VAM-001 extraction ADR. Rollback is incomplete until the replacement
compatibility sentence is present.

## Data compatibility

No schema, database, API, CLI, MCP, or stored-data behavior changed. Rollback
has no data migration or compatibility requirement.

## Post-rollback verification

Verify the exact phrase remains present, then run the baseline compatibility
node, VAM-001 extraction boundary tests, and the repository CI Cost Guard under
the same hosted-equivalent preconditions.
