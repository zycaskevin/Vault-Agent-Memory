# Rollback

## Trigger

Any candidate-route bypass, active validation without one exact two-parent merge,
collection drift, protected-review failure, or Local Green/hosted failure.

## Reversible steps

rollback_version: 1.0
target: the one merged Pull Request from agent/sdg010-mission-v5-ci-phase-routing in the current GitHub repository
command: repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)" && branch="agent/sdg010-mission-v5-ci-phase-routing" && merge_commit="$(gh pr list --repo "$repo" --head "$branch" --state merged --json state,headRefName,mergeCommit --limit 100 | python -c 'import json,sys; rows=json.load(sys.stdin); rows=[row for row in rows if row.get("state")=="MERGED" and row.get("headRefName")=="agent/sdg010-mission-v5-ci-phase-routing"]; assert len(rows)==1, "expected one exact merged PR"; merge=(rows[0].get("mergeCommit") or {}).get("oid"); assert isinstance(merge,str) and len(merge)==40, "expected mergeCommit"; print(merge)')" && git merge-base --is-ancestor "$merge_commit" HEAD && test "$(git rev-list --parents -n 1 "$merge_commit" | awk '{print NF - 1}')" = 2 && git revert --no-edit -m 1 "$merge_commit"
verify: python scripts/validate_subject_task_authorization_dispatch_v5.py --ledger --json | python -c 'import json,sys; value=json.load(sys.stdin); assert value == {"active":False,"mission_id":None,"mission_state":"INACTIVE","protocol_version":5,"sequence":6,"status":"PASS"}' && python -c 'import json,pathlib; value=json.loads(pathlib.Path("specs/subject-distillation/implementation-progress.json").read_text()); assert value["tasks"]["T-004"] == "PENDING"' && test ! -e specs/subject-distillation/.implementation-progress.pending && git diff --check

Resolve exactly one merged Pull Request from the fixed source branch and
require its immutable two-parent merge commit before appending a revert. Do not
rewrite history or reuse Mission proposals/proofs bound to the reverted
protocol base.

Run this revert only before Mission V5 activation. After activation, do not
blindly revert: use the governed mission revocation procedure and obtain fresh
authority for any follow-on state change.
