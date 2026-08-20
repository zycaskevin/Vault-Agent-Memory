# Rollback

## Trigger

Any proof-byte drift, premature activation, activation topology drift,
review/gate mismatch, verification failure, or post-merge replay failure.

## Reversible steps

rollback_version: 1.0
target: the one merged Pull Request from agent/mission-v5-activation-post-sdg012 in the current GitHub repository
command: repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)" && test "$repo" = "zycaskevin/Vault-Agent-Memory" && test "$(git remote get-url origin)" = "https://github.com/zycaskevin/Vault-Agent-Memory.git" && test "$(git remote get-url --push origin)" = "https://github.com/zycaskevin/Vault-Agent-Memory.git" && test "$(git branch --show-current)" = "main" && test -z "$(git status --porcelain=v1 --untracked-files=all)" && git fetch --prune --no-tags origin +refs/heads/main:refs/remotes/origin/main && test "$(git rev-parse HEAD)" = "$(git rev-parse refs/remotes/origin/main)" && branch="agent/mission-v5-activation-post-sdg012" && merge_commit="$(gh pr list --repo "$repo" --head "$branch" --state merged --json state,headRefName,baseRefName,mergeCommit --limit 100 | python -c 'import json,sys; rows=json.load(sys.stdin); rows=[row for row in rows if row.get("state")=="MERGED" and row.get("baseRefName")=="main" and row.get("headRefName")=="agent/mission-v5-activation-post-sdg012"]; assert len(rows)==1; merge=(rows[0].get("mergeCommit") or {}).get("oid"); assert isinstance(merge,str) and len(merge)==40; print(merge)')" && test "$(git rev-parse HEAD)" = "$merge_commit" && test "$(git rev-parse refs/remotes/origin/main)" = "$merge_commit" && test "$(git rev-list --parents -n 1 "$merge_commit" | awk '{print NF}')" = "3" && test "$(git rev-parse "$merge_commit^1")" = "327ebe1b557fc30cbc5482a1de87e1757b8873da" && test "$(git rev-parse "$merge_commit^{tree}")" = "$(git rev-parse "$merge_commit^2^{tree}")" && test -f specs/subject-distillation/task-authorizations/MISSION-V5-T004-T033.json && test ! -e specs/subject-distillation/.implementation-progress.pending && python -c 'import json,pathlib; value=json.loads(pathlib.Path("specs/subject-distillation/implementation-progress.json").read_text()); assert sorted(event["sequence"] for event in value["events"])==list(range(1,7)); assert all(value["tasks"].get(f"T-{index:03d}")=="PENDING" for index in range(4,34))' && git revert --no-edit -m 1 "$merge_commit"
verify: test "$(git branch --show-current)" = "main" && test "$(git rev-parse HEAD^)" = "$(git rev-parse refs/remotes/origin/main)" && python scripts/validate_subject_task_authorization_dispatch_v5.py --ledger --json | python -c 'import json,sys; value=json.load(sys.stdin); assert value == {"active":False,"mission_id":None,"mission_state":"INACTIVE","protocol_version":5,"sequence":6,"status":"PASS"}' && python -c 'import json,pathlib; value=json.loads(pathlib.Path("specs/subject-distillation/implementation-progress.json").read_text()); assert sorted(event["sequence"] for event in value.get("events",[]))==list(range(1,7)); assert all(value.get("tasks",{}).get(f"T-{index:03d}")=="PENDING" for index in range(4,34))' && test ! -e specs/subject-distillation/task-authorizations/MISSION-V5-T004-T033.json && test ! -e specs/subject-distillation/.implementation-progress.pending && test -z "$(git status --porcelain=v1 --untracked-files=all)" && git diff --check

Resolve exactly one merged source-branch PR only from a clean canonical `main`
that equals freshly fetched `origin/main` and the resolved merge commit. Require
exactly two ordered parents, the exact protocol base as first parent,
topic-tree equality, the proof still present, and every T004-T033 task still
`PENDING`; only then append a first-parent revert. Never rewrite history or
reuse the reverted proof.

Use only before any Mission task starts. After task start, use governed Mission
revocation and fresh authority rather than blind revert.
