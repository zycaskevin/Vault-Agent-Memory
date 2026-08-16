# Rollback

## Trigger

Any regression that accepts a non-exact SDG-010 anchor, accepts current
`efa43a4` as the new proposal base, accepts an SDG-011 scope/topology drift, or
fails required local, independent, hosted, or merge-readback verification.

## Reversible steps

rollback_version: 1.0
target: the one merged Pull Request from agent/sdg011-post-sdg010-l1-compatibility in the current GitHub repository
command: repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)" && branch="agent/sdg011-post-sdg010-l1-compatibility" && merge_commit="$(gh pr list --repo "$repo" --head "$branch" --state merged --json state,headRefName,baseRefName,mergeCommit --limit 100 | python -c 'import json,sys; rows=json.load(sys.stdin); rows=[row for row in rows if row.get("state")=="MERGED" and row.get("baseRefName")=="main" and row.get("headRefName")=="agent/sdg011-post-sdg010-l1-compatibility"]; assert len(rows)==1, "expected one exact merged PR"; merge=(rows[0].get("mergeCommit") or {}).get("oid"); assert isinstance(merge,str) and len(merge)==40, "expected mergeCommit"; print(merge)')" && git merge-base --is-ancestor "$merge_commit" HEAD && test "$(git rev-parse "$merge_commit^1")" = "efa43a4dfb305cd51d8a57a20838be6123ccb514" && test "$(git rev-parse "$merge_commit^{tree}")" = "$(git rev-parse "$merge_commit^2^{tree}")" && git revert --no-edit -m 1 "$merge_commit"
verify: python scripts/validate_subject_task_authorization_dispatch_v5.py --ledger --json | python -c 'import json,sys; value=json.load(sys.stdin); assert value == {"active":False,"mission_id":None,"mission_state":"INACTIVE","protocol_version":5,"sequence":6,"status":"PASS"}' && python -c 'import json,pathlib; value=json.loads(pathlib.Path("specs/subject-distillation/implementation-progress.json").read_text()); assert value["tasks"]["T-004"] == "PENDING"' && test ! -e specs/subject-distillation/.implementation-progress.pending && git diff --check

Resolve exactly one merged source-branch PR, require exact SDG-010 as first
parent and topic-tree equality, then append a first-parent revert. Never
rewrite history or reuse a proposal/proof bound to the reverted release.

Run only before Mission V5 activation. After activation, use governed mission
revocation and fresh authority instead of a blind compatibility revert.
