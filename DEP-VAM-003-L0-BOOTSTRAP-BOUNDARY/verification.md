# Verification

## Green command and result

`sddgov ci local-gate .` passed under hosted-equivalent `umask 022`, file modes,
and a Python-only PATH shim. Identity isolation passed 446 nodes. The disjoint
repository suite passed 2,935 tests with 10 skips and one pre-existing
deprecation warning.

## Before/after evidence

Before: focused boundary tests produced 11 failures and one legacy-alias pass.
After: new projects create `L0-bootstrap`, both directory spellings infer L0,
generated guides are maintenance-only in three languages, active docs and the
manifest declare the provider boundary, and all focused/full gates pass.

## Remaining limitations

- `memory_agents`, `personal-agent`, `profile`, `care`, and `dream` remain
  public compatibility identifiers; they are now documented as labels rather
  than modeling ownership.
- Existing `L0-identity` data is intentionally not renamed or migrated.
- Repository governance is 0.2.0-experimental.6 while the installed CLI is
  0.2.0-experimental.3; doctor reports a warning only.
- Independent review remains required before merge; CodeRabbit could not be
  installed safely in this environment.

## Green command and result

TODO

## Before/after evidence

TODO

## Remaining limitations

TODO
