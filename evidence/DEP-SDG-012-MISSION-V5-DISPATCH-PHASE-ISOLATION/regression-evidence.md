# Regression Evidence

## Required checks

- Retained hosted RED identifies exactly two dispatcher V5 failures.
- Candidate phase replays proof-present preliminary topics as inactive and both
  dispatcher assertions pass without authority.
- Active phase retains active delivery replay and both assertions pass ACTIVE.
- Dispatcher V5 collection is exactly 2; identity total is exactly 446.
- The two exact dispatcher node IDs are pinned, and AST guards reject
  `pytest.mark.skip`, `pytest.mark.skipif`, `pytest.mark.xfail`, `pytest.skip`,
  `pytest.xfail`, and `pytest.importorskip`.
- Both generic remainders ignore the file exactly once; no skip/xfail/deselect,
  `-k`, abbreviation, or `continue-on-error` is introduced.
- Each isolated node writes a unique JUnit XML under `xfail_strict=true`; exact
  tests=1, skipped=0, failures=0, and errors=0 is mandatory in addition to rc 0.
- Static guards reject direct and aliased pytest outcomes, dynamic `getattr`,
  pytest subscripting, imported outcome helpers, and string-spelled marks.
- Rollback binds canonical origin plus freshly fetched exact delivery, proves
  retained candidate/active/malformed semantics before revert, then requires
  first-parent tree equality and only base-compatible INACTIVE proof afterward.
- Production dispatcher, validator, and updater bytes remain unchanged.
- Focused regression, static pins, strict DEP, full Local Green, independent
  review, hosted CI, and exact merge readback pass.

## Executed results

- Hosted RED and current source/config omission are mechanically confirmed.
- The first v2 remediation focused lease was invalidated by concurrent writers;
  its log was overwritten and no digest or result from that lease is accepted.
  The collision nevertheless exposed a genuine deterministic RED: the SDG-011
  historical pin assertion read the current workflow and therefore expected an
  obsolete SDG-012 harness pin in changing bytes. Exact object readback showed
  the immutable SDG-011 workflow at `9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0`
  pins `de169a26c04130d07219ca427e0fcf34b809868156f815181bac11ea6a0f32a5`.
  The bounded repair reads that historical workflow blob directly; the SDG-012
  assertion continues to verify the exact current harness digest separately.
- First focused source revision: 7 passed, 1 failed. The failure was exact
  historical SDG-004 replay denial caused by two accidentally contaminated
  historical compatibility sets; dispatcher test bodies themselves passed.
- The failure log SHA-256 is
  `f3fa2e25e6b7e26924237d4b3d5a8b89428b6f5097d2b4fe46973635a363395e`;
  exact exit is 1. It remains RED evidence and is not claimed as Green.
- Bounded repair removes the two historical entries and refreshes exact CI
  hashes.
- Focused v2 passed 8 source checks in 28.15 seconds, then passed both exact
  dispatcher nodes on PR #487's proof-present candidate topology in 5.40
  seconds and on a synthetic exact two-parent active topology in 5.80 seconds.
  Combined exit was 0.
- Full Local Green v2 passed all six commands. Candidate identity isolation
  passed exactly 446 nodes. The disjoint remainder passed 2868 tests with 12
  skipped and one pre-existing SyntaxWarning; every command returned 0.
- Fresh v2B focused proof on exact source
  `bcd2686eb9dff28365a8bd24ae600e808506885e` passed the repaired historical
  and current pin checks (3 tests), proof-bearing preliminary dispatch (2), and
  exact two-parent active dispatch (2). A same-parent malformed delivery with
  a non-topic tree was denied for both nodes. The accepted focused log SHA-256
  is `f3afee7e3e2befff2bec1c3d25661b49147e1113bb37de9a0334955757408bd5`;
  wrapper exit was 0.
- The one Full Local Green v2B on the same source passed all six commands.
  Candidate identity isolation passed exactly 446 nodes. The disjoint
  remainder passed 2868 tests with 12 skips and one pre-existing SyntaxWarning.
  Every command returned 0. The full log SHA-256 is
  `fd4f765c6c32575936fa7c811db2488932fb44a2fb17f803f03d9c01e6ff2e4f`.
- Security re-review P0=0/P1=3 identified outcome interpretation and rollback
  chronology/preflight gaps. The bounded v2C source repair is static-only at
  this stage. No earlier focused or Local Green result is relabeled as proof of
  the changed harness and rollback bytes; its later exact RED follows below.
- Focused v2C static/historical-current/JUnit-bypass/rollback selection passed
  3 checks, then both proof-bearing candidate nodes errored with exact `Denied`.
  The fixture had overlaid the reviewed SDG-012 runner, while PR #487's proof
  correctly binds its earlier runner bytes. Exact wrapper exit was 1; log
  SHA-256 is
  `b6fdc829d0082fc66fea989ff2e94905895161c15ed7c45db27f9dc31c20519a`.
  This is retained RED and is not Green. v2D preserves the proof-bound runner
  in candidate/active/malformed fixtures, retains the reviewed runner without
  executing it there, and executes reviewed runner bytes only for post-revert
  no-proof INACTIVE/sequence-6/T-004-PENDING proof.
- Focused v2D on exact source
  `1e1c23eae226446bd79b8d9809bc7716658fa546` passed three static/JUnit/bypass/
  rollback checks; both exact candidate nodes and both exact two-parent active
  nodes reported genuine one-test JUnit PASS; malformed active produced the
  required two Denied errors; and the retained-runner baseline passed both
  nodes plus explicit INACTIVE, sequence 6, T-004 PENDING, absent pending, and
  absent proof assertions. Wrapper exit was 0; log SHA-256 is
  `553ff380be518be95122fc560936344779cabd4c0a1f6241841935741da6d29a`.
- The one Full Local Green v2D on the same source passed all six commands.
  Identity isolation passed exact 446 nodes. The disjoint remainder reported
  2868 passed, 12 skipped, and one pre-existing SyntaxWarning. Every command
  and the wrapper returned 0. Full log SHA-256 is
  `2821ec3171aec734adc28bb6689f68f6078d14fe39f22de7c9361696c40a9dee`.
- Post-sign experimental.6 merge verification then failed fast with exact
  `rollback record is missing or incomplete`. The attempted reviewer receipt
  is unusable and remains absent from this Builder lineage. Static inspection
  confirmed the v2D record declared version `1.1` and did not expose top-level
  `command` or `verify` fields required by the pinned parser. v2E changes only
  existing closed paths, retains the complete fail-closed shell body, and adds
  an exact hygiene reproduction of the parser contract. No v2D test or receipt
  is promoted to the changed v2E bytes; fresh gates remain mandatory.
- Corrected focused v2E2 on exact source
  `97728ce5f524cc6029a798abe7f34c2828231697` passed direct experimental.6
  `_real_rollback=True`, rollback shell syntax, three parser/JUnit/bypass/static
  checks, both proof-bound candidate nodes, both exact two-parent active nodes,
  malformed active denial, and both retained-runner no-proof baseline nodes
  with exact INACTIVE/sequence 6/T-004 PENDING and absent pending/proof state.
  Wrapper exit was 0; log SHA-256 is
  `ebc6624607b6a7fe52824d24e2963891465ad31f277556b5ef3ceb1e76b37f83`.
- The one Full Local Green v2E2 on the same exact source passed all six
  commands. Identity isolation passed exact 446 nodes. The disjoint remainder
  reported 2868 passed, 12 skipped, and one pre-existing SyntaxWarning. Every
  command and wrapper returned 0. Full log SHA-256 is
  `e98fe7fe12f477a84fcee51c1e55335718efb3e10faf90ae9c366d4d73a09049`.
- Hosted PR #490 run `31953893529` at exact head
  `0ebb5ae33c5ed69a78356c35a2a6fa3b8248430f` is the current RED. Candidate
  identity jobs `95181435476` (Python 3.10), `95181435516` (3.11), and
  `95181435533` (3.12) each reported one legitimate Darwin-only skip and then
  failed the over-broad one-PASS parser. Governance job `95181435523`
  reproduced the same skip and local-gate failure.
- v3 statically pins the sole exception as exact node
  `tests/test_subject_authorization_runner.py::test_verify_uses_canonicalized_default_temp_root_and_cleans`
  only when platform is not `darwin`, with exact reason
  `Darwin system alias integration`, exact `pytest.skip` JUnit type, one case,
  one skip, and zero failures/errors. Every other node still requires one real
  PASS. Negatives cover wrong node/platform/reason/type, xfail, malformed and
  multi-case XML, failure, and error. The subsequently accepted fresh dynamic
  proof is recorded below; no prior Green is promoted.
- The first authorized v3 focused run on exact source
  `1b4d06820e4639c4b76dee8c56d019a77a30261c` passed four selected checks and
  then stopped before dynamic topology fixtures. One stale source-test string
  still required `_verify_single_pass_junit(junit)`, while v3 intentionally
  routes main through `_verify_identity_junit`. Exact exit was 1; log SHA-256
  is `1808648384be1e46bf0b38fb4fa7eef6baba767f18a25343398edfe608033b14`.
  This is retained RED, not product failure and not Green. The bounded repair
  mechanically inspects the helper's PASS fallback and main's exact delegation;
  its fresh focused and Full Local Green results follow below.
- Fresh focused v3b on exact repaired source
  `8ae13eabbd4652746052aa8f67b7946b80267be7` passed all five selected source
  checks, proof-bound candidate exact 2, exact two-parent active exact 2,
  malformed active denial, and no-proof baseline exact 2 plus INACTIVE,
  sequence 6, T-004 PENDING, and absent pending/proof assertions. Wrapper exit
  was 0; log SHA-256 is
  `9eaaba32012c87d6a65eef329888ef986d8f34042574b57c94d096f617c319fc`.
- The one Full Local Green on that same source passed all six commands. Exact
  identity isolation completed 446 nodes; the remainder reported 2869 passed,
  12 skipped, and one pre-existing SyntaxWarning. Wrapper exit was 0; log
  SHA-256 is
  `fb790a7cf363c33004da21a05f68f9d64a10c29d9de6af8de0b8419eddb1ab4a`.
- Static reviewer v3 found one later rollback P1: a direct cleanup trap for
  TERM could release the lease without forcing shell termination. The bounded
  repair makes signal exits explicit and adds an executable TERM negative that
  requires return code 143, absent mutation marker, and removed lease. Prior
  Green remains evidence only for exact source `8ae13eab...`; fresh focused and
  Local Green are required for the changed rollback/test bytes.
- Fresh signal-focused on exact source
  `9f0e25715b0d4cc5673748a668f7908902a2eaa4` passed the executable TERM
  rc143/no-marker/lease-removed negative, all five selected checks, candidate
  exact 2, active exact 2, malformed denial, and baseline exact 2 plus exact
  INACTIVE state. Exit was 0; log SHA-256 is
  `2392204a86890c616bc1248d78ec406fa5ae1df17b0240d5dc350dc7cb138e9c`.
- The one Full Local Green on that source passed all six commands, exact 446
  identity nodes, and a remainder of 2869 passed, 12 skipped, and one existing
  warning. Exit was 0; log SHA-256 is
  `65bedd99fe6c267d48f534d77936e42d8d7cd74cd2458ec592cbc31be49b4694`.
- PR #491 hosted run `31959287396` at exact v3 head
  `7ac2f2c6b6e27cea8f488fd261f5f3e05b242846` passed all required checks.
  Python jobs `95194687238`, `95194687365`, and `95194687218` passed candidate
  identity; governance job `95194687188` passed exact merge verification.
  The slowest candidate identity step took 187 seconds and the slowest Python
  job took 304 seconds against a 1200-second timeout.
- Later CodeRabbit RED is P0=0/P1=1: malformed proof lacked dispatcher-specific
  API and CLI denial evidence. v4 adds exact outcome checks and hygiene pins,
  separately binds delivery and Mission-fixture PR metadata, and replaces the
  tautological anchor-only live-main assertion with a transition-aware check.
  No v3 Green or receipt is promoted; v4 focused and Full Local Green remain
  NOT RUN pending a fresh exclusive lease.
- First v4 focused on exact source
  `9746e434ef430125e097a7cd73df273827289c33` stopped with 2 failed and 4
  passed selected checks in 42.98 seconds. The ordering assertion used
  `str.index` on a helper name and selected its definition before the intended
  call. The preflight fixture still defined `topic_commit`/`merge_commit` after
  the rollback function had moved to unambiguous
  `delivery_topic_commit`/`delivery_merge_commit`, so `set -u` denied the
  expected-good path. Candidate/active/malformed/baseline dynamic fixtures were
  not reached. Log SHA-256 is
  `99ec548bacd73b457505a3d0d4e72a04e1ea1cfd4de747e9805c2af75a48b5f4`;
  exit marker SHA-256 is
  `4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865`.
  The bounded test-only repair targets exact call token
  `\nassert_malformed_dispatcher_nodes_denied\n` and injects current fixture
  variable names. The consumed lease cannot be reused; fresh focused remains
  required.

## Unverified boundary

The original PR #489 head `bbc6e476ae3444cef77400f28710de73f9cf7f73`
receipt and hosted Green are historical exact-head evidence only and are not in
this rebuilt topic. Fresh focused and Local Green pass on the exact v2B source.
Fresh v2E2 focused and Local Green pass only for exact historical source
`97728ce5...`; hosted v3 RED supersedes it for current acceptance. Fresh
signal-safe focused and Local Green pass only for exact source `9f0e257...`;
PR #491 Hosted Green passes only for exact v3 head `7ac2f2c...`; v4 is static
and untested until a fresh lease. Independent receipt remains absent. Exact merge readback,
proposal, task start, and production outcome remain unclaimed until
post-delivery.
