# Dependency Graph

    WP-GOV-001 Autonomous governance
      ├─ WP-SD-B001 Identity-safe runner
      │    └─ WP-SD-T001 Implementation control plane
      │         └─ WP-SD-FOUNDATION T-002..T-004
      │              └─ WP-SD-SCHEMA T-005..T-007
      │                   └─ Auth, policy, candidate governance T-008..T-010
      │                        └─ Evidence and assertions T-011..T-013
      │                             └─ Models, grants, Context Packs T-014..T-016
      │                                  └─ Decisions and relationships T-017..T-020
      │                                       └─ Public surfaces T-021..T-024
      │                                            └─ Evaluation T-025..T-026
      │                                                 └─ Recovery and closure T-027..T-033
      └─ WP-CI-001 New-debt prevention
           └─ Test evidence taxonomy
                └─ Staging-readiness smoke

Deferred Policy Cards, dual retrieval and Persona IR depend on stable
T-014/T-016 context contracts and T-025/T-026 evaluation contracts.

## Parallelization boundaries

- WP-CI-001 may run independently of the exact two-path B-001 implementation.
- Fixture/traceability preparation may run in parallel after T-001, but generic
  contracts remain their integration dependency.
- Auth/policy and evidence implementation may use separate builders after the
  typed store is stable; shared schema and invariants require integration review.
- CLI/MCP/Gateway adapters may run in parallel after service contracts stabilize.
- Recovery/privacy/regression evidence may be prepared early but cannot close
  before all behavior-bearing packages pass.
- Private shadow pilots, Production and release are never implied by this graph.
