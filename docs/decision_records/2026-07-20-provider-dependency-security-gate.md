# Provider dependency security publication gate

Date: 2026-07-20

## Decision

A live external-memory benchmark is not publishable merely because retrieval,
isolation, source binding, and teardown checks pass. When a provider executes a
third-party runtime dependency tree, its execution evidence must include a
dependency audit bound to the same package lock and complete dependency tree.

The AgentMemory publication profile requires:

- audit tool recorded as `npm audit`;
- audit-report SHA-256 digest;
- matching provider lock and dependency-tree digests;
- zero critical vulnerabilities;
- zero high vulnerabilities.

The gate is provider-specific rather than retroactively changing already
published Vault and mem0 artifacts. Future provider profiles should define an
equivalent ecosystem-appropriate audit contract before publication.

## Evidence

Isolated exact-version installs of `@agentmemory/agentmemory@0.9.27` and the
then-current `0.9.28` release both produced the same npm audit totals:

- critical: 1
- high: 6
- moderate: 10
- total: 17

The critical advisory path included
`@xenova/transformers@2.17.2 -> onnxruntime-web@1.14.0 -> onnx-proto@4.0.4 -> protobufjs@6.11.6`.
The audit reported no complete direct fix for the AgentMemory package tree.

## Consequences

AgentMemory remains `Diagnostic`. Vault does not launch the affected provider
directly on a trusted host for promotional evidence. A new run can proceed
after the upstream dependency tree clears the threshold or inside an explicitly
approved disposable isolation boundary, but an isolated run does not by itself
waive the public disclosure or audit binding.
