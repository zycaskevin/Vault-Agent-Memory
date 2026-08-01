# Subject Distillation — Normative SBE Traceability

**Status:** Canonical traceability contract; frozen bytes record integrity only
**Public repository baseline:** `09a0f4c08f2f7479a01c9b6c083dd3cd0e564c27`
**Integrity binding:** `baseline-manifest.json`; integrity does not imply review approval, implementation authorization, migration registration, or release authorization.
**Implementation status:** Not implemented and not authorized by this artifact.
**Scope:** Exact mapping for the 43 approved examples in `requirements.md`.

This file is a normative part of the technical-design package. T-003 may serialize these mappings into a fixture, but implementation may not invent, remove, merge, or remap an example. Every listed test path is planned until implementation is separately authorized.

| Example | Approved behavior | Design contract | Task(s) | Planned test file(s) |
|---|---|---|---|---|
| E-P-001 | Explicit preference remains explicit | §5.3, §8.1, §8.2 | T-008, T-009, T-013, T-016 | `tests/test_subject_auth.py`; `tests/test_subject_policy.py`; `tests/test_subject_assertions.py`; `tests/test_subject_context.py` |
| E-P-002 | Constraint is not mislearned as preference | §5.3, §6.4, §11.4 | T-013, T-017 | `tests/test_subject_assertions.py`; `tests/test_subject_decisions.py` |
| E-P-003 | Repeated behavior with counter-evidence stays calibrated | §5.3, §6.2, §6.3 | T-013, T-014 | `tests/test_subject_assertions.py`; `tests/test_subject_models.py` |
| E-P-004 | Subject correction supersedes old inference | §5.3, §9.2, §11.3 | T-013, T-014 | `tests/test_subject_assertions.py`; `tests/test_subject_models.py` |
| E-P-005 | Present pattern and desired direction remain separate | §6.3, §8.2 | T-014, T-016 | `tests/test_subject_models.py`; `tests/test_subject_context.py` |
| E-P-006 | Purpose-limited Context Packs | §8.2 | T-015, T-016 | `tests/test_subject_grants.py`; `tests/test_subject_context.py` |
| E-P-007 | Revoked access fails closed | §8.2, §9.2 | T-015, T-016 | `tests/test_subject_grants.py`; `tests/test_subject_context.py` |
| E-P-008 | Outcome feedback updates confidence, not history | §6.3, §6.4, §11.4 | T-014, T-017 | `tests/test_subject_models.py`; `tests/test_subject_decisions.py` |
| E-P-009 | High-stakes decision remains advisory | §8.2, §15.1 | T-009, T-015, T-016 | `tests/test_subject_policy.py`; `tests/test_subject_grants.py`; `tests/test_subject_context.py` |
| E-P-010 | Controller testimony does not impersonate the subject | §5.3, §8.1 | T-008, T-009, T-013 | `tests/test_subject_auth.py`; `tests/test_subject_policy.py`; `tests/test_subject_assertions.py` |
| E-P-011 | Agent observation enters as a decision candidate | §6.2, §11.2, §11.4 | T-010, T-017 | `tests/test_subject_candidates.py`; `tests/test_subject_decisions.py` |
| E-P-012 | Later outcome appends without rewriting prediction | §6.4, §11.4 | T-017 | `tests/test_subject_decisions.py` |
| E-P-013 | Relationship role changes without identity loss | §6.4, §11.4 | T-018 | `tests/test_subject_relationships.py` |
| E-P-014 | Alias supports recognition without becoming identity | §6.4, §8.2 | T-016, T-018 | `tests/test_subject_context.py`; `tests/test_subject_relationships.py` |
| E-P-015 | Perspective model and counterparty self-fragment coexist | §5.4, §12 | T-018, T-019 | `tests/test_subject_relationships.py`; `tests/test_subject_fragments.py` |
| E-P-016 | New installation starts with a safe root subject | §9.1, §11.1 | T-021 | `tests/test_subject_setup.py` |
| E-P-017 | Balanced shadow gate passes with preregistered evidence | §6.5, §9.4, §15.3 | T-025, T-026 | `tests/test_subject_evaluation.py` |
| E-P-018 | Larger pilots scale every aggregate denominator | §15.3 | T-025 | `tests/test_subject_evaluation.py` |
| E-O-001 | Official strategy outranks local habit | §5.3, §13 | T-009, T-020 | `tests/test_subject_policy.py`; `tests/test_subject_organization_contract.py` |
| E-O-002 | Employee preference is not company policy | §5.3, §13 | T-009, T-020 | `tests/test_subject_policy.py`; `tests/test_subject_organization_contract.py` |
| E-O-003 | Strategy supersession preserves history | §5.3, §9.3, §13 | T-020 | `tests/test_subject_organization_contract.py` |
| E-O-004 | Authority conflict is visible | §8.1, §13 | T-009, T-020 | `tests/test_subject_policy.py`; `tests/test_subject_organization_contract.py` |
| E-O-005 | Organization Context Pack is role-scoped | §8.2, §13 | T-016, T-020 | `tests/test_subject_organization_contract.py`; `tests/test_subject_context.py` |
| E-F-001 | Insufficient evidence returns unknown | §5.2, §5.3, §15.1 | T-013, T-014 | `tests/test_subject_assertions.py`; `tests/test_subject_models.py` |
| E-F-002 | Unavailable source prevents overclaim | §8.2, §11.5 | T-011, T-016 | `tests/test_subject_evidence.py`; `tests/test_subject_context.py` |
| E-F-003 | Legacy Vault remains valid | §9.1, §14.1 | T-006, T-027 | `tests/test_subject_migration.py` |
| E-F-004 | Generic schema accepts organization fixtures | §6, §13 | T-006, T-020 | `tests/test_subject_db_schema.py`; `tests/test_subject_organization_contract.py` |
| E-F-005 | Missing pointer source degrades verifiability | §5.3, §6.2, §11.5 | T-011, T-013, T-014 | `tests/test_subject_evidence.py`; `tests/test_subject_assertions.py`; `tests/test_subject_models.py` |
| E-F-006 | Synthetic success alone remains experimental | §15.2, §15.3 | T-025, T-029 | `tests/test_subject_evaluation.py` |
| E-F-007 | Revoked shared fragment stops future disclosure | §12 | T-019 | `tests/test_subject_fragments.py` |
| E-F-008 | Existing Vault upgrade does not infer a person | §9.1, §14.1 | T-006, T-021 | `tests/test_subject_migration.py`; `tests/test_subject_setup.py` |
| E-F-009 | Relayed first-person quote is not an explicit self-statement | §5.3, §11.2 | T-009, T-010, T-013 | `tests/test_subject_policy.py`; `tests/test_subject_candidates.py`; `tests/test_subject_assertions.py` |
| E-F-010 | Unauthorized fragment issuer is rejected | §12 | T-019 | `tests/test_subject_fragments.py` |
| E-F-011 | Mismatched counterparty binding is rejected | §12 | T-019 | `tests/test_subject_fragments.py` |
| E-F-012 | Unverifiable revocation does not mutate lifecycle state | §12 | T-019 | `tests/test_subject_fragments.py` |
| E-F-013 | Primary-subject consent cannot disclose counterparty data | §5.4, §8.2 | T-016, T-018 | `tests/test_subject_context.py`; `tests/test_subject_relationships.py` |
| E-F-014 | Subject migration is idempotent | §14.1 | T-006 | `tests/test_subject_migration.py` |
| E-F-015 | Interrupted migration fails safely | §14.1, §14.2 | T-006, T-027 | `tests/test_subject_migration.py` |
| E-F-016 | Backup rollback restores a usable legacy Vault | §14.3 | T-027 | `tests/test_subject_migration.py`; `tests/test_db_backup.py` |
| E-F-017 | Aggregate success cannot hide a weak domain | §15.3 | T-025 | `tests/test_subject_evaluation.py` |
| E-F-018 | Post-hoc threshold changes apply only to a later pilot | §9.4, §15.3 | T-025, T-026 | `tests/test_subject_evaluation.py` |
| E-F-019 | A hard failure overrides all utility scores | §15.1, §15.3 | T-025, T-026 | `tests/test_subject_evaluation.py` |
| E-F-020 | Correct choice with wrong rationale is scored separately | §15.3 | T-025 | `tests/test_subject_evaluation.py` |

## Lifecycle/access/relationship/evaluation invariant execution ownership

This table narrows RED／legal-positive ownership for six cross-layer invariants without changing any approved SBE row above. It adds no test path or task: each concrete file retains the single earlier `Create` owner named below, and T-029 only executes/reuses those files in the unit stage before fixture、surface and legacy gates.

| Contract | Requirement / existing SBE edge | Required targeted RED and legal positive | Sole `Create` owner → concrete test | Task-local focused command |
|---|---|---|---|---|
| INV-LIFECYCLE-AUTH | R-SD-003、007、012、025；E-P-016 remains T-021-owned | Wrong lifecycle target kind／cross-subject event and wrong global-principal kind／non-NULL Subject／other-principal binding are denied. Exact same-subject `subject.inactivated`／`subject.revoked`／`subject.deleted` transitions and global self-bound `principal.suspended`／`principal.revoked` transitions are legal controls. | T-006 → `tests/test_subject_db_schema.py`; T-008 → `tests/test_subject_auth.py`; T-021 → `tests/test_subject_setup.py` | `python -m pytest -q tests/test_subject_db_schema.py`<br>`python -m pytest -q tests/test_subject_auth.py`<br>`python -m pytest -q tests/test_subject_setup.py` |
| INV-ACCESS-DUAL-TIME | R-SD-008、011-012、018-019；E-P-006..007 remain T-015/T-016-owned | A sealed exact access policy valid only at issuance or only at grant start is denied; validity at both issuance `occurred_at` and grant `effective_from` is the legal control. | T-006 → `tests/test_subject_db_schema.py`; T-015 → `tests/test_subject_grants.py` | `python -m pytest -q tests/test_subject_db_schema.py`<br>`python -m pytest -q tests/test_subject_grants.py` |
| INV-RELATIONSHIP-CLOSURE | R-SD-006、018、022-023；E-P-013 remains T-018-owned | Relationship close is denied when either `perspective` or `relationship_experience` assertion extends past the endpoint; closing both namespaces by the endpoint is legal. | T-006 → `tests/test_subject_db_schema.py`; T-018 → `tests/test_subject_relationships.py` | `python -m pytest -q tests/test_subject_db_schema.py`<br>`python -m pytest -q tests/test_subject_relationships.py` |
| INV-COUNTERPARTY-FAIL-CLOSED | R-SD-018、022-023；E-P-013 remains T-018-owned | Active/still-usable control blocks relationship close. `purge_pending` entered strictly before the endpoint is accepted as closed only with immediate store/model/export/disclosure denial, without waiting for later physical completion. | T-006 → `tests/test_subject_db_schema.py`; T-018 → `tests/test_subject_relationships.py` | `python -m pytest -q tests/test_subject_db_schema.py`<br>`python -m pytest -q tests/test_subject_relationships.py` |
| INV-DELETION-ORDER | R-SD-018、022；E-P-013 remains T-018-owned | Deletion request at/equal/after the endpoint is denied. A request strictly before it may complete later after the endpoint and hold expiry, but completion never restores processing or disclosure. | T-006 → `tests/test_subject_db_schema.py`; T-018 → `tests/test_subject_relationships.py` | `python -m pytest -q tests/test_subject_db_schema.py`<br>`python -m pytest -q tests/test_subject_relationships.py` |
| INV-EVAL-DIGEST | R-SD-016、026；E-P-017..018 and E-F-017..020 remain T-025/T-026-owned | One-field twins must diverge for manifest SHA, each eligibility/exclusion/hard-failure/scoring-definition version and SHA, and `created_at`/`frozen_at`; byte-identical twins remain stable. Missing `subject_sha256` makes view and close fail closed; registered deterministic UDF is the legal control. | T-006 → `tests/test_subject_db_schema.py`; T-025 → `tests/test_subject_evaluation.py` | `python -m pytest -q tests/test_subject_db_schema.py`<br>`python -m pytest -q tests/test_subject_evaluation.py` |

## Event-authority/half-open endpoint invariant execution ownership

This row assigns five paired cross-layer invariants without changing an approved SBE mapping, adding a task, or adding a test path. Every concrete test keeps its earlier sole `Create` owner, and all four files are already executed by T-029's unit stage before legacy regression.

| Contract | Requirement / existing SBE edge | Required targeted DENY and legal positive | Sole `Create` owner → concrete test | Task-local focused command |
|---|---|---|---|---|
| INV-EVENT-AUTHORITY-PAIRS | R-SD-004、006-007、012、018、022-023、025；E-P-016 remains T-021-owned and E-P-013 remains T-018-owned | Five paired categories are mandatory: (1) lifecycle backed only by a same-Subject controller grant or carrying `actor_role='controller'` DENY versus exact event-time-valid same-Subject `subject` role ALLOW；(2) principal `actor_role <> 'subject'` DENY versus exact NULL-Subject same-principal `actor_role='subject'` self-event ALLOW；(3) lifecycle/principal `recorded_at < occurred_at` DENY versus equality/later ALLOW, and principal same/regressing `updated_at` DENY versus strictly later `updated_at = occurred_at` ALLOW；(4) each relationship-bound `perspective` and `relationship_experience` assertion ending exactly at the parent endpoint ALLOW versus ending after it or remaining open DENY；(5) one deletion-request event replayed across two controls DENY versus distinct authorized, control-bound events ALLOW. | T-006 → `tests/test_subject_db_schema.py`; T-008 → `tests/test_subject_auth.py`; T-018 → `tests/test_subject_relationships.py`; T-021 → `tests/test_subject_setup.py` | `python -m pytest -q tests/test_subject_db_schema.py`<br>`python -m pytest -q tests/test_subject_auth.py`<br>`python -m pytest -q tests/test_subject_relationships.py`<br>`python -m pytest -q tests/test_subject_setup.py` |

## Mechanical closure rules

1. The exact ID set must equal `E-P-001..018 + E-O-001..005 + E-F-001..020` with no duplicates.
2. Every fixture row must name one or more planned test files and only task IDs/section anchors that already exist.
3. T-003 must serialize this exact approved mapping to `sbe-traceability.json`, then bind every planned file to collected pytest nodes before final implementation closure.
4. Unit → fixture → surface → legacy regression → private live/shadow order remains mandatory; a later result cannot repair an earlier failed gate.
5. `BLOCKED` is not completion. Organization rows prove contract compatibility only and do not authorize an Organization runtime projection in v1.
6. Any mapping change requires a design review and a new traceability artifact digest; it cannot be changed post hoc to fit implementation output.
7. T-006/T-028 physical-contract tests must include direct-SQL negatives and matching legal positives for composite payload ownership; exact authority events/role equality and half-open event-time grants, including later-revoked grants; exact Subject lifecycle target-state events with same-Subject `subject` rather than controller authority, and global principal self-status events with fixed `actor_role='subject'`; lifecycle/principal `recorded_at >= occurred_at` plus strictly monotonic principal `updated_at`; cross-subject auth-binding revoke; relationship/assertion lower bounds and dependent relationship-window closure across both `perspective` and `relationship_experience`, including legal `effective_until = parent endpoint` versus open/after-endpoint denial; single-use deletion-request events across controls; pre-endpoint fail-closed `purge_pending`, post-endpoint request denial and pre-endpoint-request/later-completion cleanup; model creation/generation ordering plus generated-time policy validity; pack generated/sealed monotonicity and zero-entry top-level grant/policy/model/action-rule revalidation; one-step decision projection/terminal append denial; counterparty request-before-completion, retention lower bound, legal-hold policy window and active-hold completion denial; monotonic purge proofs; same-subject sealed access-policy validity at both issuance and grant start; active-auth-binding confirmation; per-subject gate version and created/frozen ordering; reviewable-rationale PASS; canonical scorecard digest binding every frozen gate field through explicit one-field twins; missing-UDF fail closure; and earned evaluation PASS in `tests/test_subject_db_schema.py` plus the owning domain test file.
8. T-029 must first collect every planned pytest node, serialize exactly 43 unique SBE→node bindings, then execute every bound node during the fixture stage; testing only this Markdown/JSON mapping is not behavioral closure.
9. T-002 is the sole Create owner of `tests/fixtures/subject_distillation/organization/authority-boundary-cases.json` and its manifest SHA-256; T-020 only reads/reuses them and verifies the exact `E-O-001..005` set/hash, failing on a missing, renamed, duplicate, unreferenced or byte-drifted row.
10. The T-029 unit allowlist must include every behavior-bearing non-surface Subject test named by T-004..T-028; full legacy pytest is later defense-in-depth and cannot repair a missing unit/fixture execution.
11. Evaluation closure must first prove scorecard view and close both fail when deterministic `subject_sha256` is missing, then compare `subject_evaluation_scorecard_v1` one-field twins for manifest SHA, every preregistered eligibility/exclusion/hard-failure/scoring-definition version and SHA, every threshold, and `created_at`/`frozen_at`; byte-identical inputs must remain stable and two signoffs that merely repeat one caller digest are not closure.
12. T-033 remains the closure-only attester for R-SD-016 through the requirement/task matrix; it is not a generic behavior/test owner and must not be added to an SBE `Task(s)` edge without a planned-test intersection.
13. The cross-layer invariant ownership matrices preserve the exact inventory of 26 requirement IDs, 33 task headers and 43 approved SBE rows. These ownership tables are not a new requirement/example matrix: every named concrete owner executes in T-029's unit command before legacy regression, aggregate T-029 does not become a second `Create` owner, no new test path is introduced, and NOT_AUTHORIZED remains fail closed.
