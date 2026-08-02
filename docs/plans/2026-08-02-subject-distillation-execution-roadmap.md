# Vault Agent Memory — Subject Distillation Execution Roadmap

**Date:** 2026-08-02
**Repo:** `zycaskevin/Vault-Agent-Memory`
**Planning baseline checked from:** local worktree at `3bbb07a03c4a1134e37b585af458264d2c96d709`, matching `origin/main` at inspection time
**Planning status:** reviewed execution plan and Codex handoff source; this document is not implementation authorization
**Current delivery authorization:** Arthur explicitly authorized committing the completed baseline/planning artifacts, creating/updating GitHub issues, pushing the documentation branch, and opening a PR
**Remaining boundary:** this delivery does not authorize merge, deployment, production migration, GB10/private/live shadow, T-001, or B-000 execution without the exact digest-bound owner instruction required below

---

## 1. One-sentence verdict

Vault Agent Memory should continue with **Agent Memory Governance** as the product north star, but the immediate engineering plan must narrow to **Subject Distillation governance closure first**, then T-001 baseline-control implementation, then public-safe T-002+ slices; retrieval/temporal/graph work must wait until the baseline/progress/evidence control plane can prove what changed.

---

## 2. Evidence inspected

| Evidence | Current observation | Planning impact |
|---|---|---|
| Default branch | GitHub default branch is `main`; local HEAD and `origin/main` both `3bbb07a03c4a1134e37b585af458264d2c96d709` during inspection | Plan is grounded on current public main, not old chat state |
| Delivery state | Branch `docs/subject-distillation-b000-handoff` stages exactly four canonical/baseline files and three planning/handoff files | This PR is the clean reviewed delivery unit; B-000 implementation must still use its own later branch, scope and review unit |
| Product strategy | `docs/strategy/README.md`, `product-architecture.md`, `killer-demo.md`, `90-day-validation.md` position Vault as the memory governance layer for multi-agent teams | Product work should sell governance, not generic RAG/search |
| Subject overview | `docs/subject-distillation.md` says runtime is not implemented; canonical package is `specs/subject-distillation/` | Runtime claims must remain blocked until implementation evidence exists |
| Parent epic | GitHub #410 is open: governed Subject Distillation baseline with fail-closed validation | #410 remains the current epic |
| Current executable blocker | GitHub #421 remains blocked on the superseded baseline `d2b883e518cbc495`; B-000 is now tracked separately in #422 | T-001 must not reuse the old authorization and cannot begin until B-000 passes and a separate T-001 receipt verifies |
| Adjacent open issues | #413 retrieval benchmark, #414 semantic/vector retrieval, #415 temporal validity, #416 entity/edge graph extraction | These are valid post-baseline workstreams, but should not jump ahead of #421/T-001 gates |
| Reviewed successor baseline | Canonical validator and fresh closure review passed for baseline `0f688cf2e2472beb`, full digest `0f688cf2e2472beb22082fb16c9c344de921e06e71a5efc939c8a4c70f5ed773` | This exact baseline is the only valid starting point for the B-000 handoff; any canonical byte change invalidates the binding |
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

### Lane S — Subject Distillation public-safe vertical slices

**Purpose:** Implement T-002+ in dependency order using synthetic fixtures only.

**Exit condition:** Generic Subject Core + Person v1 is implemented through final attestation; Organization remains contract-only until separately authorized.

### Lane R — Retrieval and product proof

**Purpose:** Turn Subject artifacts into searchable, measurable, cited, and demonstrable public value.

**Exit condition:** Public benchmark (#413) precedes semantic/vector ranking changes (#414); temporal validity (#415) and graph extraction (#416) are validated by synthetic fixtures and do not use private data.

### Lane P — Product adoption and self-host pilots

**Purpose:** Prove the product wedge: candidate-first memory governance across agents.

**Exit condition:** The killer demo is runnable, documented, and used in real OSS/self-host workflows before cloud/enterprise expansion.

---

## 5. Milestone sequence

| Milestone | Goal | Primary issue/docs | Start gate | Stop/exit gate |
|---|---|---|---|---|
| M0 — Planning alignment | Freeze roadmap and progress anchor | This file + `SUBJECT_DISTILLATION_PROGRESS.md` | Current live repo inspected | Plan exists, progress anchor updated, no product implementation side effects |
| M1 — Rulefix closeout | Finish docs-only remediation for the 5 original plus 6 fresh-review P1 blockers | #421, `specs/subject-distillation/*` | Arthur docs-only approval | **Complete:** baseline `0f688cf2e2472beb` manifest PASS + fresh review P0=0/P1=0/P2=0; no T-001 code |
| M2 — B-000 bootstrap | Implement authorization schema/verifier/bootstrap tests only | #422, B-000 in `tasks.md`, Codex handoff | Clean reviewed base + exact digest-bound B-000 owner instruction | B-000 tests/ruff/fresh security review PASS; stop before T-001 |
| M3 — T-001 baseline control | Implement T-001 scripts/schemas/progress/evidence | #421, T-001 | T-001 receipt verifies under B-000 | T-001 ledger complete + reviews PASS |
| M4 — Public fixture and traceability foundation | T-002/T-003 | #410 | T-001 complete | 43 SBE fixture owners + machine-readable traceability PASS |
| M5 — Subject core and policy substrate | T-004..T-010 | #410 | M4 complete | generic contracts, DB lifecycle, v15 DDL, store, auth, policy, candidate bridge PASS |
| M6 — Evidence/model/context runtime | T-011..T-020 | #410 | M5 complete | evidence, assertions, model assembler, grants, Context Pack, decisions, relationships, fragments, Organization compatibility PASS |
| M7 — Surfaces/evaluation/recovery/closure | T-021..T-033 | #410 | M6 complete | CLI/MCP/Gateway, evaluation, backup/rollback, privacy/log, full regression, fresh reviews, attestation PASS |
| M8 — Retrieval proof slices | #413..#416 | #413, #414, #415, #416 | M3 complete; prefer M4 for subject-specific data | benchmark before semantic ranking; temporal and graph contracts public-safe PASS |
| M9 — Adoption loop | Killer demo + 90-day validation | `docs/strategy/*` | At least local demo stable | installs, real agent workflows, self-host/team demand evidence collected |

---

## 6. Atomic tasks

Each task below is intentionally smaller than the canonical T-task when needed. These are **execution management atoms**, not replacements for canonical T-IDs.

### G-series — Governance and baseline readiness

| ID | Objective | Inputs | Outputs | Allowed files/scope | Acceptance commands/evidence | Depends on | Reauth? | Rollback unit |
|---|---|---|---|---|---|---|---|---|
| G-001 | Freeze execution roadmap planning artifact | Live repo, #410/#421/#422/#413-#416, strategy docs | `docs/plans/2026-08-02-subject-distillation-execution-roadmap.md` | docs/plans only | `git diff --check -- docs/plans/2026-08-02-subject-distillation-execution-roadmap.md` | none | No | delete plan file |
| G-002 | Create planning progress anchor | execution roadmap | `docs/plans/SUBJECT_DISTILLATION_PROGRESS.md` | docs/plans only | readback contains current status + next gate | G-001 | No | delete/update progress file |
| G-003 | Close current docs-only rulefix candidate mechanically | modified `requirements.md/design.md/tasks.md`, parent verify scripts | final rulefix diff evidence | existing modified canonical docs only | parent rulefix verifier PASS; T-002..T-033 preserved; stale baseline fails before rebind | G-002 | No, still docs-only | restore captured pre-atom state; if no pre-state was captured, stop for owner direction instead of resetting to HEAD |
| G-004 | Rebind baseline manifest after docs-only canonical edits | five canonical files | updated `baseline-manifest.json` | manifest only | `python scripts/validate_subject_baseline.py --repo-root . --manifest specs/subject-distillation/baseline-manifest.json --json` returns PASS | G-003 | Yes before implementation | restore previous manifest backup |
| G-005 | Fresh review new docs baseline | new manifest + canonical files | spec/quality/security review evidence | repo-external review evidence | **Complete:** P0=0/P1=0/P2=0 bound to baseline `0f688cf2e2472beb` and exact candidate diff | G-004 | No | discard review candidate |
| G-006 | Generate next authorization packet | reviewed baseline | owner-readable authorization summary + Codex handoff | `docs/plans/2026-08-02-subject-distillation-codex-handoff.md` | packet names baseline ID/full digest/scope digest/task/non-goals | G-005 | Yes | restore captured pre-edit state |
| G-007 | Arthur authorization decision | G-006 packet | exact approval or stop | trusted channel only | owner instruction explicitly contains lane, baseline ID, full digest, and scope digest | G-006 | Yes | stop |

### B-series — B-000 bootstrap implementation atoms

| ID | Objective | Outputs | Acceptance | Depends on | Reauth? | Rollback |
|---|---|---|---|---|---|---|
| B-001 | Write RED tests for authorization bootstrap | `tests/test_subject_authorization_bootstrap.py` | focused test fails for missing verifier/schema, not for unrelated import failure | G-007 | No within B-000 auth | revert test file |
| B-002 | Implement authorization schema | `specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json` | tests cover required fields, duplicate-key/type/path/time/public-safety deny cases | B-001 | No | revert schema |
| B-003 | Implement verifier CLI | `scripts/verify_subject_implementation_authorization.py` | deny exit 2, error exit 3, success compact JSON; no secret/path echo | B-002 | No | revert script |
| B-004 | Run B-000 direct gates | command transcripts | `python -m pytest -q tests/test_subject_authorization_bootstrap.py`; `python -m ruff check ...` | B-003 | No | none |
| B-005 | Fresh B-000 security/spec review | review evidence | P0=0/P1=0 on exact B-000 tree | B-004 | No | reject candidate |

### I-series — T-001 baseline-control atoms

| ID | Objective | Outputs | Acceptance | Depends on | Reauth? | Rollback |
|---|---|---|---|---|---|---|
| I-001 | Establish T-001 local-safe environment | `.venv` local only, environment notes | exact setup commands succeed; `command -v python`; no credential env dependency | B-005 + T-001 receipt | No | remove `.venv` |
| I-002 | RED coverage for baseline/evidence/progress controls | `tests/test_subject_baseline_control.py`, progress tests as needed | tests fail for missing reader/evidence/progress artifacts | I-001 | No | revert tests |
| I-003 | Baseline ID reader | `scripts/read_subject_baseline_id.py` | reads only verified manifest baseline_id; mismatch fails closed | I-002 | No | revert script |
| I-004 | Evidence schemas | `specs/subject-distillation/evidence-schemas/*.schema.json` | schema tests reject secrets/private paths/malformed artifacts | I-002 | No | revert schemas |
| I-005 | Evidence validator | `scripts/validate_subject_evidence.py` | validates `environment.json`; denies hostile carriers without echo | I-004 | No | revert script |
| I-006 | Progress schema and seed ledger | `implementation-progress.schema.json`, `implementation-progress.json` | seed is T-001 IN_PROGRESS, T-002..T-033 PENDING, binds manifest/tasks sha | I-003 | No | revert ledger/schema |
| I-007 | Progress validator | `scripts/validate_subject_progress.py` | duplicate-key safe; legal transitions; one active task; evidence refs safe | I-006 | No | revert script |
| I-008 | Environment evidence artifact | `evidence/<baseline-id>/environment.json` | public-safe, source_commit, git status, python/sqlite/schema info, normative hashes | I-005/I-007 | No | delete evidence dir |
| I-009 | T-001 mandatory command run | transcripts | every T-001 command exits 0; no waiver unless new authorized amendment | I-008 | No | mark BLOCKED in progress ledger |
| I-010 | T-001 fresh reviews | review JSON/evidence | spec-compliance PASS, quality/security PASS, P0=0/P1=0 | I-009 | No | keep T-001 IN_PROGRESS/BLOCKED |
| I-011 | Complete T-001 ledger transition | updated progress ledger | validator PASS after IN_PROGRESS→COMPLETED with evidence refs | I-010 | No | append BLOCKED instead if validator fails |
| I-012 | T-001 closure report / issue update | #421 comment or local report | states done/not done, exact baseline, tests, remaining side effects | I-011 | Yes for PR/push | no external update if not authorized |

### V-series — Verification and quality gate atoms

These atoms are not feature work. They normalize evidence so that every later implementation task can be mechanically judged instead of argued from prose.

| ID | Objective | Outputs | Acceptance | Depends on | Rollback |
|---|---|---|---|---|---|
| V-001 | Normalize acceptance command blocks | Per-task command matrix in the relevant Work Packet or task section | every command has setup, argv, expected exit code, stdout/stderr rule, and artifact path | G-005 | revert command matrix |
| V-002 | Define RED/GREEN/HOSTILE/REGRESSION evidence classes | verification checklist | every test is classified and cannot substitute for another class | V-001 | revert checklist |
| V-003 | Define artifact completeness checklist | checklist for schemas, scripts, JSON evidence, transcripts, issue comments | missing artifact blocks completion rather than becoming a note | V-001 | revert checklist |
| V-004 | Define traceability coverage gate | requirement/example/task/test/evidence mapping rule | no approved E-* is unmapped; no duplicate owner for finite ID sets | V-003 | revert gate |
| V-005 | Define no-guess/no-hardcode review checklist | reviewer checklist | every material field has owner/source; guessed policy is P1 | V-003 | revert checklist |
| V-006 | Define docs-change rebind checker | rule or script invocation in Work Packet | canonical byte change forces stale-baseline FAIL before rebind and PASS after rebind | G-004 | revert checker text |
| V-007 | Define fresh review template set | spec/quality/security/release review template | review binds exact baseline/tree/diff and reports P0/P1/P2 | G-005 | discard templates |
| V-008 | Capture minimum evidence bundle for each milestone | evidence bundle index | focused, hostile, baseline, regression, diff, and review evidence are named separately | V-002..V-007 | remove index |

### E-series — Risk, rollback, and side-effect atoms

These atoms prevent a good plan from becoming unsafe execution. They are especially important because this delivery carries canonical docs-only changes that must remain separate from B-000 implementation.

| ID | Objective | Outputs | Acceptance | Depends on | Rollback |
|---|---|---|---|---|---|
| E-001 | Define rollback unit for each atom | rollback column in Work Packet/task table | every atom can name the files/artifacts to restore or the ledger state to append | G-001 | update table |
| E-002 | Define artifact retention policy | retention note for local ephemeral review outputs, repo evidence, GitHub comments, review JSON | public-safe evidence retained; private/live/raw content excluded | E-001 | update note |
| E-003 | Define issue/comment evidence norm | issue update template | comments state baseline, scope, verdict, side effects, and next gate without leaking private context | E-002 | update template |
| E-004 | Define branch hygiene norm | branch/preflight checklist | branch/base/worktree checked before baseline, review, authorization, and PR | E-001 | update checklist |
| E-005 | Define scope-mixing prohibitions | explicit no-mix list | docs-only, bootstrap, implementation, migration, private shadow, release, and deploy cannot share one authorization | E-001 | update no-mix list |
| E-006 | Define side-effect-zero checklist | local-only checklist | no commit/push/PR/deploy/migration/external write unless separately authorized | E-005 | update checklist |
| E-007 | Define release-blocking risk register | risk register rows | P0/P1 risks name mitigation, stop gate, and owner | E-006 | update register |
| E-008 | Define failure disposition policy | waiver/exception table | default no-waiver; any exception has owner, ceiling, duration, evidence, and affected requirement | E-007 | update policy |

### S-series — Subject Distillation atomic implementation tasks after T-001

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
| S-020 | T-021 | Implement default-on Subject capability state | capability-state docs/code/tests | default state is safe/off unless explicitly enabled as specified | S-019 | Maybe if capability policy changes | revert capability files |
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
| S-031 | T-032 | Private shadow pilot, operator-private | private receipt reference only | remains operator-private; public release can stay experimental if blocked | S-030 | Yes; private/live explicit only | discard private pilot artifacts |
| S-032 | T-033 | Final attestation and implementation closure | attestation artifact and final ledger transition | attestation validates evidence/review/authorization binding | S-030 and S-031 if stable, or S-031 BLOCKED allowed for experimental | Yes for release/push/merge | do not mark final complete; append BLOCKED |

### R-series — Retrieval, temporal, and graph proof slices

| ID | Issue | Objective | Must wait for | Atomic acceptance |
|---|---|---|---|---|
| R-001 | #413 | Public retrieval benchmark baseline | T-001 complete; preferably T-002 fixtures | synthetic fixtures + expected query results + stable quality/latency signal |
| R-002 | #414 | Deterministic semantic/vector retrieval path | R-001 | provider identity metadata, deterministic CI provider, stale-index/rebuild tests, fallback preserved |
| R-003 | #415 | Temporal validity handling for distilled facts | S-003 or equivalent subject contract | effective/expiry/source time fields, expired/current/unknown validation tests, stale marking docs |
| R-004 | #416 | Entity/edge graph extraction contract | S-001/S-002 | entity/edge shapes, alias/relationship fixtures, confidence/evidence refs, unsafe payload rejection |
| R-005 | docs/strategy | Killer demo hardening | T-001 and candidate flow stable | `propose -> review -> promote -> search -> bounded read -> rollback -> audit` demo stays runnable and public-safe |

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

The docs-only rulefix and exact-baseline review are complete. Continue through the Codex handoff in this order:

```text
review and merge this baseline/plan PR (or explicitly choose a reviewed stacked base)
→ start a clean B-000 branch from the accepted commit
→ give Codex the exact four-value owner instruction from the handoff
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
- [x] Current seven-file staged delivery inventory called out
- [x] Roadmap optimized into lanes, milestones, risks, and atomic tasks
- [x] Progress anchor synchronized in `docs/plans/SUBJECT_DISTILLATION_PROGRESS.md`
- [x] Mechanical docs check run on planning files
- [x] Fresh planning review closure PASS after P1 repair
- [x] Canonical rulefix baseline rebound and validated as `0f688cf2e2472beb`
- [x] Fresh exact-baseline closure review PASS with P0=0/P1=0/P2=0
- [x] B-000 Issue #422 created
- [x] Codex continuation handoff prepared

This document records the plan and current owner-authorized Git delivery. It does not itself authorize B-000/T-001 execution, merge, deployment, private shadow, or production migration.
