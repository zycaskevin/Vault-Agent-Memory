# Rollback

rollback_version: 1.0
target: compatibility wording introduced by ec107d134fc491cc48d44f5a01b919da30c2f913 in docs/subject-distillation.md; preserve the extraction ADR, frozen Subject artifacts, and all evidence
command: test -n "$VAM001_ROLLBACK_DEP" && test -n "$VAM001_ROLLBACK_REQUEST" && sddgov evidence verify "$VAM001_ROLLBACK_DEP" --strict && test -z "$(git status --porcelain=v1 --untracked-files=all)" && merge_oid="$(gh pr view 498 --repo zycaskevin/Vault-Agent-Memory --json state,baseRefName,headRefName,mergeCommit --jq 'select(.state == "MERGED" and .baseRefName == "main" and .headRefName == "codex/vam-001-subject-extraction-adr" and .mergeCommit.oid != null) | .mergeCommit.oid')" && test -n "$merge_oid" && test "$(git rev-list --parents -n 1 "$merge_oid" | awk '{print NF - 1}')" -ge 2 && git merge-base --is-ancestor ec107d134fc491cc48d44f5a01b919da30c2f913 "$merge_oid" && test "$(git branch --show-current)" = main && test "$(git rev-parse HEAD)" = "$merge_oid" && sddgov autonomy evaluate "$VAM001_ROLLBACK_REQUEST" --path . | python -c 'import json,sys; value=json.load(sys.stdin); assert value.get("state")=="CONTINUE" and value.get("approval_consumed") is True' && git revert --no-commit ec107d134fc491cc48d44f5a01b919da30c2f913 && git restore --source=HEAD --staged --worktree -- DEP-VAM-001-DELIVERY-GATE
verify: python -c 'from pathlib import Path; assert "Runtime is not implemented" in Path("docs/subject-distillation.md").read_text(encoding="utf-8")' && python -m pytest -q tests/test_subject_baseline.py::test_public_package_has_no_stale_private_governance_metadata tests/test_subject_extraction_boundary_docs.py tests/test_subject_contracts.py && python scripts/validate_subject_progress.py --manifest specs/subject-distillation/baseline-manifest.json --schema specs/subject-distillation/implementation-progress.schema.json --tasks specs/subject-distillation/tasks.md --progress specs/subject-distillation/implementation-progress.json && python scripts/run_subject_identity_test_isolation.py --phase candidate && umask 022 && sddgov ci local-gate . && sddgov evidence verify "$VAM001_ROLLBACK_DEP" --strict

## Trigger

Rollback only if the compatibility sentence is shown to misstate the approved
Subject extraction decision or causes a new documentation regression.

## Mandatory authorization and evidence gate

Before executing `command`, prepare a new rollback DEP through
Red -> Evidence -> Fix -> Green -> Proof and strictly verify it. Import a fresh,
exact, unexpired owner-signed L3 approval for this rollback and reference it in
`VAM001_ROLLBACK_REQUEST`; the autonomy evaluation must consume that approval
immediately before the repository mutation. A prior merge/deploy decision is
not reusable rollback authority.

## Reversible steps

The guarded command resolves the exact merged PR, requires its expected base
and head branch plus a multi-parent merge commit, and proves that the bounded
compatibility commit is part of that merge. It also requires the local branch
to be `main` at that exact merge commit before consuming approval. It then
creates an uncommitted revert candidate for `ec107d1` and restores the delivery
DEP so no evidence is deleted. Before committing, replace the restored
pre-extraction sentence with an owner-approved compatibility sentence that
retains the exact case-sensitive phrase `Runtime is not implemented`.

Do not alter or remove the extraction ADR, the completed Issue-disposition
record, any existing governance decision/event, either VAM-001 DEP, or frozen
Subject artifacts. Rollback is incomplete until the replacement sentence and
the entire `verify` sequence pass in the new rollback DEP.

## Data compatibility

No schema, database, API, CLI, MCP, or stored-data behavior changed. Rollback
has no data migration or compatibility requirement.

## Post-rollback verification

Run the exact machine-readable `verify` sequence above: phrase check, baseline
compatibility node, VAM-001 boundary/contract/progress tests, full CI Cost
Guard Local Green, and strict verification of the new rollback DEP.
