# Rollback

rollback_version: 1.0
target: The exact merged PR #500 merge commit on current main
command: Run the guarded preparation below, consume one exact rollback approval, then execute git revert --no-commit -m 1 "$merge_oid"
verify: Confirm only the committed PR #500 paths are staged for removal or restoration and all pre-PR main content, including VAM-001 and VAM-003, remains unchanged

## Trigger

Use this rollback only after PR #500 is merged and a verified regression,
policy leak, stale-revision disclosure, cursor-authority defect, or required
merge-proof failure requires removing the complete VAM-002 delivery.

## Reversible steps

From an up-to-date, clean local `main`, resolve PR #500 through authenticated
GitHub metadata and fail closed unless:

1. PR #500 is merged and supplies one exact merge commit.
2. The merge has exactly two parents.
3. Local branch is `main`, local `HEAD` equals the resolved merge commit, and
   `origin/main` equals the same commit.
4. Parent 1 is the PR base and parent 2 is the exact reviewed receipt head.
5. The receipt head is an ancestor of parent 2 and not an ancestor of parent 1.
6. Worktree, index, and untracked-file status are empty.
7. The autonomy classifier validates and consumes one fresh exact L3 approval
   for operation `rollback-pr500-vam002-<merge_oid>`.

Then run `git revert --no-commit -m 1 "$merge_oid"`. Abort on any failed
precondition. Inspect the staged path set before committing; it must equal the
exact PR #500 diff and must not remove or rewrite any VAM-001/VAM-003 path that
already existed at parent 1. Commit and push only after the normal rollback
review and tests pass.

## Data compatibility

No schema or data migration was introduced by VAM-002. Reverting the merge
removes the additive provider methods, read-only Gateway route, documentation,
tests, VAM-002 evidence, gate, and receipt. Existing memory rows and all prior
Work Packages remain byte-compatible.

## Post-rollback verification

Before committing the revert:

- `git diff --cached --name-only` equals the exact PR #500 changed-path set.
- `git status --porcelain=v1 --untracked-files=all` contains only that staged
  revert and no untracked path.
- VAM-001/VAM-003 receipts and Frozen Subject paths match parent 1.
- Existing Gateway/provider compatibility tests pass without VAM-002 tests.
- README smoke, release parity, `sddgov ci verify .`, strict retained DEP
  verification, and the full Local Green gate pass.
