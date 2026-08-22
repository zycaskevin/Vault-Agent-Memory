# Regression Evidence

## Regression test added or strengthened

- Invalid non-empty sensitivity tests cover change listing, metadata,
  revision lookup, and bounded evidence with no rows/content on failure.
- Gateway/OpenAPI tests bind the exact three client errors to HTTP 400 and the
  allowed sensitivity enum.
- A real HTTP test covers invalid cursor, cursor-policy mismatch, and invalid
  sensitivity for page and revision-bound reads.
- Audit-only revision semantics and a non-vacuous audit SQL query are asserted.
- The PR #500 rollback guard is probed under optimized Python for approval and
  staged-path mismatch failures.

## Related tests executed

Focused sandbox-safe Green: 16 passed. This includes the complete change
envelope/provider files, three direct Gateway contract nodes, and the rollback
fail-closed node. Changed core modules pass Ruff. The exact committed private
Local Green then exercised the real loopback node and complete suite: 446
identity-isolated Subject nodes passed, followed by 2,962 passed, 10 skipped,
and one already dispositioned warning.

## Unaffected paths sampled

No database/schema/migration file, cursor encoding, Frozen Subject path,
identity/personality surface, dependency declaration, or existing valid
sensitivity result shape is changed.
