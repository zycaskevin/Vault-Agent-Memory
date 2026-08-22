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

The historical focused summary reported 16 passed but omitted its exact node
list; it is therefore not used as a reproducible proof count. Its scoped Ruff
PASS covered `vault/access_policy.py`, `vault/memory_provider.py`,
`vault/gateway_openapi.py`, and `tests/test_memory_change_envelope.py`, not
every changed Python file. The exact committed private Local Green is the
authoritative proof: 446 identity-isolated Subject nodes passed, followed by
2,962 passed, 10 skipped, and one already dispositioned warning. The follow-up
DEP records exact repo-relative Green and all-changed-Python Ruff commands.

## Unaffected paths sampled

No database/schema/migration file, cursor encoding, Frozen Subject path,
identity/personality surface, dependency declaration, or existing valid
sensitivity result shape is changed.
