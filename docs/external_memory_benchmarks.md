# External Memory Benchmarks

Vault can run retrieval-only adapters for external long-term memory benchmarks.
These adapters measure whether Vault search retrieves the expected evidence
source. They do **not** measure final-answer quality, reader-model reasoning, or
official leaderboard scores.

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

The comparison flow is:

```text
LoCoMo / LongMemEval JSON
  -> neutral fixture
  -> one run artifact per memory system
  -> optional fixed-reader answer run
  -> shared scorer
  -> retrieval, final QA, latency, and engineering report
```

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

| System | Benchmark | Cases | Top-k | Retrieval hit rate | Top-1 | Top-5 | MRR | Mean latency | p95 latency | Final QA | Engineering supported/measured |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| Vault | LoCoMo | 1,982 | 10 | 0.609485 | 554 | 1,016 | 0.377273 | 6.898 ms | 14.445 ms | not run | 5 / 1 |
| Vault | LongMemEval small | 500 | 10 | 0.988 | 361 | 462 | 0.812902 | 84.010 ms | 178.797 ms | not run | 5 / 1 |

`Engineering supported/measured` counts the local-first, multi-agent shared
memory, sync, report, and audit fields in the run artifact. The Vault comparison
run directly measures local-first retrieval. Shared-memory setup, sync,
reporting, and audit workflows are declared as supported but should be measured
with separate install/runtime probes before being used in public comparison
claims.

## References

- LoCoMo project: <https://snap-research.github.io/locomo/>
- LoCoMo repository: <https://github.com/snap-research/LoCoMo>
- LongMemEval repository: <https://github.com/xiaowu0162/LongMemEval>
- LongMemEval paper: <https://arxiv.org/abs/2410.10813>
