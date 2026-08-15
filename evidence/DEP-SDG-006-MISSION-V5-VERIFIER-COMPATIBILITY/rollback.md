# Rollback

rollback_version: 1.0
target: SDG-006 GitHub merge commit resolved from the exact agent/sdg006-mission-v5-verifier-compatibility PR branch and mergeCommit oid
command: git revert --no-edit -m 1 "$(gh pr view agent/sdg006-mission-v5-verifier-compatibility --repo zycaskevin/Vault-Agent-Memory --json mergeCommit --jq .mergeCommit.oid)"
verify: python scripts/readme_command_smoke.py

Trigger rollback if any hostile private-file or external-directory replacement
is accepted, the exact release closure admits an extra path/history action, or
a required gate fails after merge.

The change writes no product or private data and performs no migration. Revert
the exact two-parent GitHub merge commit; do not rewrite completed Subject
history. After rollback, run the README smoke and the current Subject
validators. Mission activation remains blocked until a corrected compatibility
release is merged and a fresh proposal is confirmed.
