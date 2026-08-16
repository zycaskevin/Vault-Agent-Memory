# Rollback

## Trigger

Any collection mismatch, missing/duplicate node, hidden release path/history,
authorization acceptance change, Local Green failure, or hosted gate failure.

## Reversible steps

rollback_version: 1.0
target: SDG-007 GitHub merge commit resolved from agent/sdg007-mission-v5-local-green-isolation in zycaskevin/Vault-Agent-Memory
command: git revert --no-edit -m 1 "$(gh pr view agent/sdg007-mission-v5-local-green-isolation --repo zycaskevin/Vault-Agent-Memory --json state,headRefName,mergeCommit --jq 'select(.state == "MERGED" and .headRefName == "agent/sdg007-mission-v5-local-green-isolation" and .mergeCommit.oid != null) | .mergeCommit.oid')"
verify: python scripts/readme_command_smoke.py

Resolve exactly one merged Pull Request for the fixed repository and head
branch, require its immutable two-parent merge commit, and append a revert. Do
not rewrite history or reuse any Mission proposal created on the reverted base.

## Data compatibility

No product data or schema changes. Revert restores the previous Local Green
routing and invalidates any proposal bound to the hotfix base.

## Post-rollback verification

Run README smoke, doctor, CI Cost Guard, the prior 301-node harness, Mission V5
dispatcher in inactive sequence-6 state, and `git diff --check`.
