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

## Limits

These adapters are designed for the first benchmark stage:

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

## References

- LoCoMo project: <https://snap-research.github.io/locomo/>
- LoCoMo repository: <https://github.com/snap-research/LoCoMo>
- LongMemEval repository: <https://github.com/xiaowu0162/LongMemEval>
- LongMemEval paper: <https://arxiv.org/abs/2410.10813>
