# AgentMemory provider security review

Date: 2026-07-20

## Scope

Read-only dependency review of exact npm installs for
`@agentmemory/agentmemory@0.9.27` and `0.9.28`. Neither provider server was
started. No Vault quality result was generated from these installs.

## Result

Both versions reported 17 dependency advisories through `npm audit`: 1
critical, 6 high, and 10 moderate. The critical finding was in a transitive
`protobufjs@6.11.6` path used by the bundled Xenova/ONNX stack. Other findings
included ONNX, archive, and OpenTelemetry dependency paths.

The exact command is reproducible in an isolated directory:

```bash
npm init -y
npm install --save-exact @agentmemory/agentmemory@0.9.27
npm ls @agentmemory/agentmemory iii-sdk @xenova/transformers onnxruntime-node protobufjs --all
npm audit --json
```

## Assessment

This audit does not prove that the benchmark fixture can exploit the affected
code path. It does prove that directly executing the pinned tree on a trusted
host would weaken the standard expected from an institutional evidence
pipeline. The safe result is a blocked publication gate, not a zero score and
not a silent omission.
