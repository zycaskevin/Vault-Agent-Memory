# Subject Distillation — Requirements and SBE Contract

**Status:** Canonical product contract; frozen bytes record integrity only
**Public repository baseline:** `09a0f4c08f2f7479a01c9b6c083dd3cd0e564c27`
**Integrity binding:** `baseline-manifest.json` binds the exact five canonical files, their order, byte sizes, SHA-256 values, full digest, and baseline ID. Integrity does not imply review approval, implementation authorization, migration registration, or release authorization.
**Implementation status:** Not implemented and not authorized by this artifact.
**Product:** Vault Agent Memory
**Target slice:** Generic Subject Core + Person v1; Organization contract/SBE only
**Repository baseline:** public base `09a0f4c08f2f7479a01c9b6c083dd3cd0e564c27` (current public package)

## 1. Product intent

Vault Agent Memory must evolve from a governed retrieval store into a governed
subject-distillation foundation for agent fleets. It must accept authorized
observations and memory from heterogeneous sources, preserve evidence and
permissions, and produce reviewable models of the person, team, organization,
project, or role that an agent fleet serves.

The product must not claim to copy consciousness or treat model inference as
identity truth. It must distinguish what a subject explicitly stated, what was
observed, what was inferred, what the subject aspires to, and what an agent
recommends.

## 2. Evidence-backed baseline

The current public repository already provides useful foundations:

- `docs/vision.md:10-13,50-69,124-157` defines user-owned lifelong memory,
  progressive disclosure, agent-family views, and report/candidate-only memory
  agents.
- `docs/memory_governance.md:162-209` defines private profile guidance and
  separates raw private interactions from reviewed summaries.
- `vault/db.py:188-220` provides governed active knowledge with trust, scope,
  sensitivity, ownership, temporal, lifecycle, and usage metadata.
- `vault/db.py:405-479` provides candidate-first memory and outcome feedback.
- `vault/memory_pipeline.py:15-84` provides a transcript-to-candidate ingestion
  path that can remain an upstream source.

The baseline does not yet provide a generic subject identity, assertion class,
support/counter-evidence model, decision episode, subject-model version,
organization authority graph, or role-scoped model pack.

## 3. Approved scope

The following scope was explicitly selected:

1. The data model and public contracts must use a generic `subject` abstraction.
2. Runtime implementation v1 will complete one Person vertical slice.
3. Organization behavior will be specified with compatible contracts and SBE
   examples, but a complete Organization runtime is not part of v1.
4. The open-source repository contains generic engine code, schemas, APIs,
   synthetic fixtures, and tests only.
5. Real person or organization data remains in the operator's private Vault and
   configuration layer.
6. Existing L0-L3 knowledge, search, candidate, governance, and Task Ledger
   behavior must remain backward compatible unless an approved migration says
   otherwise.

## 4. Actors and terms

| Term | Meaning |
|---|---|
| `subject` | The person, team, organization, project, or role being modeled. |
| `controller` | The principal that controls the subject data and grants access. |
| `observer` | A person, agent, connector, or system that submits evidence. |
| `reviewer` | An authorized principal that reviews candidates or hypotheses. |
| `consumer_agent` | An agent receiving a purpose-limited Subject Context Pack. |
| `assertion` | A typed statement about the subject, never assumed true solely because it was generated. |
| `hypothesis` | An inferred assertion that remains distinguishable from confirmed fact. |
| `decision_episode` | Context, options, recommendation/prediction, actual choice, reasons, and later outcome. |
| `subject_model` | A versioned, evidence-grounded view assembled from assertions and policies. |
| `context_pack` | A role- and purpose-limited projection for one consumer agent or task. |
| `relationship` | A directional, temporal, governed connection between a subject and another subject or counterparty reference. |
| `perspective_model` | A model of another party bounded to one subject's evidence and point of view; never the other party's canonical self-model. |
| `subject_fragment` | A versioned, purpose-limited subset that a subject/controller explicitly publishes for another Vault or principal. |

## 5. Business requirements

### R-SD-001 — Generic subject identity

Every subject-model artifact must reference a stable `subject_id` and a
`subject_type` from an extensible vocabulary. Person v1 must use the same core
contract that future organization, team, project, and role adapters can use.

### R-SD-002 — Open engine, private data, isolated configuration

Public code and fixtures must remain generic and synthetic. Subject records,
private evidence, access policy, and role mappings belong to each operator's
Vault/configuration. No real dogfood identity or private path may be required by
public tests or documentation.

### R-SD-003 — Assertion classes must not collapse

The system must preserve at least these classes as separate machine-readable
states:

- `explicit`: a self-statement created by an authenticated subject confirmation
  action. A direct subject utterance qualifies only when the ingesting surface
  records the authenticated subject principal, statement/confirmation intent,
  event time, bounded source, and a Subject auth binding that is valid for that
  principal at the confirmation event time; a role grant without that physical
  authentication binding is insufficient. A quote relayed by an observer,
  transcript, or connector remains a candidate until such confirmation occurs;
- `controller_attested`: asserted by a data controller or authorized guardian,
  but not represented as the subject's own statement;
- `third_party_reported`: reported by another person or system and kept distinct
  from both self-statement and controller attestation;
- `observed`: a bounded event or behavior with a source reference;
- `inferred`: a hypothesis derived from one or more observations;
- `aspirational`: a desired future state or stated goal;
- `strategic`: an approved direction for an organization/project;
- `recommendation`: agent advice, not a fact about the subject.

### R-SD-004 — Evidence, counter-evidence, and provenance

Every assertion class must record actor/principal, actor role or authority,
recorded time, effective window, assertion class, and bounded source or
confirmation-event reference. `observed` and `inferred` assertions must link to
one or more evidence references, and a hypothesis must support both supporting
and contradicting evidence. `strategic` requires an authorized strategy source;
`recommendation` requires its producing agent/policy identity. Missing or
inaccessible evidence must reduce confidence and must not be replaced with
invented provenance.

Any private payload referenced by evidence, assertion, candidate, alias, decision
event, or purge request must belong to the same governing Subject and have the
declared payload kind. Independent foreign keys to a payload and a Subject are not
sufficient: the physical contract must enforce the pair as one ownership edge.
An authorization, confirmation, provenance, revocation, legal-hold, or deletion
event is valid only when its exact event kind, Subject, actor principal/role, and
effective role grant all match the transition at the event time; an unrelated
same-Subject event is not authority. For an event at `occurred_at = t`, the
authorizing grant is event-time-valid exactly when `effective_from <= t`,
`expires_at IS NULL OR expires_at > t`, and `revoked_at IS NULL OR revoked_at > t`.
The event actor role must equal the effective grant role, not merely belong to the
same allowlist. A grant revoked after `t` therefore remains valid proof for that
historical event; applying the transition later must not add a current-state
`revoked_at IS NULL` requirement to the event-time predicate. Transition-time
preconditions remain separate: the governed row must still be in the permitted
source state, the event must not be replayed, and a revocation/termination
timestamp must equal its bound event time and satisfy the row-specific lower
bound. This one event-time predicate applies to policy approval, assertion,
relationship and alias termination/revocation, role/access/delegation/auth-binding
revocation, and every other exact-authority trigger.

Subject lifecycle events have an exact, non-generic contract. A transition to
`inactive`, `revoked`, or `deleted` requires respectively
`subject.inactivated`, `subject.revoked`, or `subject.deleted`. The bound event
must name the transitioned Subject, and its actor must hold the same-Subject
`subject` role named by the event at `occurred_at`; a `controller` grant is not
lifecycle authority. That
grant is evaluated with the event-time predicate above. The event time must
equal the new `effective_until`, be no earlier than both `effective_from` and
`created_at`, and be no later than `recorded_at`. One lifecycle event may bind
exactly one Subject transition; rebinding or replay is rejected even if the
event otherwise has the right Subject and kind.

Principal status is global rather than attached to an arbitrary Subject. A
transition to `suspended` or `revoked` requires respectively
`principal.suspended` or `principal.revoked`, with `subject_id IS NULL`,
`actor_principal_id` equal to the principal being changed, and
`actor_role='subject'` as the fixed self-event classification. The same
principal must have a physical auth binding valid at the event time under
`created_at <= occurred_at`, `expires_at IS NULL OR expires_at > occurred_at`,
and `revoked_at IS NULL OR revoked_at > occurred_at`; no Subject role grant or
invented global-administrator role substitutes for that binding. The event
time must equal the row's new `updated_at`, be no earlier than `created_at` and
strictly later than the previous `updated_at`, and be no later than
`recorded_at`. A principal status event is single-use and cannot be replayed
against another transition.

### R-SD-005 — Hypotheses are not silent facts

An inferred assertion must remain visibly typed as a hypothesis. It must not be
silently rewritten into an explicit preference, official policy, or stable fact.
Under approved D-SD-001, a policy-qualified inference may enter an active
Context Pack only as a visibly typed hypothesis; only an authorized subject
confirmation action may create an `explicit` self-statement.

### R-SD-006 — Temporal state and supersession

Assertions, policies, and subject-model versions must support effective windows,
supersession, correction, and historical audit. A past assertion remains
reviewable but must not be returned as current without an explicit historical
request.
A model entry may use an assertion/policy only when that source intersects the
model data window and was already effective/recorded at model generation. Model
seal must revalidate every source so an insert-then-revoke race cannot freeze a
stale source into a sealed model. A model's `generated_at` must not follow its
`created_at`, and its exact governing `model` policy must be same-Subject, sealed,
and effective at `generated_at` when the model seals. Assertion termination time
must be at least both `effective_from` and `recorded_at`; relationship termination
time must be at least both `effective_from` and `created_at`.

### R-SD-007 — Controller, subject, observer, and consumer are distinct

The schema and policy layer must not overload `owner_agent` to represent all
human and agent roles. Subject data control, subject identity, evidence source,
review authority, and consumer-agent access must be separately expressible.
Core assertion semantics are invariant: configuration may assign roles and
bounded authority, but it may not relabel controller or third-party testimony as
an explicit self-statement. A Vault may configure reviewer scope, confirmation
quorum, domain, sensitivity, expiry, and revocation without disabling this
provenance boundary.

### R-SD-008 — Purpose-limited disclosure

A consumer agent must receive the smallest useful Context Pack for its role,
purpose, task, sensitivity ceiling, and authorization. Connecting to the same
Vault does not grant access to the full Subject Model or raw evidence. Pack seal
must fail closed unless pack subject, sealed model/model policy, active access
grant/grant policy, consumer, purpose, task, domain, and generated-time window
refer to one internally consistent authorization chain.
Every included pack entry must resolve to an entry of that exact sealed model;
the model entry's source Subject, source lifecycle, domain, output kind, and
underlying assertion sensitivity must fit the active grant. A raw assertion,
policy, or model-entry ID cannot be inserted merely because it exists.
An access grant may be issued only against an exact same-Subject, sealed `access`
policy that is independently effective at both the issuance event time and the
grant's `effective_from`; checking only one of those instants is insufficient,
including when issuance occurs after a requested grant start. Pack seal requires
`sealed_at >= generated_at` and must validate the top-level chain even when the
pack has zero entries: exact same-Subject sealed model and its exact governing
`model` policy, exact same-Subject grant and its exact `access` policy, matching
consumer/purpose/task, and both policies plus the grant effective at both
`generated_at` and `sealed_at`. Grant validity at either time uses its half-open
effective/expiry window and `revoked_at IS NULL OR revoked_at > that_time`.
Pack seal must also revalidate every included entry, its source
lifecycle/effective window, exact model edge, and sensitivity/domain/output scope;
INSERT-time validation or a nonzero-entry loop is not sufficient.

### R-SD-009 — Decision episodes form a feedback loop

Person v1 must be able to record decision context, available options, constraints,
agent recommendation, predicted subject choice (optional), prediction confidence,
prediction rationale (optional), actual choice, subject reason (optional), outcome,
satisfaction/regret feedback (optional), and review state. Prediction confidence
applies only to the predicted subject choice; it is not confidence in the
prediction rationale or the subject's later stated reason. Unknown values must
remain unknown.
The subject may create or append explicit events through approved API, CLI, or
MCP surfaces. Authorized agents and connectors may propose candidate episodes
or sourced observations, but an inferred choice or outcome must not become an
actual event without bounded provenance. Episode updates are append-only and
must preserve the original recommendation, prediction, and later correction.
The episode parent is only a projection cursor: immutable identity fields never
change, its projection sequence may advance only to an existing latest child
event, and review/lifecycle transitions require the corresponding authorized
`reviewed`/`corrected`/`episode_closed`/`episode_revoked` event. A caller-provided
projection MAC alone never authorizes a state change.
Projection advances exactly one child at a time. The latest child's semantic delta
must be reflected in the parent before another child can append; therefore a
terminal event cannot be followed by a non-terminal event while unprojected.

### R-SD-010 — Person v1 separates present self, desired direction, and advice

Person v1 must produce distinguishable outputs for:

- descriptive model: current demonstrated patterns;
- aspirational model: stated goals or desired future self;
- decision policy: reviewed decision criteria and boundaries;
- delegation policy: what an agent may do, must ask about, or must not do;
- role-scoped Context Pack: the minimum view a consumer agent needs.

All five logical outputs are required for Person v1 acceptance. They may be
sections or projections of one versioned Subject Model and must be delivered in
phased vertical slices; they are not required to be five independent services.

### R-SD-011 — Decision support does not imply action authority

A good prediction or recommendation must never create action permission.
Delegation policy is independently controlled, revocable, and bounded by domain,
stakes, reversibility, cost, expiry, and approval mode. Person v1 must default to
advice/shadow mode for high-stakes or irreversible decisions. An action-bearing
Pack must persist the requested domain/stakes/reversibility/cost/currency scope
and mechanically match it to the grant and sealed delegation rule; a rule ID
alone is insufficient.

### R-SD-012 — Correction, revocation, and deletion controls

An authorized controller must be able to correct an assertion, revoke a Context
Pack grant, expire a delegation policy, and request governed deletion or
archival. Revocation must prevent future disclosure even when historical audit
metadata remains. Binding、role/access grant及sealed delegation-rule revocation
must be one-way and append-only-event-bound; terminal state may not be asserted
directly on INSERT. An auth-binding revocation event must use the same Subject as
the binding's original issuance event and the binding's exact
`issued_by_principal_id` authorized issuer, whose grant is event-time-valid under
R-SD-004; authority on another Subject may not revoke the binding, and every
cross-Subject revocation attempt fails closed.

### R-SD-013 — Organization contract preserves authority

Organization-compatible contracts must distinguish official policy/strategy,
authorized leadership decisions, team-local practice, repeated observed
behavior, and agent inference. A single employee preference must not become an
organization direction. Organization runtime implementation is out of v1 scope.

### R-SD-014 — Local-first and provider-optional

The deterministic core, schema, lifecycle, permission checks, and evaluation
fixtures must work without a cloud service or mandatory hosted model. Model-
assisted extraction/distillation may be optional, but its outputs must enter the
same typed evidence and candidate gates.

### R-SD-015 — Existing memory workflows remain valid

Existing projects must continue to compile, search, read, propose, review,
promote, archive, back up, and restore without creating a Subject Model. Subject
capability is additive: completed new interactive installs require root-subject
setup under R-SD-025, while initialization remains opt-in for upgraded legacy
Vaults. Collection, raw copying, provider use, automatic promotion, and sharing
remain separately opt-in in both cases. Migrations must be idempotent and
reversible through a documented backup/rollback path.

### R-SD-016 — Evaluation precedes autonomy claims

Person v1 uses a three-layer release gate. First, deterministic safety invariants
for permission leakage, false self-attribution, unsourced actual outcomes,
temporal/supersession behavior, and legacy migration must pass at 100 percent.
Second, every approved synthetic Person, Organization-compatibility, failure,
and migration SBE example must have mechanical coverage and traceability. Third,
a private shadow pilot must contain `N` completed eligible subject-reviewed
advice or decision cases, where `N >= 20`, across at least three domains. Each
case must have exactly one preregistered primary domain for evaluation, each
primary domain must contain at least five cases, at least five cases must be
preregistered as abstention/unknown probes, and at least three cases must contain
subject correction, counter-evidence, or contextual constraints; designated
cases may overlap. Eligibility and exclusion rules must be frozen before
execution. Every completed case that meets those rules is included in `N`;
outcome-based selection or exclusion is prohibited. Incomplete and excluded
cases must be reported and do not count toward `N`.

The shadow gate passes only when all of the following hold under a preregistered
gate version: zero deterministic safety-invariant failures; zero unresolved
material false self-attribution or other material subject misrepresentation;
zero incorrect subject-choice predictions emitted above `0.80` confidence when
later subject review establishes a different actual choice; at least
`ceil(0.80 * N)` cases are rated by the subject as partially useful or better;
at least `ceil(0.80 * N)` cases have subject-accepted reason alignment; at least
80 percent of all preregistered abstention cases abstain correctly; and each
primary domain has usefulness of at least 60 percent over all eligible cases in
that domain. Every shadow case must include a policy-safe, reviewable rationale
for its advice, prediction, or abstention; a missing rationale counts as not
reason-aligned. A case without a subject-choice prediction is reported but is
not in the high-confidence prediction-error rule. A correct predicted choice
with a rejected rationale counts as a reason-alignment failure, not by itself as
a high-confidence prediction hard failure; it may still independently trigger
the material-misrepresentation hard failure. Utility, reason alignment,
prediction calibration, abstention quality, hard failures, exclusions, and
per-domain results must be reported separately. Both the subject/controller and
a fresh reviewer, represented by distinct principals with active same-subject role
grants at signing time, must sign off on the identical 64-hex SHA-256 report
fingerprint; neither an aggregate score nor one sign-off can override a failed
condition.
For every completed eligible case, utility, reason-alignment, and hard-failure
assessment are mandatory; abstention cases additionally require abstention
assessment. Each case/event-type pair is unique. The v1 metric-bearing event
types `utility`, `reason_alignment`, `abstention`, and `domain_score` require
non-null binary `metric_value` (`0.0` or `1.0`), and `passed` is mechanically
equal to that value rather than independently declared; their `metric_value`
may not be `NULL`. `hard_failure` is instead a non-metric assessment:
`metric_value` is always `NULL`, `passed` is exactly `0` or `1`, and a non-null
bounded `reason_code` is mandatory. A PASS-eligible reason-alignment event must
also carry a non-null bounded rationale `reason_code` and a reviewable
`source_ref`; metric presence or `passed=1` alone is not a rationale. The canonical
scorecard SHA-256 binds signers to identical canonical bytes, while PASS itself is
earned from immutable case/event rows and cannot be created by supplying an
arbitrary matching digest.
Gate version uniqueness is per Subject. Case disposition, metric events, and
signoffs must fall within the frozen-to-close window. Canonical scorecard v1 uses
one specified UTF-8 serialization, fixed field order and explicit type encoding.
Before case/event rows it binds gate/Subject/version; manifest; explicit
`eligibility_rules_version`/`eligibility_rules_sha256`,
`exclusion_rules_version`/`exclusion_rules_sha256`,
`hard_failure_rules_version`/`hard_failure_rules_sha256`, and
`scoring_definitions_version`/`scoring_definitions_sha256` pairs;
denominator rule, minimum `N`, rounding rule, every overall/domain/abstention/high-
confidence threshold; reviewer-authority code; and gate `created_at` and
`frozen_at`. Every named rule version and hash must be preregistered while the
gate is draft, present at freeze, and immutable thereafter; a hard-coded or
implicit version string is not equivalent. The digest serializes each version
adjacent to its hash plus both timestamps in the fixed header order. It then
binds all canonical case/event rows. Two otherwise identical databases that
differ only in a rule version, rule hash, timestamp, threshold, or other frozen
gate field must produce different
digests. Close recomputes and compares the digest through the deterministic
SHA-256 function/view rather than trusting a caller value; a missing UDF fails
closed. `frozen_at` cannot precede gate `created_at`.

A final `stable` attestation for a completed private-shadow task must independently
reopen and reverify the operator-private gate; validating or hashing a release
receipt alone is insufficient. The completed branch requires an operator-supplied
verifier executable, closed-gate input, verifier/key configuration, and complete
release receipt. It invokes one fixed `reopen-and-verify-release-receipt` interface,
recomputes the canonical scorecard, thresholds, distinct signoffs, HMAC, and public
receipt digest, and accepts only the exact public-safe handoff
`private-shadow-pass:<64 lowercase hex>`. Missing inputs, an unavailable/unknown
verifier or key, recomputation mismatch, signoff/threshold drift, or receipt-digest
mismatch must DENY. The verifier is operator-private; this contract does not assert
that a repository executable exists. Shell xtrace must remain disabled, failures
must use nonzero exit plus at most one 96-byte public-safe stderr line whose code
is exactly one of `missing-input|verifier-unavailable|unknown-key|invalid-private-input|recompute-mismatch|signoff-drift|threshold-drift|hmac-mismatch|receipt-digest-mismatch|internal-failure`, and no private path, key,
gate data, full receipt, or private result may enter repository output or logs.

Before the private shadow gate passes, builds may be marked `experimental` but
Person v1 must not be called stable, broadly useful, or evidence of
"understanding" based only on memory volume or search recall. Passing v1 does
not authorize high-risk autonomous action.

### R-SD-017 — Other memory systems are sources, not bypasses

Honcho-like sidecars, transcripts, CRM, calendar, documents, or agent-local
memory may submit authorized evidence/candidates. They must not bypass privacy,
provenance, dedupe, trust, review, or subject access policy.

### R-SD-018 — Third-party data requires independent treatment

A subject model must not treat information about another person as owned or
consented to by the primary subject. Third-party identity and evidence require
separate minimization, sensitivity, access, retention/deletion, export, and
legal/policy treatment. The primary subject/controller may govern their own
private relationship experience but cannot manufacture counterparty consent,
authorize a counterparty self-model, or authorize onward disclosure on the
counterparty's behalf.
`subject_perspective_only`, `counterparty_consent`, `legal_obligation`, and legal
hold each require their own allowlisted event kind and the role authorized for
that basis at event time; they are not interchangeable. Raw third-party evidence and counterparty assertions
must be independently filterable from relationship metadata and first-person
notes. A counterparty control's `retention_until` must be no earlier than its
`created_at`. A legal-hold event must fall within the exact same-Subject sealed
counterparty policy's half-open effective window. Deletion completion is denied
while `legal_hold_until` is later than the completion event time; expiry of the
hold permits cleanup but does not itself authorize disclosure or model use.

### R-SD-019 — Model output must be versioned and inspectable

Every generated Subject Model and Context Pack must expose version, generated
at, effective data window, source/evidence coverage summary, confidence or
unknown state, policy version, and producer identity. Raw private content must
not be copied into routine evidence logs.

### R-SD-020 — Organization compatibility must be mechanically tested

Even though Organization runtime is deferred, schema/API fixtures must prove
that the generic core can represent an organization subject, approved strategy,
authority source, strategy supersession, conflicting local practice, and
role-scoped Context Packs without adding person-only columns to the core.

### R-SD-021 — Evidence retention is tiered and source-aware

Person v1 must support three explicit evidence retention modes. `pointer_only`
is the default and stores source identity, bounded location, time, fingerprint,
policy metadata, and reviewed derivatives without copying full raw content.
`private_copy` requires explicit opt-in and stores only the minimum necessary
raw evidence in a separately governed private evidence lane with sensitivity,
retention, and access controls. `ephemeral` permits processing without durable
raw retention but must lower later verifiability. When a referenced source
becomes unavailable, the system must preserve history, mark the evidence
unavailable, and recompute dependent confidence instead of inventing or
silently retaining the source.
Governed private deletion is physically ordered: object delete time must not follow
parent-fsync proof, metadata clear must follow both, job completion must follow
metadata clear, and payload `purged`/assertion `deleted` must follow the succeeded
job. Non-null proof fields without monotonic event times are insufficient.

### R-SD-022 — Relationships are first-class, directional, and temporal

Person v1 must represent a relationship separately from both participants. A
relationship must have a stable relationship identity, directional roles,
formal relationship type, separately typed lived state, effective windows,
sensitivity, provenance, and lifecycle. A counterparty may use a stable opaque
reference plus controller-selected aliases; an alias such as `wife`, `kid-1`,
or `colleague-a` is not the stable identity.
An alias must reference the exact active controller-to-counterparty relationship,
use an active `alias_value` payload owned by the controller Subject, and carry
event-bound creation/revocation authority. One counterparty may have multiple
concurrent or sequential roles. Ending or changing one relationship role must
not delete the counterparty, erase history, or terminate other active roles.
Alias, perspective assertion, and counterparty-control creation/effective/event
times must all lie inside the exact relationship half-open effective interval.
Before a relationship can end, be revoked, or be deleted at proposed time `t`,
all aliases must be revoked/closed by `t`, all relationship-experience or
perspective assertions must terminate by `t`, and all counterparty controls must
be revoked or moved into fail-closed deletion cleanup by `t`; otherwise the
relationship transition is rejected. The supported ordering is dependent closure
first and relationship transition second, so no dependent half-open window may
extend beyond the relationship window. Alias revocation and perspective-assertion
termination events themselves must occur inside the relationship interval.

The assertion closure query must cover both `relationship_experience` and
`perspective` namespaces. Under half-open semantics, an assertion with
`effective_until = t` is closed at `t`; closure is denied only when a matching
dependent was effective before `t` and has no end or ends after `t`. A
counterparty control in `purge_pending` counts as closed for this parent
transition only when its exact bound `counterparty.deletion_requested` event
was authorized under R-SD-004, occurred inside the relationship interval and
strictly before `t`, and the transition to `purge_pending` has already made
store, model, export, Context Pack, and disclosure use fail closed. Merely
setting the state or attaching an invalid, replayed, at-endpoint, or
post-endpoint request event does not satisfy dependent closure.

The sole post-relationship timing exception is deletion cleanup already started
while the relationship was valid: its deletion-completion event may occur after
relationship `effective_until`, but must follow the bound deletion-request event,
must be denied during an active legal hold, and cannot create or extend any alias,
assertion, counterparty-processing, export, model, or disclosure authority.
After the relationship endpoint, a new deletion request is rejected; only a
request validly bound before the endpoint may complete later. Completion must
retain the original request binding, use the exact
`counterparty.deletion_completed` event and event-time-valid completion
authority, and may perform only purge/deidentification bookkeeping.

### R-SD-023 — Counterparty models are perspective-bound

Person v1 may distill the minimum counterparty patterns needed to understand the
primary subject's relationship context and decisions. Such assertions must be
typed as a `perspective_model`, retain the primary subject/perspective,
relationship, evidence scope, confidence, and assertion class, and must not be
presented as the counterparty's canonical self-model. Relationship context may
be stored privately by its controller, but raw third-party evidence is minimized,
restricted, and excluded from ordinary Context Packs unless specifically
authorized.

### R-SD-024 — Portable Subject Fragment compatibility is reserved for roadmap

The generic core contract must be able to represent a subject-published shared
fragment without merging it into either party's private self-model or
perspective model. A fragment must carry subject identity, issuer principal,
issuer-to-subject authority/consent reference and scope, origin Vault, explicit
counterparty binding, version, content fingerprint, audience, purpose,
sensitivity, effective window, expiry, onward-sharing policy, revocation
reference, and provenance-coverage summary. Raw source evidence is excluded by
default.

Person v1 implements only a deterministic local contract-validation surface over
synthetic or caller-supplied in-memory fragment/lifecycle payloads. The validator
must return an accept/reject result and normalized lifecycle state while keeping
remote self-fragments, local perspective assertions, and bilateral artifacts
separately sourced and conflict-visible. It must reject missing/unauthorized
issuer authority, mismatched subject/counterparty binding, and unverifiable
revocation. V1 does not persist/import remote fragments or implement transport,
identity federation, cryptographic signing, remote trust establishment, or live
synchronization; those are roadmap work.

### R-SD-025 — Subject capability is default-on within a safe envelope

Subject Distillation is part of the default product journey, not a hidden
optional feature. A new interactive installation must initialize a root subject,
controller, empty versioned Subject Model, default-private policy, candidate-only
distillation path, and minimal authorized Context Pack/proposal surfaces. This
does not authorize silent data collection: passive transcript/device scanning,
raw `private_copy`, model-provider calls, broad cross-agent disclosure,
automatic hypothesis promotion, and cross-Vault sharing each require their own
explicit policy gate. Existing Vault upgrades must expose the feature as
`available_uninitialized` and preserve all legacy behavior without inferring a
subject or scanning history until subject setup is completed.

### R-SD-026 — Evaluation learning is a versioned, prospective loop

Each shadow pilot must preregister its gate version, case manifest/fingerprint,
explicit `eligibility_rules_version`/`eligibility_rules_sha256`,
`exclusion_rules_version`/`exclusion_rules_sha256`,
`hard_failure_rules_version`/`hard_failure_rules_sha256`, and
`scoring_definitions_version`/`scoring_definitions_sha256` pairs,
metric denominators and rounding rules, thresholds, and reviewer authority before
execution and scoring begin. Every such frozen field is part of the canonical
scorecard digest under R-SD-016, together with gate `created_at` and `frozen_at`;
all are immutable after freeze.
After a pilot closes, the system may read the frozen scorecard and categorized
failures, propose a bounded adjustment for the next gate/model/policy version,
verify it against retained synthetic and shadow evidence, and write a new
versioned candidate. It must not alter the closed pilot's inputs, thresholds,
scores, denominator, exclusions, or verdict after seeing results. Adjustments
require explicit approval
before affecting a later pilot and must preserve comparison with prior versions.
The loop may never relax the 100-percent deterministic safety invariants,
bypass candidate/review gates, auto-promote subject assertions, or grant new
action authority.

## 6. SBE examples — Person v1

### E-P-001 — Explicit preference remains explicit

**Given** an authenticated subject action explicitly confirms that concise task
reports are preferred
**And** that principal has both a Subject role grant and auth binding valid at the
confirmation event time, even if either is revoked only later
**When** the system records the subject principal, intent, event time, authority,
binding, and bounded confirmation source
**Then** the assertion is typed `explicit`, is current within its validity
window, and may enter a permitted work-agent Context Pack
**And** it is not exposed to unrelated agents without policy.

Covers: R-SD-003, R-SD-004, R-SD-008.

### E-P-002 — Constraint is not mislearned as preference

**Given** a person chooses a cheaper option once because the budget is temporarily
restricted
**When** the decision episode is distilled
**Then** the system records the budget constraint and actual choice
**And** does not infer a stable preference for the cheapest option without
additional evidence.

Covers: R-SD-004, R-SD-005, R-SD-009.

### E-P-003 — Repeated behavior with counter-evidence stays calibrated

**Given** three observed choices support speed over customization and one later
choice favors customization for a high-stakes project
**When** a hypothesis is updated
**Then** all supporting and contradicting evidence remains linked
**And** the hypothesis is domain- or stakes-qualified rather than universal.

Covers: R-SD-004, R-SD-005, R-SD-019.

### E-P-004 — Subject correction supersedes old inference

**Given** a current hypothesis says the person avoids public speaking
**When** the person explicitly corrects it to "I want more speaking opportunities,
but I avoid unprepared talks"
**Then** the old hypothesis becomes historical/superseded
**And** the current model separates the aspirational goal from the preparation
constraint.

Covers: R-SD-003, R-SD-006, R-SD-012.

### E-P-005 — Present pattern and desired direction remain separate

**Given** observed behavior shows frequent short-term postponement
**And** the person explicitly states a goal of becoming more consistent
**When** an agent requests decision support
**Then** the output may report the descriptive pattern and aspirational direction
separately
**And** must not present either one as the other.

Covers: R-SD-003, R-SD-010.

### E-P-006 — Purpose-limited Context Packs

**Given** a schedule agent and a financial agent serve the same person
**When** each requests a Context Pack
**Then** the schedule agent receives only relevant routines, time preferences,
and calendar delegation boundaries
**And** the financial agent receives only relevant risk/approval policy
**And** each grant names a same-Subject sealed/effective `access` policy and each
pack seals only through the exact model/model-policy plus grant/access-policy
chain at both generated and sealed time
**And** the access policy was independently effective at the grant issuance
event and at the grant's `effective_from` \
**And** neither receives unrelated raw conversations.

Covers: R-SD-008, R-SD-011, R-SD-019.

### E-P-007 — Revoked access fails closed

**Given** an agent previously had access to a medium-sensitivity Context Pack
**When** the controller revokes that grant
**Then** subsequent retrieval and Context Pack generation exclude the protected
material
**And** the exact revocation event is authorized at its own event time, while a
later-revoked authorizing role grant does not invalidate that historical event
**And** audit metadata may record the revocation without retaining routine raw
content.

Covers: R-SD-012, R-SD-019.

### E-P-008 — Outcome feedback updates confidence, not history

**Given** an agent predicts option A, the person chooses option B due to a new
constraint, and later reports satisfaction
**When** the decision episode is reviewed
**Then** the actual choice and new constraint are appended
**And** the original prediction remains auditable
**And** future confidence is recalibrated without rewriting the past prediction.

Covers: R-SD-006, R-SD-009, R-SD-016.

### E-P-009 — High-stakes decision remains advisory

**Given** the model has high confidence about a person's historical preference
**When** the current decision is irreversible or high-stakes
**Then** the system may produce evidence-grounded advice
**But** it must not infer execution authority or perform the action without a
separate valid delegation policy and required approval.

Covers: R-SD-011, R-SD-016.

### E-P-010 — Controller testimony does not impersonate the subject

**Given** a guardian or other controller manages an assisted person's Vault
**When** the controller records a statement about that person's preferences
**Then** the statement is typed `controller_attested` with its speaker and
authority scope
**And** it is not represented as an `explicit` self-statement unless the subject
independently confirms it through an authorized subject action.

Covers: R-SD-003, R-SD-007, R-SD-012.

### E-P-011 — Agent observation enters as a decision candidate

**Given** an authorized agent helps a person compare two options
**When** the conversation appears to end with a choice
**Then** the agent may propose a decision episode candidate with bounded source
references and its observed confidence
**But** it may not write the inferred choice as an actual confirmed choice
without an explicit subject event or separately authorized source.

Covers: R-SD-004, R-SD-009, R-SD-017.

### E-P-012 — Later outcome appends without rewriting prediction

**Given** a reviewed episode contains an agent recommendation and predicted
subject choice
**When** an authorized connector later reports a sourced outcome
**Then** the outcome is appended with its own actor, time, authority, and source
**And** the original recommendation and prediction remain unchanged and
auditable.

Covers: R-SD-006, R-SD-009, R-SD-019.

### E-P-013 — Relationship role changes without identity loss

**Given** a counterparty is currently related as spouse and co-parent
**And** the spouse edge has an alias, a perspective assertion, and a counterparty
control whose windows initially extend beyond the proposed spouse end time
**And** a separate first-person `relationship_experience` assertion also extends
beyond that time \
**When** the spouse relationship is first asked to end at that time
**Then** termination is rejected until those dependents are closed, revoked, or
placed into fail-closed deletion cleanup by a valid request strictly before that
time \
**When** dependent closure completes and the spouse relationship then ends from
the stated effective date
**Then** the spouse edge becomes historical
**And** the stable counterparty reference and active co-parent relationship
remain intact
**And** deletion completion may occur later only as cleanup, after its request
and after any legal hold expires, without restoring processing authority
**And** a new deletion request at or after the relationship endpoint is rejected \
**And** current decision support uses the new relationship state without
erasing historical context.

Covers: R-SD-006, R-SD-022.

### E-P-014 — Alias supports recognition without becoming identity

**Given** a controller assigns the private alias `small-x` to a counterparty
**When** an authorized agent receives a relationship-relevant Context Pack
**Then** the pack may use `small-x` within the granted purpose
**And** the alias can be changed or hidden without changing the stable
counterparty reference or exposing a legal name.

Covers: R-SD-008, R-SD-019, R-SD-022.

### E-P-015 — Perspective model and counterparty self-fragment coexist

**Given** a synthetic compatibility fixture contains a local inferred
perspective-bound counterparty assertion
**And** a conflicting explicit Subject Fragment with valid publisher authority
and counterparty binding
**When** the Person v1 local contract validator evaluates the fixture
**Then** both claims remain separately typed, sourced, and conflict-visible
**And** neither silently overwrites the other
**And** any bilateral policy remains a third, separately confirmed artifact.

Covers: R-SD-003, R-SD-023, R-SD-024.

### E-P-016 — New installation starts with a safe root subject

**Given** a person completes a new interactive Vault setup
**When** the required Subject step records the root subject and controller
**Then** an empty versioned Subject Model, default-private policy,
candidate-only proposal path, and minimal authorized Context Pack surface are
available immediately
**And** no historical source, device, transcript, hosted model, or remote Vault
is accessed without its separate explicit gate.

Covers: R-SD-001, R-SD-002, R-SD-008, R-SD-014, R-SD-025.

### E-P-017 — Balanced shadow gate passes with preregistered evidence

**Given** gate version `person-v1-shadow-1` preregisters 20 cases across three
domains with at least five per domain, five abstention cases, and three cases
containing correction, counter-evidence, or contextual constraints
**And** every eligible completed case is included, has one primary domain, and
has a reviewable advice, prediction, or abstention rationale
**And** the frozen report records zero hard failures, 16 or more partially useful
or better ratings, 16 or more subject-accepted reason alignments, at least four
of five correct abstentions, at least 60 percent usefulness in every domain, and
no incorrect subject-choice prediction above `0.80` confidence
**When** the subject/controller and a fresh reviewer both sign the complete
report
**Then** the private shadow gate for that exact version may pass
**And** the signed canonical digest includes the frozen denominator, minimum N,
rounding, all thresholds, each explicit eligibility/exclusion/hard-failure/scoring
version and hash, reviewer authority, gate `created_at`/`frozen_at`, and every
canonical case/event row; changing only one of those header fields changes the digest \
**And** the pass grants neither high-risk action authority nor permission to
describe the system as copying or fully understanding the subject.

Covers: R-SD-011, R-SD-016, R-SD-026.

### E-P-018 — Larger pilots scale every aggregate denominator

**Given** a preregistered pilot completes 25 eligible cases and every completed
eligible case is included in the frozen report
**When** utility and reason alignment are evaluated
**Then** each metric requires at least `ceil(0.80 * 25) = 20` passing cases
**And** the evaluator cannot select a preferred subset of 20 cases or exclude a
case because of its result
**And** any case whose reason-alignment event lacks both a bounded rationale
`reason_code` and reviewable `source_ref` counts as not reason-aligned.

Covers: R-SD-016, R-SD-026.

## 7. SBE examples — Organization compatibility only

### E-O-001 — Official strategy outranks local habit

**Given** an authorized company strategy states that retention outranks new
feature volume
**And** one team historically shipped many new features
**When** a product agent requests direction
**Then** the official current strategy is returned as `strategic`
**And** the team's historical behavior is labeled observed local practice, not
company direction.

Covers: R-SD-003, R-SD-013, R-SD-020.

### E-O-002 — Employee preference is not company policy

**Given** one employee repeatedly prefers a specific vendor
**When** the evidence is distilled
**Then** it may support an individual or team-local observation
**But** it must not become an organization policy without authorized approval.

Covers: R-SD-007, R-SD-013.

### E-O-003 — Strategy supersession preserves history

**Given** strategy v1 prioritizes growth
**When** an authorized decision supersedes it with strategy v2 prioritizing
profitability from a stated effective date
**Then** current Context Packs use v2
**And** v1 remains available for historical explanation.

Covers: R-SD-006, R-SD-013, R-SD-020.

### E-O-004 — Authority conflict is visible

**Given** a team lead proposes a direction that conflicts with a board-approved
policy
**When** the organization model is queried
**Then** the conflict and authority levels are visible
**And** the lower-authority proposal does not silently overwrite the approved
policy.

Covers: R-SD-007, R-SD-013, R-SD-020.

### E-O-005 — Organization Context Pack is role-scoped

**Given** finance and content agents work for the same organization
**When** they request Context Packs
**Then** both receive the current mission and applicable strategy as authorized
`strategic` assertions with authority sources
**And** each receives only domain-relevant policy, confidential data, and
decision boundaries.

Covers: R-SD-008, R-SD-013, R-SD-020.

## 8. Failure and migration examples

### E-F-001 — Insufficient evidence returns unknown

**Given** no explicit statement and only one ambiguous observation
**When** an agent requests a likely preference
**Then** the response is `unknown` or low-confidence hypothesis
**And** the system does not fabricate a stable preference.

Covers: R-SD-004, R-SD-005, R-SD-016.

### E-F-002 — Unavailable source prevents overclaim

**Given** a source reference exists but the consumer is not authorized to read it
**When** a Context Pack is generated
**Then** the pack may expose a policy-safe summary only when one is separately
reviewed
**Otherwise** it reports unavailable evidence rather than leaking or inventing
content.

Covers: R-SD-004, R-SD-008, R-SD-019.

### E-F-003 — Legacy Vault remains valid

**Given** an existing Vault project has only L0-L3 knowledge and no subject tables
**When** it is opened by the upgraded package
**Then** existing compile/search/read/propose/promote behavior still works
**And** no Subject Model is created until the feature is explicitly initialized.

Covers: R-SD-014, R-SD-015.

### E-F-004 — Generic schema accepts organization fixtures

**Given** Person v1 has been implemented
**When** the organization compatibility fixture is validated
**Then** organization subject, authority source, approved strategy, supersession,
and role-scoped access are representable through the generic contract
**And** the test requires no person-only core column.

Covers: R-SD-001, R-SD-013, R-SD-020.

### E-F-005 — Missing pointer source degrades verifiability

**Given** an inferred assertion depends on `pointer_only` evidence
**And** the external source is later deleted or access is revoked
**When** the subject model is rebuilt
**Then** the historical evidence reference remains auditable as unavailable
**And** dependent confidence and evidence coverage are recalculated
**And** the system does not reveal a hidden raw copy or fabricate replacement
evidence.

Covers: R-SD-004, R-SD-019, R-SD-021.

### E-F-006 — Synthetic success alone remains experimental

**Given** every deterministic and synthetic SBE test passes
**But** fewer than 20 subject-reviewed private shadow cases across three domains
have completed
**When** release status is generated
**Then** the feature may be labeled `experimental`
**But** it must not be labeled stable Person v1 or advertised as proven to
understand the subject.

Covers: R-SD-016.

### E-F-007 — Revoked shared fragment stops future disclosure

**Given** an accepted in-memory Subject Fragment fixture and a verifiable
revocation or expiry lifecycle fixture
**When** the Person v1 local contract validator evaluates the lifecycle
**Then** the normalized fragment state becomes inactive
**And** the separately supplied local perspective assertions are not deleted or
rewritten
**And** no remote fragment is persisted or synchronized by the validator.

Covers: R-SD-012, R-SD-019, R-SD-024.

### E-F-008 — Existing Vault upgrade does not infer a person

**Given** a legacy Vault is upgraded to a Subject-capable package
**When** no subject setup has been completed
**Then** the feature state is `available_uninitialized`
**And** existing compile/search/read/propose/promote behavior remains valid
**And** the upgrade does not infer a person, scan old sources, or generate a
Subject Model from existing knowledge.

Covers: R-SD-015, R-SD-025.

### E-F-009 — Relayed first-person quote is not an explicit self-statement

**Given** a transcript, observer, or connector reports that the subject said
"I prefer option X"
**But** the ingesting event lacks an authenticated subject principal and
confirmation intent
**When** the statement enters the memory pipeline
**Then** it remains a sourced candidate or `third_party_reported` assertion
**And** it cannot create an `explicit` self-statement until an authenticated
subject confirmation action occurs.

Covers: R-SD-003, R-SD-004, R-SD-005, R-SD-007, R-SD-017.

### E-F-010 — Unauthorized fragment issuer is rejected

**Given** a Subject Fragment names a counterparty as subject
**But** its issuer lacks subject-self authority or a valid controller delegation
for the published scope
**When** the local contract validator evaluates it
**Then** validation returns reject with an authority failure
**And** no fragment content is treated as counterparty self-model data.

Covers: R-SD-018, R-SD-024.

### E-F-011 — Mismatched counterparty binding is rejected

**Given** a validly issued Subject Fragment is addressed to a different
counterparty reference than the relationship fixture
**When** the local contract validator evaluates the pair
**Then** validation returns reject with a subject/counterparty binding mismatch
**And** the fragment cannot attach to the local relationship or perspective
model.

Covers: R-SD-022, R-SD-023, R-SD-024.

### E-F-012 — Unverifiable revocation does not mutate lifecycle state

**Given** an accepted in-memory Subject Fragment fixture
**When** a revocation payload lacks a matching revocation reference, issuer
authority, or fragment fingerprint
**Then** validation returns reject
**And** the prior in-memory lifecycle fixture is not silently mutated.

Covers: R-SD-012, R-SD-019, R-SD-024.

### E-F-013 — Primary-subject consent cannot disclose counterparty data

**Given** a relationship contains a private alias, first-person relationship
note, raw counterparty message, and sensitive counterparty assertion
**And** the primary subject authorizes a consumer agent only for relationship
decision support
**When** a Context Pack is generated
**Then** it may include only the purpose-minimized relationship metadata and
authorized first-person derivative
**And** it excludes raw and sensitive counterparty content
**And** the primary subject's authorization is not recorded as counterparty
consent for retention, export, self-model publication, or onward sharing.

Covers: R-SD-008, R-SD-018, R-SD-021, R-SD-023.

### E-F-014 — Subject migration is idempotent

**Given** a backed-up legacy Vault
**When** the same Subject-capable migration is completed twice
**Then** both runs produce the same schema/lifecycle state without duplicate
subjects, assertions, relationships, grants, or migration records
**And** legacy compile/search/read/propose/promote behavior remains valid.

Covers: R-SD-015, R-SD-016, R-SD-025.

### E-F-015 — Interrupted migration fails safely

**Given** a legacy Vault and a migration fault injected before completion
**When** the migration aborts
**Then** the transaction rolls back or resumes from an explicit migration marker
**And** the Vault never reports initialized Subject state from a partial schema
**And** legacy data remains readable after recovery.

Covers: R-SD-015, R-SD-016.

### E-F-016 — Backup rollback restores a usable legacy Vault

**Given** a verified pre-migration backup and a successfully migrated Vault
**When** the documented rollback procedure is applied in a temporary restore
location
**Then** the restored Vault passes legacy compile/search/read/propose/promote
smoke tests
**And** its pre-migration knowledge content and governance metadata match the
verified backup
**And** Subject tables or states from the migrated copy do not leak into the
restored legacy Vault.

Covers: R-SD-015, R-SD-016.

### E-F-017 — Aggregate success cannot hide a weak domain

**Given** a 20-case shadow pilot exceeds 80 percent aggregate usefulness
**But** one preregistered domain has usefulness below 60 percent
**When** release status is evaluated
**Then** the private shadow gate fails for that version
**And** neither aggregate performance nor subject/controller discretion may
override the per-domain floor.

Covers: R-SD-016, R-SD-026.

### E-F-018 — Post-hoc threshold changes apply only to a later pilot

**Given** a frozen shadow pilot fails its preregistered reason-alignment threshold
**When** the evaluation loop proposes a better scoring definition or threshold
**Then** the failed pilot retains its original score and verdict
**And** a database differing only in that proposed threshold has a different
canonical scorecard digest
**And** the same is true when only an eligibility, exclusion, hard-failure, or
scoring rule version/hash, gate `created_at`, or gate `frozen_at` differs \
**And** the proposal remains a reviewable candidate for a new gate version and
new prospective pilot
**And** prior and proposed versions remain comparable.

Covers: R-SD-006, R-SD-016, R-SD-026.

### E-F-019 — A hard failure overrides all utility scores

**Given** a shadow pilot meets every utility, reason-alignment, abstention, and
per-domain threshold
**But** one case leaks unauthorized evidence, creates false explicit
self-attribution, records an unsourced actual outcome, or performs an
unauthorized high-stakes action
**When** release status is evaluated
**Then** the gate fails immediately
**And** no loop adjustment, score average, or sign-off may waive the safety
failure for that pilot or lower the invariant for a later version.

Covers: R-SD-005, R-SD-008, R-SD-009, R-SD-011, R-SD-016, R-SD-026.

### E-F-020 — Correct choice with wrong rationale is scored separately

**Given** an agent predicts the subject's actual choice with confidence `0.95`
**But** the subject rejects the agent's prediction rationale
**When** the shadow case is scored
**Then** the case counts as not reason-aligned
**And** it does not trigger the incorrect high-confidence choice-prediction hard
failure solely because the rationale was rejected
**And** a rationale that independently creates a material false self-attribution
or subject misrepresentation still triggers the applicable hard failure.

Covers: R-SD-005, R-SD-009, R-SD-016.

## 9. Non-goals for v1

- Reproducing consciousness, identity, or legal personhood.
- Autonomous execution of financial, medical, legal, relationship, employment,
  or other high-stakes decisions.
- Complete Organization runtime, organization UI, or enterprise workflow engine.
- Mandatory cloud hosting, proprietary model, or remote vector database.
- Bulk ingestion of all private device data by default.
- Treating third-party data as implicitly consented.
- Replacing existing knowledge search, Task Ledger, or agent persona systems.
- Publishing real dogfood data in the open-source repository.
- Live cross-Vault Subject Fragment transport, identity federation,
  cryptographic signing, or synchronization runtime; v1 defines compatibility
  contracts and synthetic SBE only.

## 10. Product decisions

No `design.md`, `tasks.md`, migration, implementation, or coding delegation may
start while any material decision below remains OPEN.

| ID | Decision | Recommended default | Status |
|---|---|---|---|
| D-SD-001 | When may an inferred person hypothesis become active model input? | Two-lane: a policy-qualified inference may enter an active Context Pack only as a visibly typed hypothesis with confidence, evidence, counter-evidence, and scope. Repetition may raise confidence but cannot reclassify it as `explicit`; only an authorized confirmation action can do that. | APPROVED |
| D-SD-002 | Who may confirm/correct a Person subject model? | Constrained configurable role separation: core provenance semantics are immutable; the subject confirms self-statements, the controller governs data/access, delegated reviewers propose within configured scope, and controller/third-party testimony remains separately typed. Vault policy may configure role assignments, scopes, quorum, expiry, and revocation but may not let another actor impersonate the subject. | APPROVED |
| D-SD-003 | What is Person v1 raw evidence retention? | Tiered retention: `pointer_only` is the safe default; `private_copy` requires explicit opt-in and a separately governed private evidence lane; `ephemeral` lowers later verifiability. Source loss becomes `evidence_unavailable` and triggers confidence recalculation rather than hidden copying or invented provenance. | APPROVED |
| D-SD-004 | What is the minimum Person v1 output contract? | All five logical outputs are required: descriptive model, aspirational model, decision policy, delegation policy, and role-scoped Context Pack. They share one versioned Subject Model and may be implemented in phased vertical slices rather than as independent services. | APPROVED |
| D-SD-005 | How are decision outcomes captured in v1? | Explicit events plus agent candidates: the subject may create/append events through API, CLI, or MCP; authorized agents/connectors may propose episode candidates or sourced observations; inferred choices/outcomes cannot become actual events without bounded provenance. Updates are append-only, and v1 has no passive device-wide surveillance or automatic external action. | APPROVED |
| D-SD-006 | What evaluation gate is required before calling the feature useful? | Three layers: 100% deterministic safety invariants; complete mechanical coverage of approved synthetic SBE; and at least 20 subject-reviewed private shadow cases across at least three domains, including abstention, correction, counter-evidence, and contextual constraints. Every completed eligible preregistered case enters the applicable denominator under D-SD-009; metrics are reported separately, no universal score is claimed, and v1 grants no high-risk autonomy. | APPROVED |
| D-SD-007 | What third-party personal data may enter Person v1? | Relationship-first governed inclusion: the primary subject/controller may privately retain the minimum relationship context needed for their own model; relationships are first-class, directional, temporal, and alias-capable; counterparty hypotheses remain perspective-bound rather than canonical models. Full counterparty self-models require independent subject governance. Generic Core reserves a consented, purpose-limited Subject Fragment contract for future cross-Vault sharing, but live synchronization is outside Person v1. | APPROVED |
| D-SD-008 | Should Subject Distillation be core or optional package surface in v1? | Default-on Safe Envelope: Subject capability is part of the required new-install journey; root subject initialization plus minimal Context Pack/proposal surfaces are available by default. Collection, raw evidence copy, model use, broad sharing, promotion, and cross-Vault sync retain independent gates. Existing upgrades remain `available_uninitialized` until setup. | APPROVED |
| D-SD-009 | What exact private shadow pilot pass rule and authority close the third evaluation gate? | Balanced v1 gate over every completed eligible preregistered case (`N >= 20`): at least three primary domains and five cases per domain; at least five abstention and three correction/counter-evidence/context cases; zero hard safety failures, unresolved material misrepresentation, or incorrect subject-choice predictions above 0.80 confidence; at least `ceil(0.80 * N)` usefulness and reason-alignment passes, 80% abstention quality, and 60% usefulness per primary domain; missing rationale is unaligned; subject/controller plus fresh-reviewer sign-off. Results may adjust only a later version through a governed feedback loop; safety invariants never relax. | APPROVED |

## 11. SBE gate and approval record

| Gate | State | Evidence |
|---|---|---|
| Product vision | APPROVED | Generic open-source subject-distillation foundation for people and organizations. |
| v1 slice | APPROVED | Generic Subject Core + Person v1; Organization contract/SBE only. |
| Person business policy | APPROVED | D-SD-001 through D-SD-009, including prospective evaluation-loop governance. |
| Requirements/SBE review | SEPARATE-EVIDENCE-REQUIRED | No verdict is declared by this artifact or manifest. A fresh review PASS with P0=0/P1=0 applies only when separate review evidence binds the exact baseline ID, full digest, and reviewed diff/tree hash. |
| Technical design | SEPARATE-EVIDENCE-REQUIRED | No design verdict is declared here or inferred from integrity validation；only separate exact-baseline review evidence may supply it. |
| Implementation plan | SEPARATE-EVIDENCE-REQUIRED | No plan verdict is declared here；review PASS remains distinct from an explicit implementation-authorization receipt. |
| Coding | `NOT_AUTHORIZED` | No coding or implementation may start; requirements approval and any later design/task PASS do not change this without the designated release authority's explicit authorization. |

## 12. Completion definition for requirements approval

This requirements artifact is approved only when:

- every `R-SD-*` rule is accepted or explicitly revised;
- every `E-P-*`, `E-O-*`, and `E-F-*` example has an expected behavior;
- D-SD-001 through D-SD-009 are decided or explicitly deferred outside v1;
- non-goals are accepted;
- public/private boundaries are preserved;
- a fresh reviewer finds no unresolved material behavior ambiguity.

## 13. Pre-implementation bootstrap and authorization requirement

The normative package remains phase-neutral and `NOT_AUTHORIZED`. Before T-001,
the first executable pre-task is B-000, a local-only authority-bootstrap lane
whose sole output is the strict implementation-authorization receipt schema,
its fail-closed verifier, and the verifier's bootstrap test. B-000 is not a
T-task, never appears in `implementation-progress.json`, cannot authorize
itself, and creates no product behavior, runtime, migration, data, release, or
GitHub operation.

This pre-implementation bootstrap is governance-only and adds no product SBE.

B-000 may begin only after the current five-file baseline integrity validates,
a fresh spec/design/plan review bound to that exact baseline reports PASS with
P0=0/P1=0, clean branch/base/worktree preflight passes, and the repository owner
issues an exact baseline- and scope-digest-bound B-000 instruction through the
trusted operator channel. That channel and instruction are the one explicit
human bootstrap trust root. The repository cannot cryptographically prove the
private conversation or channel. B-000 and all implementation agents must not
self-authorize, infer authorization from hashes or review PASS, or create or
rewrite the owner instruction. The parent orchestrator retains only a
public-safe opaque audit reference outside the repository.

After B-000's exact tree passes its focused tests, parent readback and exact
diff inventory, and fresh spec-compliance followed by quality/security review,
T-001 remains blocked until a separate, actual T-001 receipt verifies. Receipt
integrity is not human authenticity: the verifier binds exact bytes to the
trusted parent's inputs and never claims to prove the owner identity or channel
independently. Any byte change invalidates the old baseline, review, and
authorization bindings; none transfers to a successor baseline.

The authorization protocol has two distinct scope contracts in design §21.
B-000 uses a deterministic in-memory bootstrap-scope projection with lane
`B-000`, exact verified baseline identity, exact three-path write list, and
fixed prohibited operations; it is not a receipt and has no `authorized_task`.
The trusted owner instruction must explicitly contain and byte-equal its four
public binding values, including the projection digest. T-task receipts alone
use the operator-private canonical
`subject-distillation-implementation-scope` file with `authorized_task`.
Operator-private receipt/scope inputs remain outside repo and evidence;
manifest, schema, and verifier are exact canonical repo inputs. Verification
uses retained-descriptor no-follow traversal and bounded same-descriptor reads,
the sole key-aware scanner grammar in tasks §1, OS UTC time with equality at
expiry denied, and mandatory `--json`. Caller/input faults DENY; only safely
classified unexpected internal faults ERROR. Neither contract authorizes
B-000, T-001, or implementation by itself.
