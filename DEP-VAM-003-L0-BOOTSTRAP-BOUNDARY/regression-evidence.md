# Regression Evidence

## Regression test added or strengthened

`tests/test_vault_boundary_freeze.py` covers both project-creation paths,
canonical and legacy source inference, three-language generated maintenance
guidance, the manifest boundary, and primary README/core documentation.
Existing CLI and setup-agent assertions were updated to the new canonical
output without removing the legacy compiler checks.

## Related tests executed

- Focused boundary and setup tests: 14 passed.
- Initialization/compiler/setup/access suite: 350 passed.
- Complete `sddgov ci local-gate .`: 446 identity-isolated nodes passed, then
  2,935 repository tests passed with 10 skips.
- README command smoke, release parity, governance doctor, and CI contract all
  passed.

## Unaffected paths sampled

Frozen Subject files and progress history had no diff from `origin/main`.
Legacy `L0-identity` inference, access presets/role identifiers, database layer
values, candidate workflow, and remote/setup behavior remained covered by the
full suite.

## Unverified boundary

Independent CodeRabbit review is pending because the CLI is absent and its
remote-script installer was rejected by the environment safety policy. This
does not weaken local proof; it blocks merge readiness until an independent
review is supplied.

## Regression test added or strengthened

TODO

## Related tests executed

TODO

## Unaffected paths sampled

TODO
