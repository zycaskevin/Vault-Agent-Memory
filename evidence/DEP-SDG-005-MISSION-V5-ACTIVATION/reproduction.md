# Reproduction

## Expected

The exact owner-confirmed proof is insufficient by itself. A closed reviewed
activation topic is preliminary and leaves Mission V5 inactive; only its exact
normal two-parent merge from the protocol base activates the mission.

## Actual baseline

Exact clean main `9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0` contains no
Mission V5 proof and dispatches sequence 6 as `INACTIVE`. The external proof is
canonical and immutable, but has not yet crossed the reviewed delivery gate.

## Deterministic steps

1. Require exact base `9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0`.
2. Compare the repository proof with the external artifact byte for byte and
   require SHA-256 `70113552d582f5f579a0c9d01a5206ff74df678801accca59173ff76bae6d528`.
3. Require the exact closed 16-path activation action/mode set.
4. Replay the topic as a candidate and require `preliminary` plus inactive
   dispatcher state.
5. After independent review and hosted CI, merge normally and require exact
   first parent, topic second parent, topic-tree equality, and active replay.

## Environment and preconditions

Issue #457; branch `agent/mission-v5-activation-post-sdg011`; CPython 3; Git;
Agentic SDD Governance 0.2.0-experimental.6. No private transcript, live data,
task work, deployment, or production operation is involved.
