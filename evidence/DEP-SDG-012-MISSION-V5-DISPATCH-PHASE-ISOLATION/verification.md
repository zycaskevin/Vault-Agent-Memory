# Verification

## Builder static verification

- Exact base/worktree/branch and hosted RED identifiers confirmed.
- Root cause localized to test partitioning and snapshot ownership.
- Production dispatcher/validator/updater bytes are outside the patch.
- First focused source run retained exact exit 1 after 7/8 selected checks;
  static inspection confirmed two accidental historical path-set additions.
- The bounded repair restores both historical sets byte-for-byte and keeps the
  hygiene test only in SDG-012.
- Focused v2: 8 source checks PASS; 2 proof-present candidate dispatcher nodes
  PASS; 2 synthetic active dispatcher nodes PASS; combined exit 0.
- Full Local Green v2: doctor, CI verify, README smoke, release parity, exact
  446-node candidate identity isolation, and the disjoint remainder all PASS.
  The remainder reported 2868 passed, 12 skipped, and one pre-existing warning.

## Required final proof

- Ruff, Python 3.10 grammar, JSON parse, CI pins, closed-path/action/mode audit,
  and `git diff --check`.
- Candidate and active dispatcher-focused Green.
- Exact 446-node identity collection and disjoint remainder proof.
- Doctor, CI verification, strict DEP, full Local Green, independent review,
  hosted CI, and exact SDG-012 two-parent merge readback.

Strict DEP is completed at Builder proof freeze. Independent review, hosted CI,
merge readback, activation, task start, and production outcome remain unclaimed.
