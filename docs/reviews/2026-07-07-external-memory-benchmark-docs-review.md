# External Memory Benchmark Docs Review

Date: 2026-07-07
Scope: `README.md`, `docs/external_memory_benchmarks.md`, and
`docs/readme_claim_matrix.md`.

## Review Decision

The documentation is acceptable for developer-facing preview of the external
memory comparison harness.

It is not yet acceptable as a public performance benchmark claim that Vault
beats mem0, Letta, MemGPT-style agents, or any other memory system.

## Findings

No release-blocking documentation issues remain for the current harness scope.

The main remaining risk is claim inflation: retrieval-only source-hit metrics
can be misread as final LoCoMo or LongMemEval scores. The docs now state that
the current numbers measure evidence recall under fixed top-k and exact
`source` id matching, not end-to-end answer quality or official leaderboard
performance.

## What The Docs Now Cover

- Vault-only LoCoMo and LongMemEval retrieval probes.
- Neutral fixture export for cross-system comparisons.
- Vault, mem0, and Letta run-artifact adapters.
- Optional fixed-reader `answer-run` for diagnostic final-QA scoring.
- Shared `score-run` retrieval, answer, latency, and engineering reporting.
- Separation of index latency from per-query latency.
- Separation of retrieval metrics, final-QA metrics, and engineering capability
  fields.
- Publication wording that is safe to use before official benchmark runs.

## Residual Limits

- mem0 has only a 10-case LoCoMo adapter smoke documented here, not a full
  LoCoMo or LongMemEval baseline.
- Letta has an adapter documented here, but no published live Letta run result.
- Final-QA answer generation and judging have not been run as a shared public
  benchmark.
- Dependency versions, model versions, vector-store configuration, and API
  settings must be recorded before publishing comparison numbers outside the
  repo.
- Engineering capability counts are reported from run artifacts; shared-memory,
  sync, report, and audit claims need separate runtime probes before they are
  used in public comparison tables.

## Publication Checklist

Before publishing external-memory comparison numbers:

- Use one neutral fixture for every compared system.
- Use the same top-k for every compared system.
- Use the same evidence matching rule for every compared system.
- Label smoke runs and full runs separately.
- Keep retrieval-only metrics separate from final-QA metrics.
- Keep final-QA metrics separate from official benchmark leaderboard language.
- Record dependency, model, vector-store, and API settings.
- Do not include private paths, secrets, local database files, or copied
  benchmark data.

## Approved Wording

Safe:

- "retrieval-only evidence recall"
- "source-id hit rate under fixed top-k"
- "adapter smoke"
- "diagnostic final-QA metrics"
- "not an official LoCoMo or LongMemEval leaderboard score"

Unsafe until additional evidence exists:

- "Vault's LoCoMo score"
- "Vault's LongMemEval score"
- "Vault beats mem0"
- "Vault beats Letta"
- "end-to-end memory QA benchmark"
- "final answer quality benchmark"
