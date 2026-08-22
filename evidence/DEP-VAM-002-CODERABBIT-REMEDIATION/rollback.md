# Rollback

## Trigger

Rollback if numeric legacy reads regress, policy filtering leaks a hidden row,
cursor behavior changes, content/audits are hydrated beyond selected readable
rows, or the 80-line ceiling is weakened.

## Reversible steps

An explicitly approved operator may revert only VAM-002 follow-up commit
`a3be45e272f126a96d519cffc6ea59027055a3e5`, then review-fix commit
`5dd09ef8e2c15800fc8ff750afb51a5e542feb2e` if the original review remediation
must also be removed. Keep the earlier Draft PR isolated; do not alter tables,
data rows, reviewer metadata, releases, or deployments.

## Data compatibility

No schema or stored-data change is planned. Opaque identifiers remain API
strings; the SQLite adapter continues to decode its current decimal format.

## Post-rollback verification

Run these exact checks from the rollback candidate:

```bash
python -m pytest -q tests/test_memory_change_envelope.py tests/test_memory_provider.py
python -m pytest -q tests/test_gateway.py -k 'memory_changes or revision_bound or openapi_contract'
ruff check vault/memory_change_envelope.py vault/memory_provider.py vault/gateway_memory_api.py vault/gateway_openapi.py tests/test_memory_change_envelope.py
sddgov evidence verify evidence/DEP-VAM-002-MEMORY-CHANGE-ENVELOPE --strict
sddgov evidence verify evidence/DEP-VAM-002-CODERABBIT-REMEDIATION --strict
sddgov ci local-gate .
```

Every command must exit 0; the focused tests must preserve opaque ids, bounded
policy scanning, revision-bound reads, and OpenAPI assertions.
