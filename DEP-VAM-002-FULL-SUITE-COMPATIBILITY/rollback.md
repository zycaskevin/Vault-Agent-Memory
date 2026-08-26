# Rollback

rollback_version: 3.0
target: exact historical VAM-002 full-suite compatibility implementation commit
rollback_action: git_revert
rollback_ref: 1a346913563f5437b7815f655393f0eee5a0da52
reconcile_action: setup_agent_from_reverted_source
reconcile_agent: codex
reconcile_profile: team-standard
verify_action: doctor_and_python_module
verify_module: unittest

## Trigger

Rollback the compatibility fix if malformed-label reads become allowed, known
authorization diagnostics change, or the HTTP regression no longer proves
candidate-first requests leave active knowledge unchanged.

## Reversible steps

At exact historical head `1a346913563f5437b7815f655393f0eee5a0da52`, a
local uncommitted preparation is reproducible with:

```bash
set -euo pipefail
test "$(git rev-parse HEAD)" = 1a346913563f5437b7815f655393f0eee5a0da52
test -z "$(git status --porcelain=v1 --untracked-files=all)"
git revert --no-commit 1a346913563f5437b7815f655393f0eee5a0da52
test -z "$(git status --porcelain=v1 --untracked-files=all | awk 'substr($0,1,2) == "??" { print }')"
git diff --check
```

Do not apply that isolated historical revert to a successor head. On the
current branch or after merge, use only the exact guarded PR procedure in
`DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md`, which preserves all
VAM-002 evidence and does not touch VAM-001/VAM-003 history.

## Data compatibility

No schema or stored data changes are introduced. The reason-code adjustment is
response diagnostic cleanup for an already-denied malformed row.

## Post-rollback verification

At the historical head, run these two named regressions before the revert:

```bash
env PYTHONPATH=. "$VAULT_TEST_PYTHON" -m pytest -q \
  tests/test_memory_foundation_compare.py::test_strict_guard_fails_closed_for_unknown_scope_and_sensitivity \
  tests/test_gateway.py::test_memory_change_http_errors_use_non_success_status_and_openapi_contract \
  tests/test_gateway.py::test_gateway_memory_api_facade_is_candidate_first_and_metadata_only
```

They must pass at the historical head. After preparing the revert, run the
same three nodes again; they must still pass, together with `git diff --cached
--check` and repository governance verification. Confirm the staged path set
matches the historical commit and no untracked or ignored rollback artifact
remains.
