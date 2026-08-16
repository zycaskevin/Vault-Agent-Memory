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

## Review remediation and exact proof state

The original PR #489 topic `bbc6e476ae3444cef77400f28710de73f9cf7f73`
had a valid independent review receipt and all 17 hosted checks passed in run
`31945978098`. Those results are retained as historical evidence bound only to
that exact head. This rebuilt `-v2` topic starts from exact base
`9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0`, does not descend from the stale
receipt commit, and keeps `.sddgov/reviews/REV-SDG-012.json` absent until fresh
independent review.

The remediation source is not merge-ready until its local proof, fresh
independent receipt, and hosted CI all pass on their exact recorded revisions.
No result is inferred from the earlier receipt or hosted run.

Fresh remediation proof now passes on exact source
`bcd2686eb9dff28365a8bd24ae600e808506885e`: focused static/current pin checks,
proof-bearing preliminary dispatch, exact two-parent active dispatch, malformed
active denial, exact 446-node identity isolation, and the 2868-test disjoint
remainder. The fresh focused and Full Local Green wrappers both returned 0.
The source worktree was clean before and after these runs.

## Required pre-merge proof

- Ruff, Python 3.10 grammar, JSON parse, CI pins, closed-path/action/mode audit,
  and `git diff --check`.
- Candidate and active dispatcher-focused Green.
- Exact 446-node identity collection and disjoint remainder proof.
- Doctor, CI verification, strict DEP, full Local Green, fresh independent
  review, and hosted CI on the final reviewed topic.

## Post-delivery proof

Exact two-parent merge/readback, a fresh Mission V5 proposal, any task start,
and production outcome can exist only after delivery to the new `main`. They
remain mandatory at their protocol phases and are currently unclaimed. This
pre-merge DEP neither fabricates nor predicts those outcomes.

The earlier Builder proof freeze is retained as historical evidence. Fresh
review-remediation focused and Local Green now pass; strict DEP proof is
refreshed on the final source. A fresh independent receipt and hosted CI remain
pending. Merge readback, proposal, task start, and production outcome remain
post-delivery and unclaimed.
