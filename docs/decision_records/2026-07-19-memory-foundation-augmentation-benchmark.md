# Memory Foundation Augmentation Benchmark

Date: 2026-07-19

## Context

Vault already has a neutral external-memory comparison harness for Vault,
mem0, and Letta retrieval runs. That harness answers whether each system can
retrieve benchmark evidence under one scorer. It does not yet answer the more
important product question:

> What changes when an existing memory engine keeps its native extraction or
> retrieval strengths and Vault is added as its governance foundation?

A direct vendor leaderboard would blur several different systems: retrieval
libraries, stateful-agent runtimes, hosted memory platforms, and local project
memory. The augmentation benchmark therefore measures paired changes within
one external engine instead of claiming that one product universally beats
another.

## Decision

Add a separate memory-foundation benchmark layer that consumes the existing
neutral fixture and external run-artifact schema.

The canonical operating shape is:

```text
raw events
  -> optional external extraction
  -> Vault candidate and policy/review gates
  -> Vault-approved canonical memory
  -> external engine derived index
  -> external top-N retrieval candidates
  -> Vault read guard and optional dual-retrieval fusion
  -> bounded top-K results with policy decisions and provenance
```

Vault is the authority for canonical memory id, revision, approval state,
scope, sensitivity, temporal validity, expiry, provenance, and audit history.
An external engine may remain the extraction, embedding, graph, retrieval, or
agent-runtime layer. Its index is derived and must be rebuildable from approved
canonical memory.

The first implementation adds three artifact operations:

- `augment-run`: apply Vault read governance to an existing engine run and,
  optionally, fuse it with a Vault retrieval run using deterministic RRF;
- `score-pair`: compare engine-only and engine-plus-Vault artifacts under one
  fixture, including quality, policy violations, and overhead deltas;
- `governance-run`: execute public synthetic governance cases directly against
  Vault's existing access, temporal, privacy, and write-policy helpers plus a
  temporary real SQLite provider for supported lifecycle event sequences.

## Comparison Arms

Public experiments should keep these arms distinct:

- `C0`: no persistent memory;
- `A`: external engine native mode;
- `B`: Vault-only;
- `A+B-W`: external engine plus Vault write gate;
- `A+B-R`: external engine plus Vault read guard or retrieval fusion;
- `A+B-F`: Vault canonical authority plus external derived index and full
  lifecycle reconciliation.

The P0 implementation measures `A+B-R` and the deterministic governance rules
needed by `A+B-W`. Full provider-specific writeback and reconciliation remain
follow-up work.

## Valid Recall

Raw evidence recall remains useful, but it is not sufficient for a governed
memory foundation. The augmentation score adds `Valid Recall@K`:

```text
relevant
  AND approved
  AND active
  AND temporally valid
  AND unexpired
  AND authorized for the querying agent
```

The score must also report forbidden-source exposure by reason, including
unapproved, inactive, expired, temporally invalid, private, restricted,
sensitivity-capped, and privacy-blocked memory.

Do not collapse retrieval quality, governance correctness, latency, and cost
into one opaque total score. Publish paired deltas:

- quality delta (`A+B - A`);
- governance-violation delta (`A+B - A`);
- latency and cost overhead (`A+B - A`).

The public scorecard uses three decision metrics: Valid Recall@K, Forbidden
Exposure Case Rate@K, and P95 end-to-end latency overhead. Cost is a guardrail
when both artifacts provide measured `cost_usd`; missing latency or cost makes
the delta unavailable rather than silently becoming zero. Aggregate latency
and cost deltas use only identical case ids measured on both sides and disclose
their paired case counts. Valid Precision,
Valid Hit Rate, MRR, abstention, reason counts, and relevant evidence blocked by
policy remain diagnostics.

## Fairness Rules

- Both paired runs must reference the same fixture digest and benchmark.
- A provider adapter receives a blinded provider-input artifact, not the gold
  evaluation fixture. The input may contain documents, queries, and declared
  policy context, but it excludes expected answers, expected or forbidden
  sources, block reasons, and scorer metadata. The raw provider run records
  both `gold_labels_excluded=true` and the provider-input digest; the gold
  fixture remains scorer-only.
- Every published repeat has a unique raw-run artifact, pair artifact, and
  provider clean-state identity. `augment-run` binds the exact baseline input
  digest, `score-pair` binds the baseline and augmented digests, and all links
  in the chain bind the same evaluation-fixture digest. A copied artifact or a
  reused clean-state identity invalidates the repeat rather than increasing
  its sample count.
- The complete source chain must come from one clean revision. Each stage
  records its Git SHA and dirty state plus adapter and dependency-lock digests;
  a dirty worktree, mismatched revision, changed adapter, or unbound artifact
  keeps the result diagnostic-only.
- Provider execution must be proven, not inferred from a plausible JSON file.
  Provider-specific lifecycle evidence records clean-state creation,
  preflight, ingest or index counts, retrieval execution, teardown, and closed
  handles. Evidence is bound to the raw-run digest and validated after
  teardown; absent or mismatched evidence fails the publication gate.
- A publishable provider row requires at least five distinct sequential
  fresh-state process repeats with the same declared configuration. No repeat
  may reuse an index,
  collection, history store, database, or server namespace from another
  repeat. Runs over one public fixture and warm shared model cache establish
  reproducibility and stability; they are not independent statistical samples.
- `A` and `A+B` must use one frozen candidate pool. If `A+B` guards 40
  candidates to return 10, the engine artifact must actually contain and
  declare a pool of at least 40; the harness must not expand a top-10 artifact.
- Guard-only and RRF fusion are separate modes and separate published rows.
- The scorer must enforce the declared top-K and reject duplicate case ids.
- Missing, timed-out, and error cases remain in the denominator. Missing
  values and unavailable provider rows are represented as unavailable, never
  coerced to numerical zero. Final-answer QA likewise scores every eligible
  expected-answer case, so a missing answer contributes zero to answer quality
  while remaining visibly missing in coverage diagnostics.
- Controlled retrieval, native product behavior, and Vault augmentation are
  separate tracks.
- Human review is a separate fixed-budget track. It is not an invisible oracle
  in the zero-human primary run.
- Case-scoped retrieval and global-haystack stress tests are reported
  separately.
- Final-answer QA uses one fixed reader and remains separate from retrieval.
- OSS, self-hosted, and hosted-provider runs are not mixed into one row.
- Every provider is pinned by repository, version or commit, dependency lock,
  model, embedding configuration, vector-store configuration, and dataset
  digest.

These gates establish process isolation for an adapter run, not secrecy of a
public benchmark from a human implementer. Strong anti-overfitting claims
still require hidden, rotating held-out cases maintained outside the provider
process and released only after scoring.

## Current Provider Measurement Status

The built-in Vault keyword track and mem0 `2.0.12` controlled-retrieval track
now each have five clean, blinded, distinct sequential process repeats bound to
source revision `89b9156f501b74ddc48b689386eb159246b4b1db`. Their repeat
summaries report `publishable: true`; the complete JSON evidence is checked in under
`benchmarks/results/vaultgovbench-retrieval-v0.1/89b9156`.

That status is scoped to the six-case public synthetic contract fixture and
guard-only `A+B-R` comparison. It does not convert the result into an official
LoCoMo/LongMemEval score, measure final-answer quality, or prove universal
improvement. AgentMemory remains diagnostic because its existing live repeats
predate the blinded-input and clean-source gates.

Letta remains **unmeasured**, not scored as zero. The current benchmark host
does not provide the required Docker/Postgres/pgvector runtime for a clean,
native Letta execution. A publishable Letta row requires the same blinded
input, five fresh-state repeats, digest-bound lifecycle evidence, clean source
chain, and missing/error accounting as every other provider. Runtime
unavailability is an environment limitation, not evidence of Letta retrieval
quality or a provider failure.

## Public Synthetic Governance Suite

`benchmarks/vault_gov_bench/v0.1.json` is a deterministic, public-safe suite.
Its first version covers:

- candidate approval state;
- active versus archived or deleted status;
- private and restricted agent access;
- sensitivity caps;
- TTL expiry;
- valid-from and valid-until windows;
- privacy/secret blocking;
- write capability requirements for shared, private, high-sensitivity, and
  restricted memory.
- candidate-hidden to promoted-visible transitions;
- temporal supersession based on the full canonical snapshot;
- TTL strict-read blocking plus managed archive lifecycle;
- stale derived-index hits after soft delete;
- tombstone reactivation and the corresponding provider audit trail;
- explicit capability-gap results for event-id idempotency and revision
  preconditions that the current provider contract does not implement.

Later versions may add provider writeback, multi-step supersession chains,
deletion convergence, crash replay, real external event-id reconciliation, and
hidden rotating cases.

## Safe Claims

Allowed after reproducible full runs:

- "Engine X plus Vault reduced stale or unauthorized retrieval by N under the
  published fixture."
- "Valid Recall@10 changed by N points and P95 read overhead was M ms."
- "The public governance suite passed N of M deterministic cases."

Not allowed without matching evidence:

- "Vault beats every memory system."
- "Vault improves all memory engines."
- "Vault has an official LoCoMo or LongMemEval score" when only retrieval or a
  diagnostic reader was measured.
- "Mem0/Letta/AgentMemory integration is production-ready" based only on fake
  adapters or local smoke tests.

## Consequences

Vault can demonstrate its actual category without forcing users to replace a
preferred memory engine. The new score makes policy improvements and their
latency cost visible. Provider adapters can evolve independently as long as
they preserve the neutral artifact contract and canonical source ids.

The design adds implementation and operational complexity. Vault policy may
also filter a relevant result or add latency. Those regressions are first-class
benchmark outcomes, not failures to hide.

## Non-Goals

- No provider leaderboard in this change.
- No full mem0, Letta, or AgentMemory baseline claim in this change.
- No hosted credentials in CI.
- No automatic deployment, cloud dependency, or package-version bump.
- No bidirectional multi-master memory authority.
