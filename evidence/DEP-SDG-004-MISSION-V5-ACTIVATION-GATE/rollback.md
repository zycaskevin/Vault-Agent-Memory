# Rollback

## Trigger

Any authority expansion, unexpected path/action/mode acceptance, failed full
gate, or inability to create a fresh post-merge proposal.

## Reversible steps

rollback_version: 1.0
target: immutable mergeCommit.oid of Pull Request 478 from agent/sdg004-mission-v5-activation-gate in zycaskevin/Vault-Agent-Memory
command: merge_oid="$(gh pr view 478 --repo zycaskevin/Vault-Agent-Memory --json state,headRefName,mergeCommit --jq 'select(.state == "MERGED" and .headRefName == "agent/sdg004-mission-v5-activation-gate" and .mergeCommit.oid != null) | .mergeCommit.oid')" && test -n "$merge_oid" && test "$(git rev-list --parents -n 1 "$merge_oid" | awk '{print NF - 1}')" = 2 && git revert --no-edit -m 1 "$merge_oid"
verify: python scripts/validate_subject_task_authorization_dispatch_v5.py --ledger --json

Resolve the immutable merge commit from the GitHub Pull Request readback before
running the command. Roll back only before a new Mission V5 proof is published.
After activation, use the mission revocation/BLOCKED protocol and never rewrite
authority history.

## Data compatibility

No product or data format changes. Before activation, rollback restores the
inactive sequence-6 state.

## Post-rollback verification

Run the inactive V5 dispatcher, focused Mission V5 tests, `sddgov doctor .`,
`sddgov ci verify .`, and `git diff --check`.
