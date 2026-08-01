# Subject Distillation

Subject Distillation is a proposed pipeline for turning bounded evidence about a
subject into durable, reviewable memory. The public contract is intentionally
conservative: artifacts must remain traceable to evidence, time-bounded when
appropriate, and safe to publish before any downstream system can consume them.

This document is a public specification for future Subject Distillation work. The
current Phase 0 implementation only provides a standalone public-safety
validator; it is not yet wired into full subject artifact emission.

## Status and scope

Current status:

- **Phase 0 implemented:** a standalone public-safety validator for JSON-like
  candidate artifacts.
- **This spec:** defines the public contract future implementation slices should
  follow.
- **Not implemented yet:** integrated emission, retrieval ranking, semantic
  vectors, temporal enforcement, and entity/edge graph extraction.

In scope for the public contract:

- input boundaries for evidence and extraction requests
- output shape for distilled subject assertions
- confidence and trust fields
- evidence and provenance requirements
- temporal validity and stale-fact handling
- publication safety gates and fail-closed behavior
- synthetic examples for later tests

Out of scope:

- processing live or private data in this PR
- promoting claims into active memory automatically
- exposing private runtime metadata, local paths, credentials, or operator notes
- ranking, vector search, graph visualization, or MCP parity implementation
- claiming that Subject Distillation is production-ready

## Terminology

| Term | Meaning |
|---|---|
| Subject | The abstract entity the system is summarizing. Public examples use synthetic identifiers only. |
| Evidence | Bounded source material used to support a possible assertion. Evidence is not memory by itself. |
| Assertion | A normalized statement about the subject, supported by evidence and review metadata. |
| Candidate | A proposed assertion that has not been promoted to active memory. |
| Promotion | A governed review action that accepts a candidate into active memory. |
| Public artifact | Any documentation, JSON, report, or API output intended to be safe for public repositories or public PRs. |

## Input contract

A Subject Distillation request should accept JSON-like data with explicit subject,
evidence, and policy fields. Future implementations may split this across CLI,
MCP, or service APIs, but the semantic boundary is the same.

Required fields:

| Field | Type | Requirement |
|---|---:|---|
| `subject_id` | string | Synthetic or already-authorized identifier. Must not encode private names or local paths. |
| `subject_type` | string | Finite public enum such as `person`, `project`, `organization`, or `unknown`. |
| `evidence_items` | list | Bounded evidence references or redacted snippets. Empty evidence cannot produce promoted assertions. |
| `distillation_goal` | string | Short public-safe goal, for example `profile_summary` or `decision_support`. |
| `policy` | object | Safety and review policy for this run. |

Evidence item fields:

| Field | Type | Requirement |
|---|---:|---|
| `evidence_id` | string | Stable synthetic ID, unique within the request. |
| `source_kind` | string | Finite enum such as `note`, `transcript`, `ticket`, or `manual_fixture`. |
| `observed_at` | string/null | ISO-8601 timestamp or null when unknown. |
| `content_ref` | string | Public-safe reference, digest, or fixture label. Not a local path. |
| `content_excerpt` | string/null | Optional redacted excerpt. Must pass publication safety gates. |

Policy fields:

| Field | Type | Requirement |
|---|---:|---|
| `target_visibility` | string | `public`, `internal`, or `private`; this spec focuses on `public`. |
| `allow_auto_promotion` | bool | Must be `false` for public Subject Distillation candidates. |
| `require_human_review` | bool | Must be `true` before active-memory promotion. |
| `max_assertions` | integer | Positive bound for generated assertions. |

Invalid input must fail closed with a stable diagnostic that does not echo the
payload.

## Output contract

A distillation result contains normalized candidates plus run-level metadata. The
output must be deterministic for the same validated input and policy.

Required top-level fields:

| Field | Type | Requirement |
|---|---:|---|
| `schema_version` | string | Version for the public Subject Distillation output contract. |
| `subject_id` | string | Same authorized subject identifier as input. |
| `subject_type` | string | Same validated subject type as input. |
| `status` | string | `candidate_created`, `blocked`, or `no_assertions`. |
| `assertions` | list | Candidate assertions; may be empty. |
| `safety` | object | Publication-safety decision and blocked reason code if any. |
| `trace` | object | Content-redacted evidence summary. |

Assertion fields:

| Field | Type | Requirement |
|---|---:|---|
| `assertion_id` | string | Stable synthetic ID for this output. |
| `kind` | string | Finite enum such as `preference`, `constraint`, `role`, `relationship`, `skill`, or `unknown`. |
| `statement` | string | Public-safe normalized claim text. |
| `confidence` | number | Numeric confidence from 0.0 to 1.0. |
| `trust_basis` | string | Human-readable basis such as `direct_statement`, `observed_behavior`, or `inference`. |
| `evidence_refs` | list | One or more evidence IDs used for the assertion. |
| `validity` | object | Temporal validity window and stale status. |
| `promotion_state` | string | Must start as `candidate`. |

## Confidence and trust model

Confidence and trust are related but not interchangeable.

- `confidence` measures how strongly the evidence supports the assertion.
- `trust_basis` records why the system is allowed to consider the assertion.
- `promotion_state` records governance state, not model certainty.

Recommended trust-basis values:

| Value | Meaning |
|---|---|
| `direct_statement` | The subject or authorized operator explicitly stated the fact. |
| `observed_behavior` | The fact is derived from repeated behavior in bounded evidence. |
| `inference` | The fact is inferred and must remain lower trust until reviewed. |
| `external_reference` | The fact is supported by a public or authorized source reference. |
| `unknown` | The system cannot classify the basis safely. |

Rules:

1. High confidence cannot bypass review.
2. Inference cannot be promoted without explicit review evidence.
3. Missing evidence references force `status = "blocked"` or an empty candidate
   list.
4. Public artifacts must not expose raw reviewer notes or private run metadata.

## Evidence requirements

Every assertion must cite at least one evidence reference. Evidence references
must be content-redacted and stable enough for audit.

Allowed public evidence shapes:

- synthetic fixture labels
- public documentation anchors
- opaque content digests
- redacted excerpts that pass the public-safety validator

Forbidden public evidence shapes:

- local file-system paths
- credentials or credential-shaped assignments
- raw private messages or transcripts
- operator-only review IDs
- authorization receipts or session metadata
- realistic personal identifiers unless already explicitly public and necessary

The evidence layer should preserve enough structure for later audit without
making the public artifact a copy of the raw source.

## Temporal validity

Subject facts can expire, conflict, or become stale. The output contract makes
that visible instead of treating every assertion as timeless.

Validity fields:

| Field | Type | Requirement |
|---|---:|---|
| `observed_at` | string/null | When supporting evidence was observed. |
| `valid_from` | string/null | Earliest known date/time the assertion applies. |
| `valid_until` | string/null | Latest known date/time the assertion applies. |
| `stale_after` | string/null | Suggested revalidation time. |
| `temporal_status` | string | `current`, `expired`, `unknown`, or `conflicted`. |

Rules:

1. Unknown time is allowed but must be labeled `unknown`.
2. Expired facts must not be presented as current.
3. Conflicting facts must remain separate candidates until review resolves them.
4. A later implementation should make temporal indexing and stale retrieval a
   dedicated slice, tracked separately from this spec.

## Safety and publication gate

Before a Subject Distillation artifact can be public, it must pass a fail-closed
publication gate.

Required checks:

- JSON-like structure only: dictionaries, lists, strings, numbers, booleans, and
  null.
- Exact string keys only; non-string dictionary keys are rejected.
- No forbidden field names that imply credentials or private machine state.
- No credential-shaped strings, local-path-shaped strings, or private-key-shaped
  material.
- No non-finite numbers, unsupported objects, cycles, or aliasing that could make
  validation ambiguous.
- Fixed diagnostics that do not echo rejected payloads.

Publication-gate output should use stable reason codes such as:

| Code | Meaning |
|---|---|
| `invalid_structure` | Input is not exact JSON-like data. |
| `unsafe_field_name` | A field name implies a secret, credential, or private machine state. |
| `unsafe_string` | A string contains credential-shaped or local-path-shaped material. |
| `unsafe_number` | A number is not finite or cannot be represented safely. |
| `unsupported_value` | A value cannot be safely validated. |

## Synthetic examples

### Valid public candidate

```json
{
  "schema_version": "subject-distillation/v0",
  "subject_id": "subject-alpha",
  "subject_type": "person",
  "status": "candidate_created",
  "assertions": [
    {
      "assertion_id": "assertion-001",
      "kind": "preference",
      "statement": "The subject prefers concise operational reports.",
      "confidence": 0.82,
      "trust_basis": "direct_statement",
      "evidence_refs": ["evidence-001"],
      "validity": {
        "observed_at": "2026-01-01T00:00:00Z",
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_until": null,
        "stale_after": "2026-04-01T00:00:00Z",
        "temporal_status": "current"
      },
      "promotion_state": "candidate"
    }
  ],
  "safety": {
    "target_visibility": "public",
    "passed": true,
    "reason_code": null
  },
  "trace": {
    "evidence_count": 1,
    "content_digest": "digest-synthetic-001"
  }
}
```

### Blocked public candidate

```json
{
  "schema_version": "subject-distillation/v0",
  "subject_id": "subject-alpha",
  "subject_type": "person",
  "status": "blocked",
  "assertions": [],
  "safety": {
    "target_visibility": "public",
    "passed": false,
    "reason_code": "unsafe_string"
  },
  "trace": {
    "evidence_count": 1,
    "content_digest": "digest-synthetic-002"
  }
}
```

The blocked example intentionally omits the rejected payload. Public diagnostics
must explain the class of failure without reproducing sensitive text.

## Failure modes

A future implementation must fail closed for these cases:

- required fields are missing or use unsupported types
- evidence references are empty, unknown, or duplicated ambiguously
- output assertions cite evidence not present in the request
- confidence is outside the 0.0 to 1.0 range
- temporal windows are inverted or impossible to compare
- public-safety validation fails
- a formatter or serializer would expose raw private content
- promotion is requested without review authority

Failures should return stable codes and content-redacted diagnostics. They should
not throw raw parser, URL, serialization, or filesystem errors that include the
original payload.

## Relationship to follow-up issues

This spec is intentionally a contract slice. Implementation work should remain
split across the follow-up issues:

- [#412](https://github.com/zycaskevin/Vault-Agent-Memory/issues/412): MCP
  contract parity for public memory tools.
- [#413](https://github.com/zycaskevin/Vault-Agent-Memory/issues/413): public
  retrieval benchmark baseline.
- [#414](https://github.com/zycaskevin/Vault-Agent-Memory/issues/414):
  semantic/vector retrieval path.
- [#415](https://github.com/zycaskevin/Vault-Agent-Memory/issues/415): temporal
  validity handling.
- [#416](https://github.com/zycaskevin/Vault-Agent-Memory/issues/416):
  entity/edge graph extraction contract.
- [#417](https://github.com/zycaskevin/Vault-Agent-Memory/issues/417): this
  public Subject Distillation spec.

## Validation

For the current Phase 0 validator, run:

```bash
python -m pytest -q -p no:cacheprovider tests/test_subject_public_safety.py
```

For public repository changes, run the public PR gate against the candidate diff:

```bash
python scripts/public_pr_gate.py --base <base-branch> --head HEAD --target-visibility public
```

When this document is changed in a stacked PR, use the stacked base branch for
candidate review so the spec diff remains separate from the Phase 0 foundation
PR.
