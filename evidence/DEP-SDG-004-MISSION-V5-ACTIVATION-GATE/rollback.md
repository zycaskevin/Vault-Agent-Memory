# Rollback

## Trigger

Any authority expansion, unexpected path/action/mode acceptance, failed full
gate, or inability to create a fresh post-merge proposal.

## Reversible steps

rollback_version: 1.0
target: immutable mergeCommit.oid of the unique merged Pull Request from agent/sdg004-mission-v5-activation-gate in zycaskevin/Vault-Agent-Memory
command: test "$(gh pr list --repo zycaskevin/Vault-Agent-Memory --state merged --head agent/sdg004-mission-v5-activation-gate --limit 2 --json number --jq length)" = 1 && git revert --no-edit -m 1 "$(gh pr list --repo zycaskevin/Vault-Agent-Memory --state merged --head agent/sdg004-mission-v5-activation-gate --limit 2 --json mergeCommit --jq '.[0].mergeCommit.oid')"
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
