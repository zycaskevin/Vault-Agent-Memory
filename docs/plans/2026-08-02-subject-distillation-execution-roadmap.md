# Vault Agent Memory — Subject Distillation Execution Roadmap

**Date:** 2026-08-02
**Repo:** `zycaskevin/Vault-Agent-Memory`
**Original delivery base inspected:** `3bbb07a03c4a1134e37b585af458264d2c96d709`; this is historical delivery context, not an implementation base
**Current repair base:** `167b2eec443bc2e6ad0af21cb36a8b01c7cae5f7` plus this owner-authorized docs-only LT-C candidate
**Planning status:** docs-only LT-C alignment and rebaseline in progress; this document is not implementation authorization
**Current authorization:** local docs-only contract/planning edits, manifest rebind, mechanical validation and fresh review only
**Remaining boundary:** no commit/push/PR/GitHub write, merge, deployment, production migration, GB10/private/live shadow, B-000, or T-001 without separate later authorization

---

## 1. One-sentence verdict

Vault Agent Memory should continue with **Agent Memory Governance** as the product north star, but the immediate engineering plan must narrow to **Subject Distillation governance closure first**, then T-001 baseline-control implementation, then public-safe T-002+ slices; retrieval/temporal/graph work must wait until the baseline/progress/evidence control plane can prove what changed.

---

## 2. Evidence inspected

| Evidence | Current observation | Planning impact |
|---|---|---|
| Default branch | GitHub default branch is `main`; local HEAD and `origin/main` both `3bbb07a03c4a1134e37b585af458264d2c96d709` during inspection | Plan is grounded on current public main, not old chat state |
| Delivery state | Branch `docs/subject-distillation-b000-handoff` carries exactly five changed canonical/baseline files and three planning/handoff files | This eight-file candidate is the clean reviewed delivery unit; B-000 implementation must still use its own later branch, scope and review unit |
| Product strategy | `docs/strategy/README.md`, `product-architecture.md`, `killer-demo.md`, `90-day-validation.md` position Vault as the memory governance layer for multi-agent teams | Product work should sell governance, not generic RAG/search |
| Subject overview | `docs/subject-distillation.md` says runtime is not implemented; canonical package is `specs/subject-distillation/` | Runtime claims must remain blocked until implementation evidence exists |
| Parent epic | GitHub #410 is open: governed Subject Distillation baseline with fail-closed validation | #410 remains the current epic |
| Current executable blocker | GitHub #421 remains blocked on the superseded baseline `d2b883e518cbc495`; B-000 is now tracked separately in #422 | T-001 must not reuse the old authorization and cannot begin until B-000 passes and a separate T-001 receipt verifies |
| Adjacent open issues | #413 retrieval benchmark, #414 semantic/vector retrieval, #415 temporal validity, #416 entity/edge graph extraction | These are valid post-baseline workstreams, but should not jump ahead of #421/T-001 gates |
| LT-C candidate baseline | Canonical validator passes for candidate `51625dffe08539b6`, full digest `51625dffe08539b60520b4c21c4793cc19aad0dd63f8066d4e0c5f277056a08f`; fresh ordered review evidence is still pending | This candidate cannot start B-000 until design §20.1 evidence PASS, docs delivery commit, exact base selection, and a new five-value owner instruction |
| Existing task package | `specs/subject-distillation/tasks.md` declares B-000 and T-001..T-033 | Preserve canonical order; use grouped milestones for management, not to rewrite task authority |

---

## 3. Roadmap review: what to change

### 3.1 What is good

1. **Strong governance posture:** The existing Subject Distillation plan correctly separates integrity, review, authorization, progress, evidence, and release.
2. **Public/private boundary is explicit:** The package repeatedly excludes private data, GB10/live shadow, production migration, and real person/org data from public implementation.
3. **Product wedge is coherent:** Strategy docs already converge on “memory governance for multi-agent teams,” not just a memory database.
4. **Open issues map to meaningful product layers:** #413–#416 are real supporting capabilities: benchmark, semantic retrieval, temporal validity, and graph extraction.

### 3.2 Structural problems to fix before more coding

| Problem | Current symptom | Required optimization |
|---|---|---|
| Bootstrap cycle | T-001 required the authorization verifier before T-001 created it | Keep B-000 as a separate governance/bootstrap lane, outside progress ledger and outside product implementation |
| Baseline/authorization coupling | Old baseline authorization cannot survive canonical byte changes | Every canonical edit must lead to manifest rebind, fresh review, and new exact authorization before implementation |
| Task size drift | T-001 originally mixed identity reader, auth verifier, evidence validator, progress ledger, environment evidence, tests, and review gates | T-001 may remain one canonical task, but execution must be managed as smaller non-authority substeps with one owner/test boundary each |
| Descriptive acceptance criteria | Some gates were prose-heavy and left command behavior to implementers | Every executable slice needs exact commands, expected exit code, stdout/stderr contract, artifact path, and failure disposition |
| Waiver ambiguity | “Pre-existing non-blocking failure” lacked owner, ceiling, and evidence policy | Default rule: zero waiver for governance tasks unless an owner-approved normative amendment names the exception before execution |
| Product-roadmap mixing | Retrieval/semantic/graph issues are tempting but not safe until baseline controls exist | Use explicit dependency gates: post-T-001 only, public-safe only, benchmark before ranking changes |

---

## 4. Optimized development lanes

### Lane G — Governance and authorization control plane

**Purpose:** Make future tasks mechanically authorized, reviewable, and non-self-approving.

**Exit condition:** New canonical baseline passes mechanical integrity, fresh spec/quality/security review, and exact owner authorization is available for the next executable scope.

### Lane I — T-001 baseline-control implementation

**Purpose:** Implement the minimal scripts/schemas/tests/evidence/progress controls needed to start governed Subject Distillation work safely.

**Exit condition:** T-001-only implementation passes focused, hostile, baseline, regression, and fresh review gates; progress ledger can mark T-001 complete without mutating canonical task checkboxes.

### Lane S — Subject Distillation governed vertical slices

**Purpose:** Implement T-002..T-031 in dependency order using public-safe synthetic fixtures/evidence. T-032 is a separate operator-private lane and is never implied by Lane S authorization.

**Exit condition:** Generic Subject Core + Person v1 is implemented through final attestation; Organization remains contract-only until separately authorized.

### Lane R — Retrieval and product proof

**Purpose:** Turn Subject artifacts into searchable, measurable, cited, and demonstrable public value.

**Exit condition:** Public benchmark (#413) precedes semantic/vector ranking changes (#414); temporal validity (#415) and graph extraction (#416) are validated by synthetic fixtures and do not use private data.

### Lane P — Product adoption and self-host pilots

**Purpose:** Prove the product wedge: candidate-first memory governance across agents.

**Exit condition:** The killer demo is runnable, documented, and used in real OSS/self-host workflows before cloud/enterprise expansion.

### Lane LT — Long-term identity/behavior governance roadmap

**Purpose:** Extend Subject governance without creating a second persona SSOT or allowing model-generated content to rewrite human identity.

**Merge into the current canonical contract only as invariants:** four conceptual responsibility planes map onto existing Subject evidence/candidates/policy/model/context projections；Behavioral Diff is candidate-only；authorship/producer/model provenance is preserved；decision/persona output grants no action authority；snapshots are deterministic derived projections；evaluation must measure grounding, boundary/context sensitivity, drift and abstention separately.

**Deferred implementation:** dual Evidence/Policy retrieval, Runtime Policy Cards, Virtual Session Persona Snapshot productization, Canonical Persona IR, training-export datasets, SFT/DPO/LoRA and cross-model deployment. These depend on T-001 control plane, T-002/T-003 public fixtures/traceability, relevant Subject authority/model/context tasks, and a fresh privacy/security review. Model training additionally requires separate private-data, consent, spend and deletion authorization.

**Exit condition:** Each future artifact has one existing Subject source of truth, explicit provenance/authority/retention boundaries, synthetic negative tests, rollback, and no path from observation or AI output directly to approved policy.

---

## 5. Milestone sequence

| Milestone | Goal | Primary issue/docs | Start gate | Stop/exit gate |
|---|---|---|---|---|
| M0 — Planning alignment | Freeze roadmap and progress anchor | This file + `SUBJECT_DISTILLATION_PROGRESS.md` | Current live repo inspected | Plan exists, progress anchor updated, no product implementation side effects |
| M1 — LT-C rebaseline | Repair exact-base/evidence/environment/interface gaps and align the long-term persona report without adding runtime | `specs/subject-distillation/*`, planning/handoff docs | Arthur docs-only LT-C authorization | New manifest PASS + retrievable design §20.1 ordered-review evidence P0=0/P1=0; no B-000/T-001 code or Git side effect |
| M2 — B-000 bootstrap | Implement authorization schema/verifier/bootstrap tests only | #422, B-000 in `tasks.md`, Codex handoff | Clean reviewed base + exact digest-bound B-000 owner instruction | B-000 tests/ruff/fresh security review PASS; stop before T-001 |
| M3 — T-001 baseline control | Implement T-001 scripts/schemas/progress/evidence | #421, T-001 | T-001 receipt verifies under B-000 | T-001 ledger complete + reviews PASS |
| M4 — Public fixture and traceability foundation | T-002/T-003 | #410 | T-001 complete | 43 SBE fixture owners + machine-readable traceability PASS |
| M5 — Subject core and policy substrate | T-004..T-010 | #410 | M4 complete | generic contracts, DB lifecycle, v15 DDL, store, auth, policy, candidate bridge PASS |
| M6 — Evidence/model/context runtime | T-011..T-020 | #410 | M5 complete | evidence, assertions, model assembler, grants, Context Pack, decisions, relationships, fragments, Organization compatibility PASS |
| M7 — Surfaces/evaluation/recovery/closure | T-021..T-033 | #410 | M6 complete | CLI/MCP/Gateway, evaluation, backup/rollback, privacy/log, full regression, fresh reviews, attestation PASS |
| M8 — Retrieval proof slices | #413..#416 | #413, #414, #415, #416 | M4 complete for Subject-specific benchmark; generic read-only benchmark preparation may begin after M3 | benchmark before semantic ranking; temporal and graph contracts public-safe PASS |
| M9 — Adoption loop | Killer demo + 90-day validation | `docs/strategy/*` | At least local demo stable | installs, real agent workflows, self-host/team demand evidence collected |

---

## 6. Atomic tasks

Each task below is intentionally smaller than the canonical T-task when needed. These are **execution management atoms**, not replacements for canonical T-IDs.

### G-series — Governance and baseline readiness

| ID | Owner role | Objective | Inputs | Outputs | Allowed files/scope | Acceptance commands/evidence | Depends on | Reauth? | Rollback unit |
|---|---|---|---|---|---|---|---|---|---|
| G-001 | Contract steward | Freeze LT-C scope/non-goals | owner authorization + long-term report + prior findings | explicit current/deferred decisions | docs only | no runtime/schema implementation path added；scope readback | none | No | restore owned docs |
| G-002 | Domain architect | Align canonical interfaces and long-term mapping | requirements/design/tasks/traceability | one SSOT mapping + exact CLI/DB/setup contracts | four canonical Markdown files | `git diff --check`; no new SBE ID; all 43 existing IDs preserved | G-001 | No | restore captured canonical bytes |
| G-003 | Execution planner | Synchronize roadmap/progress/handoff | canonical candidate | aligned three planning docs | docs/plans only | exact base/evidence/offline/owner gates agree | G-002 | No | restore captured planning bytes |
| G-004 | Manifest owner | Rebind after canonical edits | five canonical files | updated manifest | manifest only | stale manifest fails before edit; validator PASS after rebind | G-002 | No | restore captured manifest |
| G-005 | Parent verifier | Build exact review inputs | selected delivery base + candidate paths | normative-tree and delivery-diff canonical bytes/digests | repo-external public-safe evidence inputs | independently recomputed path/hash inventories match candidate | G-003/G-004 | No | discard external candidate evidence |
| G-006 | Reviewer A | Fresh spec/design/plan review | exact G-005 candidate | public-safe review result | read-only | P0=0/P1=0; every P2 disposition explicit | G-005 | No | reject candidate |
| G-007 | Reviewer B (different principal) | Fresh quality/security review | unchanged exact candidate + Review A | public-safe review result | read-only | P0=0/P1=0; evidence/base/environment/interfaces reviewed | G-006 | No | reject candidate |
| G-008 | Parent verifier | Canonicalize repo-external evidence | both reviews + exact hashes | retrievable design §20.1 body, locator, SHA-256 | outside repo only | retrieve-by-locator round trip; body digest/tree/diff/counts PASS | G-007 | No | discard evidence body |
| G-009 | Handoff owner | Generate next authorization packet | reviewed baseline + evidence locator/digest | owner-readable B-000 tuple template | handoff/progress only before final review; otherwise no write | packet names lane/base/baseline/full/scope and evidence proof | G-008 | Yes before Git delivery/B-000 | stop |
| G-010 | Repository owner | Select committed implementation base and decide B-000 | accepted docs delivery commit + G-009 | exact approval or stop | trusted channel only | five explicit byte-equal owner values; commit tree contains reviewed bytes | G-009 + separately authorized Git delivery | Yes | stop |

### B-series — B-000 bootstrap implementation atoms

| ID | Owner role | Objective | Outputs | Acceptance | Depends on | Reauth? | Rollback |
|---|---|---|---|---|---|---|---|
| B-001 | Trusted parent | Offline environment + exact preflight | local `.venv` + preflight record | wheelhouse-only install; exact base/evidence/baseline/scope/worktree PASS | G-010 | No within exact B-000 auth | remove local `.venv`; no repo write |
| B-002 | B-000 implementer | Write genuine RED tests | `tests/test_subject_authorization_bootstrap.py` | focused test fails because desired verifier/schema are absent, not because of import/fixture error | B-001 | No | restore owned test path |
| B-003 | B-000 implementer | Implement authorization schema | implementation authorization schema | strict schema tests including type/canonical/resource boundaries | B-002 | No | restore owned schema path |
| B-004 | B-000 implementer | Implement verifier CLI/adversarial matrix | verifier + completed test matrix | fixed ALLOW/DENY/ERROR, no echo, descriptor/race/resource controls | B-003 | No | restore owned verifier/test paths |
| B-005 | B-000 implementer | Run deterministic gates | public-safe command results | baseline, pytest, Ruff, diff, exact three-path status all PASS | B-004 | No | none |
| B-006 | Parent verifier | Full readback and exact diff inventory | candidate hashes/readback result | all three files read; baseline unchanged; hostile controls inspected | B-005 | No | reject candidate |
| B-007 | Fresh spec reviewer | Ordered spec compliance review | Review 1 result | PASS P0=0/P1=0 on exact tree | B-006 | No | reject candidate |
| B-008 | Different security reviewer | Ordered quality/security review | Review 2 result | PASS P0=0/P1=0 on unchanged exact tree + Linux gate | B-007 | No | reject candidate |
| B-009 | Parent verifier | Stop/return packet | machine-checkable handoff | hashes, RED/GREEN, OS/Python, unresolved, no Git side effects | B-008 | No | stop before T-001 |

### I-series — T-001 baseline-control atoms

| ID | Owner role | Objective | Outputs | Acceptance | Depends on | Reauth? | Rollback |
|---|---|---|---|---|---|---|---|
| I-001 | Trusted parent | Establish T-001 local-safe environment | `.venv` local only, environment notes | offline exact setup succeeds; accepted B-000 tree and actual T-001 receipt verify | B-009 + accepted B-000 Git delivery + verified T-001 receipt | Yes, separate T-001 owner decision | remove `.venv` |
| I-002 | Control-plane test owner | RED coverage for baseline/evidence/progress controls | baseline/progress tests | tests fail for missing reader/evidence/progress artifacts | I-001 | No | restore owned tests |
| I-003 | Baseline-control owner | Baseline ID reader | `scripts/read_subject_baseline_id.py` | reads only verified manifest baseline_id; mismatch fails closed | I-002 | No | restore script |
| I-004 | Evidence-contract owner | Evidence schemas | evidence schemas | schema tests reject secrets/private paths/malformed artifacts | I-002 | No | restore schemas |
| I-005 | Evidence-contract owner | Evidence validator | `scripts/validate_subject_evidence.py` | validates environment; hostile carriers DENY without echo | I-004 | No | restore script |
| I-006 | Progress-contract owner | Progress schema and seed ledger | progress schema + ledger | exact T-001 IN_PROGRESS seed binds manifest/tasks | I-003 | No | restore ledger/schema |
| I-007 | Progress-contract owner | Validator + atomic transition writer | validate/update progress scripts | transition/dependency/evidence validation + fsync/atomic-replace crash matrix PASS | I-006 | No | restore scripts |
| I-008 | Evidence producer | Environment evidence artifact | environment evidence | public-safe source commit/status/python/sqlite/normative hashes | I-005/I-007 | No | delete owned evidence artifact |
| I-009 | Verification owner | T-001 mandatory command run | transcripts | every command exits 0; zero waiver absent new amendment | I-008 | No | writer records BLOCKED |
| I-010 | Two independent reviewers | T-001 fresh reviews | review evidence | ordered spec and quality/security PASS, P0=0/P1=0 | I-009 | No | keep task non-completed |
| I-011 | Progress-contract owner | Complete T-001 transition | updated ledger | atomic writer validates IN_PROGRESS→COMPLETED + evidence refs | I-010 | No | writer records BLOCKED if legal |
| I-012 | Parent reporter | T-001 closure report / optional issue update | local report or #421 comment | exact baseline/tests/remaining side effects; no external write without authority | I-011 | Yes for any GitHub/PR/push write | keep report local |

### V-series — Verification and quality gate atoms

These atoms are not feature work. They normalize evidence so that every later implementation task can be mechanically judged instead of argued from prose.

| ID | Owner role | Objective | Outputs | Acceptance | Depends on | Rollback |
|---|---|---|---|---|---|---|
| V-001 | Verification owner | Normalize acceptance command blocks | command matrix | setup/argv/exit/stdout/stderr/artifact all exact | G-005 | revert matrix |
| V-002 | Verification owner | Define RED/GREEN/HOSTILE/REGRESSION classes | checklist | evidence classes cannot substitute for each other | V-001 | revert checklist |
| V-003 | Evidence owner | Define artifact completeness | checklist | missing artifact blocks completion | V-001 | revert checklist |
| V-004 | Traceability owner | Define coverage gate | mapping rule | no missing E-* or duplicate finite-ID owner | V-003 | revert gate |
| V-005 | Review coordinator | Define no-guess checklist | reviewer checklist | every material field has owner/source; guessed policy is P1 | V-003 | revert checklist |
| V-006 | Manifest owner | Define docs-change rebind check | Work Packet rule | stale-baseline FAIL before rebind and PASS after | G-004 | revert rule |
| V-007 | Review coordinator | Define fresh review templates | template set | exact baseline/tree/diff + P0/P1/P2 | G-005 | discard templates |
| V-008 | Evidence owner | Capture minimum evidence bundle index | evidence index | focused/hostile/baseline/regression/diff/review named separately | V-002..V-007 | remove index |

### E-series — Risk, rollback, and side-effect atoms

These atoms prevent a good plan from becoming unsafe execution. They are especially important because this delivery carries canonical docs-only changes that must remain separate from B-000 implementation.

| ID | Owner role | Objective | Outputs | Acceptance | Depends on | Rollback |
|---|---|---|---|---|---|---|
| E-001 | Execution planner | Define rollback unit for each atom | rollback column | exact owned files/artifacts/ledger action named | G-001 | update table |
| E-002 | Privacy/evidence owner | Define artifact retention | retention note | public-safe retained; private/live/raw excluded | E-001 | update note |
| E-003 | Parent reporter | Define issue/comment evidence norm | template | baseline/scope/verdict/side effects/next gate without leak | E-002 | update template |
| E-004 | Parent verifier | Define branch hygiene | preflight checklist | branch/base/worktree checked at every gate | E-001 | update checklist |
| E-005 | Security reviewer | Define no-mix scopes | prohibition list | docs/bootstrap/implementation/migration/private/release/deploy separate | E-001 | update list |
| E-006 | Parent verifier | Define zero-side-effect check | local checklist | no external/destructive state without authority | E-005 | update checklist |
| E-007 | Risk owner | Define release-blocking register | risk rows | every P0/P1 names mitigation/stop/owner | E-006 | update register |
| E-008 | Designated authority | Define failure/waiver policy | exception table | default zero waiver; bounded explicit exception only | E-007 | update policy |

### S-series — Subject Distillation atomic implementation tasks after T-001

Canonical task owner map（one accountable role per implementation task；review/release roles remain independent）：

| Task | Accountable owner role | Task | Accountable owner role |
|---|---|---|---|
| T-001 | Control-plane owner | T-018 | Relationship/privacy owner |
| T-002 | Synthetic-fixture owner | T-019 | Fragment-contract owner |
| T-003 | Traceability owner | T-020 | Organization-contract owner |
| T-004 | Subject-contract owner | T-021 | Setup/lifecycle owner |
| T-005 | DB-lifecycle owner | T-022 | CLI surface owner |
| T-006 | Schema/migration owner | T-023 | MCP surface owner |
| T-007 | Subject-store owner | T-024 | Gateway/OpenAPI owner |
| T-008 | Authentication owner | T-025 | Evaluation-gate owner |
| T-009 | Policy/authority owner | T-026 | Evaluation-governance owner |
| T-010 | Candidate-bridge owner | T-027 | Recovery owner |
| T-011 | Evidence-metadata owner | T-028 | Privacy/log-gate owner |
| T-012 | Operator-private storage owner | T-029 | Final verification owner |
| T-013 | Assertion/provenance owner | T-030 | Documentation owner |
| T-014 | Model-assembly owner | T-031 | Review coordinator + three independent reviewers |
| T-015 | Grant owner | T-032 | Separately authorized private-pilot operator |
| T-016 | Context Pack owner | T-033 | Reviewed attester owner; release authority remains separate |
| T-017 | Decision-ledger owner |  |  |

Only one canonical T-task may be `IN_PROGRESS`. Parallel work is limited to
read-only review/research or repo-external Work Packet drafting that does not edit
an owned source path or claim task progress. Changing that rule requires a new
progress contract, rebaseline, fresh review and new authorization.

These rows preserve the canonical T-002..T-033 authority while adding execution-management fields requested for atomic planning. Each row still needs a full Work Packet before coding; this table is the roadmap-level atom index.

| ID | Canonical | Objective | Outputs | Acceptance | Depends on | Reauth? | Rollback |
|---|---|---|---|---|---|---|---|
| S-001 | T-002 | Add public synthetic fixture taxonomy | fixture manifest, person/org/fragments/migration fixtures, privacy test | 43 SBE IDs unique; no real/private data; fixture privacy test PASS | I-011 | No within authorized T-002 | remove created fixtures/tests |
| S-002 | T-003 | Add machine-readable SBE traceability | `sbe-traceability.json` seed and exporter | no missing/extra/duplicate E-*; exporter PASS | S-001 | No | remove traceability seed/exporter |
| S-003 | T-004 | Implement generic Subject contracts | core contract modules/tests | existing L0-L3/candidate behavior remains compatible; contract tests PASS | S-002 | Maybe if canonical contract changes | revert contract modules/tests |
| S-004 | T-005 | Implement fail-closed DB lifecycle preflight | lifecycle preflight helper/tests | schema status mismatch blocks; no silent upgrade | S-003 | No | revert helper/tests |
| S-005 | T-006 | Add v15 Subject DDL and explicit migration | v15 DDL/migration registration/tests | migration positive + hostile + rollback tests PASS | S-004 | Yes for migration/release use | revert migration registration/DDL |
| S-006 | T-007 | Add typed Subject store | store module/tests | typed CRUD obeys transaction and legacy compatibility boundaries | S-005 | No | revert store/tests |
| S-007 | T-008 | Implement principal authentication bindings | auth binding module/tests | body/tool-profile spoofing denied; bound principal accepted | S-006 | No | revert auth binding files |
| S-008 | T-009 | Implement role, authority, and assertion policy engine | policy engine/tests | event-time authority and assertion class separation enforced | S-007 | No | revert policy files |
| S-009 | T-010 | Bridge existing candidate gates | candidate sidecar/bridge/tests | generic promote cannot directly promote Subject payload | S-008 | No | revert bridge/tests |
| S-010 | T-011 | Implement evidence metadata and retention modes | evidence metadata helpers/tests | pointer/private/ephemeral rules enforced without raw leak | S-009 | No | revert evidence helpers/tests |
| S-011 | T-012 | Implement operator-local private evidence lane | local private-lane hooks/tests | private lane stays out of public repo/evidence | S-010 | Yes for private/live use | revert hooks/tests |
| S-012 | T-013 | Implement immutable assertions and provenance | assertion module/tests | support/counter-evidence and provenance immutability PASS | S-011 | No | revert assertion files |
| S-013 | T-014 | Implement deterministic Subject Model assembler | assembler/tests | model output deterministic; no cloud dependency | S-012 | No | revert assembler/tests |
| S-014 | T-015 | Implement access grants and revocation | grant module/tests | revocation blocks future packs but preserves legal history | S-013 | No | revert grant files |
| S-015 | T-016 | Implement Context Pack generator | pack generator/tests | purpose-limited packs enforce grant/policy at generated and sealed time | S-014 | No | revert generator/tests |
| S-016 | T-017 | Implement append-only decision event validation | decision event validator/tests | append-only events; no overwrite of recommendation/choice/outcome | S-015 | No | revert decision files |
| S-017 | T-018 | Implement directional and temporal relationships | relationship module/tests | temporal/directional/perspective invariants PASS | S-016 | No | revert relationship files |
| S-018 | T-019 | Implement pure Subject Fragment validator | fragment validator/tests | deterministic validation; no persistence/transmission side effect | S-017 | No | revert validator/tests |
| S-019 | T-020 | Verify Organization contract compatibility | org compatibility fixtures/tests | contract-only org examples pass; no org runtime sneaks in | S-018 | No | revert org compatibility files |
| S-020 | T-021 | Implement default-on safe-envelope Subject setup | capability-state docs/code/tests | new interactive setup ends `active` with root, sealed privacy/model policies and empty sealed model; legacy/direct/non-interactive stays `available_uninitialized`; collection/promotion/private copy remain separately gated | S-019 | Maybe if capability policy changes | revert capability files |
| S-021 | T-022 | Add CLI Subject command tree | CLI commands/tests/docs | CLI cannot self-prove principal via body field | S-020 | No | revert CLI additions |
| S-022 | T-023 | Add minimal MCP Subject tools | MCP handlers/tests/docs | MCP profile is not authorization boundary; tests PASS | S-021 | No | revert MCP additions |
| S-023 | T-024 | Add Gateway Subject adapters | Gateway/OpenAPI/tests | bearer/body identity override denied; contract metadata correct | S-022 | Yes before external exposure | revert Gateway additions |
| S-024 | T-025 | Implement frozen evaluation gate | evaluation gate/tests/fixtures | frozen manifest, hard-failure, scoring rules enforced | S-023 | No | revert evaluation files |
| S-025 | T-026 | Implement sign-off and prospective adjustment | signoff/prospective tests | no post-close learning into same gate; signoff distinct | S-024 | No | revert signoff files |
| S-026 | T-027 | Prove backup and rollback recovery | migration and backup-restore evidence | v14→v15 backup/rollback recovery PASS | S-025 | Yes for migration use | restore backup/revert migration files |
| S-027 | T-028 | Run privacy and log-redaction gate | privacy/log transcripts | no raw evidence, private path, token-shaped strings in logs | S-026 | No | remove generated evidence and fix source |
| S-028 | T-029 | Run full synthetic and legacy regression gate | unit/fixture/surface/legacy transcripts and final traceability | full synthetic+legacy gates PASS; SBE node mapping complete | S-027 | No | append BLOCKED evidence; revert candidate code if needed |
| S-029 | T-030 | Update canonical docs and changelog | docs/changelog updates | docs match implemented behavior; no post-review drift | S-028 | Yes if canonical bytes change | restore captured pre-doc state |
| S-030 | T-031 | Fresh code/security/migration review | review JSON/evidence | P0=0/P1=0; reviewed tree digest bound | S-029 | No | reject review candidate |
| S-031 | T-032 | Private shadow pilot, separate operator-private lane | private receipt reference only | requires separate private/live authorization; remains outside Lane S/public evidence; public attestation may stay experimental if blocked | S-030 | Yes; private/live explicit only | discard private pilot artifacts |
| S-032 | T-033 | Final attestation and implementation closure | attestation artifact and final ledger transition | attestation validates evidence/review/authorization binding | S-030 and S-031 if stable, or S-031 BLOCKED allowed for experimental | Yes for release/push/merge | do not mark final complete; append BLOCKED |

### R-series — Retrieval, temporal, and graph proof slices

| ID | Owner role | Issue | Objective | Must wait for | Atomic acceptance |
|---|---|---|---|---|---|
| R-001 | Retrieval evaluation owner | #413 | Public Subject retrieval benchmark | T-001 + T-002/T-003 stable; generic harness drafting only after T-001 | fixed queries/evidence refs/provenance + numeric quality/latency baseline |
| R-002 | Retrieval implementation owner | #414 | Deterministic semantic/vector path | R-001 | provider identity, deterministic CI, stale/rebuild/fallback tests |
| R-003 | Temporal-contract owner | #415 | Temporal validity handling | S-003 or equivalent contract | effective/expiry/source time + stale/unknown tests |
| R-004 | Graph-contract owner | #416 | Entity/edge extraction | S-001/S-002 | shapes/aliases/relationships/confidence/evidence + unsafe payload DENY |
| R-005 | Demo owner | docs/strategy | Killer demo hardening | T-001 and candidate flow stable | governed demo remains runnable/public-safe |

### LT-series — Deferred long-term behavior-governance atoms

These entries are roadmap authority only. None belongs to B-000/T-001, and each
requires its own Work Packet and authorization after the named prerequisites.

| ID | Owner role | Output | Prerequisites | Minimal acceptance |
|---|---|---|---|---|
| LT-000 | Isolation/security owner | User-persona × project/org-policy × consumer-agent-role × model-render-style isolation matrix | T-004/T-008/T-009 | default deny; no implicit inheritance/evidence/authority crossover; synthetic confusion matrix + legacy compatibility PASS |
| LT-001 | Domain architect | Existing-SSOT plane/type crosswalk | LT-000 | every Evidence/Memory/Policy/Runtime concept maps to one owner; no second persona truth store |
| LT-002 | Provenance/privacy owner | Authorship and AI-contamination contract | LT-000 + T-011/T-013 | human/agent/model/third-party producer metadata preserved; AI output cannot become human-explicit without typed sourced action |
| LT-003 | Candidate/policy owner | Behavioral Diff candidate protocol | LT-000 + T-010/T-013 | diff is deterministic, provenance-bound and candidate-only; replay/stale-base/generic-promote DENY |
| LT-004 | Decision-policy owner | Decision Boundary contract | LT-000 + T-015/T-017 | action authority remains false absent independent grant; high-impact/irreversible cases ask or deny; one-field DENY twins |
| LT-005 | Model/context owner | Versioned persona/session snapshot | LT-000 + T-014/T-016 | deterministic refs-only projection, fixed per session, no raw evidence or authority, rollback/replay PASS |
| LT-010 | Retrieval/compiler owner | Dual Evidence/Policy retriever + budget/precedence compiler | R-001 + T-016 + LT-001/003 | no candidate/approved cross-stream leakage; explicit instruction precedence; provenance/fallback/stale-index tests PASS |
| LT-011 | Evaluation owner | Persona governance evaluation suite | T-025/T-026 + LT-002..005 + LT-010 | separately reports exactly Evidence Grounding, Decision Agreement, Constraint Violation Rate, Boundary Consistency, Context Sensitivity, Persona Drift, Cross-model Portability and Abstention Quality；synthetic/private data remain separated |
| LT-020 | IR architect | Canonical Persona IR v1 export view | LT-005/010/011 stable | versioned lossless provenance mapping and round-trip; derived artifact, never DB authority |
| LT-030 | Privacy/export owner | Governed SFT/DPO dataset export | T-028/T-033 + LT-020 | explicit consent/scope, minimization, revocation/deletion, AI-contamination weights, audit; raw/private default DENY |
| LT-040 | ML owner + independent privacy/security reviewers | Optional LoRA/SFT/DPO experiment | LT-030 PASS + separate private/live/spend authority | isolated/deletable artifacts, benchmarked against non-trained baseline, no unapproved data, no mutation of canonical memory/policy |

---

## 7. Dependency graph in plain language

```text
Subject Distillation execution roadmap
  -> docs-only rulefix closure
  -> new baseline manifest
  -> fresh review
  -> exact authorization
  -> B-000 authorization verifier
  -> T-001 baseline/evidence/progress controls
  -> T-002/T-003 fixtures + traceability
  -> Subject core / DB / policy / surfaces
  -> evaluation + attestation

Parallel-but-gated product proof lane:
  -> retrieval benchmark after T-001 and public fixtures are stable
  -> semantic/vector retrieval only after benchmark evidence
  -> temporal/graph slices only after their Subject contract prerequisites
  -> killer demo / pilots / cloud-enterprise decision after local public-safe demo proof
```

Do **not** run semantic/vector retrieval, temporal fact handling, or graph extraction as production features before the baseline/evidence/progress gates exist. Benchmark and contract work may start only at the dependency gates named in R-series; production claims still require their own runtime evidence and release authorization.

---

## 8. Risk register

| Risk | Severity | Mitigation |
|---|---:|---|
| Reusing stale authorization after canonical bytes change | P1 | Baseline rebind + fresh review + new exact authorization is mandatory |
| Meta-circular governance task self-authorizes | P1 | Keep B-000 outside T ledger; exact owner instruction is repo-external trust root |
| Public repo leaks private data/path/evidence | P0/P1 | Synthetic-only fixtures; content-redacted evidence; hostile secret/path tests |
| Generic memory promotion bypasses Subject governance | P1 | Candidate bridge must block direct Subject payload promotion via generic path |
| Retrieval work becomes ranking rewrite without benchmark | P2/P1 if release-blocking | #413 benchmark before #414 ranking/provider changes |
| Cloud/enterprise surfaces arrive before adoption proof | Product P1 | Follow 90-day validation; build self-host pilots before Vault Cloud |
| Over-large canonical task hides failing sub-control | P1 | Manage canonical tasks with atomic execution atoms and focused evidence |
| Dirty planning/implementation worktree causes false baseline | P1 | Preflight clean/diff inventory before every baseline/review/authorization gate |

---

## 9. Review gates for future work packets

Every future coding Work Packet should answer these before delegation:

1. Does this task depend on a tool or authorization artifact it creates itself?
2. Does it change canonical bytes? If yes, has baseline been rebound and re-reviewed?
3. Are every required command, exit code, stdout/stderr rule, and artifact path executable verbatim?
4. Is there any field or policy the implementer would have to invent?
5. Can command failure be classified as spec error, environment error, implementation error, or authorized waiver?
6. Is any pre-existing failure being silently swallowed?
7. Are docs-only remediation and product implementation separated?
8. Are private/live/migration/deploy scopes excluded unless explicitly authorized?
9. Are tests RED for the intended reason before implementation?
10. Is there a rollback unit that restores the task's side effects?

---

## 10. Recommended next action

Complete this owner-authorized docs-only LT-C repair and stop before B-000. The valid sequence is:

```text
finish canonical/planning alignment
→ rebind and mechanically validate the five-file manifest
→ build exact normative-tree + delivery-diff review inputs
→ obtain two ordered distinct-reviewer PASS results
→ retain a retrievable design §20.1 evidence body outside the repo
→ under separate Git authorization, commit/deliver the reviewed docs candidate
→ select that exact commit as a clean B-000 base
→ give Codex the exact five-value owner instruction from the handoff
→ implement only the three B-000 paths with genuine RED first
→ parent readback + fresh spec review + fresh quality/security review
→ stop
→ create a separate B-000 commit/PR only under separate Git authorization
→ after B-000 is accepted, obtain and verify a separate T-001 receipt
→ only then begin T-001
```

Do not combine B-000 and T-001 into one branch, receipt, review unit, commit, or PR.

---

## 11. Completion checklist for this planning request

- [x] Live GitHub issues inspected: #410, #421, #422, #413, #414, #415, #416
- [x] Strategy docs inspected: product architecture, killer demo, 90-day validation
- [x] Subject canonical task order inspected: B-000 + T-001..T-033
- [x] Current eight-file staged delivery inventory called out
- [x] Roadmap optimized into lanes, milestones, risks, and atomic tasks
- [x] Progress anchor synchronized in `docs/plans/SUBJECT_DISTILLATION_PROGRESS.md`
- [x] Mechanical docs check run on planning files
- [x] LT-C canonical/planning repair complete
- [x] New manifest rebound and validator PASS
- [ ] Retrievable design §20.1 ordered-review evidence PASS with P0=0/P1=0
- [x] B-000 Issue #422 created
- [x] Codex continuation handoff prepared

This document records the plan and current owner-authorized local docs-only repair. It does not authorize commit/push/PR/GitHub writes, B-000/T-001 execution, merge, deployment, private shadow, release, or production migration.
