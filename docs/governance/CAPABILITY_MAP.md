# Capability Map

## Product capability layers

| Layer | User/Agent outcome | Current evidence | Next gap |
|---|---|---|---|
| Local memory core | Agents keep user-owned memory in local SQLite/Markdown | CLI, DB, compiler, import/export and backup tests | Continue regression protection |
| Governance lifecycle | Agents propose, review, promote, deprecate and audit memory | Governance, memory, access-policy and MCP tests | Subject-aware governance bridge |
| Retrieval/context | Agents search and read bounded sourced context | Keyword/semantic/search QA, Document Map and MCP tests | Subject purpose-limited Context Packs |
| Agent integration | Multiple runtimes use shared CLI/MCP contracts and scoped tools | Setup, registry, MCP parity and integration docs/tests | Subject role/policy retrieval |
| Remote sharing | Trusted hosts expose governed remote adapters and optional sync | Gateway/security/multi-host/Supabase adapter tests | No new live deployment claimed |
| Lifecycle intelligence | Reports, reflection, archive and task handoff improve memory | Automation, daily-loop, reflection and ledger tests | Subject decision/evaluation feedback |
| Subject governance | Evidence-grounded person/org models stay scoped, reversible and auditable | Approved SDD, schema v15 and traceability | B-001 then T-001..T-031 |
| Persona governance roadmap | Behavior policy remains evidence-grounded and model-independent | D-SD-010 crosswalk | Policy Cards, dual retrieval and training export deferred |

## First executable Work Packages

1. **WP-GOV-001 — Autonomous governance control plane (risk:L0):** contracts,
   state, traceability, claims, templates and machine validation.
2. **WP-SD-B001 — Identity-safe authorization runner (risk:L1):** stateless
   proposal, exact confirmation, verifier invocation and cleanup.
3. **WP-CI-001 — New-debt prevention (risk:L0):** changed-file lint and dependency
   audit without converting historical debt into unrelated PR failures.
4. **WP-SD-T001 — Subject implementation control plane (risk:L1):** baseline,
   evidence and progress artifacts with fail-closed validators.
5. **WP-SD-FOUNDATION — Public Subject foundation (risk:L1):** approved synthetic
   fixtures, machine traceability and generic contracts.
6. **WP-SD-SCHEMA — Subject v15 persistence foundation (risk:L1 with migration
   dry-run):** lifecycle preflight, DDL, migration and typed store.

Later packages follow the normative T-008..T-031 dependency order and are split
by complete capabilities, not by individual files or functions.
