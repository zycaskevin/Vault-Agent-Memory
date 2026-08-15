# Verification

## Green command and result

`.venv-sddgov/bin/sddgov claim SDG-001 --agent codex --ttl-minutes 240
--path .` exited zero and returned one active claim.

## Before/after evidence

Before: `NotADirectoryError` with no claim. After: one active claim whose
project state is `.sddgov/work-claims.json`.

## Remaining limitations

The claim expires automatically after four hours and does not itself verify the
larger SDG integration Work Package.
