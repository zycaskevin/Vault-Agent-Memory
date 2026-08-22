# Rollback

rollback_version: 1.0
target: exact behavioral and active-public-documentation delta merged by Pull Request 499; preserve all VAM-003 decision, SDD, Work Package, DEP, review, and governance provenance
command: Run the guarded preparation command below from the exact merged main checkout after consuming the required approval.
verify: Run every post-rollback verification below and record the results in the new strictly verified rollback DEP.

## Trigger

Rollback only if a supported legacy project stops resolving L0 content, a new
project cannot initialize, or generated setup output violates the approved
memory/identity boundary. A new product decision is required before replacing
`L0-bootstrap` with another public contract.

## Mandatory authorization and evidence gate

Before execution, prepare a new rollback DEP through Red -> Evidence -> Fix ->
Green -> Proof and strictly verify it. Import a fresh, exact, unexpired
owner-signed L3 approval for this rollback. Set `VAM003_ROLLBACK_DEP` to that
DEP and `VAM003_ROLLBACK_REQUEST` to the exact autonomy request. The approval
must be consumed immediately before the repository mutation; no prior merge or
deployment authorization is reusable.

## Guarded preparation command

Run from a clean local `main` checkout whose HEAD is exactly PR #499's merge
commit. This prepares an uncommitted rollback candidate and fails closed before
any commit:

```bash
set -euo pipefail
test -n "$VAM003_ROLLBACK_DEP"
test -n "$VAM003_ROLLBACK_REQUEST"
sddgov evidence verify "$VAM003_ROLLBACK_DEP" --strict
test -z "$(git status --porcelain=v1 --untracked-files=all)"
merge_oid="$(gh pr view 499 --repo zycaskevin/Vault-Agent-Memory --json state,baseRefName,headRefName,mergeCommit --jq 'select(.state == "MERGED" and .baseRefName == "main" and .headRefName == "codex/vam-003-l0-bootstrap-boundary" and .mergeCommit.oid != null) | .mergeCommit.oid')"
test -n "$merge_oid"
test "$(git rev-list --parents -n 1 "$merge_oid" | awk '{print NF - 1}')" -eq 2
test "$(git rev-parse "$merge_oid^1")" = db1763482f0f603ccd63817f26c73308bc186697
git merge-base --is-ancestor 441db54118aa3157703727d2168e15d174f44af0 "$merge_oid^2"
! git merge-base --is-ancestor 441db54118aa3157703727d2168e15d174f44af0 "$merge_oid^1"
test "$(git branch --show-current)" = main
test "$(git rev-parse HEAD)" = "$merge_oid"
approval_json="$(sddgov autonomy evaluate "$VAM003_ROLLBACK_REQUEST" --path .)"
printf '%s\n' "$approval_json" | python -c 'import json,sys; value=json.load(sys.stdin); raise SystemExit(0 if value.get("state")=="CONTINUE" and value.get("approval_consumed") is True else 1)'
git revert --no-commit -m 1 "$merge_oid"
git restore --source=HEAD --staged --worktree -- \
  .sddgov \
  DEP-VAM-003-HOSTED-MODULE-SIZE-GATE \
  DEP-VAM-003-IDENTITY-ISOLATION-RECHECK \
  DEP-VAM-003-INDEPENDENT-REVIEW-REMEDIATION \
  DEP-VAM-003-L0-BOOTSTRAP-BOUNDARY \
  DEP-VAM-003-SHAREABLE-PATH-REDACTION \
  docs/issues/VAM-003-l0-bootstrap-boundary.md \
  docs/specs/vam-003-l0-bootstrap-boundary.md \
  docs/work-packages/VAM-003-l0-bootstrap-boundary.md
git diff --cached --name-only -z | python -c 'import sys; actual=set(filter(None,sys.stdin.buffer.read().decode().split("\0"))); expected=set("""README.md
README.zh-CN.md
README.zh-Hant.md
agent_manifest.json
docs/agent_install.md
docs/agent_integrations.md
docs/cli_reference.md
docs/core-concepts.md
docs/memory_governance.md
docs/vision.md
tests/test_agent_setup.py
tests/test_cli_extended.py
tests/test_vault_boundary_freeze.py
vault/agent_access.py
vault/agent_setup.py
vault/agent_setup_memory.py
vault/agent_setup_remote_server.py
vault/agent_setup_roster.py
vault/agent_setup_startup.py
vault/agent_setup_supabase.py
vault/cli_core.py
vault/compiler.py
vault/memory_layers.py""".splitlines()); raise SystemExit(0 if actual == expected else 1)'
test -z "$(git diff --name-only)"
test -z "$(git status --porcelain=v1 --untracked-files=all | awk 'substr($0,1,2) == "??" { print }')"
```

## Reversible steps

Review the staged candidate produced above. It may change only the exact
allowlist embedded in the command. Do not rename or delete any user directory.
Do not remove VAM-003's Issue, SDD, Work Package, DEP packages, review receipt,
or governance history. Commit the candidate only after the new rollback DEP
captures the approval consumption, candidate path list, and complete Green
proof.

If rollback occurs after projects created `L0-bootstrap`, that directory
remains ordinary user data and must not be moved automatically. Existing
`L0-identity` content also remains untouched.

## Data compatibility

The database layer value remains `L0`; no schema or stored-row change exists.
Both directory spellings are source-path inference labels, so rollback performs
no migration, rename, delete, or backup/restore operation.

## Post-rollback verification

The rollback DEP must include executable checks for project initialization,
both source-inference spellings, setup-agent guidance, README command smoke,
release parity, `git diff --check`, and the complete Local Green Gate. It must
also prove that no user data was renamed or removed, the staged/committed path
set matched the exact allowlist above, and all preserved VAM-003 governance and
evidence paths are byte-for-byte unchanged.
