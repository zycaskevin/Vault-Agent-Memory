# Regression Evidence

## Required checks

- Exact live SDG-010 anchor PASS, including trusted gate/receipt bytes.
- Current `efa43a4` protocol base DENY.
- Exact closed future SDG-011 two-parent merge PASS.
- Wrong parent, reversed parent order, merge-tree mismatch, extra path, hidden
  add-delete, wrong add/modify action, executable-mode drift, gate drift, and
  receipt drift each DENY.
- SDG-010 rollback text binds exact PR #484, actual v4 head, exact merge
  commit, parent order, and tree equality.
- Focused regression, Ruff, Python 3.10 grammar, diff check, doctor, CI Cost
  Guard, full Local Green, independent protected review, hosted CI, and exact
  merge readback PASS.

## Executed results

- Final focused capture: 14 passed in 47.75 seconds with exact pytest exit 0.
- Two earlier focused executions also reported 14 passed (46.17 and 46.00
  seconds), but their wrapper exit telemetry was not retained; they are not
  used as exit proof.
- Source `db4f142ab` Local Green: doctor, CI verify, README smoke, and release
  parity passed; identity collection then denied because the frozen count was
  77 instead of the new exact 90. No node or disjoint remainder test ran.
- A prior invocation stopped before all configured commands because PATH did
  not expose the pinned `sddgov` child command. It ran zero repo tests and is
  retained only as environment-bootstrap evidence.
- Focused v2 and one new-revision Local Green remain pending after the bounded
  90-node pin repair.

## Unverified boundary

The future protected review receipt and hosted/merged commit do not exist at
the source-building phase. They remain mandatory before delivery.
