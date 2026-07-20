# Memory Foundation Benchmarks

Vault can be evaluated as a standalone memory system and as a governance layer
added to an existing memory engine. This page documents the second shape.

The benchmark is intentionally paired:

```text
external engine run (A)
  -> Vault policy guard
  -> external engine + Vault run (A+B)
  -> shared paired scorer
```

It reports what changed in retrieval quality, policy exposure, and latency. It
does not produce a universal vendor score. Retrieval fusion is a separate row,
because it changes both retrieval and governance.

## Commands

Run the deterministic public governance suite:

```bash
python benchmarks/memory_foundation_compare.py governance-run \
  --fixture benchmarks/vault_gov_bench/v0.1.json \
  --output /tmp/vault-gov-bench-v0.1.json
```

Run the bundled governance-aware retrieval contract smoke:

```bash
python benchmarks/memory_foundation_compare.py augment-run \
  --fixture benchmarks/vault_gov_bench/retrieval_v0.1.json \
  --engine-run benchmarks/vault_gov_bench/frozen_candidate_pool_v0.1.json \
  --output /tmp/vault-gov-retrieval-augmented.json \
  --mode guard-only \
  --top-k 1 \
  --candidate-pool-k 4

python benchmarks/memory_foundation_compare.py score-pair \
  --fixture benchmarks/vault_gov_bench/retrieval_v0.1.json \
  --baseline-run benchmarks/vault_gov_bench/frozen_candidate_pool_v0.1.json \
  --augmented-run /tmp/vault-gov-retrieval-augmented.json \
  --output /tmp/vault-gov-retrieval-paired.json \
  --top-k 1
```

The bundled candidate pool is deliberately synthetic and deterministic. It
tests the artifact, policy, backfill, and scoring contract; it is not a result
for mem0, Letta, AgentMemory, or Vault retrieval quality, and its local guard
timing is not provider latency evidence.

For a live provider run, first derive a redacted input from the full gold
fixture:

```bash
python benchmarks/external_memory_compare.py export-provider-input \
  --fixture /tmp/longmemeval-fixture.json \
  --output /tmp/longmemeval-provider-input.json
```

Only the provider adapter receives `longmemeval-provider-input.json`.
`augment-run`, `score-pair`, and `summarize-repeats` continue to receive the
full `longmemeval-fixture.json`, because policy replay and scoring require the
separate gold labels. The raw provider artifact binds both digests so the
stages cannot be silently mixed.

CI reruns the dynamic suite and paired contract on every relevant change,
enforces zero unexpected failures/exposures/filter-regret, and uploads the
four JSON artifacts as the `memory-foundation-contract-<git sha>` workflow
artifact for 30 days. Small, sanitized, schema-validated bundles derived only
from a repository-owned public fixture may be committed under
`benchmarks/results/`. Large, external, licensed, private, or credential-bearing
provider packages belong in a release asset or dedicated results repository,
not in the source tree.

Apply Vault read governance to an existing engine run:

```bash
python benchmarks/memory_foundation_compare.py augment-run \
  --fixture /tmp/longmemeval-fixture.json \
  --engine-run /tmp/mem0-longmemeval-run.json \
  --output /tmp/mem0-plus-vault-run.json \
  --top-k 10 \
  --candidate-pool-k 40
```

The engine run must have been produced with at least 40 candidates per query
(`top_k` or `candidate_pool_k` at least 40). The comparison freezes that pool:
`A = raw[:10]` and `A+B = guard(raw[:40])[:10]`. The harness refuses to invent
40 candidates from an engine artifact that only saved 10.

Optionally fuse a Vault retrieval run before applying the same policy:

```bash
python benchmarks/memory_foundation_compare.py augment-run \
  --fixture /tmp/longmemeval-fixture.json \
  --engine-run /tmp/mem0-longmemeval-run.json \
  --vault-run /tmp/vault-longmemeval-run.json \
  --output /tmp/mem0-plus-vault-fusion-run.json \
  --mode rrf-fusion \
  --top-k 10 \
  --candidate-pool-k 40 \
  --rrf-k 60
```

Score the paired change:

```bash
python benchmarks/memory_foundation_compare.py score-pair \
  --fixture /tmp/longmemeval-fixture.json \
  --baseline-run /tmp/mem0-longmemeval-run.json \
  --augmented-run /tmp/mem0-plus-vault-run.json \
  --output /tmp/mem0-vault-paired-score.json \
  --top-k 10
```

## Governance Fixture Extensions

Existing LoCoMo and LongMemEval neutral fixtures remain valid. With no
governance metadata, documents default to approved, active, project-scoped,
low-sensitivity, and timeless.

Governance-aware fixtures may add these document fields either at the top level
or inside `governance`:

```json
{
  "source": "example/current-address",
  "content": "The current office is in Taipei.",
  "governance": {
    "approval_state": "approved",
    "status": "active",
    "scope": "shared",
    "sensitivity": "low",
    "owner_agent": "agent-a",
    "allowed_agents": ["agent-b"],
    "expires_at": "",
    "valid_from": "2026-01-01T00:00:00Z",
    "valid_until": "",
    "privacy_status": "pass"
  }
}
```

Cases may add:

```json
{
  "agent_id": "agent-b",
  "include_private": false,
  "max_sensitivity": "medium",
  "as_of": "2026-07-19T00:00:00Z",
  "expected_sources": ["example/current-address"],
  "forbidden_sources": ["example/old-address"],
  "expected_block_reasons": {
    "example/old-address": "temporal_past"
  }
}
```

## Interpretation

The paired report keeps four surfaces separate:

- raw and valid evidence recall;
- forbidden-source and policy-reason exposure;
- fixed-reader final QA when available;
- retrieval and Vault augmentation latency.

`augment-run` is explicitly labelled `policy replay`: its canonical snapshot
comes from the frozen fixture while its allow/block decisions call Vault's
product read guard. `governance-run` separately exercises candidate promotion,
provider status transitions, audit events, lifecycle archive, temporal
supersession, and known capability gaps against a temporary real Vault SQLite
database. A provider-specific live writeback/reconciliation run is still
required before claiming that integration is production-ready.

For latency comparisons, index latency must include the complete index build,
including embedding generation or rebuild. Historical artifacts whose timers
exclude that work remain diagnostic and must not be placed in the same public
latency table.

The primary product claim is not that Vault retrieves more than every engine.
It is that an engine can keep its native strengths while Vault makes durable
shared memory more trustworthy and inspectable.

### Primary KPIs and guardrails

Keep the public scorecard small and decision-oriented:

1. `Valid Recall@K`: unique expected-valid sources returned at K divided by all
   expected-valid sources. This is the primary usefulness outcome.
2. `Forbidden Exposure Case Rate@K`: cases with at least one fixture-declared
   forbidden source at K divided by all eligible cases. Report reason counts;
   never hide them inside one composite score.
3. `P95 end-to-end latency overhead`: augmented P95 minus baseline P95 on the
   same hardware and frozen pool. Also report `cost_usd` total/mean when both
   runs supply measured provider costs. A delta is unavailable when either side
   omitted the measurement; missing cost or latency is not treated as zero.
   Aggregate deltas use only matching case ids measured on both sides and
   publish `latency_paired_cases` / `cost_paired_cases`.

Useful diagnostics are Valid Precision@K, Valid Hit Rate@K, Valid MRR,
correct-abstention rate, blocked-candidate reasons, and
`relevant_blocked_by_policy` (filter regret). Results are emitted at K=1, 5,
10, and the configured K when available. Missing, error, and timeout cases stay
in the denominator.

Do not set a universal lift target before live provider baselines exist. The
P0 release gate is instead deterministic correctness: artifact/digest checks
pass, the public governance suite has zero unexpected failures, every known
gap is labelled, forbidden exposure is zero after the guard on the synthetic
contract fixture, and no expected-valid source is blocked by policy. Live
provider reports then publish observed deltas with their version, configuration,
hardware, fixed clock, repetition identities, applicable RNG settings, latency,
and cost.

For a live row, `summarize-repeats` additionally requires at least five unique
raw artifacts, five unique pair artifacts, five distinct provider clean-state
identities, exact A-to-A+B digest bindings, zero indexing failures, a clean and
identical committed git/lock/adapter/scorer source chain captured at every
stage, provider inputs with `gold_labels_excluded: true`, and
provider-specific empty-store/teardown proof bound to each raw run digest.
AgentMemory supplies the latter through post-teardown
[`provider_execution_evidence.v1`](../benchmarks/schemas/provider_execution_evidence.v1.schema.json)
artifacts passed with repeated `--execution-evidence` arguments. Missing or
caller-only version/isolation assertions cannot make a row publishable.

The blinded input is a process-isolation control, not proof that a public test
was secret. Anyone can review a checked-in fixture and reconstruct its gold
labels. Public VaultGovBench runs are valuable for reproducibility and policy
contract review, while promotion-grade comparative claims also need a rotating
hidden holdout run by an independent scorer. Its gold must remain unavailable
to provider and adapter code until artifacts and execution evidence are sealed.

## Provider Scope

### Integration coverage matrix

| Engine track | Native `A` artifact | `A+B` read guard | RRF fusion | Governed writeback / full reconciliation |
|---|---|---|---|---|
| Vault | `vault_fixture_run.py` blind provider-input track; legacy `vault-run` is diagnostic only | Product guard + VaultGovBench | Supported as the `B` retrieval contributor | Canonical provider lifecycle is exercised locally |
| mem0 | Built-in `mem0-run` (`infer=False` controlled track) | Supported from the same frozen run artifact | Supported, reported separately | Not yet a live, published integration claim |
| Letta / MemGPT | Built-in `letta-run` Archive/Passages track | Supported from the same frozen run artifact | Supported, reported separately | Not yet a live deletion/writeback reconciliation claim |
| `rohitg00/agentmemory` | `agentmemory_compare.py` controlled track | Supported from the same frozen run artifact | Supported when a second Vault run is supplied | Live lifecycle reconciliation is not yet implemented |
| Another engine | Emit the neutral run-artifact schema | Supported without changing the scorer | Supported when a second Vault run is supplied | Requires a provider-specific adapter and lifecycle test |

“Supported” here means the harness path exists. It does not mean a live full
baseline has been run. Every provider row still needs pinned versions, a fresh
namespace, a redacted provider input, complete artifacts, and the release gate
below. The legacy `external_memory_compare.py vault-run` and
`vault-mode-compare` commands parse raw benchmark data and gold in one process;
they cannot satisfy the blinded-input gate. Use `vault_fixture_run.py --fixture
<provider-input.json>` for a publishable Vault candidate.

Run an actual mem0 `A` and `A+B-R` experiment on the public governance-aware
retrieval fixture from a pinned, isolated environment. The checked-in file is
a direct benchmark dependency lock, not a complete transitive lock; save the
resolved `pip freeze`, Python/platform details, and result manifest with the
published package.

```bash
python -m venv /tmp/vault-mem0-2.0.12-venv
/tmp/vault-mem0-2.0.12-venv/bin/python -m pip install \
  -r benchmarks/provider_requirements/mem0-2.0.12.txt

results_root="$(mktemp -d /tmp/vaultgov-mem0-2.0.12-XXXXXX)"
model_cache="${results_root}/fastembed-cache"
/tmp/vault-mem0-2.0.12-venv/bin/python -m pip freeze \
  > "${results_root}/environment.freeze.txt"

python benchmarks/external_memory_compare.py export-provider-input \
  --fixture benchmarks/vault_gov_bench/retrieval_v0.1.json \
  --output "${results_root}/provider-input.json"

# Prewarm both pinned FastEmbed assets. Network/model download time is not a
# provider indexing result; each measured repeat starts from this same cache.
FASTEMBED_CACHE_PATH="${model_cache}" \
  /tmp/vault-mem0-2.0.12-venv/bin/python -c \
  "from fastembed import TextEmbedding, SparseTextEmbedding; list(TextEmbedding(model_name='thenlper/gte-large').embed(['prewarm'])); list(SparseTextEmbedding(model_name='Qdrant/bm25').embed(['prewarm']))"

summary_args=()
for repeat in 1 2 3 4 5; do
  run_root="${results_root}/repeat-${repeat}"

  PYTHONPATH=. /tmp/vault-mem0-2.0.12-venv/bin/python \
    benchmarks/external_memory_compare.py mem0-run \
    --fixture "${results_root}/provider-input.json" \
    --limit 4 \
    --search-scope global \
    --vector-store-path "${run_root}/qdrant" \
    --history-db-path "${run_root}/history.db" \
    --model-cache-path "${model_cache}" \
    --collection-name "vaultgov_mem0_2_0_12_r${repeat}" \
    --run-namespace "vaultgov-mem0-2-0-12-r${repeat}" \
    --embedder fastembed \
    --embed-model thenlper/gte-large \
    --embedding-dims 1024 \
    --llm-provider ollama \
    --threshold 0 \
    --output "${run_root}/A-mem0.json"

  python benchmarks/memory_foundation_compare.py augment-run \
    --fixture benchmarks/vault_gov_bench/retrieval_v0.1.json \
    --engine-run "${run_root}/A-mem0.json" \
    --output "${run_root}/A-plus-Vault-guard.json" \
    --mode guard-only \
    --top-k 1 \
    --candidate-pool-k 4

  python benchmarks/memory_foundation_compare.py score-pair \
    --fixture benchmarks/vault_gov_bench/retrieval_v0.1.json \
    --baseline-run "${run_root}/A-mem0.json" \
    --augmented-run "${run_root}/A-plus-Vault-guard.json" \
    --output "${run_root}/paired-score.json" \
    --top-k 1

  summary_args+=(
    --pair "${run_root}/paired-score.json"
    --run "${run_root}/A-mem0.json"
  )
done

python benchmarks/memory_foundation_compare.py summarize-repeats \
  --fixture benchmarks/vault_gov_bench/retrieval_v0.1.json \
  "${summary_args[@]}" \
  --output "${results_root}/repeat-summary.json"
```

Each repeat above receives a fresh Qdrant path, history database, collection,
and run namespace. The adapter also gives mem0 a run-local state directory and
disables telemetry by default; do not pass `--enable-telemetry` in a controlled
public run. Keep `infer=False` for this retrieval track. Although the Ollama
client is a pinned direct dependency, `infer=False` means the run should not
invoke native LLM extraction.

The checked-in gold fixture is intentionally not passed to mem0. It remains
available only to the local Vault policy replay, paired scorer, and repeat
summary after the raw provider artifact is sealed.

The public governance fixture has no per-case category partition, so it must
use `--search-scope global`. The adapter rejects an empty case scope rather
than silently labelling a global search as case-scoped. Run repeats
sequentially: parallel provider processes contend for CPU and memory and make
latency numbers unsuitable for publication.

The exact FastEmbed pair is part of the method, not an incidental default:
`fastembed==0.8.0`, `thenlper/gte-large`, 1024 dimensions, `Qdrant/bm25`,
`spacy==3.8.14`, and `en-core-web-sm==3.8.0`. The adapter performs a fail-closed
preflight and refuses a normal artifact if BM25, lemmatization, entity boost,
or embedding dimensions are unavailable. FastEmbed warns
that this model now uses mean pooling rather than the CLS pooling used by older
behavior. Do not combine these repeats with an older artifact unless its
FastEmbed version and pooling behavior are known and reported.

Letta creates and deletes a fresh run-scoped Archive and therefore does not
need a benchmark agent or LLM. For AgentMemory or another engine, emit
`external_memory_comparison_run` with `benchmark`, `fixture_digest`, `top_k`,
`candidate_pool_k`, all fixture case ids, and result `source` provenance; then
run the same `augment-run` and `score-pair` commands. The publishable v1 JSON
contract is available at
[`benchmarks/schemas/external_memory_comparison_run.v1.schema.json`](../benchmarks/schemas/external_memory_comparison_run.v1.schema.json).

### Live-provider execution prerequisites and current status

These rows distinguish execution evidence from release approval. A completed
local diagnostic is still not publishable unless its repeat summary says
`publishable: true`.

| Provider track | Pinned target | Execution prerequisites | Status represented here |
|---|---|---|---|
| Vault keyword retrieval | Source revision `89b9156`; built-in local provider | Five separate clean-state processes; blinded provider input; isolated SQLite databases; fixed keyword configuration; full initialization included in index timing | Five clean, digest-bound repeats completed; every applicable release gate passed and the repeat summary reports `publishable: true`. |
| mem0 controlled retrieval | `mem0ai==2.0.12`; direct dependency lock above | Five separate clean-state processes; blinded provider input; explicit FastEmbed model/dimensions; isolated Qdrant, history, collection, namespace, and mem0 state; telemetry off; `infer=False`; full initialization included in index timing | Five clean, digest-bound current-adapter repeats completed from source revision `89b9156`; native retrieval, gold-isolation, clean-state execution, source-binding, and ranking-stability gates passed. The repeat summary reports `publishable: true`. |
| Letta / MemGPT Archive/Passages | Letta server `0.16.8`; `letta-client==1.12.1` | Reachable pinned server with PostgreSQL/pgvector; blinded provider input; explicit embedding configuration; one fresh Archive per repeat; verify Archive deletion; include server/client/image/model versions and complete initialization timing | Adapter is implemented; local live run is blocked because this host has no Docker or PostgreSQL runtime. Missing is not scored as zero. |
| `rohitg00/agentmemory` | Repository owner `rohitg00`, release `v0.9.27` | Pin the exact repository release and full npm tree; use a blinded provider input and one fresh isolated store per repeat; map result `obsId` back to fixture source before trusting `sessionId`; split index and query timing; bind zero-count/readiness/teardown and dependency-audit evidence to each raw run digest | Five fresh-store developer-diagnostic repeats completed. Publication remains blocked because the runs predate the blind-input gate, the source chain was not cleanly bound, and isolated audits of 0.9.27 and 0.9.28 reported 1 critical, 6 high, and 10 moderate dependency vulnerabilities. |

If a prerequisite is unavailable, report the provider track as blocked or not
measured. Never substitute zero latency, zero cost, or an empty result for a
missing live run.

### 2026-07-19 clean Vault and mem0 publication snapshot

This dated snapshot is reproducible evidence for the harness, not an official
LoCoMo, LongMemEval, or vendor leaderboard result. It used the six-case
VaultGovBench retrieval contract fixture (12 documents, fixture digest
`sha256:017c0629a5611a571ce4088af5b2474d18d8672e12169a2c70d05bc92c3b0b5f`),
global search, candidate pool K=4, and five sequential clean-state provider
processes. Each provider process received only the redacted input digest
`sha256:ddd3a0799c4640c71bff63d86ead20da2c4a5fa5344840f41da828141c6f4fc4`;
the full fixture remained in the policy replay and scorer processes.

Both tracks ran five distinct sequential clean-state process repeats from
committed source revision
`89b9156f501b74ddc48b689386eb159246b4b1db`. The exact provider input, five
raw/guard/pair chains per track, and digest-bound repeat summaries are checked
in under
[`benchmarks/results/vaultgovbench-retrieval-v0.1/89b9156`](../benchmarks/results/vaultgovbench-retrieval-v0.1/89b9156/README.md).
These repeated processes check reproducibility over one public fixture and,
for mem0, one warm pinned model cache; they are not independent statistical
samples.

Anyone can independently verify the checked-in publication bundle's integrity
and release-gate declarations without installing mem0 or trusting the website:

```bash
python scripts/verify_publication_bundle.py \
  benchmarks/results/vaultgovbench-retrieval-v0.1/89b9156
```

The verifier fails closed if a file is changed, omitted from `SHA256SUMS`, or
added without a checksum; if a path escapes the bundle; if the artifact index
is invalid; or if a published track is not marked publishable by both its index
and repeat summary. A pass proves artifact integrity and internal contract
consistency. It does **not** prove that an independent party reran the provider,
recreated the environment, or confirmed the benchmark's external validity.

Independent operators can perform that stronger test with the
[`External Reproduction Kit`](../benchmarks/external_reproduction/README.md).
The v1 kit pins mem0 `2.0.12`, runs five blinded fresh-store repeats, records
the resolved environment, writes exhaustive checksums, validates a public
operator attestation, and provides a GitHub submission form plus CI gate.
Until a submitted bundle is contract-valid and maintainer-reviewed, the public
site continues to report zero accepted external reproductions.

The mem0 provider profile was mem0 `2.0.12` controlled raw insertion
(`infer=False`), FastEmbed `0.8.0`, `thenlper/gte-large` at 1024 dimensions,
Qdrant `1.18.0`, ONNX Runtime `1.27.0`, spaCy `3.8.14`, and
`en-core-web-sm==3.8.0`. The fail-closed preflight passed in all five repeats:
semantic retrieval, Qdrant BM25, lemmatization, entity boost, and embedding
dimensions were all available. The dense and BM25 cache revisions were
`770e825c74a004f165b78793f7c8fc4a95280878` and
`e499a1f8d6bec960aab5533a0941bf914e70faf9`, respectively.

| Paired top-1 result | mem0 only | mem0 + Vault guard | Delta |
|---|---:|---:|---:|
| Valid hit rate | 0.666667 | 1.000000 | +0.333333 |
| Valid Recall@1 | 0.666667 (4/6) | 1.000000 (6/6) | +0.333333 |
| Valid MRR | 0.666667 | 1.000000 | +0.333333 |
| Forbidden-exposure case rate | 0.333333 (2/6) | 0.000000 (0/6) | -0.333333 |
| Mean query latency across repeat means | 747.7018 ms | 747.8500 ms | +0.1482 ms |
| Mean of paired per-repeat P95 values | 1,138.8622 ms | 1,138.9214 ms | +0.0592 ms |

All six provider rankings were identical across all five repeats. Mean complete
provider index time was 10,009.3916 ms (3,295.5360 ms setup and 6,713.8464 ms
ingestion). The mean of the five per-repeat baseline query P95 values was
1,138.8622 ms and the guarded mean was 1,138.9214 ms;
do not reinterpret that aggregate as a pooled P95.

The Vault keyword track scored 0.833333 Valid Recall@1, valid hit rate, and MRR
before and after the guard, with zero forbidden-exposure cases in both arms.
Its mean query latency changed from 0.3950 ms to 0.5428 ms (+0.1478 ms), and its
complete mean index time was 13.1312 ms. The mean of its paired per-repeat P95
values changed from 1.0154 ms to 1.5566 ms (+0.5412 ms). All six Vault rankings
were also identical across all five repeats. Provider/API cost was not measured
for either local track and remains unavailable; it is not zero.

An earlier pre-blind keyword-Vault RRF fusion diagnostic reached the same
top-1 quality and zero-exposure result, but it is not part of this blinded
snapshot and cannot be combined with these latency rows. The blinded
guard-only result supports the governance-foundation claim; it does not claim
that fusion always improves recall.

Both final digest-bound repeat summaries pass blinded-input provenance,
provider clean-state execution, provider retrieval integrity, unique-artifact,
unique clean-state, clean source-chain, zero-index-failure, and five-repeat
gates. The mem0 native-retrieval preflight also passed all five repeats; that
gate is not applicable to the built-in Vault track. Both summaries report
`publishable: true` with no release-gate reasons.

“Publishable” applies only to this frozen six-case contract row and its stated
claim boundary. It does not turn these numbers into end-to-end memory QA or
prove that Vault improves every engine.

### 2026-07-19 local AgentMemory validation snapshot (not yet publishable)

This used the same six cases, 12 documents, global scope, candidate pool K=4,
and five sequential fresh stores. The target was
`rohitg00/agentmemory v0.9.27`, local
`Xenova/all-MiniLM-L6-v2` at 384 dimensions, `iii-sdk@0.11.2`, and a noop LLM.
The runtime lock, complete npm tree, and model digests are recorded in
[`agentmemory-0.9.27.md`](../benchmarks/provider_requirements/agentmemory-0.9.27.md).

| Paired top-1 result | AgentMemory only | AgentMemory + Vault guard | Delta |
|---|---:|---:|---:|
| Valid hit rate | 0.833333 | 1.000000 | +0.166667 |
| Valid MRR | 0.833333 | 1.000000 | +0.166667 |
| Forbidden-exposure case rate | 0.166667 | 0.000000 | -0.166667 |
| Mean query latency across repeat means | 11.3172 ms | 11.4612 ms | +0.1440 ms |

All six full rankings were identical in all five repeats. Mean index time was
507.2062 ms. The mean of the five per-repeat query P95 values was 13.7596 ms;
the pooled 30-query P95 was 14.8766 ms, so those two aggregates must not be
interchanged. The RRF-fusion row reached the same quality with +0.4588 ms mean
paired overhead and therefore added no quality beyond guard-only on this
fixture.

Each successful run verified an empty store before indexing, indexed 12/12
documents, returned zero unmapped ids, and closed all server ports. Five
post-teardown execution-evidence artifacts were SHA-256-bound to their raw
runs and passed the v1 validator. Across setup there were six server-start
attempts with one pre-index 404 failure, plus six health-preflight invocations
with one transient pre-index 503; the five successful adapter runs had zero
errors and zero timeouts.

The final summary still says `publishable: false`: the runs were produced from
a dirty/evolving harness and their run-time benchmark source chain cannot pass
the new clean-source gate; they also predate the blinded-provider-input gate.
These are transparent developer diagnostics, not promotion claims. Letta
remains `not measured`, and broader promotion still requires clean artifact
bundles plus neutral LoCoMo/LongMemEval runs.

### Complete experiment program

Keep six evidence tracks rather than one misleading leaderboard:

| Track | Question | Required evidence |
|---|---|---|
| Retrieval | Can the engine find relevant evidence? | LoCoMo/LongMemEval retrieval-only and optional fixed-reader QA |
| Governance | Does Vault remove invalid exposure without blocking useful evidence? | VaultGovBench paired Valid Recall and forbidden-exposure deltas |
| Lifecycle | Do promotion, expiry, supersession, delete, and restore converge? | Dynamic fixed-clock SQLite/provider cases, then live provider writeback cases |
| Native extraction | What changes when the engine decides what to remember? | A separate `infer=True`/native-agent track including model, tokens, cost, and human-labelled memory quality |
| Robustness/security | What happens on replay, out-of-order events, secret input, and stale indexes? | Event-sequence fixtures; unsupported idempotency/revision behavior remains a named gap |
| Operations | What does the improvement cost? | Full index-build time, P50/P95 query latency, error/timeout rate, storage growth, API/token cost, and cleanup evidence |

LoCoMo or LongMemEval fixtures that mark every document valid should normally
show no guard-only quality delta. Use them for raw retrieval comparability, not
to manufacture a governance lift. The governance-aware fixture supplies the
separate invalid-memory oracle needed for the foundation claim.

- mem0: controlled retrieval should keep `infer=False`; native-product runs
  should separately measure `infer=True`, including LLM extraction cost.
- Letta (formerly MemGPT): archival memory and always-visible memory blocks are
  separate tracks.
- AgentMemory: always publish the full repository owner, release or commit, and
  whether the full server, SDK, or MCP-only surface was used.

MCP compatibility smokes do not replace SDK or REST benchmark runs because an
agent's decision to call a tool would otherwise be mixed into memory-system
quality.
