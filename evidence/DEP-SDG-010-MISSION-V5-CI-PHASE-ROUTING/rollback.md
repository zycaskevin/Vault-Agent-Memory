# Rollback

## Trigger

Any candidate-route bypass, active validation without one exact two-parent merge,
collection drift, protected-review failure, or Local Green/hosted failure.

## Reversible steps

rollback_version: 1.0
target: exact merged Pull Request #484 from agent/sdg010-mission-v5-ci-phase-routing-v4 into main in the current GitHub repository
command: repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)" && merge_commit="$(gh pr view 484 --repo "$repo" --json state,baseRefName,baseRefOid,headRefName,headRefOid,mergeCommit | python -c 'import json,sys; row=json.load(sys.stdin); assert row.get("state")=="MERGED", "expected PR 484 merged"; assert row.get("baseRefName")=="main", "expected main base"; assert row.get("baseRefOid")=="46690372e532c50761f9232ff5b2e20e18779d28", "expected exact base oid"; assert row.get("headRefName")=="agent/sdg010-mission-v5-ci-phase-routing-v4", "expected exact head"; assert row.get("headRefOid")=="7e155ca8907b31a14d5abadeeeb73e3edac71c14", "expected exact head oid"; merge=(row.get("mergeCommit") or {}).get("oid"); assert merge=="efa43a4dfb305cd51d8a57a20838be6123ccb514", "expected exact mergeCommit"; print(merge)')" && git merge-base --is-ancestor "$merge_commit" HEAD && test "$(git rev-list --parents -n 1 "$merge_commit")" = "efa43a4dfb305cd51d8a57a20838be6123ccb514 46690372e532c50761f9232ff5b2e20e18779d28 7e155ca8907b31a14d5abadeeeb73e3edac71c14" && test "$(git rev-parse "$merge_commit^{tree}")" = "$(git rev-parse 7e155ca8907b31a14d5abadeeeb73e3edac71c14^{tree})" && git revert --no-edit -m 1 "$merge_commit"
verify: python scripts/validate_subject_task_authorization_dispatch_v5.py --ledger --json | python -c 'import json,sys; value=json.load(sys.stdin); assert value == {"active":False,"mission_id":None,"mission_state":"INACTIVE","protocol_version":5,"sequence":6,"status":"PASS"}' && python -c 'import json,pathlib; value=json.loads(pathlib.Path("specs/subject-distillation/implementation-progress.json").read_text()); assert value["tasks"]["T-004"] == "PENDING"' && test ! -e specs/subject-distillation/.implementation-progress.pending && git diff --check

Resolve exact PR #484, require its state, main/base oid, actual v4 source
branch/head oid, exact immutable two-parent merge commit, parent order, and
topic-tree equality before appending a revert. Do not rewrite history or reuse
Mission proposals/proofs bound to the reverted protocol base.

Run this revert only before Mission V5 activation. After activation, do not
blindly revert: use the governed mission revocation procedure and obtain fresh
authority for any follow-on state change.
