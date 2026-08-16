# Rollback

## Trigger

Any candidate authority regression, active replay regression, missing/duplicate
dispatcher node, count drift, CI pin drift, or required verification failure.

## Reversible steps

rollback_version: 1.0
target: the one merged Pull Request from agent/sdg012-mission-v5-dispatch-phase-isolation in the current GitHub repository
command: repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)" && branch="agent/sdg012-mission-v5-dispatch-phase-isolation" && merge_commit="$(gh pr list --repo "$repo" --head "$branch" --state merged --json state,headRefName,baseRefName,mergeCommit --limit 100 | python -c 'import json,sys; rows=json.load(sys.stdin); rows=[row for row in rows if row.get("state")=="MERGED" and row.get("baseRefName")=="main" and row.get("headRefName")=="agent/sdg012-mission-v5-dispatch-phase-isolation"]; assert len(rows)==1, "expected one exact merged PR"; merge=(rows[0].get("mergeCommit") or {}).get("oid"); assert isinstance(merge,str) and len(merge)==40, "expected mergeCommit"; print(merge)')" && git merge-base --is-ancestor "$merge_commit" HEAD && test "$(git rev-parse "$merge_commit^1")" = "9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0" && test "$(git rev-parse "$merge_commit^{tree}")" = "$(git rev-parse "$merge_commit^2^{tree}")" && git revert --no-edit -m 1 "$merge_commit"
verify: SUBJECT_MISSION_V5_PHASE=candidate python -m pytest -q tests/test_subject_task_authorization_dispatch_v5.py && git diff --check

Resolve one exact merged branch PR, require exact first parent and topic-tree
equality, then append a first-parent revert. Never rewrite history.

Use only before any proposal/proof is bound to the SDG-012 release. After that,
regenerate authority through the governed protocol instead of blind revert.
