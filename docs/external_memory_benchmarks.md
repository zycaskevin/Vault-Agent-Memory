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
2026-07-07. They validate that the adapters run and expose evidence-recall
behavior. They are not official benchmark scores.

| Benchmark | Data | Cases | Limit | Hit rate | Top-1 | Top-5 | MRR | Mean latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LoCoMo | `locomo10.json` | 1,982 | 10 | 0.566599 | 495 | 951 | 0.345966 | 12.158 ms |
| LongMemEval | `longmemeval_s_cleaned.json` first 20 evidence cases | 20 | 10 | 0.85 | 6 | 14 | 0.490417 | 16.111 ms |
| LongMemEval | `longmemeval_s_cleaned.json` first 100 evidence cases | 100 | 10 | 0.63 | 20 | 48 | 0.317889 | 68.794 ms |

The naive full `longmemeval_s_cleaned.json` run was interrupted after more than
two minutes during per-case FTS search. Before treating full LongMemEval as a
release benchmark, add progress reporting and a more efficient full-run path
such as sharding, cached DB reuse, or benchmark-specific retrieval batching.

## References

- LoCoMo project: <https://snap-research.github.io/locomo/>
- LoCoMo repository: <https://github.com/snap-research/LoCoMo>
- LongMemEval repository: <https://github.com/xiaowu0162/LongMemEval>
- LongMemEval paper: <https://arxiv.org/abs/2410.10813>
