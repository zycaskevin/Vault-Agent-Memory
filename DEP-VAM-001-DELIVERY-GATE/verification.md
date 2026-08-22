# Verification

## Green command and result

With hosted-equivalent `umask 022`, source directory modes, and a Python-only
PATH shim, `sddgov ci local-gate .` passed. Identity isolation passed 446 nodes;
the disjoint suite passed 2,926 tests with 10 skips and one pre-existing
deprecation warning.

## Before/after evidence

Before: the baseline test rejected wording that omitted the exact historical
phrase `Runtime is not implemented`. After: that phrase is retained while the
page still states that Subject will not continue in Vault. The complete gate
then passed without frozen artifact or runtime changes.

## Remaining limitations

The installed governance CLI is 0.2.0-experimental.3 while the repository
governance package is 0.2.0-experimental.6; `sddgov doctor` reports this as a
warning, not an error. Hosted CI has not run because this delivery remains local
until its Draft PR is opened.
