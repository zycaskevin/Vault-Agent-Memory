# Rollback

## Trigger

Any authority expansion, unexpected path/action/mode, protected-review or
hosted gate failure, non-exact merge topology, post-merge readback failure, or
attempt to start T-004 before ACTIVE validation.

## Reversible steps

rollback_version: 1.0
target: open SDG-005 Pull Request from agent/mission-v5-activation-post-sdg008 in zycaskevin/Vault-Agent-Memory before activation merge
command: test "$(gh pr view agent/mission-v5-activation-post-sdg008 --repo zycaskevin/Vault-Agent-Memory --json state,headRefName,mergeCommit --jq 'select(.state == "OPEN" and .headRefName == "agent/mission-v5-activation-post-sdg008" and .mergeCommit == null) | .headRefName')" = "agent/mission-v5-activation-post-sdg008" && gh pr close agent/mission-v5-activation-post-sdg008 --repo zycaskevin/Vault-Agent-Memory
verify: test "$(gh pr view agent/mission-v5-activation-post-sdg008 --repo zycaskevin/Vault-Agent-Memory --json state,headRefName,mergeCommit --jq 'select(.state == "CLOSED" and .headRefName == "agent/mission-v5-activation-post-sdg008" and .mergeCommit == null) | .headRefName')" = "agent/mission-v5-activation-post-sdg008" && verify_root="$(mktemp -d /tmp/vault-sdg005-rollback-XXXXXX)" && trap 'rm -rf "$verify_root"' EXIT && git clone --no-local --quiet . "$verify_root/repo" && git -C "$verify_root/repo" remote set-url origin https://github.com/zycaskevin/Vault-Agent-Memory.git && git -C "$verify_root/repo" -c advice.detachedHead=false checkout --detach 46690372e532c50761f9232ff5b2e20e18779d28 && test -z "$(git -C "$verify_root/repo" status --porcelain)" && (cd "$verify_root/repo" && python3 -c 'import json,pathlib,subprocess; p=subprocess.run(["python3","scripts/validate_subject_task_authorization_dispatch_v5.py","--ledger","--json"],capture_output=True,text=True); assert p.returncode == 0 and p.stderr == ""; value=json.loads(p.stdout); assert value == {"active":False,"mission_id":None,"mission_state":"INACTIVE","protocol_version":5,"sequence":6,"status":"PASS"}; ledger=json.loads(pathlib.Path("specs/subject-distillation/implementation-progress.json").read_text()); assert len(ledger["events"]) == 6 and ledger["tasks"]["T-004"] == "PENDING"; assert all(not pathlib.Path(item).exists() for item in ("specs/subject-distillation/.task-authorization.pending","specs/subject-distillation/.implementation-progress.pending","specs/subject-distillation/.development-mission-v5-revocation.pending"))')

Before merge, close the exact activation Pull Request and do not publish any
task proof. After the activation merge, do not delete the Mission proof or
rewrite authority history: use the owner-delivered V5 revocation packet and
`update_subject_task_progress_v5.py revoke`, then deliver the required BLOCKED
event if a task is active.

## Data compatibility

No product data or schema changes. Pre-merge rollback leaves the immutable
sequence-6 state. Post-merge revocation preserves completed history and blocks
new authority without deleting the activation proof.

## Post-rollback verification

Confirm the Pull Request is closed and unmerged, Mission V5 remains INACTIVE,
T-004 remains PENDING, both pending paths are absent, and run doctor, CI Cost
Guard, the V5 dispatcher, and `git diff --check`. For post-merge revocation,
require dispatcher state `REVOKED` with history valid and all new starts DENY.
