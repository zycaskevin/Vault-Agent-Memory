# Vault Agent Memory — Subject Distillation Execution Roadmap

**Date:** 2026-08-02
**Repository:** `zycaskevin/Vault-Agent-Memory`
**Current docs base:** `018a4d518f84783ecc2538f44aeb665c80a5112b` plus the owner-authorized local Simplification Rebaseline candidate
**Status:** docs-only alignment；B-000 and T-001 are not part of this cycle

## 1. Outcome

Vault should continue toward governed memory and identity/behavior continuity,
but the next executable phase remains the Subject Distillation control plane.
This rebaseline removes process ceremony that did not add safety while keeping
the boundaries that protect credentials, private data, production systems and
irreversible actions.

The simplified sequence is:

```text
docs alignment → manifest validation → focused review → Git delivery if authorized
→ owner selects exact B-000 base → B-000 → independent security review → stop
→ separate T-001 receipt/authorization → T-001
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

- an agent cannot self-authorize or create the owner's instruction;
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

T-task authorization remains receipt-based because it may govern broader and
more sensitive scopes. Simplifying B-000 does not weaken the T-task receipt
verifier or production/private-data boundaries.

## 4. Milestones

| Milestone | Scope | Start gate | Acceptance / stop gate |
|---|---|---|---|
| M1 — Simplification Rebaseline | Requirements/design/tasks + roadmap/progress/handoff + manifest | Current owner docs-only authorization | Manifest PASS, focused safety review P0=0/P1=0, no implementation files |
| M2 — Docs delivery | Commit/push/PR update for the reviewed docs unit | Separate Git-delivery authorization | Exact commit containing reviewed bytes; stop before B-000 |
| M3 — B-000 bootstrap | Authorization schema, verifier and bootstrap test only | Owner names `lane=B-000` + exact base commit | RED/GREEN, focused tests/Ruff, exact three-path diff, independent security review; stop |
| M4 — T-001 control plane | Baseline/evidence/progress controls | Accepted B-000 + actual T-001 receipt and separate authority | T-001 commands and risk-based reviews PASS; ledger records completion |
| M5 — Public Subject foundation | T-002/T-003 | T-001 complete | Public-safe fixture ownership and 43-example traceability PASS |
| M6 — Subject runtime | T-004..T-031 | M5 complete | Core, policy, evidence, model/context, surfaces, recovery and closure PASS |
| M7 — Private evaluation | T-032 | Separate private/live authority | Private receipt only; no raw/private repo artifact |
| M8 — Attestation | T-033 | T-001..T-031 complete; T-032 complete or validly blocked | Experimental/stable attestation according to canonical contract |

## 5. Atomic plan

### G-series — Current docs-only cycle

| ID | Owner | Inputs | Output | Success criteria | Parallelism |
|---|---|---|---|---|---|
| G-001 | Contract steward | Owner simplification instruction + current canonical docs | Aligned requirements/design/tasks | Old five-value, wheelhouse, external-body and double-review gates removed; safety boundaries unchanged | Complete first |
| G-002 | Planning owner | G-001 diff + long-term report | Aligned roadmap/progress/handoff | Current-cycle vs roadmap decisions and stop boundaries agree | After G-001; planning files may be edited together |
| G-003 | Manifest owner | Exact five canonical bytes | Rebound manifest | Validator recomputes every file hash, full digest and baseline ID with PASS | After G-001 |
| G-004 | Parent verifier | G-001..G-003 exact tree | Mechanical report | `git diff --check`, counts, stale-term scan and exact changed-path inventory PASS | After G-002/G-003 |
| G-005 | Focused reviewer | Frozen local docs candidate | Safety-boundary verdict | P0=0/P1=0; simplification does not authorize implementation/production/private/destructive work | After G-004 |
| G-006 | Parent reporter | Validated/reviewed candidate | Owner packet | New baseline values, exact changed paths and next authorization template; stop | After G-005 |

### B-series — Future B-000 cycle

| ID | Owner | Inputs | Output | Success criteria |
|---|---|---|---|---|
| B-001 | Parent | Two-value owner instruction + clean selected commit | Derived preflight + usable `.venv` | Manifest/HEAD/three-path allowlist clean; standard dev install succeeds |
| B-002 | Implementer | Canonical B-000 contract | Genuine RED bootstrap test | Focused test fails only because schema/verifier are absent |
| B-003 | Implementer | RED test + design §21 | Schema, verifier and complete adversarial matrix | Focused pytest and Ruff PASS; no dependency/package metadata change |
| B-004 | Parent + independent security reviewer | Exact three-path tree | Readback/review packet | Exact diff, no echo/resource/path controls and Linux-CI requirement accepted; stop before T-001 |

### I-series — Future T-001 cycle

| ID | Owner | Inputs | Output | Success criteria |
|---|---|---|---|---|
| I-001 | Parent | Accepted B-000 + actual T-001 receipt/scope | Verified authorization and environment | Receipt verifier PASS; private inputs remain outside repo/no echo |
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
| Process simplification accidentally weakens security | P1 | Focused diff review; receipt/no-echo/private/production/destructive contracts unchanged |
| Stale owner instruction applied to changed bytes | P1 | Exact base commit is owner-supplied; preflight derives and validates current manifest |
| Agent self-authorizes from a PASS/hash | P1 | Owner instruction remains the trust root; review and hashes are never authority |
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
- No remaining active instruction requires `SUBJECT_DEV_WHEELHOUSE`, a five-value
  B-000 prompt, a repo-external review body or two ordered B-000 reviewers.
- One focused review confirms P0=0/P1=0 on the frozen docs candidate.

## 9. Next action

Finish G-001..G-006 and stop. Git delivery requires separate authorization. Once
the reviewed docs bytes exist in an exact commit, the owner may authorize B-000
with only `lane=B-000` and that commit SHA. B-000 must stop after its independent
security review; T-001 still requires its own receipt and authorization.
