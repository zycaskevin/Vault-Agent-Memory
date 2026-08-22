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

## Remaining limitations

The real-loopback HTTP assertions and complete suite remain assigned to one
owner-authorized exact committed private-checkout Builder Local Green. A new
gate binding and independent Reviewer re-review are required afterward.
