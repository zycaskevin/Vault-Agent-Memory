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
- mem0 and Letta adapters exist for same-fixture comparison runs.
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
| `benchmarks/external_memory_compare.py vault-run` | Run Vault against the same comparison fixture shape. | Vault run artifact. |
| `benchmarks/external_memory_compare.py vault-mode-compare` | Run Vault against the same data/top-k/scorer across multiple retrieval modes. | Vault mode-comparison artifact with per-mode runs, scores, and deltas. |
| `benchmarks/external_memory_compare.py mem0-run` | Run mem0 against the neutral fixture. | mem0 run artifact. |
| `benchmarks/external_memory_compare.py letta-run` | Run Letta archival memory against the neutral fixture. | Letta run artifact. |
| `benchmarks/external_memory_compare.py answer-run` | Generate final answers from retrieved evidence with one fixed reader. | Answered run artifact. |
| `benchmarks/external_memory_compare.py score-run` | Score retrieval, optional final QA, latency, and engineering fields. | Score JSON. |

The comparison flow is:

```text
LoCoMo / LongMemEval JSON
  -> neutral fixture
  -> one run artifact per memory system
  -> optional fixed-reader answer run
  -> shared scorer
  -> retrieval, final QA, latency, and engineering report
```

### Prerequisites

Vault runs use the local repo checkout and the benchmark JSON files. No cloud
service, embedding API, or hosted model is required for retrieval-only keyword
runs.

mem0 runs are optional and should be done in an isolated Python environment.
Install and pin `mem0ai`, the selected embedder package, vector store, and LLM
provider before publishing numbers. The local smoke used `fastembed` with the
SDK's default `thenlper/gte-large` model dimensions and `ollama` as the mem0 LLM
provider, even though retrieval insertion used `infer=False`.

Letta runs require a Letta server or cloud project, `LETTA_API_KEY`, and a
benchmark agent id. Use a fresh agent or unique `--run-id`; the adapter does not
delete existing archival memory.

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

Run Vault into the shared run-artifact schema:

```bash
python benchmarks/external_memory_compare.py vault-run \
  --benchmark longmemeval \
  --input /path/to/longmemeval_s_cleaned.json \
  --limit 10 \
  --progress-every 50 \
  --output /tmp/vault-longmemeval-run.json
```

Run Vault mode comparisons with one benchmark file, one top-k, one search scope,
and one exact `source` id scorer:

```bash
python benchmarks/external_memory_compare.py vault-mode-compare \
  --benchmark longmemeval \
  --input /path/to/longmemeval_s_cleaned.json \
  --limit 10 \
  --modes keyword,hybrid,semantic \
  --progress-every 50 \
  --output /tmp/vault-longmemeval-mode-comparison.json
```

For CI or local plumbing checks without downloading a real embedding model, add
`--allow-hash --hash-dim 8`. Hash vectors only verify semantic/hybrid command
wiring and artifact shape; do not publish hash-vector numbers as semantic
retrieval quality.

Run mem0 into the same run-artifact schema:

```bash
python benchmarks/external_memory_compare.py mem0-run \
  --fixture /tmp/longmemeval-fixture.json \
  --limit 10 \
  --embedder fastembed \
  --vector-store-path /tmp/mem0-longmemeval-qdrant \
  --output /tmp/mem0-longmemeval-run.json
```

The mem0 adapter is optional and requires the `mem0ai` package. It inserts
fixture documents with `infer=False` for retrieval-only comparison so an LLM
memory-extraction pass is not mixed into evidence recall. The adapter preserves
benchmark `source` ids in metadata and uses the same case/global search-scope
contract as the Vault adapter. Pin the embedder and vector-store settings before
publishing numbers. For the current mem0 SDK, `--embedder fastembed` requires
the separate `fastembed` package and defaults to 1024 embedding dimensions for
the SDK's default `thenlper/gte-large` model; override with `--embedding-dims`
when using a different embedder model. Retrieval-only runs still initialize a
mem0 LLM provider, so the local smoke path uses `--llm-provider ollama` and
requires the `ollama` Python package even when `infer=False`.

Run Letta archival memory into the same run-artifact schema:

```bash
python benchmarks/external_memory_compare.py letta-run \
  --fixture /tmp/longmemeval-fixture.json \
  --agent-id "$LETTA_AGENT_ID" \
  --letta-api-key "$LETTA_API_KEY" \
  --run-id vault-memory-benchmark-001 \
  --limit 10 \
  --output /tmp/letta-longmemeval-run.json
```

The Letta adapter uses the HTTP archival-memory create/search endpoints. It
stores benchmark source ids as passage tags and searches with the generated
`run:<id>` tag plus the case category tag when `--search-scope case` is used.
The adapter intentionally does not delete existing Letta memory; use a fresh
agent or unique `--run-id` for benchmark runs.

Generate final answers from the same retrieved evidence with a fixed reader:

```bash
python benchmarks/external_memory_compare.py answer-run \
  --fixture /tmp/longmemeval-fixture.json \
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
  "top_k": 10,
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
    "audit": {"supported": true, "measured": true, "evidence": "source ids preserved"}
  }
}
```

The scorer uses exact `source` id matching for retrieval. Final QA is reported
separately with non-official normalized exact-match, contains-expected, and
token-F1 metrics when a run supplies `answer`. Use `answer-run` to add answers
from a fixed reader prompt without rerunning retrieval. This keeps
retrieval-only and answer-generation results from being mixed into one
misleading score.

### Running a Fair Comparison

1. Export one fixture from the benchmark data.
2. Run every memory system against that exact fixture.
3. Use the same `--limit` / top-k for every run.
4. Keep the same `--search-scope` policy for every run.
5. Score every run with `score-run`.
6. Compare retrieval-only metrics before comparing final-QA metrics.
7. Only compare final-QA metrics after every system uses the same fixed reader
   and scorer.
8. Report index latency separately from query latency.
9. Report engineering fields separately from retrieval and answer quality.
10. Publish dependency versions, model versions, vector-store settings, and
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

- every compared system used the same fixture;
- every compared system used the same top-k;
- every compared system used the same evidence matching rule;
- smoke runs are labeled as smoke runs;
- full runs are labeled as full runs;
- final-QA metrics are separated from retrieval metrics;
- dependency, model, vector-store, and API settings are recorded;
- no private paths, API keys, local database files, or benchmark data copies are
  committed.

## Initial Local Smoke Results

These are local keyword retrieval baselines from a development machine on
2026-07-07 with the default `--search-scope case`. They validate that the
adapters run and expose evidence-recall behavior. They are not official
benchmark scores.

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
- Letta archival-memory create API: <https://docs.letta.com/api/resources/agents/subresources/passages/methods/create>
- Letta archival-memory search API: <https://docs.letta.com/api/resources/agents/subresources/passages/methods/search>
