# Rollback

rollback_version: 1.0
target: implementation commit 51ba82b33c76b7d2fbda35ef00e3b0f7e373ec81 and its direct audit-only child b2c8378db44079080d1d9bbd418febf93e527ec9
command: test -n "$VAM001_LOCAL_TARGET_ROLLBACK_DEP" && test -n "$VAM001_LOCAL_TARGET_ROLLBACK_REQUEST" && sddgov evidence verify "$VAM001_LOCAL_TARGET_ROLLBACK_DEP" --strict && test "$(git rev-parse HEAD)" = b2c8378db44079080d1d9bbd418febf93e527ec9 && test "$(git rev-parse b2c8378db44079080d1d9bbd418febf93e527ec9^)" = 51ba82b33c76b7d2fbda35ef00e3b0f7e373ec81 && approval_json="$(sddgov autonomy evaluate "$VAM001_LOCAL_TARGET_ROLLBACK_REQUEST" --path .)" && printf '%s\n' "$approval_json" | python -c 'import json,sys; value=json.load(sys.stdin); assert value.get("state")=="CONTINUE" and value.get("approval_consumed") is True' && git revert --no-commit b2c8378db44079080d1d9bbd418febf93e527ec9 && git revert --no-commit 51ba82b33c76b7d2fbda35ef00e3b0f7e373ec81
verify: python -m pytest -q tests/test_subject_extraction_boundary_docs.py && sddgov evidence verify "$VAM001_LOCAL_TARGET_ROLLBACK_DEP" --strict && git diff --check

## Trigger

The new local branch/head guard rejects a documented valid post-merge checkout
or the regression assertion fails on unchanged approved wording.

## Reversible steps

Only if the immutable selector above matches, prepare reversals in strict reverse
order: audit-only gate `b2c8378` first, implementation `51ba82b` second. Any
advanced head, different parent, changed identity, or changed order fails closed
and requires a new compensating-change DEP instead. Keep PR #498 blocked until
another independently reviewed guard exists.

## Data compatibility

No runtime, schema, database, or stored-memory change exists.

## Post-rollback verification

Run the focused VAM-001 documentation tests, all strict VAM-001 DEPs, complete
Local Green, and independent review against the replacement exact head.
