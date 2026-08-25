# Rollback

rollback_version: 3.0
target: exact VAM-002 final 14-item CodeRabbit implementation commit
rollback_action: git_revert
rollback_ref: 9308751b8616e5cccd51f2f1d0c00ca35f01b558
reconcile_action: setup_agent_from_reverted_source
reconcile_agent: codex
reconcile_profile: team-standard
verify_action: doctor_and_python_module
verify_module: unittest

## Trigger

Rollback before merge only if the new fail-closed label handling denies a
documented valid canonical row, PATCH/DELETE valid requests regress, or the
authoritative rollback/disposition tests become false.

## Reversible steps

At exact implementation head, prepare only an uncommitted local revert:

```bash
set -euo pipefail
test "$(git rev-parse HEAD)" = 9308751b8616e5cccd51f2f1d0c00ca35f01b558
test -z "$(git status --porcelain=v1 --untracked-files=all)"
git revert --no-commit 9308751b8616e5cccd51f2f1d0c00ca35f01b558
git diff --cached --check
git diff --cached --name-only -z | python -c 'import sys; actual=set(filter(None,sys.stdin.buffer.read().decode().split("\0"))); expected=set("""DEP-VAM-002-BUILDER-LOCAL-GREEN-PATH/regression-evidence.md
DEP-VAM-002-BUILDER-LOCAL-GREEN-PATH/verification.md
DEP-VAM-002-CODERABBIT-FINAL-REMEDIATION/verification.md
DEP-VAM-002-CODERABBIT-REPLACEMENT-REVIEW-REMEDIATION/rollback.md
DEP-VAM-002-FULL-SUITE-COMPATIBILITY/reproduction.md
DEP-VAM-002-FULL-SUITE-COMPATIBILITY/rollback.md
DEP-VAM-002-INDEPENDENT-REVIEW-REMEDIATION/reproduction.md
DEP-VAM-002-INDEPENDENT-REVIEW-REMEDIATION/verification.md
DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md
docs/decision_records/2026-08-21-memory-change-envelope.md
docs/specs/vam-002-memory-change-envelope.md
evidence/DEP-VAM-002-CODERABBIT-REMEDIATION/verification.md
evidence/DEP-VAM-002-CODERABBIT-THREAD-CLOSURE/verification.md
tests/test_access_policy.py
tests/test_gateway.py
tests/test_memory_change_envelope.py
tests/test_vault_boundary_freeze.py
vault/access_policy.py
vault/gateway.py
vault/gateway_openapi.py
vault/governance_read_guard.py
vault/memory_change_envelope.py
vault/memory_provider.py""".splitlines()); raise SystemExit(0 if actual == expected else 1)'
test -z "$(git status --ignored=matching --porcelain=v1 | awk 'substr($0,1,2) == "??" || substr($0,1,2) == "!!" { print }')"
```

On any successor head or after merge, do not revert this component alone. Use
only `DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md` with its fresh exact
approval and preserve this DEP.

## Data compatibility

No schema or stored-data migration exists. Rollback restores the former
interpretation of malformed stored labels and HTTP error status, so it is only
appropriate to diagnose a verified regression before merge.

## Post-rollback verification

Require the expected RED for the new three-node boundary, Green pre-existing
valid-row and valid-caller behavior, exact staged/untracked allowlists, Ruff,
module-size, Doctor, CI verify, `git diff --check`, and repository Local Green.
