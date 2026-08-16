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
shell block, and refreshes its exact workflow byte pins. At that source-freeze
boundary no pytest or Local Green had run; the subsequently accepted exact
v2E2 results are recorded below. Fresh independent review remains pending.

## Accepted v2E2 Builder proof

On exact source `97728ce5f524cc6029a798abe7f34c2828231697`, corrected
focused v2E2 passed direct pinned dev6 parser evaluation, rollback shell syntax,
all three static/JUnit/bypass checks, two proof-bound candidate nodes, two exact
active nodes, malformed delivery denial, and two no-proof baseline nodes with
exact INACTIVE state. Its log SHA-256 is
`ebc6624607b6a7fe52824d24e2963891465ad31f277556b5ef3ceb1e76b37f83`.

The one Full Local Green v2E2 then passed all six commands. Candidate identity
isolation executed exactly 446 nodes; the disjoint remainder reported 2868
passed, 12 skipped, and one pre-existing SyntaxWarning. Its log SHA-256 is
`e98fe7fe12f477a84fcee51c1e55335718efb3e10faf90ae9c366d4d73a09049`.
Both wrappers returned 0 and the source worktree remained clean. Fresh
independent review, hosted CI, and delivery readback remain unclaimed.

## v3 hosted platform-skip remediation

PR #490 exact head `0ebb5ae33c5ed69a78356c35a2a6fa3b8248430f`
then failed hosted run `31953893529` because v2E required one PASS from the
single test intentionally skipped off Darwin. The current v3 source is rebuilt
from exact base `9ddc508...`, keeps previous receipt/gate history unreachable,
and adds one exact platform-skip allowlist entry while retaining genuine PASS
proof for all other nodes. Raw job logs are local-only; the public-safe run/job
summary is redacted in the shareable artifact.

Static v3 verification requires exact allowlist bytes, exact existing skipif
decorator/reason, dispatcher skip/xfail rejection, wrong node/platform/reason/
type denial, malformed/multi-case/failure/error denial, exact 446 collection,
CI byte pins, rollback v3 branch closure, Ruff, Python 3.10 AST, JSON, and diff
checks. No pytest or Local Green has run on these changed bytes; both require a
fresh external exclusive lease.

## CodeRabbit v3 dispositions

Accepted P1 rollback remediation holds a newly and atomically acquired external
exclusive lease across the full procedure. The exact mutable delivery checks
are rerun after phase proof and immediately before revert, including a fresh
fetch, canonical fetch/push origin, symbolic `main`, fully clean tracked and
untracked state, exact HEAD/origin-main/parents/tree, owner-confirmed absence of
an issued proposal, and absent proof/pending files. The current hygiene source
contains executable negative fixtures for lease collision, missing owner
confirmation, dirty state, proof presence, and changed remote main.

Accepted P1 topology remediation creates an actual extra-path descendant of a
valid two-parent fixture, proves the SDG-012 checker receives that descendant,
and requires denial; the exact anchor remains independently early-denied. The
P2 literal reuse is accepted without weakening its exact value assertion.

The gate-head/receipt and repository trust-store comments are recorded as false
positives. Audit-only gate chronology intentionally binds a reviewed source
ancestor and leaves the receipt absent until independent signing. The signature
trust root intentionally remains external and runtime-pinned. No gate, signing,
or trust architecture is changed by this source repair.

## First v3 focused RED

The one authorized focused run on exact clean source
`1b4d06820e4639c4b76dee8c56d019a77a30261c` passed process/lease preflight,
direct dev6 rollback parsing, rollback Bash syntax, and four of five selected
static/topology tests. It then stopped with one failure before any
candidate/active/malformed/baseline fixture: the source test still demanded the
removed direct string `_verify_single_pass_junit(junit)` even though main now
correctly delegates to `_verify_identity_junit(junit, node=node,
platform=sys.platform)`. Log SHA-256 is
`1808648384be1e46bf0b38fb4fa7eef6baba767f18a25343398edfe608033b14`;
wrapper exit was 1. No rerun or Full Local Green occurred.

The bounded repair preserves implementation semantics and changes that stale
self-assertion to inspect the exact main delegation plus the helper's exact
`_verify_single_pass_junit(path)` fallback and exact platform-skip branch. A
fresh external lease and fresh focused run are mandatory for the new revision.

## Accepted v3b Builder proof

Fresh focused on exact clean source
`8ae13eabbd4652746052aa8f67b7946b80267be7` passed direct dev6 rollback
parsing, rollback Bash syntax, five static/JUnit/rollback/topology checks, both
proof-bound candidate nodes, both exact two-parent active nodes, malformed
active denial, and both no-proof baseline nodes. The baseline remained exact
INACTIVE, sequence 6, T-004 PENDING, with pending/proof absent. Log SHA-256 is
`9eaaba32012c87d6a65eef329888ef986d8f34042574b57c94d096f617c319fc`;
wrapper exit was 0.

The one Full Local Green on the same exact source passed all six commands.
Doctor, CI verify, README smoke, and release parity returned 0. Candidate
identity isolation passed exact 446 nodes. The disjoint remainder reported
2869 passed, 12 skipped, and one pre-existing SyntaxWarning; all commands and
the wrapper returned 0. Log SHA-256 is
`fb790a7cf363c33004da21a05f68f9d64a10c29d9de6af8de0b8419eddb1ab4a`.
The worktree was clean before and after both runs. Fresh independent receipt,
hosted Green, and exact delivery readback remain pending.
