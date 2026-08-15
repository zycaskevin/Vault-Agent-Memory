# Rollback

rollback_version: 1.0
target: SDG-001 GitHub merge commit at rollback-time HEAD
command: git revert --no-edit -m 1 HEAD
verify: python scripts/readme_command_smoke.py

The DEP itself has no runtime effect. If the SDG integration merge must be
rolled back, revert its two-parent GitHub merge commit from the exact main HEAD
and run the existing README documented-command smoke. Do not rewrite or delete
T-001 through T-003 history. Rollback does not migrate or transform data.
