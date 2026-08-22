# Fix Scope

## Smallest sufficient change

Replace only the contradictory active guidance, make the existing rollback
record conform to verifier version 1.0, replace optimization-sensitive asserts
with explicit exits, detect untracked paths after mutation, and add executable
regression coverage.

## Files or components in scope

- `docs/memory_governance.md`
- `docs/agent_install.md`
- `docs/vision.md`
- `DEP-VAM-003-L0-BOOTSTRAP-BOUNDARY/rollback.md`
- `tests/test_vault_boundary_freeze.py`
- this remediation DEP and the exact-head identity proof metadata

## Explicit non-scope

- No Vault storage, retrieval, schema, CLI, or API behavior change.
- No rename or removal of legacy public compatibility identifiers.
- No Identity Runtime implementation.
- No user data migration, deletion, or automatic rollback execution.

## Blast radius

Low and documentation/governance bounded. The only executable behavior added is
test coverage that evaluates embedded rollback checks with synthetic JSON and
path lists; it performs no Git mutation.
