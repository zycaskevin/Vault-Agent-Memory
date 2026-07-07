# External Memory Comparison Harness

Date: 2026-07-07

## Context

Vault has local retrieval-only adapters for LoCoMo and LongMemEval. Those runs
are useful for evidence-recall validation, but they are not enough for a fair
comparison with other memory systems such as mem0, Letta, MemGPT-style agents,
or custom RAG memory stores.

External systems have different APIs and storage models. A fair benchmark must
avoid giving any system a different dataset, top-k policy, evidence matching
rule, answer judge, or engineering checklist.

## Decision

Add a neutral comparison harness with three artifacts:

- fixture: benchmark documents, cases, expected evidence sources, expected
  answers, and matching rules.
- run: one memory system's top-k retrieval results, optional final answers,
  latency measurements, and engineering capability evidence.
- score: shared retrieval, final-QA, latency, and engineering metrics computed
  from the fixture and run artifacts.

Retrieval-only evidence recall and final-answer QA must be reported separately.
The shared scorer uses exact source-id evidence matching. Final-answer metrics
are diagnostic normalized exact-match, contains-expected, and token-F1 values;
they are not official LoCoMo or LongMemEval leaderboard scores.

Engineering capabilities are reported as separate support/measured fields for:

- local-first operation
- shared multi-agent memory
- sync
- reporting
- auditability

## Consequences

Vault can publish reproducible retrieval baselines without overstating answer
quality. Other memory systems can be compared by writing adapters that emit the
same run artifact schema. This keeps benchmark fairness in one scorer instead
of scattering matching logic across each integration.

The first implementation includes the neutral fixture exporter, Vault run
artifact emitter, and shared scorer. mem0, Letta, and MemGPT-style adapters
should be added only after their current install/API surfaces are verified.
