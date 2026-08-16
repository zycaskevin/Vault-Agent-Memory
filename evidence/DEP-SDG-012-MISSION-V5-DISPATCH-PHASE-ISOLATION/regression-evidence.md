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

## Unverified boundary

The original PR #489 head `bbc6e476ae3444cef77400f28710de73f9cf7f73`
receipt and hosted Green are historical exact-head evidence only and are not in
this rebuilt topic. Review-remediation focused/Local Green, a fresh independent
receipt, and a new hosted Green remain pending. Exact merge readback, proposal,
task start, and production outcome remain unclaimed until post-delivery.
