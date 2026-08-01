# Subject Distillation

Subject Distillation is the extensible, generic Subject contract for governed
models of a person, organization, team, project, role, or another future
subject type. The core does not treat an inference as identity truth: it keeps
subject identity, principals, authority, evidence, assertions, relationships,
models, decisions, policies, grants, Context Packs, retention, and evaluation
as distinct governed concepts.

The canonical package is
[`specs/subject-distillation/`](../specs/subject-distillation/requirements.md).
It contains the complete Generic Subject Core and Person-v1 requirements,
architecture, 33 immutable implementation-contract task sections, exact
traceability for 43 approved SBE examples, and the standalone normative SQLite
v15 physical contract. Organization is an Organization contract/SBE-only
boundary; a complete Organization runtime is outside Person v1.

`baseline-manifest.json` binds exactly those five canonical artifacts by path,
order, byte size, SHA-256, a domain-separated full digest, and a shortened
baseline ID. “Frozen” means byte integrity only. It does not imply review
approval, implementation authorization, migration registration, release
authorization, production readiness, or that any task checkbox was executed.

## Status and ownership

Issue #417 historically introduced the earlier public semantic specification.
Issue #410 owns the current canonical five-file product and physical contract.
The earlier public-safety validator remains a separate Phase 0 mechanism and
does not implement the Subject domain.

Runtime is not implemented. In particular, this package does not register the
v15 migration or add Subject emission, retrieval, promotion, Context Pack,
decision, relationship, deletion, evaluation, CLI, MCP, Gateway, Person, or
Organization runtime behavior.

## Person v1 contract

Person v1 preserves the full approved semantics, including:

- authenticated subject confirmation and event-time authority with exact role,
  scope, half-open grant windows, expiry, and revocation rules;
- explicit separation of self-statements, controller or third-party testimony,
  observations, inferences, aspirations, strategy, and recommendations;
- pointer-only, private-copy, and ephemeral evidence retention with source-loss
  handling, support and counter-evidence, immutable provenance, and governed
  correction or supersession;
- one versioned Subject Model producing descriptive, aspirational, decision,
  delegation, and purpose-limited role-scoped Context Pack outputs;
- append-only decision episodes with context, options, constraints,
  recommendations, predictions, actual choices, reasons, outcomes, feedback,
  review state, and one-step projections;
- directional and temporal relationships, alias boundaries, independent
  counterparty privacy, perspective namespaces, retention, legal holds, and
  deletion ordering;
- safe root-subject setup, legacy-Vault compatibility, explicit migration and
  rollback contracts, and no inferred person during upgrade; and
- preregistered synthetic and private-shadow evaluation, hard-failure rules,
  canonical scorecard closure, distinct signoff, and prospective-only learning.

The normative details and all 26 requirement IDs live in `requirements.md`;
this overview does not replace or narrow them.

## Public and private boundary

The public package contains generic contracts, synthetic examples, DDL, and
mechanical integrity tooling only. Real subject data, raw evidence, private
evaluation inputs, secrets, local paths, and operator-private governed records
must remain outside the repository. Candidate-first writes and bounded reads
remain the safe integration direction for any separately authorized future
runtime.
