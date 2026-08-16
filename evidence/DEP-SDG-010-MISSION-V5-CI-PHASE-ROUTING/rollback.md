# Rollback

## Trigger

Any preliminary bypass, active validation without one exact two-parent merge,
collection drift, protected-review failure, or Local Green/hosted failure.

## Reversible steps

rollback_version: 1.0
target: the exact merged SDG-010 pull request commit
command: git revert --no-edit -m 1 <exact-two-parent-merge-commit>
verify: python scripts/run_subject_identity_test_isolation.py --phase preliminary

Use only the merged two-parent hotfix commit. Do not rewrite history or reuse
Mission proposals/proofs bound to the reverted protocol base.
