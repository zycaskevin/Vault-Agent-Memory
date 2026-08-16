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
review-remediation focused and Local Green pass only for exact v2B source
`bcd2686eb9dff28365a8bd24ae600e808506885e`. Security re-review then required
strict per-node JUnit outcomes, dynamic-bypass guards, and corrected rollback
preflight/chronology. Those v2C source bytes first had static verification only;
their subsequent exact RED is recorded below and no old result is promoted. A
fresh independent receipt and hosted CI remain pending. Merge readback,
proposal, task start, and production outcome remain post-delivery and
unclaimed.

Focused v2C is exact RED: three static/historical checks passed, then the
proof-bearing candidate correctly denied a later reviewed runner whose bytes
are outside that proof's immutable trust root. v2D keeps the proof-bound runner
for candidate/active/malformed phase evidence, while retaining/hash-binding the
reviewed runner and executing it only on the post-revert no-proof baseline.
Fresh v2D focused and Local Green were required; their accepted results follow.

Both required Builder gates now pass on exact source
`1e1c23eae226446bd79b8d9809bc7716658fa546`. Focused v2D proved the exact
proof-bound candidate/active/malformed matrix and retained-runner no-proof
baseline with true JUnit outcomes. The one Full Local Green passed doctor, CI
verify, README smoke, release parity, exact 446-node candidate isolation, and
the disjoint remainder (2868 passed, 12 skipped, one pre-existing warning).
Independent receipt, hosted CI, and delivery readback remain pending and are
not inferred.

## v2E rollback parser remediation

Pinned experimental.6 post-sign verification rejected v2D with exact
`rollback record is missing or incomplete`. Its reviewer receipt is unusable
and is not present in this Builder lineage. Static v2E verification directly
calls the pinned `_real_rollback` parser and requires `True`, reproduces the
same field algorithm in repository hygiene checks, syntax-checks the retained
shell block, and refreshes its exact workflow byte pins. This source change has
not run pytest or Local Green; all dynamic gates and a fresh independent receipt
remain pending.
