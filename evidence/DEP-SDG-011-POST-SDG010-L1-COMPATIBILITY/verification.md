# Verification

## Builder verification

Focused compatibility and rollback regressions passed 14/14 with exact exit 0
on source `db4f142ab`. The same revision's Local Green exposed an exact
collection-count drift before identity node execution.

On repaired source `a9318c8`, focused v2 passed 14/14 with exact exit 0 and
collection proved 444 total nodes with exactly 90 Mission V5 nodes. Full Local
Green v2 passed all configured commands: doctor, CI verification, README smoke,
release parity, 444-node candidate identity isolation, and the disjoint
remainder (2870 passed, 12 skipped, one pre-existing SyntaxWarning).

## Required final proof

- Focused genuine positive and negative compatibility regressions.
- Exact live SDG-010 anchor verification and current-base denial.
- Corrected rollback static and metadata proof.
- Ruff and Python 3.10 grammar checks.
- `sddgov doctor`, CI contract verification, strict DEP verification, and full
  Local Green.
- Independent protected-file review with zero P0/P1 findings.
- One hosted CI run and exact SDG-011 two-parent merge readback.

Independent review, hosted CI, and merge readback remain unclaimed and
mandatory. Command results, exact exits, limitations, and stable log hashes are
recorded in the shareable verification artifact.
