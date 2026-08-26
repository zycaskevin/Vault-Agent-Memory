# Fix Scope

## Smallest sufficient change

Retain the conflict-free merge of exact current main, add one integration DEP,
re-run VAM-002 regression proof on that combined tree, and replace the inherited
VAM-003 merge metadata with a VAM-002-specific gate and independent receipt.

## Files or components in scope

- Current-main merge commit on `codex/vam-002-memory-change-envelope`.
- `DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/`.
- `.sddgov/merge-gate.json` in a final audit-only gate commit.
- `.sddgov/reviews/REV-VAM-002.json` only after independent Reviewer PASS.

## Explicit non-scope

- No change to the approved Memory Change Envelope API or implementation.
- No change to Frozen Subject Distillation paths or Subject runtime contracts.
- No reuse, deletion, or rewriting of VAM-001/VAM-003 evidence or receipts.
- No database migration, release, deployment, branch deletion, or production
  operation.

## Blast radius

The product blast radius is limited to proving the existing VAM-002 diff on the
new sequential base. The governance blast radius is the PR #500 gate, rollback,
new integration evidence, and its independent review receipt. Prior merged Work
Packages remain ancestors and are explicitly excluded from rollback.
