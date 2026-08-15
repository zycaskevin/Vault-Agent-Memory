# Rollback

rollback_version: 1.0
target: immutable GitHub mergeCommit.oid for zycaskevin/Vault-Agent-Memory PR 476
command: git revert --no-edit -m 1 "$(gh pr view 476 --repo zycaskevin/Vault-Agent-Memory --json mergeCommit --jq .mergeCommit.oid)"
verify: python scripts/readme_command_smoke.py

## Trigger

Rollback if the exact compatibility merge causes a required hosted-CI
regression, accepts a non-closed ancestry/path/mode topology, or cannot emit a
fresh proposal from its exact merged main.

## Reversible steps

Verify that PR #476 is merged and that GitHub reports its exact two-parent
`mergeCommit.oid`, then run the machine command above. The command resolves that
immutable PR merge commit rather than a moving branch or `HEAD`; it remains
correct if main has advanced. Do not rewrite history.

## Data compatibility

No data is created or transformed. The rollback removes only the inactive
compatibility trust-root change and its public governance evidence. Mission V5
remains inactive and the sequence-6 ledger remains byte-identical.

## Post-rollback verification

Run the README documented-command smoke, the pinned V5 dispatcher, SDG doctor,
CI Cost Guard verification, and `git diff --check`. Confirm the V5 proof is
absent and T-004 remains PENDING.
