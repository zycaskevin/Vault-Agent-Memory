# Verification

## Builder verification

Focused compatibility and rollback regressions passed 14/14 with exact exit 0
on source `db4f142ab`. The same revision's Local Green exposed an exact
collection-count drift before identity node execution; the bounded 90-node pin
repair is awaiting focused v2 and new-revision Local Green.

## Required final proof

- Focused genuine positive and negative compatibility regressions.
- Exact live SDG-010 anchor verification and current-base denial.
- Corrected rollback static and metadata proof.
- Ruff and Python 3.10 grammar checks.
- `sddgov doctor`, CI contract verification, strict DEP verification, and full
  Local Green.
- Independent protected-file review with zero P0/P1 findings.
- One hosted CI run and exact SDG-011 two-parent merge readback.

No result is claimed before its command and exit status are recorded in the
shareable verification artifact.
