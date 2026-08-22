# Rollback

## Trigger

Rollback if valid sensitivity labels regress, malformed values still expose a
row/content, the three client errors cease to be HTTP 400, or the documented
row revision becomes unstable under audit-only events.

## Reversible steps

Before merge, revert the bounded remediation and its gate together, then return
the DEP to a non-proof state. After merge, use only the executable guarded PR
#500 procedure in
`DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md`; it preserves this DEP
and all governance provenance.

## Data compatibility

No table, stored row, cursor encoding, or revision material changed. The fix
only rejects malformed public policy input and corrects transport/docs/tests.

## Post-rollback verification

Run the full change-envelope/provider tests, direct and real-HTTP Gateway
contract nodes, OpenAPI checks, optimized rollback probes, strict retained DEP
verification, `git diff --check`, and the complete Local Green.
