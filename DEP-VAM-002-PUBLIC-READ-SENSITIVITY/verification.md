# Verification

## Green command and result

The exact repo-relative focused pytest command recorded in
`shareable/artifacts/terminal--stored-labels-and-tombstone-green.txt` passed 21
nodes in 1.04 seconds. The exact all-PR-changed-Python Ruff command passed with the
project-locked Ruff 0.15.20, and the module-size gate passed 159 modules.

## Before/after evidence

RED: two deterministic regression nodes failed because high-sensitivity data
was returned instead of bounded authorization errors. Green: all four provider
reads reject missing identity; Memory API get/search/timeline validate before
both adapters; range overflow is HTTP 400; and SDD/ADR now normatively bind
revision material and tombstones.
Malformed stored governance labels are denied under active policy, accepted
governance updates are canonical lowercase, and mixed-case delete becomes a
delete tombstone.

The follow-up cycle's raw RED was collected at 2026-08-22T13:55:48Z. Evidence
review and the bounded fix occurred after that capture; the exact final Green
was collected at 2026-08-22T13:57:46Z. The governance schema permits only one
linear Red/Evidence/Fix/Green history for a Green DEP, so `summary.yaml` records
the final Green completion time while these artifacts retain both cycles.

## Remaining limitations

The owner-authorized exact committed private-checkout Builder Local Green
passed at `1a346913563f5437b7815f655393f0eee5a0da52`: 446 isolated Subject nodes
and 2967 repository tests passed, with 10 skips and one existing warning.
Post-run HEAD/worktree, physical modes, and frozen Subject diff remained exact.
A new gate binding and independent Reviewer re-review are still required.
