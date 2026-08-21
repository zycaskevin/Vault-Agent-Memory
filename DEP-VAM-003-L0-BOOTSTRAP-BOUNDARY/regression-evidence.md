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

Remote CodeRabbit review supplied actionable findings on the original pull
request head. Those findings are addressed in the follow-up change; the new
exact head must complete hosted CI and independent re-review before merge.

## Regression completeness audit

### Regression test added or strengthened

The focused boundary test and updated compatibility assertions are identified above.

### Related tests executed

Focused, integration, identity-isolated, complete repository, and documentation gates are recorded above.

### Unaffected paths sampled

Frozen Subject history, legacy inference, identifiers, layer values, candidate flow, and setup paths were sampled.
