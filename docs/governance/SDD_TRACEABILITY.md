# SDD Traceability

This index connects product capabilities to their authoritative contracts,
implementation evidence and current state. Detailed Subject example mapping
remains in specs/subject-distillation/traceability.md.

| Capability | Contract | Implementation / verification | State |
|---|---|---|---|
| Local-first governed memory | docs/vision.md; docs/memory_governance.md | vault/db modules, vault/governance modules, DB/governance tests | Available |
| Candidate-first writes | AGENTS.md; docs/core-concepts.md; docs/memory_governance.md | vault/memory modules, MCP memory tools, candidate tests | Available |
| Search and bounded evidence reads | docs/api_interfaces.md; docs/mcp_tool_reference.md | vault/search modules, vault/mcp_read.py, search/MCP tests | Available |
| Backup, migration and rollback | docs/db_backup_restore.md; docs/db_migrations.md | vault/db_backup.py, vault/db_migrations.py, migration tests | Available; Subject v15 pending |
| Agent setup and scoped tool profiles | AGENTS.md; docs/agent_install.md | vault/agent_setup modules, setup tests | Available |
| Remote governed access | docs/deployment_modes.md; docs/gateway_security.md | vault/gateway modules, gateway/security tests | Available adapter; live deployment not asserted |
| Subject canonical contract | Subject requirements; design sections 1–20 | normative five-file baseline + baseline tests | Approved, not implemented |
| B-000 authorization verifier | Subject design section 21; tasks B-000 | authorization schema/verifier + bootstrap tests | Merged |
| B-001 identity-safe runner | Subject design section 21; tasks B-001 | runner + lifecycle/adversarial tests | Claimed next |
| T-001 implementation control plane | tasks T-001 | baseline/evidence/progress scripts and schemas | Blocked by B-001 |
| Subject contracts through runtime surfaces | tasks T-002..T-031 | synthetic fixtures, schema/store/policy/evidence/model/context/CLI/MCP/Gateway/evaluation/recovery | Planned |
| Persona-governance extensions | traceability D-SD-010 | current owners T-004/T-008..T-017/T-025/T-026 | Partial current-cycle semantics; advanced retrieval/training deferred |

## Traceability rules

1. A Work Package names exact SDD anchors and executable acceptance evidence.
2. A PR updates this index, the Progress Ledger or the Subject normative
   traceability when its capability state changes.
3. Tests prove behavior; document/hash validation alone proves only integrity.
4. A skipped, blocked or unexecuted planned test is not completion.
5. Product-visible, privacy, retention, public API and acceptance-criteria
   changes are risk:L2 even when mechanically easy.
