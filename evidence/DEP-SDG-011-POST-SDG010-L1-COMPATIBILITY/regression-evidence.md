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

Pending the external exclusive test lease. No pytest, identity harness, Local
Green, or merge verification has been run by this Builder yet.

## Unverified boundary

The future protected review receipt and hosted/merged commit do not exist at
the source-building phase. They remain mandatory before delivery.
