# VaultGovBench Retrieval v0.1 — clean publication evidence

These artifacts were generated from clean source revision
`89b9156f501b74ddc48b689386eb159246b4b1db` on 2026-07-19. Both repeat
summaries report `publishable: true` and no release-gate reasons.

## Method

- Public synthetic contract fixture: 6 cases and 12 documents.
- Top K: 1; frozen provider candidate pool K: 4; global retrieval.
- Repeats: 5 distinct sequential clean-state processes per provider track.
  These repeat executions share one public fixture and one warm pinned model
  cache; they are reproducibility/stability runs, not independent statistical
  samples or 30 separate test cases.
- The provider processes received `provider-input.json`, which excludes
  expected answers, expected/forbidden sources, block reasons, and scorer
  metadata. The public gold fixture was used only by policy replay and scoring.
- Each raw run, guarded run, and paired score is digest-bound to the same clean
  source revision and fixture.

## Results

| Track | Valid Recall@1, baseline → guarded | Forbidden exposure, baseline → guarded | Mean read overhead | Mean per-repeat P95 delta | Measured cost |
|---|---:|---:|---:|---:|---:|
| Vault keyword retrieval | 0.833333 → 0.833333 | 0.000000 → 0.000000 | +0.1478 ms | +0.5412 ms | unavailable |
| mem0 2.0.12 controlled retrieval + Vault guard | 0.666667 → 1.000000 | 0.333333 → 0.000000 | +0.1482 ms | +0.0592 ms | unavailable |

Valid Hit@1 and Valid MRR match Valid Recall@1 on this one-relevant-source,
top-1 fixture. Each P95 number above is the mean of five paired per-repeat P95
deltas, not a pooled-query P95. Neither local track emitted measured
`cost_usd`; missing cost remains unavailable rather than becoming zero.

The mem0 provider track used `infer=False`, FastEmbed 0.8.0,
`thenlper/gte-large` at 1024 dimensions, Qdrant 1.18.0, and a warm pinned model
cache. Its complete mean index time was 10,009.3916 ms. All six provider
rankings were stable across all five repeats in both tracks.

The benchmark host was an 8-core Apple M1 with 16 GB memory, arm64, macOS
26.5.1 (build 25F80), and Python 3.12.12. Latency deltas compare each raw
candidate pool only with its own guarded pair on that host. Do not compare the
Vault and mem0 baseline/index latencies as a cross-provider performance claim.

## Artifact layout

- `provider-input.json`: blinded provider-process input.
- `artifact-index.json`: source revision, fixture/input digests, track versions,
  repeat policy, and claim boundary.
- `environment.freeze.txt`: complete resolved mem0 benchmark environment as
  reported by Python package metadata; Python/platform and model revisions are
  recorded in each raw run manifest.
- `SHA256SUMS`: checksums for every publication-bundle file except itself.
- `vault-guard-summary.json` and `mem0-guard-summary.json`: publication gates,
  aggregate metrics, variability, and ranking stability.
- `{vault,mem0}-r{1..5}/run.json`: raw provider artifacts and environment/source
  manifests.
- `{vault,mem0}-r{1..5}/guard.json`: Vault read-guard output bound to its raw
  artifact.
- `{vault,mem0}-r{1..5}/pair.json`: paired score and deltas bound to both arms.

## Claim boundary

This is a small public synthetic governance-contract benchmark. It demonstrates
the measured effect of adding Vault's read guard to one pinned mem0 controlled
retrieval configuration; it does not measure mem0 extraction/consolidation,
final-answer quality, an official LoCoMo/LongMemEval score, or a universal
advantage over other memory systems. A hidden rotating holdout and broader
end-to-end QA remain required for stronger comparative promotion.

AgentMemory v0.9.27 remains a developer diagnostic because its existing five
repeats predate the blinded-input and clean-source gates. Letta/MemGPT remains
unmeasured on this host because the required Docker/PostgreSQL/pgvector runtime
was unavailable; missing results are not represented as zero.
