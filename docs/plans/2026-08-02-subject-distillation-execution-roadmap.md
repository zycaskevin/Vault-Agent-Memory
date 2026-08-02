# Vault Agent Memory — Subject Distillation Execution Roadmap

**Date:** 2026-08-02
**Repository:** `zycaskevin/Vault-Agent-Memory`
**Current docs base:** `4ed4e2c611713a6fd3c472a43343c669b88ec00a`
**Status:** docs-only owner-derived receipt alignment；T-001 implementation is not part of this cycle

## 1. Outcome

Vault should continue toward governed memory and identity/behavior continuity,
but the next executable phase remains the Subject Distillation control plane.
This rebaseline removes process ceremony that did not add safety while keeping
the boundaries that protect credentials, private data, production systems and
irreversible actions.

The simplified sequence is:

```text
docs alignment → manifest validation → focused review → Git delivery if authorized
→ exact reviewed main commit → B-001 runner implementation/security review/delivery
→ owner requests exact T-001/base proposal
→ stateless runner returns canonical public-safe JSON without private files
→ owner confirms exact proposal/receipt SHA
→ one runner process re-derives/materializes/verifies/cleans → T-001
```

## 2. What changed

### Removed from routine development

- mandatory offline wheelhouse and network ban;
- repo-external canonical review-evidence JSON/locator/digest;
- five-value B-000 owner prompts containing derived hashes;
- two ordered reviewers for every docs or implementation stage;
- duplicated B-000 execution atoms that could be verified together;
- treating local macOS development as blocked until a Linux machine is present.

### Retained

- an agent cannot self-authorize；the reviewed B-001 runner's first stage is
  stateless and file-free, and only the owner's exact proposal/digest
  confirmation permits its second stage to materialize、verify and clean;
- private/live data, credentials and operator-private receipt/scope bytes stay
  outside the repository and logs;
- B-000 and T-001 remain separate scopes and authorities;
- production migration, deployment, release and destructive actions require
  explicit owner authority;
- genuine RED-first tests, exact path scope, mechanical validation and rollback;
- Linux descriptor/no-follow/race CI before merge or release;
- independent review for auth, security, migration, privacy and public surfaces.

## 3. Review and authorization model

| Change class | Required gate |
|---|---|
| Docs/process only | Mechanical validation + one focused review |
| Low-risk internal implementation | Tests + parent readback; focused review when useful |
| Auth/security/migration/privacy/public surface | Tests + one independent reviewer |
| Git commit/push/PR | Separate Git-delivery authorization when not already included in the work instruction |
| Merge/release/production/private-live/destructive | Explicit owner authorization and the applicable release/production gate |

B-000 owner instruction is intentionally short:

```text
lane=B-000
implementation_base_commit=<exact clean commit containing the validated baseline>
```

The preflight derives the baseline ID, full digest and exact three-path allowlist
from that commit. Derived values are returned for traceability but do not have to
be copied by the owner into chat.

T-task authorization remains owner-confirmed and receipt-verified because it
may govern broader and more sensitive scopes. The first owner message requests
a proposal for an exact task/base only；stateless `propose` returns canonical
public-safe JSON and creates no private artifact；the second owner message
confirms that exact proposal. Only then may one `verify-confirmed` process
re-derive、temporarily materialize、verify and clean the exact bytes. Generated
bytes and hashes are integrity artifacts, not authority, and do not weaken the
verifier、production or private-data boundaries.

## 4. Milestones

| Milestone | Scope | Start gate | Acceptance / stop gate |
|---|---|---|---|
| M1 — Owner-derived receipt rebaseline | Requirements/design/tasks + roadmap/handoff + manifest | Current owner SDD-adjustment instruction | Manifest PASS, auth-focused independent review P0=0/P1=0, no implementation files or private receipt/scope |
| M2 — Docs delivery | Commit/push/PR for the reviewed docs unit | Separate Git-delivery authorization | Exact commit containing reviewed bytes；stop before T-001 proposal |
| M3 — B-000 bootstrap | Completed historical authorization schema/verifier/bootstrap delivery | Merged PR #423 | Exact B-000 tree and independent security review accepted；no reopening in this docs cycle |
| M3A — B-001 runner | Identity-safe proposal/verification/cleanup runner + hostile tests | Owner names `lane=B-001` + exact reviewed base | Exact two-path diff、focused tests/Ruff、independent security review and separate Git delivery PASS；stop before proposal |
| M4 — T-001 control plane | Baseline/evidence/progress controls | Accepted B-001 + owner proposal request + file-free canonical proposal + separate owner exact proposal/digest confirmation + one-process re-derivation/verifier/cleanup PASS | T-001 commands and risk-based reviews PASS；ledger records completion |
| M5 — Public Subject foundation | T-002/T-003 | T-001 complete | Public-safe fixture ownership and 43-example traceability PASS |
| M6 — Subject runtime | T-004..T-031 | M5 complete | Core, policy, evidence, model/context, surfaces, recovery and closure PASS |
| M7 — Private evaluation | T-032 | Separate private/live authority | Private receipt only; no raw/private repo artifact |
| M8 — Attestation | T-033 | T-001..T-031 complete; T-032 complete or validly blocked | Experimental/stable attestation according to canonical contract |

## 5. Atomic plan

### G-series — Current docs-only cycle

| ID | Owner | Inputs | Output | Success criteria | Parallelism |
|---|---|---|---|---|---|
| G-001 | Contract steward | Owner SDD-adjustment instruction + current canonical docs | Aligned requirements/design/tasks | Owner instruction remains authority；proposal is stateless/file-free and confirmed execution is one-process、repo-external、no-echo and cleanup-required | Complete first |
| G-002 | Planning owner | G-001 diff + existing roadmap/handoff | Aligned roadmap/handoff | Current-cycle vs T-001 boundaries agree；B-000 historical scope remains unchanged | After G-001；planning files may be edited together |
| G-003 | Manifest owner | Exact five canonical bytes | Rebound manifest | Validator recomputes every file hash, full digest and baseline ID with PASS | After G-001 |
| G-004 | Parent verifier | G-001..G-003 exact tree | Mechanical report | `git diff --check`, counts, stale-term scan and exact changed-path inventory PASS | After G-002/G-003 |
| G-005 | Focused reviewer | Frozen local docs candidate | Safety-boundary verdict | P0=0/P1=0; simplification does not authorize implementation/production/private/destructive work | After G-004 |
| G-006 | Parent reporter | Validated/reviewed candidate | Owner packet | New baseline values, exact changed paths and next authorization template; stop | After G-005 |

### B-series — Completed historical B-000 cycle

| ID | Owner | Inputs | Output | Success criteria |
|---|---|---|---|---|
| B0-001 | Parent | Two-value owner instruction + clean selected commit | Derived preflight + usable `.venv` | Manifest/HEAD/three-path allowlist clean; standard dev install succeeds |
| B0-002 | Implementer | Canonical B-000 contract | Genuine RED bootstrap test | Focused test fails only because schema/verifier are absent |
| B0-003 | Implementer | RED test + design §21 | Schema, verifier and complete adversarial matrix | Focused pytest and Ruff PASS; no dependency/package metadata change |
| B0-004 | Parent + independent security reviewer | Exact three-path tree | Readback/review packet | Exact diff, no echo/resource/path controls and Linux-CI requirement accepted; stop before T-001 |

### B1-series — Next B-001 runner cycle

| ID | Owner | Inputs | Output | Success criteria |
|---|---|---|---|---|
| B1-001 | Parent | `lane=B-001` + exact clean reviewed commit | Scope/env preflight | Exact two-path allowlist、manifest/HEAD clean |
| B1-002 | Test owner | Canonical B-001 contract | Genuine RED hostile lifecycle suite | Fails only because runner is absent |
| B1-003 | Implementer | RED tests + existing verifier | Stateless proposal + identity-safe verification runner | Canonical proposal、restart/replay/concurrency、descriptor lifecycle、signals、cleanup tests and Ruff PASS |
| B1-004 | Parent + independent security reviewer | Exact two-path tree | Readback/review packet | P0=0/P1=0；stop before proposal；Git delivery separately authorized |

### I-series — Future T-001 cycle

| ID | Owner | Inputs | Output | Success criteria |
|---|---|---|---|---|
| I-001 | Reviewed runner | Accepted B-001 + owner proposal request for exact T-001/base | Canonical public-safe proposal JSON | No private file/state/daemon/IPC；owner can inspect exact arrays、timestamps and digests |
| I-001A | Owner + parent | I-001 exact canonical JSON | Owner exact proposal/digest confirmation + one `verify-confirmed` process | Proposal re-derived against HEAD/base/manifest/task/schema/verifier；no-xtrace and `0700`/`0600` checks PASS；receipt verifier PASS；owned temp files cleaned and absent before implementation |
| I-002 | Test owner | T-001 contract | Genuine RED baseline/evidence/progress tests | RED fails for missing control-plane artifacts |
| I-003 | Control-plane implementer | RED tests | Readers, schemas, validators, atomic writer and ledger | Focused/hostile tests PASS; exact task scope only |
| I-004 | Evidence owner | Validated implementation | Public-safe environment evidence | Hashes and runtime versions validate; no secret/private path |
| I-005 | Independent reviewer | Exact T-001 tree | Risk-based review result | Auth/security/control-plane P0=0/P1=0 |
| I-006 | Progress owner | Accepted evidence/review | T-001 completed transition | Atomic writer and validator PASS; stop before T-002 |

## 6. Long-term planning disposition

### Merge now as contract invariants

These have high architectural impact, low implementation risk and prevent future
data contamination without expanding the current runtime scope:

- Evidence, Memory, Persona/Policy and Runtime Context are separate conceptual
  responsibilities, mapped onto the existing Subject SSOT rather than new stores.
- Behavioral Diff is candidate-only and can never directly promote policy.
- Authorship distinguishes human, agent/model and third-party material.
- Decision boundaries and persona rules carry scope, exceptions, counter-evidence,
  confidence and temporal validity.
- User policy, project policy, agent role and model rendering style remain distinct.
- Persona/model output never grants action authority.

Acceptance: the canonical requirements/design preserve these invariants, add no
runtime path or new SBE, and keep candidate-first/approved-policy authority intact.

### Defer as roadmap capabilities

| Roadmap item | Why deferred | Prerequisites | Milestones / acceptance |
|---|---|---|---|
| LT-01 Behavioral Diff runtime | Needs stable evidence/candidate APIs and provenance | T-001, T-002/T-003, relevant T-010/T-013 controls | Schema → deterministic diff → candidate-only tests → correction/replay/stale-base DENY |
| LT-02 Dual Evidence/Policy retrieval + Context Compiler | Depends on approved policy/model/context projections and benchmark | LT-01, T-014/T-016, retrieval benchmark #413 | Separate retrievers → precedence/token budget → no candidate leakage → grounding/latency benchmarks |
| LT-03 Persona/session snapshots and Policy Cards | Depends on deterministic compiler and revocation semantics | LT-02, grants/context lifecycle | Versioned refs-only snapshot → session pinning → rollback/replay and revoked-entry tests |
| LT-04 Persona evaluation suite | Requires stable outputs and withheld cases | LT-01..03, T-025/T-026 | Grounding, decision agreement, violations, context sensitivity, drift, portability and abstention reported separately |
| LT-05 Canonical Persona IR/export adapters | Deployment artifact, not a new SSOT | LT-03/LT-04 stable | Lossless versioned export, provenance round-trip, no action authority |
| LT-06 SFT/DPO/LoRA export/training | Highest privacy, contamination, cost and model-lock-in risk | LT-05 + consent/deletion/private-data/spend authority | Governed dataset export first; isolated benchmarked experiment; deletable artifacts; no core mutation |

## 7. Risks

| Risk | Severity | Control |
|---|---:|---|
| Proposal derivation is mistaken for authorization | P1 | First stage is stateless/file-free；second owner confirmation binds exact canonical JSON and receipt digest；ambiguous/stale/partial confirmation DENY |
| Stale owner instruction applied to changed bytes | P1 | Exact base commit is owner-supplied; preflight derives and validates current manifest |
| Agent self-authorizes from a PASS/hash | P1 | Only the second owner confirmation authorizes implementation；proposal derivation、materialization、review、receipt and hashes alone never do |
| B-000 and T-001 get mixed | P1 | Separate milestones, artifacts, receipt and stop boundary |
| AI-generated evidence contaminates persona | P1 | Authorship provenance + candidate-only Behavioral Diff; defer runtime until tested |
| Private data reaches public artifacts | P0/P1 | Synthetic/public-safe fixtures; private receipt/scope no echo and repo exclusion |
| Platform behavior differs | P1 | Local supported-host development; Linux security suite required before merge/release |

## 8. Acceptance criteria

- All 26 requirements, 43 SBE examples, 33 T-tasks and five canonical manifest
  members remain present.
- The manifest validates the exact canonical bytes and yields one reproducible
  baseline ID/full digest.
- No B-000/T-001 implementation artifact, receipt, scope, private/live data,
  credential, migration, deployment or destructive side effect exists.
- No active instruction treats an agent-produced receipt/hash as owner authority
  or permits implementation before owner confirmation of the complete proposal.
- One auth-focused independent review confirms P0=0/P1=0 on the frozen docs
  candidate.

## 9. Next action

Finish the owner-derived-receipt docs rebaseline and stop. Git delivery requires
separate authorization. Once the reviewed bytes exist in an exact commit on
`main`, the owner may authorize `lane=B-001` at that exact commit. After B-001's
exact two-path implementation、tests、independent security review and separately
authorized Git delivery are accepted, the owner may request a `lane=T-001`
proposal. Only a separate owner confirmation of the reviewed runner's complete
proposal/receipt SHA permits verification and T-001.
