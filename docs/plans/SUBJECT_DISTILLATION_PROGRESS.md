# Subject Distillation Progress Anchor

**Last updated:** 2026-08-02
**Repository:** `zycaskevin/Vault-Agent-Memory`
**Working branch:** `docs/subject-distillation-b000-handoff`
**Repair base:** `167b2eec443bc2e6ad0af21cb36a8b01c7cae5f7`
**Current mode:** owner-authorized local docs-only LT-C alignment + rebaseline；B-000/T-001 not started

---

## One-sentence status

The LT-C docs candidate is mechanically rebound to a new five-file baseline, but it is intentionally `NOT_AUTHORIZED`: ordered fresh review evidence, docs Git delivery, exact implementation-base selection, and a new five-value B-000 owner instruction are still separate gates.

## Source of truth

- Parent epic: #410
- B-000 implementation issue: #422
- Blocked successor T-001 issue: #421
- Canonical specification: `specs/subject-distillation/`
- Execution roadmap: `docs/plans/2026-08-02-subject-distillation-execution-roadmap.md`
- Codex handoff: `docs/plans/2026-08-02-subject-distillation-codex-handoff.md`

## Candidate baseline binding

| Field | Value |
|---|---|
| Baseline ID | `51625dffe08539b6` |
| Full digest | `51625dffe08539b60520b4c21c4793cc19aad0dd63f8066d4e0c5f277056a08f` |
| Manifest SHA-256 | `0765d28d0b722dbd4e5829e7b17d1b721171acea72912fd131965fb17e4c26cf` |
| B-000 scope SHA-256 | `3199f1e732b04db99af181d0297bc4f7342e181b129c020b684843878be7f9c3` |
| Fresh closure review | `EXTERNAL-EVIDENCE-REQUIRED`；no repo file self-declares PASS |
| Implementation base | `UNSELECTED`；must be a later exact commit containing these reviewed bytes |

Any byte change to the five canonical files requires another manifest binding and fresh review. Review evidence follows design §20.1: the parent retains the retrievable public-safe body, locator and SHA-256 outside the repo so this progress file cannot self-certify or create a review-digest cycle.

## LT-C decisions

### Merged into the current canonical contract as invariants only

- Evidence／Memory／Persona-Policy／Runtime are conceptual ownership/projection planes, not four writable stores.
- Behavioral Diff is typed candidate-only and never directly updates approved policy/model/runtime.
- Approved behavior and decision boundaries reuse existing sealed Subject policy/model authority, scope, exceptions, counter-evidence and temporal validity.
- Human、agent、model and third-party authorship remain distinct；AI-produced material cannot silently become human-explicit evidence.
- Persona/session snapshots are deterministic derived projections with no independent authority.
- Model/persona output cannot grant action authority; an independent valid grant remains mandatory.

### Deferred to the future roadmap

- Dual Evidence/Policy retrieval and precedence/token-budget compiler.
- Runtime Policy Cards and Virtual Session persona snapshot productization.
- Canonical Persona IR and cross-model deployment adapters.
- Governed SFT/DPO dataset export and any LoRA/training pipeline.

These items wait for the roadmap LT-series prerequisites and separate authorization. None expands B-000 or T-001.

## Completed in this local docs-only cycle

- [x] Captured the owner's explicit docs-only LT-C/rebaseline authorization.
- [x] Separated source-reference commit, delivery base, normative baseline ID, reviewed tree and implementation base terminology.
- [x] Defined retrievable repo-external baseline-review evidence and deterministic normative-tree/delivery-diff hashes.
- [x] Added exact implementation-base binding to the future B-000 owner instruction.
- [x] Defined offline wheelhouse-only setup for B-000/T-001.
- [x] Aligned DB lifecycle API, CLI vocabulary, root setup final state/policies, atomic progress writer and final-tree rerun gate.
- [x] Added resource/platform acceptance and clarified experimental is not release authority.
- [x] Mapped the long-term report onto the existing Subject SSOT and added deferred roadmap milestones.
- [x] Rebound `baseline-manifest.json`; mechanical validator PASS.
- [ ] Obtain ordered distinct-reviewer design §20.1 evidence with P0=0/P1=0.
- [ ] Under separate authorization, commit/push/open or update the docs delivery.
- [ ] Select the resulting exact implementation commit and issue a new five-value B-000 instruction.

## Exact local review unit

1. `specs/subject-distillation/requirements.md`
2. `specs/subject-distillation/design.md`
3. `specs/subject-distillation/tasks.md`
4. `specs/subject-distillation/traceability.md`
5. `specs/subject-distillation/baseline-manifest.json`
6. `docs/plans/2026-08-02-subject-distillation-execution-roadmap.md`
7. `docs/plans/SUBJECT_DISTILLATION_PROGRESS.md`
8. `docs/plans/2026-08-02-subject-distillation-codex-handoff.md`

`schema.v15.sql` remains canonical and hash-bound but byte-unchanged in this repair. No reviewer transcript/body, owner chat content, receipt, scope artifact, token, private/live path, runtime evidence or generated implementation artifact belongs in the repo.

## Future B-000 owner instruction template

The values below are not authorization while `implementation_base_commit` is unresolved or design §20.1 evidence has not verified:

```text
lane=B-000
implementation_base_commit=<exact accepted commit containing the reviewed candidate>
baseline_id=51625dffe08539b6
baseline_full_digest=51625dffe08539b60520b4c21c4793cc19aad0dd63f8066d4e0c5f277056a08f
scope_sha256=3199f1e732b04db99af181d0297bc4f7342e181b129c020b684843878be7f9c3
```

## Mechanical verification

```bash
python3 scripts/validate_subject_baseline.py \
  --manifest specs/subject-distillation/baseline-manifest.json \
  --repo-root . \
  --json
git diff --check
```

Expected baseline result:

```json
{"baseline_id":"51625dffe08539b6","full_digest":"51625dffe08539b60520b4c21c4793cc19aad0dd63f8066d4e0c5f277056a08f","status":"PASS"}
```

## Stop conditions

Stop and return to the owner if:

- canonical bytes no longer validate to this candidate baseline;
- review evidence body/locator/digest/tree/diff cannot be independently verified;
- any ordered review reports P0/P1;
- a selected implementation base does not contain the exact reviewed bytes;
- the B-000 prompt lacks any of the five exact binding values;
- any request mixes docs-only, B-000 and T-001 scopes;
- any action would commit/push/open or update a PR/write GitHub without separate authorization;
- private/live data, migration, runtime, release or deployment behavior appears.

## Handoff state

- Local docs-only LT-C candidate: mechanically PASS, fresh review pending.
- Git delivery: not authorized in this cycle.
- B-000 implementation: blocked before first write.
- T-001 implementation: blocked.
- Merge/deploy/release/private shadow: not authorized.
