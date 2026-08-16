# Regression Evidence

## Required checks

- Retained hosted RED identifies exactly two dispatcher V5 failures.
- Candidate phase replays proof-present preliminary topics as inactive and both
  dispatcher assertions pass without authority.
- Active phase retains active delivery replay and both assertions pass ACTIVE.
- Dispatcher V5 collection is exactly 2; identity total is exactly 446.
- Both generic remainders ignore the file exactly once; no skip/xfail/deselect,
  `-k`, abbreviation, or `continue-on-error` is introduced.
- Production dispatcher, validator, and updater bytes remain unchanged.
- Focused regression, static pins, strict DEP, full Local Green, independent
  review, hosted CI, and exact merge readback pass.

## Executed results

- Hosted RED and current source/config omission are mechanically confirmed.
- Fix implementation and static verification are in progress.

## Unverified boundary

No local pytest, Local Green, independent receipt, hosted Green, or merge result
is claimed before the external exclusive test lease and later review phases.
