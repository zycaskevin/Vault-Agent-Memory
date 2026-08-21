# Rollback

## Trigger

The section extractor misparses a valid Issue heading, the strengthened tests
reject the approved document, or the rollback contract becomes less bounded.

## Reversible steps

Revert only the independent-review remediation commit before a review receipt
is issued, then restore the previous merge-gate audit metadata. Do not change
the extraction ADR, frozen Subject artifacts, or completed Issue disposition.

## Data compatibility

No runtime, schema, or stored-data change exists.

## Post-rollback verification

Run the prior focused VAM-001 tests and strict verification of the two original
VAM-001 DEPs. The PR remains blocked until a different reviewer-approved fix is
provided.
