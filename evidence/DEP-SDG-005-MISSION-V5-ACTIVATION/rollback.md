# Rollback

## Trigger

Any proof-byte drift, premature activation, activation topology drift,
review/gate mismatch, verification failure, or post-merge replay failure.

## Reversible steps

rollback_version: 1.0
target: the one merged Pull Request from agent/mission-v5-activation-post-sdg012 in the current GitHub repository
command: repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)" && branch="agent/mission-v5-activation-post-sdg012" && merge_commit="$(gh pr list --repo "$repo" --head "$branch" --state merged --json state,headRefName,baseRefName,mergeCommit --limit 100 | python -c 'import json,sys; rows=json.load(sys.stdin); rows=[row for row in rows if row.get("state")=="MERGED" and row.get("baseRefName")=="main" and row.get("headRefName")=="agent/mission-v5-activation-post-sdg012"]; assert len(rows)==1; merge=(rows[0].get("mergeCommit") or {}).get("oid"); assert isinstance(merge,str) and len(merge)==40; print(merge)')" && git merge-base --is-ancestor "$merge_commit" HEAD && test "$(git rev-parse "$merge_commit^1")" = "327ebe1b557fc30cbc5482a1de87e1757b8873da" && test "$(git rev-parse "$merge_commit^{tree}")" = "$(git rev-parse "$merge_commit^2^{tree}")" && git revert --no-edit -m 1 "$merge_commit"
verify: python scripts/validate_subject_task_authorization_dispatch_v5.py --ledger --json | python -c 'import json,sys; value=json.load(sys.stdin); assert value == {"active":False,"mission_id":None,"mission_state":"INACTIVE","protocol_version":5,"sequence":6,"status":"PASS"}' && python -c 'import json,pathlib; value=json.loads(pathlib.Path("specs/subject-distillation/implementation-progress.json").read_text()); assert value["tasks"]["T-004"] == "PENDING"' && test ! -e specs/subject-distillation/.implementation-progress.pending && git diff --check

Resolve exactly one merged source-branch PR, require the exact protocol base as
first parent and topic-tree equality, then append a first-parent revert. Never
rewrite history or reuse the reverted proof.

Use only before any Mission task starts. After task start, use governed Mission
revocation and fresh authority rather than blind revert.
