# External Memory Benchmarks

Vault can run retrieval-only adapters for external long-term memory benchmarks.
These adapters measure whether Vault search retrieves the expected evidence
source. They do **not** measure final-answer quality, reader-model reasoning, or
official leaderboard scores.

## Current Status

What is ready to claim:

- Vault has retrieval-only adapters for LoCoMo and LongMemEval-style evidence
  recall.
- The comparison harness can export one neutral fixture, run multiple memory
  systems with the same top-k, and score all systems with the same exact
  `source` id matching rule.
- Vault full retrieval baselines have been run locally for LoCoMo `locomo10`
  and LongMemEval small.
- mem0, Letta, and `rohitg00/agentmemory` adapters exist for same-fixture
  comparison runs.
- The release-oriented adapters accept a redacted provider input, leaving
  expected answers and expected/forbidden source labels with the scorer.
- The harness can add a fixed-reader answer pass and score diagnostic final-QA
  metrics separately from retrieval.

What is not ready to claim:

- These numbers are not official LoCoMo or LongMemEval leaderboard scores.
- Current published local results do not prove final answer quality.
- Current published local results do not prove that Vault beats mem0, Letta, or
  MemGPT-style agents.
- The mem0 row below is a 10-case adapter smoke, not a full mem0 baseline.
- The Letta adapter has not yet produced a published live run result in this
  document.
- The dated mem0 and AgentMemory developer snapshots predate the blinded-input
  gate and are not promotion-ready results.

## Supported Adapters

### LoCoMo

LoCoMo is a very long-term conversational memory benchmark. The public release
contains ten conversations in `data/locomo10.json`. Each QA annotation includes
question, answer, category, and evidence dialog ids when available.

Vault indexes each dialog turn as one evidence document:

```text
locomo/<sample_id>/dia/<dialog_id>
```

By default, retrieval is scoped to the source conversation for each QA case.

Run a small retrieval smoke:

```bash
python benchmarks/external_memory_retrieval.py \
  --benchmark locomo \
  --input /path/to/LoCoMo/data/locomo10.json \
  --max-cases 20 \
  --limit 10 \
  --output /tmp/vault-locomo-retrieval.json \
  --generated-qa /tmp/vault-locomo-searchqa.json
```

### LongMemEval

LongMemEval evaluates long-term interactive memory with 500 questions across
information extraction, multi-session reasoning, temporal reasoning, knowledge
updates, and abstention. The released JSON files include `haystack_sessions`,
`answer_session_ids`, and turn-level `has_answer: true` labels.

Vault indexes session-level evidence by default:

```text
longmemeval/<question_id>/session/<session_id>
```

By default, retrieval is scoped to the haystack for the current question. This
matches the benchmark setup where each question carries its own candidate
history. Use `--search-scope global` only when intentionally stress-testing
cross-question retrieval interference across the whole generated Vault DB.

Run a small retrieval smoke on the cleaned small split:

```bash
python benchmarks/external_memory_retrieval.py \
  --benchmark longmemeval \
  --input /path/to/longmemeval_s_cleaned.json \
  --max-cases 20 \
  --limit 10 \
  --output /tmp/vault-longmemeval-retrieval.json \
  --generated-qa /tmp/vault-longmemeval-searchqa.json
```

For full-run iteration, keep a reusable benchmark DB and print progress:

```bash
python benchmarks/external_memory_retrieval.py \
  --benchmark longmemeval \
  --input /path/to/longmemeval_s_cleaned.json \
  --db-path /tmp/vault-longmemeval-s.db \
  --limit 10 \
  --progress-every 50 \
  --output /tmp/vault-longmemeval-s-retrieval.json \
  --generated-qa /tmp/vault-longmemeval-s-searchqa.json
```

Rerun against the same DB without rebuilding:

```bash
python benchmarks/external_memory_retrieval.py \
  --benchmark longmemeval \
  --input /path/to/longmemeval_s_cleaned.json \
  --db-path /tmp/vault-longmemeval-s.db \
  --reuse-db \
  --limit 10 \
  --progress-every 50 \
  --output /tmp/vault-longmemeval-s-retrieval.json
```

Turn-level indexing is also available:

```bash
python benchmarks/external_memory_retrieval.py \
  --benchmark longmemeval \
  --input /path/to/longmemeval_s_cleaned.json \
  --granularity turn \
  --max-cases 20 \
  --limit 10 \
  --output /tmp/vault-longmemeval-turn-retrieval.json
```

## Fair System Comparison Harness

Use `benchmarks/external_memory_compare.py` when comparing Vault with other
memory systems such as mem0, Letta, MemGPT-style agents, or custom RAG memory
stores. The harness separates the benchmark data, system adapter, scorer, and
engineering capability report so every system can be measured under the same
rules.

### Which Command Should I Use?

| Command | Use it for | Output |
|---|---|---|
| `benchmarks/external_memory_retrieval.py` | Quick Vault-only retrieval probes for LoCoMo or LongMemEval. | Vault retrieval report and optional Search QA file. |
| `benchmarks/external_memory_compare.py export-fixture` | Create a neutral benchmark fixture shared by all systems. | Fixture JSON with documents, cases, expected sources, and answers. |
| `benchmarks/external_memory_compare.py export-provider-input` | Remove scorer gold before a provider process reads the fixture. | Redacted provider-input JSON bound to the gold fixture digest. |
| `benchmarks/vault_fixture_run.py` | Run Vault from a redacted provider-input fixture. Use this path for a blind release candidate. | Vault run artifact with provider-input provenance. |
| `benchmarks/external_memory_compare.py vault-run` | Legacy one-process Vault diagnostic that parses the raw LoCoMo/LongMemEval file. | Non-blind Vault run artifact. |
| `benchmarks/external_memory_compare.py vault-mode-compare` | Legacy one-process Vault mode diagnostic across multiple retrieval modes. | Non-blind Vault mode-comparison artifact with scores and deltas. |
| `benchmarks/external_memory_compare.py mem0-run` | Run mem0 against a redacted provider input. | mem0 run artifact. |
| `benchmarks/external_memory_compare.py letta-run` | Run Letta Archive/Passages retrieval against a redacted provider input. | Letta run artifact. |
| `benchmarks/agentmemory_compare.py` | Run `rohitg00/agentmemory` against a redacted global provider input. | AgentMemory run artifact. |
| `benchmarks/external_memory_compare.py answer-run` | Generate final answers from retrieved evidence with one fixed reader and redacted input. | Answered run artifact. |
| `benchmarks/external_memory_compare.py score-run` | Score retrieval, optional final QA, latency, and engineering fields. | Score JSON. |

The comparison flow is:

```text
LoCoMo / LongMemEval JSON
  -> gold scoring fixture
  -> redacted provider input (documents + query/policy context only)
  -> one run artifact per memory system
  -> optional fixed-reader answer run
  -> shared scorer using the separate gold fixture
  -> retrieval, final QA, latency, and engineering report
```

To measure an external engine with Vault as its governance foundation, continue
with the paired [Memory Foundation Benchmark](memory_foundation_benchmarks.md).
That track remains retrieval-only unless a fixed reader is explicitly added.
It freezes one candidate pool: if the guard examines 40 candidates and returns
10, the engine run must actually declare/save `candidate_pool_k >= 40`;
`A = raw[:10]` and `A+B = guard(raw[:40])[:10]`. A top-10 artifact cannot be
expanded after the fact.

Publish guard-only and RRF-fusion as different rows. Guard-only isolates policy
effects; fusion changes retrieval as well and cannot attribute the whole delta
to governance. Index latency must include document ingestion plus embedding or
semantic-index generation/rebuild. Earlier artifacts whose timer excluded that
work remain diagnostic and must not be compared in the same latency table.

### Prerequisites

Vault runs use the local repo checkout and the benchmark JSON files. No cloud
service, embedding API, or hosted model is required for retrieval-only keyword
runs.

mem0 runs are optional and should be done in an isolated Python environment.
Install and pin `mem0ai`, the selected embedder package, vector store, and LLM
provider before publishing numbers. The local smoke used `fastembed` with the
SDK's default `thenlper/gte-large` model dimensions and `ollama` as the mem0 LLM
provider, even though retrieval insertion used `infer=False`.

Letta runs require a pinned Letta server and an explicit embedding
configuration. Cloud runs require `LETTA_API_KEY`; an unsecured self-hosted
server can omit it. The adapter creates and deletes one run-scoped Archive, so
it does not require a pre-existing agent or an LLM.

`rohitg00/agentmemory` runs require a fresh, isolated v0.9.27 server process for
every repetition. Its `project` request field is not a reliable filter for
ordinary memory results in that release, so the adapter only accepts global
fixtures and fails closed if search returns an id that was not created by the
current run. Pin the complete npm lock/tree, embedding provider, model, and
dimensions before publishing numbers.

Final-QA runs require a fixed reader model, prompt, decoding settings, and
evaluator policy. The included answer scorer is diagnostic. Do not treat it as
the official LoCoMo or LongMemEval judge.

Export a neutral fixture:

```bash
python benchmarks/external_memory_compare.py export-fixture \
  --benchmark longmemeval \
  --input /path/to/longmemeval_s_cleaned.json \
  --output /tmp/longmemeval-fixture.json
```

Create the file that may be given to a provider process:

```bash
python benchmarks/external_memory_compare.py export-provider-input \
  --fixture /tmp/longmemeval-fixture.json \
  --output /tmp/longmemeval-provider-input.json
```

The provider input keeps the evaluation fixture digest but has its own content
digest. It removes expected answers, expected/forbidden sources, scorer
metadata, and document label fields. Give this redacted file to every memory
provider and fixed-reader process. Keep the full gold fixture outside those
processes; use it only for `augment-run`, `score-pair`, or `score-run`. A
publishable provider repeat must report `gold_labels_excluded: true` and bind
the provider-input digest back to the full fixture digest.

This separation prevents accidental label leakage, but a checked-in public
fixture is still open to code review. An adapter author can read the repository
and reconstruct its expected or forbidden sources even if the provider process
only receives the redacted file. Public fixtures therefore prove a
reproducible contract; they are not an anti-cheating boundary. Stronger
comparative claims additionally require a rotating hidden holdout whose gold
labels stay with an independent scorer and are disclosed only after the run is
sealed.

Run Vault from the provider input into the shared run-artifact schema:

```bash
python benchmarks/vault_fixture_run.py \
  --fixture /tmp/longmemeval-provider-input.json \
  --candidate-pool-k 10 \
  --mode keyword \
  --output /tmp/vault-longmemeval-run.json
```

The older `vault-run` path remains useful for reproducing historical adapter
results:

```bash
python benchmarks/external_memory_compare.py vault-run \
  --benchmark longmemeval \
  --input /path/to/longmemeval_s_cleaned.json \
  --limit 10 \
  --progress-every 50 \
  --output /tmp/vault-longmemeval-run.json
```

`vault-run` and `vault-mode-compare` parse the raw benchmark and construct the
gold fixture in the same process. They cannot consume
`export-provider-input`, so their output is not a blinded provider run and
cannot satisfy the current publication gate. Use `vault_fixture_run.py` for a
release candidate; use the legacy commands only as clearly labelled
diagnostics.

Run Vault mode comparisons with one benchmark file, one top-k, one search scope,
and one exact `source` id scorer:

```bash
python benchmarks/external_memory_compare.py vault-mode-compare \
  --benchmark longmemeval \
  --input /path/to/longmemeval_s_cleaned.json \
  --limit 10 \
  --modes keyword,hybrid,semantic \
  --embed-provider onnx \
  --embed-model mix \
  --semantic-vector-kind node \
  --progress-every 50 \
  --output /tmp/vault-longmemeval-mode-comparison.json
```

`--embed-provider onnx --embed-model mix` uses the local ONNX embedding provider
with the repo's mixed-language default model. External benchmark documents are
raw evidence records, so the harness defaults to `--semantic-vector-kind node`
instead of claim vectors. Pin and record the provider, model, dimension, vector
kind, and model cache/source before publishing semantic or hybrid numbers.

For CI or local plumbing checks without downloading a real embedding model, add
`--allow-hash --hash-dim 8`. Hash vectors only verify semantic/hybrid command
wiring and artifact shape; do not publish hash-vector numbers as semantic
retrieval quality.

Run mem0 into the same run-artifact schema:

```bash
python benchmarks/external_memory_compare.py mem0-run \
  --fixture /tmp/longmemeval-provider-input.json \
  --limit 10 \
  --embedder fastembed \
  --vector-store-path /tmp/mem0-longmemeval-qdrant \
  --output /tmp/mem0-longmemeval-run.json
```

The mem0 adapter is optional and requires the `mem0ai` package. It inserts
fixture documents with `infer=False` for retrieval-only comparison so an LLM
memory-extraction pass is not mixed into evidence recall. The adapter preserves
benchmark `source` ids in metadata and uses the same case/global search-scope
contract as the Vault adapter. Each run creates an isolated collection and
user/run namespace by default; it does not call reset/delete on an existing
collection. Pin the embedder and vector-store settings before publishing
numbers. For the current mem0 SDK, `--embedder fastembed` requires
the separate `fastembed` package and defaults to 1024 embedding dimensions for
the SDK's default `thenlper/gte-large` model; override with `--embedding-dims`
when using a different embedder model. Retrieval-only runs still initialize a
mem0 LLM provider, so the local smoke path uses `--llm-provider ollama` and
requires the `ollama` Python package even when `infer=False`.

Run Letta Archive/Passages retrieval into the same run-artifact schema:

```bash
python benchmarks/external_memory_compare.py letta-run \
  --fixture /tmp/longmemeval-provider-input.json \
  --base-url http://127.0.0.1:8283 \
  --embedding ollama/bge-m3:latest \
  --server-version 0.16.8 \
  --run-id vault-memory-benchmark-001 \
  --limit 10 \
  --output /tmp/letta-longmemeval-run.json
```

The Letta adapter creates a run-scoped Archive, inserts passages, searches via
`POST /v1/passages/search`, and deletes the Archive in `finally`. It stores
benchmark source ids as passage tags and adds the case category tag when
`--search-scope case` is used. Self-hosted Letta 0.16.8 still requires its
PostgreSQL/pgvector runtime; an Archive without embeddings only provides a
lexical fallback and is not an equivalent semantic baseline.

Run `rohitg00/agentmemory` v0.9.27 against a neutral global fixture:

```bash
python benchmarks/agentmemory_compare.py \
  --fixture /tmp/longmemeval-provider-input.json \
  --base-url http://127.0.0.1:3911 \
  --fresh-store-id agentmemory-run-001 \
  --run-id agentmemory-run-001 \
  --embedding-provider local \
  --embedding-model Xenova/all-MiniLM-L6-v2 \
  --embedding-dims 384 \
  --limit 10 \
  --output /tmp/agentmemory-run.json
```

The adapter uses `POST /agentmemory/remember` and
`POST /agentmemory/smart-search`, maps each returned `memory.id` back to the
fixture source, and deliberately ignores the provider's constant
`sessionId: "memory"`. The caller must attest to a fresh store with
`--fresh-store-id` and stop the server after the run. The adapter records that
teardown as an external requirement; it cannot prove lifecycle isolation from
inside the HTTP process.

After teardown, bind observed version/model settings, zero-count preflight,
provider lock/tree digests, and closed-port evidence to the raw run digest with
[`provider_execution_evidence.v1.schema.json`](../benchmarks/schemas/provider_execution_evidence.v1.schema.json).
Pass one `--execution-evidence` file per run to `summarize-repeats`; the release
gate does not accept `--fresh-store-id` alone as proof.

Generate final answers from the same retrieved evidence with a fixed reader:

```bash
python benchmarks/external_memory_compare.py answer-run \
  --fixture /tmp/longmemeval-provider-input.json \
  --run /tmp/vault-longmemeval-run.json \
  --llm-provider ollama \
  --llm-model qwen3:8b \
  --output /tmp/vault-longmemeval-answered-run.json
```

Score any system run with the same evidence matching rule:

```bash
python benchmarks/external_memory_compare.py score-run \
  --fixture /tmp/longmemeval-fixture.json \
  --run /tmp/vault-longmemeval-answered-run.json \
  --output /tmp/vault-longmemeval-score.json
```

Adapters for other systems should emit this minimal run-artifact shape:

```json
{
  "schema_version": 1,
  "artifact_type": "external_memory_comparison_run",
  "system": "example-memory",
  "system_version": "1.0.0",
  "benchmark": "longmemeval",
  "fixture_digest": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "top_k": 10,
  "candidate_pool_k": 10,
  "cases_total": 1,
  "cases": [
    {
      "id": "question-id",
      "latency_ms": 12.5,
      "answer": "optional final answer",
      "results": [
        {"rank": 1, "source": "longmemeval/question-id/session/session-id"}
      ]
    }
  ],
  "engineering": {
    "local_first": {"supported": true, "measured": true, "evidence": "local DB run"},
    "multi_agent_shared_memory": {"supported": false, "measured": false, "evidence": ""},
    "sync": {"supported": false, "measured": false, "evidence": ""},
    "report": {"supported": false, "measured": false, "evidence": ""},
    "audit": {"supported": true, "measured": false, "evidence": "source ids preserved; audit lifecycle not exercised"}
  }
}
```

The scorer uses exact `source` id matching for retrieval. Final QA is reported
separately with non-official normalized exact-match, contains-expected, and
token-F1 metrics when a run supplies `answer`. Use `answer-run` to add answers
from a fixed reader prompt without rerunning retrieval. This keeps
retrieval-only and answer-generation results from being mixed into one
misleading score. Every fixture case with an expected answer remains in the
final-QA denominator; a missing answer scores zero and lowers answer coverage.

### Running a Fair Comparison

1. Export one full gold fixture from the benchmark data.
2. Export one redacted provider input from that exact gold fixture.
3. Run every memory system against the provider input, never the gold fixture.
4. Use the same `--limit` / top-k for every run.
5. Keep the same `--search-scope` policy for every run.
6. Score every run with the separate gold fixture through `score-run`.
7. Compare retrieval-only metrics before comparing final-QA metrics.
8. Only compare final-QA metrics after every system uses the same fixed reader
   and scorer.
9. Report index latency separately from query latency.
10. Report engineering fields separately from retrieval and answer quality.
11. Publish dependency versions, model versions, vector-store settings, and
    whether each run was a full run or smoke run.

## Metrics

The report includes:

- `search_scope`: `case` searches only the case-specific evidence pool;
  `global` searches the whole generated Vault DB.
- `hit_rate`: fraction of evidence-bearing cases where any expected evidence
  source appeared in top-k results.
- `top1_hits`, `top3_hits`, `top5_hits`: evidence hit counts by rank cutoff.
- `mean_reciprocal_rank`: reciprocal-rank average for first evidence hit.
- `mean_latency_ms`, `p95_latency_ms`: local search latency for the retrieval
  run.
- comparison scores additionally include final-QA answer metrics when supplied
  and engineering capability fields for local-first, shared multi-agent memory,
  sync, reporting, and auditability.
- comparison run artifacts include `index_latency_ms` so build/index cost is
  reported separately from per-query retrieval latency.

## Limits

The original retrieval adapter is designed for the first benchmark stage:

```text
history -> Vault indexing -> search -> evidence recall
```

They intentionally do not run:

```text
retrieved evidence -> reader model -> answer -> judge
```

Official LoCoMo / LongMemEval answer scores require a fixed reader model,
prompt, top-k policy, generation settings, and evaluator. LongMemEval's official
QA evaluator uses OpenAI-model judging. Do not publish these retrieval numbers
as LoCoMo / LongMemEval leaderboard scores.

The comparison harness can carry final answers, but its answer metrics are
diagnostic only. Use an official or fixed third-party judge before making public
claims about answer quality.

## Publication Policy

Safe public wording:

- "retrieval-only evidence recall"
- "source-id hit rate under fixed top-k"
- "local adapter smoke"
- "diagnostic final-QA metrics"
- "not an official leaderboard score"

Do not publish wording like this unless the matching evidence exists:

- "Vault's LoCoMo score"
- "Vault's LongMemEval score"
- "Vault beats mem0 / Letta / MemGPT"
- "end-to-end memory QA benchmark"
- "final answer quality benchmark"

Before publishing comparison numbers, check:

- each provider and reader process received a redacted input with
  `gold_labels_excluded: true`, while the scorer alone received the full gold
  fixture;
- every compared system used the same fixture;
- every compared system used the same top-k;
- every compared system used the same evidence matching rule;
- smoke runs are labeled as smoke runs;
- full runs are labeled as full runs;
- final-QA metrics are separated from retrieval metrics;
- dependency, model, vector-store, and API settings are recorded;
- at least five unique repeats used distinct clean-state identities;
- every raw run, paired score, provider-input file, and post-teardown execution
  evidence file is digest-bound to the same experiment;
- the benchmark, adapter, scorer, dependency lock, and configuration came from
  one clean committed source revision in every stage;
- public-fixture results are labelled as reproducible open-fixture evidence;
  promotion-grade comparative claims also include a rotating hidden holdout;
- no private paths, API keys, local database files, or benchmark data copies are
  committed.

## Initial Local Smoke Results

These are local keyword retrieval baselines from a development machine on
2026-07-07 with the default `--search-scope case`. They validate that the
adapters run and expose evidence-recall behavior. They are not official
benchmark scores.

These historical rows predate the current digest-binding, clean-source,
provider-execution, and full dependency-lock gates. Do not combine them with a
current provider table or use them in promotion.

| Benchmark | Data | Cases | Scope | Limit | Hit rate | Top-1 | Top-5 | MRR | Mean latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LoCoMo | `locomo10.json` | 1,982 | case | 10 | 0.609485 | 554 | 1,016 | 0.377273 | 5.868 ms |
| LongMemEval | `longmemeval_s_cleaned.json` first 100 evidence cases | 100 | case | 10 | 0.99 | 75 | 96 | 0.837952 | 18.886 ms |
| LongMemEval | `longmemeval_s_cleaned.json` full small split | 500 | case | 10 | 0.988 | 361 | 462 | 0.812902 | 95.453 ms |

The first implementation searched a global LongMemEval DB and was interrupted
after more than two minutes during per-case FTS search. That mode is now
available only as `--search-scope global` for stress testing; use the default
case-scoped mode for benchmark-shaped validation.

## Initial Comparison Harness Results

These results use the neutral fixture -> Vault run artifact -> shared scorer
pipeline. They should be the baseline for future mem0, Letta, MemGPT-style, or
custom memory-store adapters because the scorer is independent from Vault.
They are retained as historical diagnostics and are not current publishable
baselines.

| System | Benchmark | Cases | Docs | Top-k | Retrieval hit rate | Top-1 | Top-5 | MRR | Index latency | Mean query latency | p95 query latency | Final QA | Engineering supported/measured |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| Vault | LoCoMo | 1,982 | 5,882 | 10 | 0.609485 | 554 | 1,016 | 0.377273 | 1,184.902 ms | 5.038 ms | 9.558 ms | not run | 5 / 1 |
| Vault | LongMemEval small | 500 | 23,867 | 10 | 0.988 | 361 | 462 | 0.812902 | 19,184.801 ms | 61.404 ms | 132.398 ms | not run | 5 / 1 |
| Vault | LoCoMo 10-case smoke | 10 | 419 | 10 | 0.5 | 2 | 4 | 0.270833 | 103.923 ms | 2.019 ms | 3.082 ms | not run | 5 / 1 |
| mem0 | LoCoMo 10-case smoke | 10 | 419 | 10 | 0.6 | 4 | 5 | 0.466667 | 184,487.260 ms | 461.913 ms | 531.428 ms | not run | 3 / 2 |

`Engineering supported/measured` counts the local-first, multi-agent shared
memory, sync, report, and audit fields in the run artifact. The Vault comparison
run directly measures local-first retrieval. Shared-memory setup, sync,
reporting, and audit workflows are declared as supported but should be measured
with separate install/runtime probes before being used in public comparison
claims.

The 10-case rows are adapter smokes, not full benchmark baselines. They use the
same first LoCoMo sample fixture with 419 dialog documents. mem0 retrieved one
more evidence source than Vault in this small slice, but paid much higher local
index and query latency through Qdrant + fastembed. Full mem0 numbers should be
run on the same full fixtures as Vault after pinning SDK, embedder, vector-store,
and LLM-provider versions.

## References

- LoCoMo project: <https://snap-research.github.io/locomo/>
- LoCoMo repository: <https://github.com/snap-research/LoCoMo>
- LongMemEval repository: <https://github.com/xiaowu0162/LongMemEval>
- LongMemEval paper: <https://arxiv.org/abs/2410.10813>
- Letta Archive create API: <https://docs.letta.com/api/python/resources/archives/methods/create/>
- Letta Archive Passages API: <https://docs.letta.com/api/python/resources/archives/subresources/passages/>
- Letta passage search API: <https://docs.letta.com/api/python/resources/passages/methods/search/>
- `rohitg00/agentmemory` v0.9.27 release: <https://github.com/rohitg00/agentmemory/releases/tag/v0.9.27>
