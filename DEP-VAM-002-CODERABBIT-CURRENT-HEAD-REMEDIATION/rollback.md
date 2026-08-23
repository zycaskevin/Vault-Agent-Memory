# Rollback

## Trigger

Rollback if the policy SQL differs from `can_read_memory`, cursor ordering or
privacy changes, blank ceilings no longer default to low, selected hydration
widens, or the full repository gate regresses.

## Reversible steps

Revert immutable implementation commit
`cbbf2d1c174e432313654e0260450af37a766f71` without committing, then restore
all VAM-002 DEP/evidence paths from current HEAD so the audit trail remains.
The staged result may contain only the three public contract documents, the two
focused test files, and `vault/gateway_memory_api.py` plus
`vault/memory_provider.py`. Abort if any other path is staged or any untracked
path appears.

```bash
set -euo pipefail
test -z "$(git status --porcelain=v1 --untracked-files=all)"
git revert --no-commit cbbf2d1c174e432313654e0260450af37a766f71
git restore --source=HEAD --staged --worktree -- \
  DEP-VAM-002-BUILDER-LOCAL-GREEN-PATH \
  DEP-VAM-002-CODERABBIT-CURRENT-HEAD-REMEDIATION \
  DEP-VAM-002-FULL-SUITE-COMPATIBILITY \
  evidence/DEP-VAM-002-CODERABBIT-REMEDIATION \
  evidence/DEP-VAM-002-MEMORY-CHANGE-ENVELOPE
git diff --cached --name-only -z | python -c 'import sys; actual=set(filter(None,sys.stdin.buffer.read().decode().split("\0"))); expected=set("""docs/decision_records/2026-08-21-memory-change-envelope.md
docs/specs/vam-002-memory-change-envelope.md
docs/specs/vault_memory_api.md
tests/test_gateway.py
tests/test_memory_change_envelope.py
vault/gateway_memory_api.py
vault/memory_provider.py""".splitlines()); raise SystemExit(0 if actual == expected else 1)'
test -z "$(git status --porcelain=v1 --untracked-files=all | awk 'substr($0,1,2) == "??" { print }')"
```

## Data compatibility

No table, migration, stored row, candidate, audit event, cursor version, or
live data is changed. Rollback is code/test/document only.

## Post-rollback verification

Run `git revert --no-commit cbbf2d1c174e432313654e0260450af37a766f71`,
restore the VAM-002 DEP/evidence paths, and mechanically compare
`git diff --cached --name-only` with the exact seven behavior paths described
above. The exact targeted command from `reproduction.md` is the expected RED
probe: after rollback it must reproduce its documented failures and is
therefore expected to exit nonzero; it is not a Green acceptance command.

Separately run these rollback-safe Green commands:

```bash
env PYTHONPATH=. "$VAULT_TEST_PYTHON" -m pytest -q \
  tests/test_gateway.py::test_memory_api_all_read_facades_reject_invalid_sensitivity_before_dispatch
"$RUFF" check \
  tests/test_gateway.py \
  tests/test_memory_change_envelope.py \
  vault/gateway_memory_api.py \
  vault/memory_provider.py
git diff --check
sddgov evidence verify DEP-VAM-002-CODERABBIT-CURRENT-HEAD-REMEDIATION --strict
sddgov ci local-gate .
```

Every Green command must exit zero at the rollback candidate; only commands in
this separate Green set are Green acceptance commands.
