# Rollback

## Trigger

Rollback this Builder-only command composition if it selects any interpreter
other than the established Vault test Python, resolves a governance CLI other
than the reviewed merged runtime, or changes repository commands.

## Reversible steps

Discard the temporary PATH ordering and leave the exact checkout untouched.
No product commit, database, schema, installation, or live runtime is changed.

## Verification

Confirm `git status --porcelain=v1 --untracked-files=all` is empty, HEAD remains
the exact candidate, and no Local Green process remains active.

## Data compatibility

No data, schema, or product byte was changed.

## Post-rollback verification

Re-resolve the selected Python and governance executables and confirm the
private checkout remains clean without untracked gate output.
