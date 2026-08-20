# Reproduction

## Expected

The owner-confirmed proof is insufficient by itself. A closed reviewed
activation topic is preliminary and grants zero task authority; only its
exact normal two-parent merge from the protocol base activates the mission.

## Actual baseline

Exact clean main `327ebe1b557fc30cbc5482a1de87e1757b8873da` contains no
Mission V5 proof and dispatches sequence 6 as inactive. The owner-confirmed
proof was generated at `2026-08-20T05:23:51Z` and awaits reviewed delivery.

## Deterministic steps

1. Require exact base `327ebe1b557fc30cbc5482a1de87e1757b8873da`.
2. Require canonical mode-0644 proof SHA-256
   `f1c38461dd4639c50f82bd9ddc39029d8a8a02f63fbbedc6cce2df9461ec2465`.
3. Require the exact closed 16-path activation action/mode set.
4. Replay the topic as candidate and require preliminary/no authority.
5. Merge normally and require ordered parents, topic-tree equality, and active
   readback only on the delivery merge.

## Environment and preconditions

Issue #457; branch `agent/mission-v5-activation-post-sdg012`; CPython 3; Git;
Agentic SDD Governance 0.2.0-experimental.6. No private transcript, task work,
deployment, or production operation is involved.
