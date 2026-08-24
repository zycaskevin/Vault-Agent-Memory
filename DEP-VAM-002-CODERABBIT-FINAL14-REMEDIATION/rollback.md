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
git diff --check
test -z "$(git status --porcelain=v1 --untracked-files=all | awk 'substr($0,1,2) == "??" { print }')"
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
