# Subject Distillation Progress Anchor

**Last updated:** 2026-08-02
**Repository:** `zycaskevin/Vault-Agent-Memory`
**Working branch:** `docs/subject-distillation-b000-handoff`
**Docs base:** `018a4d518f84783ecc2538f44aeb665c80a5112b`
**Current mode:** owner-authorized local docs-only Simplification Rebaseline

## Current status

The development workflow is being simplified without changing product behavior.
B-000 and T-001 have not started. This cycle may align docs, rebind the canonical
manifest, validate the exact diff and obtain one focused review. It may not commit,
push, update a PR or start implementation without separate authorization.

## Simplification decision

Removed from routine development:

- mandatory offline wheelhouse;
- repo-external review evidence body/locator/digest;
- repeated five-value owner instruction;
- two ordered reviewers for every stage;
- Linux-before-local-development and excessive bootstrap substeps.

Retained:

- owner authority cannot be inferred or created by an agent;
- B-000 exact three-path scope and RED-first tests;
- separate T-001 receipt and authorization;
- credential, privacy, private/live-data and no-echo controls;
- explicit authority for Git delivery when not included in a work instruction;
- explicit authority for production migration, deploy, merge/release and
  destructive actions;
- independent review for auth/security/migration/privacy/public-surface changes;
- Linux security CI before merge/release.

## Current docs-only work unit

1. `specs/subject-distillation/requirements.md`
2. `specs/subject-distillation/design.md`
3. `specs/subject-distillation/tasks.md`
4. `specs/subject-distillation/baseline-manifest.json`
5. `docs/plans/2026-08-02-subject-distillation-execution-roadmap.md`
6. `docs/plans/SUBJECT_DISTILLATION_PROGRESS.md`
7. `docs/plans/2026-08-02-subject-distillation-codex-handoff.md`

`schema.v15.sql` and `traceability.md` remain canonical and manifest-bound but
should remain byte-unchanged in this simplification cycle. No implementation,
receipt, scope, review transcript, private path/data or generated runtime artifact
belongs in this work unit.

## Long-term planning disposition

Merged now as invariants only:

- separate Evidence/Memory/Persona-Policy/Runtime responsibilities within the
  existing Subject SSOT;
- candidate-only Behavioral Diff;
- human/agent/model/third-party authorship provenance;
- scoped, temporal, exception-aware behavior and decision-boundary policy;
- isolation of user policy, project policy, agent role and render style;
- no action authority from persona/model output.

Deferred: runtime Behavioral Diff, dual retrieval/Context Compiler, Policy Cards,
session persona snapshots, Persona IR/export adapters, persona evaluation and all
SFT/DPO/LoRA work. Their milestones/prerequisites are in the execution roadmap.

## Completion state

- [x] Owner explicitly authorized docs-only Simplification Rebaseline.
- [x] Requirements/design/tasks aligned to the simplified authorization and review model.
- [x] Roadmap/progress/handoff aligned to the long-term report and simplified flow.
- [x] Canonical manifest rebound and validator PASS.
- [x] Stale restriction scan, count checks and exact changed-path inventory PASS.
- [x] Focused safety-boundary review reports P0=0/P1=0.
- [x] New baseline packet is ready；stop before implementation.

## Future B-000 owner instruction

After the reviewed docs bytes are delivered in an exact commit:

```text
lane=B-000
implementation_base_commit=<exact clean commit containing the validated baseline>
```

The preflight derives baseline ID, full digest and exact three-path allowlist.
The owner does not need to repeat derived hashes. This template is not authority
until the owner sends it with a real commit SHA.

Current docs candidate binding:

- Baseline ID: `4011418f6c00605c`
- Full digest: `4011418f6c00605ce30e44579848687a14dae038494170bc887cc07c3ec72630`

## Mechanical verification

```bash
python3 scripts/validate_subject_baseline.py \
  --manifest specs/subject-distillation/baseline-manifest.json \
  --repo-root . \
  --json
git diff --check
```

Expected result:

```json
{"baseline_id":"4011418f6c00605c","full_digest":"4011418f6c00605ce30e44579848687a14dae038494170bc887cc07c3ec72630","status":"PASS"}
```

## Stop conditions

Stop if canonical integrity fails, a focused review reports P0/P1, a request mixes
B-000 and T-001, or the next action needs Git delivery, private/live data,
production migration/deployment, release/merge or destructive authority that has
not been explicitly granted.

## Handoff state

- Local Simplification Rebaseline: PASS；P0=0，P1=0.
- Git delivery: not authorized in this cycle.
- B-000 implementation: not started.
- T-001 implementation: not started and independently gated.
- Production/private/destructive actions: not authorized.
