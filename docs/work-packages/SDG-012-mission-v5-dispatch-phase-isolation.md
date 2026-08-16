# Work Package: SDG-012 Mission V5 dispatcher phase isolation

## References

- Issue: #488
- Hosted RED: PR #487, run `31943149157`, job `95155106192`
- SDD: `docs/decision_records/2026-08-15-mission-v5-post-sdg-activation.md`
  and `.agentic-sdd-governance/core/POLICY_KERNEL.md`
- Protocol base: merged SDG-011 PR #486 at
  `9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0`
- Risk: L1

## Objective Contract

- Outcome: run both Mission V5 dispatcher assertions inside the same explicit
  candidate/active identity-isolation boundary as the Mission V5 suite.
- Success metric: candidate PR heads replay dispatcher assertions at their
  inactive protocol/delivery anchor; active main replays the exact active
  delivery. The two dispatcher nodes execute exactly once and the disjoint
  remainder excludes their file.
- Guardrails: do not change production dispatcher, validator, updater, or
  activation semantics. Do not use skip, xfail, deselect, `-k`, abbreviation,
  `continue-on-error`, or a production runtime phase environment.
- Keep condition: the identity harness contains the dispatcher file at exact
  count 2, both exact node IDs, and total count 446; AST guards reject every
  skip/xfail/importorskip bypass; both local and hosted remainders contain one
  exact ignore; candidate remains unauthorized while active assertions remain
  unchanged.
- Rollback condition: either phase admits incorrect authority, a node is lost
  or duplicated, collection count drifts, CI pins drift, or verification fails.

## Scope

- In scope: dispatcher test-only phase-neutral snapshot fixture; identity
  harness count/collection; local and hosted remainder exclusions; CI pins;
  one closed SDG-012 compatibility delivery; this WP, strict DEP, claim/event,
  gate, independent review, hosted CI, and merge readback.
- Non-scope: production dispatcher/validator/updater bytes, activation proof,
  authority, task progress/ledger, product behavior, private/live data,
  production, deployment, release, billing, credentials, L2, or L3.
- Dependencies: exact clean main
  `9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0`; Issue #488; retained hosted
  RED from PR #487.
- Evidence requirement: exact hosted RED, static phase/collection assertions,
  focused candidate and active Green, exact 446-node collection, disjoint
  remainder, strict DEP, full Local Green under an external exclusive lease,
  independent review, one hosted run, and exact merge readback.

## CodeRabbit remediation v2

- PR #489 reported five valid review findings: rollback branch/worktree safety,
  two-phase rollback verification, semantic node/bypass guards, and exact proof
  state wording.
- The remediation topic is rebuilt from exact protocol base
  `9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0` on branch
  `agent/sdg012-mission-v5-dispatch-phase-isolation-v2`. It does not contain or
  descend from PR #489's stale receipt commit.
- The Builder source keeps `.sddgov/reviews/REV-SDG-012.json` absent. A fresh
  gate must bind the final source before an independent reviewer adds the only
  receipt commit.
- Pre-merge checks bind only their exact topic head. Merge/readback, proposal,
  task start, and production outcome remain post-delivery and unclaimed.
- Fresh focused and Full Local Green pass on exact rebuilt source
  `bcd2686eb9dff28365a8bd24ae600e808506885e`; a fresh independent receipt and
  hosted CI remain separate pre-merge gates.
- Security re-review found three additional fail-closed requirements. The
  per-node harness must prove one real JUnit PASS rather than accept `rc=0`
  after skip or non-strict xfail; its AST guard must reject alias, dynamic
  access, and string-spelled outcome bypasses. Rollback must bind canonical
  origin and freshly fetched exact delivery state, preserve reviewed phase
  bytes outside the repository, complete candidate/active/malformed phase proof
  before the revert, then claim only base-compatible INACTIVE proof after the
  revert. The earlier Green remains evidence for its exact source only; this
  remediation requires fresh focused and Local Green before review.
- Focused v2C falsified one rollback assumption: overlaying the later reviewed
  SDG-012 runner into PR #487's proof topology correctly fails its immutable
  trust-root hash. v2D therefore retains and hashes that reviewed runner without
  executing it in proof-bearing candidate/active/malformed fixtures. Those
  fixtures keep the proof-bound runner and overlay only the reviewed dispatcher
  test and outcome harness. The reviewed runner executes after revert only on
  the no-proof baseline, where exact INACTIVE/sequence 6/T-004 PENDING and
  absent pending/proof files are required. Proof validation is unchanged.
- Fresh v2D focused and the one Builder Full Local Green now pass on exact
  source `1e1c23eae226446bd79b8d9809bc7716658fa546`. The focused matrix proves
  proof-bound candidate and active exact nodes, malformed denial, and the
  retained-runner no-proof baseline. Full Green proves all six commands,
  exact 446-node identity isolation, and the disjoint remainder. Independent
  review, hosted CI, and delivery readback remain separate mandatory gates.
- Post-sign dev6 verification then failed before merge with exact error
  `rollback record is missing or incomplete`. The signed receipt from that
  attempt is not reusable and is absent from this Builder lineage. v2E keeps
  every rollback safeguard and adds the exact dev6 top-level
  `rollback_version: 1.0`, `target:`, `command:`, and `verify:` schema; fresh
  focused, Local Green, independent review, and hosted CI are required for the
  changed bytes.
- The corrected v2E2 focused matrix and the one Full Local Green pass on exact
  source `97728ce5f524cc6029a798abe7f34c2828231697`. Focused proof includes direct
  dev6 parser acceptance, candidate/active dispatch, malformed denial, and the
  exact no-proof INACTIVE baseline. Full Green retains exact 446-node identity
  isolation and the disjoint remainder. Fresh review and hosted CI remain
  mandatory.

## Hosted platform-skip remediation v3

- PR #490 run `31953893529` at exact head
  `0ebb5ae33c5ed69a78356c35a2a6fa3b8248430f` failed candidate identity on
  Python 3.10/3.11/3.12 jobs `95181435476`, `95181435516`, and `95181435533`,
  plus governance job `95181435523`.
- Each Linux run reached the one historical Darwin-only identity node, reported
  exact `1 skipped`, then v2E rejected it because genuine one-PASS JUnit proof
  had been applied to all 446 nodes instead of preserving the existing platform
  contract.
- v3 is rebuilt from exact base `9ddc508...` on branch
  `agent/sdg012-identity-junit-dispatcher-only-v3`; no prior receipt or gate is
  reachable. It requires one genuine PASS for every node except one exact
  allowlisted off-Darwin skip, whose node, required platform, reason, JUnit
  type, count, and zero failure/error fields are all pinned.
- Dispatcher skip, xfail, importorskip, wrong node/reason/platform, malformed
  or multi-case JUnit, failure, and error remain denied. Production authority
  code and the 446-node collection contract remain unchanged.
- This changed source is static-only until a fresh external exclusive test
  lease is granted. Earlier Green and review never transfer to v3.
- CodeRabbit's rollback finding is accepted: rollback now atomically acquires
  one external exclusive lease before initial preflight, holds it through
  postproof, and freshly rechecks canonical origin, symbolic main, full
  tracked/untracked cleanliness, exact fetched delivery refs/parents/tree, and
  absent proposal/proof/pending authority immediately before revert. Genuine
  tests deny lease collision, missing owner confirmation, dirty state, proof
  presence, and a changed remote main.
- The safe literal-reuse suggestion is accepted: the historical SDG-011 test
  imports `mission.SDG011_RELEASE` and separately pins its exact literal. The
  topology negative is also strengthened: a real non-anchor descendant reaches
  the SDG-012 compatibility checker and is denied, while the anchor keeps its
  earlier denial boundary.
- Two review comments are rejected as architecture mismatches. An audit-only
  gate intentionally binds an ancestor reviewed source and has no receipt until
  the later independent signing commit; dev6 verifies that chronology. The
  repository intentionally contains no trust key because the verifier uses the
  governed external trust root; v3 does not add or weaken either mechanism.
- The first v3 focused run on source `1b4d06820e4639c4b76dee8c56d019a77a30261c`
  stopped after four static checks passed because its self-test still searched
  for the superseded direct `_verify_single_pass_junit(junit)` call. The
  implementation correctly delegates through `_verify_identity_junit`; this
  bounded repair makes the test inspect that exact main call and the helper's
  exact PASS/platform-skip branches. The RED is retained and never promoted.
- Fresh focused and Full Local Green now pass on exact repaired source
  `8ae13eabbd4652746052aa8f67b7946b80267be7`. Focused proves the exact
  allowlist/negative, rollback, non-anchor topology, candidate, active,
  malformed, and no-proof baseline matrix. Full Green proves all six commands,
  exact 446-node isolation, and the disjoint remainder. Independent review,
  hosted Green, and delivery readback remain mandatory and unclaimed.
- Static reviewer v3 then found one P1 in rollback signal handling: trapping
  cleanup directly for HUP/INT/TERM could release the external lease without
  forcing shell termination. The bounded repair gives signals exact nonzero
  exits 129/130/143 and leaves cleanup exclusively on EXIT. An executable
  negative must prove TERM returns 143, never reaches the mutation marker, and
  removes the lease. Prior Green remains bound only to its exact source.
- Fresh signal-focused and Full Local Green now pass on exact source
  `9f0e25715b0d4cc5673748a668f7908902a2eaa4`. Focused includes the executable
  TERM negative plus the complete prior matrix; Full Green proves all six
  commands, exact 446-node isolation, and the disjoint remainder. Independent
  review, hosted Green, and delivery readback remain pending.

## Claim

- Agent: codex
- Claimed at: 2026-08-16T11:11:20Z
- Expires at: 2026-08-16T19:11:20Z
