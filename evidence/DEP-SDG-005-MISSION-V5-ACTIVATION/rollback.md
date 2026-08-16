# Rollback

## Trigger

Any proof-byte drift, premature activation, activation-path/topology drift,
review/gate mismatch, verification failure, or post-merge replay failure.

## Reversible steps

rollback_version: 1.0
target: the one merged Pull Request from agent/mission-v5-activation-post-sdg011 in the current GitHub repository
command: repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)" && branch="agent/mission-v5-activation-post-sdg011" && merge_commit="$(gh pr list --repo "$repo" --head "$branch" --state merged --json state,headRefName,baseRefName,mergeCommit --limit 100 | python -c 'import json,sys; rows=json.load(sys.stdin); rows=[row for row in rows if row.get("state")=="MERGED" and row.get("baseRefName")=="main" and row.get("headRefName")=="agent/mission-v5-activation-post-sdg011"]; assert len(rows)==1, "expected one exact merged PR"; merge=(rows[0].get("mergeCommit") or {}).get("oid"); assert isinstance(merge,str) and len(merge)==40, "expected mergeCommit"; print(merge)')" && git merge-base --is-ancestor "$merge_commit" HEAD && test "$(git rev-parse "$merge_commit^1")" = "9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0" && test "$(git rev-parse "$merge_commit^{tree}")" = "$(git rev-parse "$merge_commit^2^{tree}")" && git revert --no-edit -m 1 "$merge_commit"
verify: python scripts/validate_subject_task_authorization_dispatch_v5.py --ledger --json | python -c 'import json,sys; value=json.load(sys.stdin); assert value == {"active":False,"mission_id":None,"mission_state":"INACTIVE","protocol_version":5,"sequence":6,"status":"PASS"}' && python -c 'import json,pathlib; value=json.loads(pathlib.Path("specs/subject-distillation/implementation-progress.json").read_text()); assert value["tasks"]["T-004"] == "PENDING"' && test ! -e specs/subject-distillation/.implementation-progress.pending && git diff --check

Resolve exactly one merged source-branch PR, require the exact protocol base as
first parent and topic-tree equality, then append a first-parent revert. Never
rewrite history or reuse the reverted proof.

Use this rollback only before any Mission task starts. After task start, use
the governed Mission revocation path and fresh authority instead of blind
revert.
