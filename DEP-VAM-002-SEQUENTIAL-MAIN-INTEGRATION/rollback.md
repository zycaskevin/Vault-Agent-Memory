# Rollback

rollback_version: 1.0
target: exact behavioral and public-contract delta merged by Pull Request 500; preserve all VAM-002 evidence, review, issue, Work Package, and governance provenance
command: Run the guarded preparation command below from the exact `PR #500` merge commit after preparing a new strict rollback DEP and fresh exact L3 approval.
verify: Run every post-rollback verification below and record approval consumption, staged allowlist, and Green results in the new rollback DEP.

## Trigger

Use this rollback only after `PR #500` is merged and a verified policy leak,
stale-revision disclosure, cursor-authority defect, client-contract regression,
or required merge-proof failure requires removing the VAM-002 runtime/API
delivery. A design change requires a new Decision Package, not this rollback.

## Mandatory authorization and evidence gate

Before execution, prepare a new rollback DEP through Red -> Evidence -> Fix ->
Green -> Proof and strictly verify it. Import one fresh, exact, unexpired
owner-signed L3 approval for this rollback. Set `VAM002_ROLLBACK_DEP` to that
DEP and `VAM002_ROLLBACK_REQUEST` to the exact autonomy request. The approval
must be consumed immediately before `git revert`; no earlier merge, release, or
deployment authorization is reusable.

## Guarded preparation command

Run from an up-to-date, clean local `main` whose HEAD is exactly `PR #500`'s
merge commit. This prepares an uncommitted rollback candidate and fails closed
before any commit or push:

```bash
set -euo pipefail
test -n "$VAM002_ROLLBACK_DEP"
test -n "$VAM002_ROLLBACK_REQUEST"
sddgov evidence verify "$VAM002_ROLLBACK_DEP" --strict
test -z "$(git status --porcelain=v1 --untracked-files=all)"
merge_oid="$(gh pr view 500 --repo zycaskevin/Vault-Agent-Memory --json state,baseRefName,headRefName,mergeCommit --jq 'select(.state == "MERGED" and .baseRefName == "main" and .headRefName == "codex/vam-002-memory-change-envelope" and .mergeCommit.oid != null) | .mergeCommit.oid')"
test -n "$merge_oid"
test "$(git rev-list --parents -n 1 "$merge_oid" | awk '{print NF - 1}')" -eq 2
test "$(git rev-parse "$merge_oid^1")" = c284e1c7bedf288a10009b98e5f2da525c3ee4bc
test "$(git branch --show-current)" = main
test "$(git rev-parse HEAD)" = "$merge_oid"
test "$(git rev-parse origin/main)" = "$merge_oid"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
test -f .sddgov/merge-gate.json
test -f .sddgov/reviews/REV-VAM-002.json
reviewed_head="$(python -c 'import json; print(json.load(open(".sddgov/merge-gate.json", encoding="utf-8"))["head_sha"])')"
gate_base="$(python -c 'import json; print(json.load(open(".sddgov/merge-gate.json", encoding="utf-8"))["base_sha"])')"
gate_change="$(python -c 'import json; print(json.load(open(".sddgov/merge-gate.json", encoding="utf-8"))["change_digest"])')"
receipt_change="$(python -c 'import json; print(json.load(open(".sddgov/reviews/REV-VAM-002.json", encoding="utf-8"))["review"]["change_digest"])')"
receipt_meta="$(python -c 'import json; print(json.load(open(".sddgov/reviews/REV-VAM-002.json", encoding="utf-8"))["review"]["gate_metadata_digest"])')"
test "$gate_base" = c284e1c7bedf288a10009b98e5f2da525c3ee4bc
python -c 'import json,sys; r=json.load(open(".sddgov/reviews/REV-VAM-002.json", encoding="utf-8"))["review"]; raise SystemExit(0 if r.get("review_id")=="REV-VAM-002" and r.get("builder_id")=="codex" and r.get("verdict")=="approved" else 1)'
git merge-base --is-ancestor "$reviewed_head" "$merge_oid^2"
! git merge-base --is-ancestor "$reviewed_head" "$merge_oid^1"
test "$gate_change" = "$receipt_change"
actual_change="$(sddgov merge digest . --base-ref "$gate_base" | python -c 'import json,sys; print(json.load(sys.stdin)["change_digest"])')"
actual_meta="$(sddgov merge gate-digest . | python -c 'import json,sys; print(json.load(sys.stdin)["gate_metadata_digest"])')"
test "$actual_change" = "$gate_change"
test "$actual_meta" = "$receipt_meta"
approval_json="$(sddgov autonomy evaluate "$VAM002_ROLLBACK_REQUEST" --path .)"
printf '%s\n' "$approval_json" | python -c 'import json,sys; value=json.load(sys.stdin); raise SystemExit(0 if value.get("state")=="CONTINUE" and value.get("approval_consumed") is True else 1)'
git revert --no-commit -m 1 "$merge_oid"
git restore --source=HEAD --staged --worktree -- \
  .sddgov \
  DEP-VAM-002-INDEPENDENT-REVIEW-REMEDIATION \
  DEP-VAM-002-PUBLIC-READ-SENSITIVITY \
  DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION \
  evidence/DEP-VAM-002-CODERABBIT-REMEDIATION \
  evidence/DEP-VAM-002-MEMORY-CHANGE-ENVELOPE \
  docs/issues/VAM-002-memory-change-envelope.md \
  docs/work-packages/VAM-002-memory-change-envelope.md
git diff --cached --name-only -z | python -c 'import sys; actual=set(filter(None,sys.stdin.buffer.read().decode().split("\0"))); expected=set("""docs/decision_records/2026-08-21-memory-change-envelope.md
docs/specs/vam-002-memory-change-envelope.md
docs/specs/vault_memory_api.md
tests/test_gateway.py
tests/test_memory_change_envelope.py
vault/access_policy.py
vault/gateway.py
vault/gateway_memory_api.py
vault/gateway_openapi.py
vault/memory_change_envelope.py
vault/memory_provider.py""".splitlines()); raise SystemExit(0 if actual == expected else 1)'
test -z "$(git diff --name-only)"
test -z "$(git status --porcelain=v1 --untracked-files=all | awk 'substr($0,1,2) == "??" { print }')"
```

## Reversible steps

Review the staged candidate produced above. It may change only the exact
allowlist embedded in the command. Do not rename, rewrite, or delete user data.
Do not remove VAM-002 Issue/Work Package/DEP/review/governance provenance, and
do not touch any VAM-001 or VAM-003 path that existed at the exact base.
Commit and push only after the new rollback DEP captures the consumed approval,
candidate path set, and complete Green proof.

## Data compatibility

VAM-002 introduced no schema or stored-data migration. Reverting the additive
read contract leaves existing memory rows byte-compatible. Cursor and revision
tokens held by clients become unsupported API artifacts; they do not identify
storage mutations and require no data cleanup.

## Post-rollback verification

Run these exact checks from the uncommitted rollback candidate; every command
must exit 0 and be captured in the new rollback DEP:

```bash
python -m pytest -q tests/test_memory_provider.py -k 'not change'
python -m pytest -q tests/test_gateway.py -k 'not memory_changes and not revision_bound and not memory_change_http'
ruff check vault/access_policy.py vault/gateway.py vault/gateway_memory_api.py vault/gateway_openapi.py vault/memory_provider.py
python scripts/readme_command_smoke.py
python scripts/check_release_parity.py
sddgov ci verify .
sddgov evidence verify "$VAM002_ROLLBACK_DEP" --strict
sddgov ci local-gate .
```

Also prove mechanically that the staged path set still equals the embedded
allowlist, no untracked path exists, all preserved VAM-001/VAM-003 and VAM-002
provenance paths match HEAD byte-for-byte, no database/user-data path changed,
and `git diff --check` passes.
