# `rohitg00/agentmemory` v0.9.27 provider profile

This profile identifies the local-hybrid provider used by the controlled
VaultGovBench diagnostic run. It is not a substitute for the complete npm lock
and tree artifacts required for a publishable rerun.

- repository/release: `rohitg00/agentmemory` `v0.9.27`
- npm package: `@agentmemory/agentmemory@0.9.27`
- runtime: Node.js `24.12.0`, npm `11.6.2`
- engine SDK: `iii-sdk@0.11.2`
- embedding provider: local
- embedding model: `Xenova/all-MiniLM-L6-v2`
- embedding dimensions: `384`
- ONNX runtime observed: `onnxruntime-node@1.27.0`
- LLM provider: noop; no LLM extraction was scored

Diagnostic dependency evidence from 2026-07-19:

- runtime package-lock digest:
  `sha256:ed8432d35b104f762569019720b467b17f0870b804131bd9f210b02c74790be1`
- complete npm-tree JSON digest:
  `sha256:96a262705cd6aef49f66a5440e433b01b5cbcc6b0cda06119c90c6a8ab58d31a`
- local MiniLM ONNX model digest:
  `sha256:afdb6f1a0e45b715d0bb9b11772f032c399babd23bfc31fed1c170afc848bdb1`

For every repeat, create a new provider root and store, verify memory count zero
before ingestion, observe the runtime version/model/dimensions from the live
server, and stop the server afterward. Bind that evidence to the raw run using
[`provider_execution_evidence.v1.schema.json`](../schemas/provider_execution_evidence.v1.schema.json).
The repeat summary must reject duplicate raw artifacts, duplicate clean-state
identities, missing teardown evidence, and dirty or mismatched source chains.
