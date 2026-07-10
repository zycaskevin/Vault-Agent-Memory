from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_readme_positions_vault_as_backend_agnostic_governance_layer():
    readme = _read("README.md")
    first_screen = "\n".join(readme.splitlines()[:70])

    assert "Vault is a local-first, backend-agnostic memory governance layer for AI agents." in first_screen
    assert "Vault Memory API" in first_screen
    assert "Vault Governance Contract" in first_screen
    assert "Memory Provider Interface" in first_screen
    assert "Backend adapter" in first_screen
    assert "Local SQLite / Self-host central host / Supabase / future Vault Cloud" in first_screen
    assert "approved reads, candidate submissions, review, promotion, audit, and daily" in first_screen
    assert "Vault works standalone" in first_screen
    assert "other agent memory frameworks" in first_screen
    assert "multi-master cloud memory database" not in readme.lower()


def test_deployment_modes_define_contract_modes_and_backend_adapter_boundary():
    deployment = _read("docs/deployment_modes.md")

    for term in [
        "Vault Governance Contract",
        "Vault Memory API",
        "Memory Provider Interface",
        "Backend Adapter Requirements",
        "Local Vault",
        "Self-host Central Memory Host",
        "Trusted Local Central Memory Host",
        "Supabase Adapter",
        "Cloud Adapter",
        "Vault Cloud",
    ]:
        assert term in deployment

    for operation in [
        "search_approved_memory(query, agent_id, policy)",
        "read_approved_memory(handle, agent_id, policy)",
        "submit_candidate(memory_candidate, agent_id, source)",
        "review_candidate(candidate_id, decision, reviewer_or_policy)",
        "promote_candidate(candidate_id, policy)",
        "audit_memory_event(event)",
        "daily_loop_status()",
        "daily_loop_report()",
    ]:
        assert operation in deployment

    assert "Backends can store and index data differently" in deployment
    assert "they must not bypass the\ncandidate-first contract" in deployment
    assert "a hard boundary preventing remote agents from writing active memory directly" in deployment


def test_remote_semantic_privacy_limitations_are_explicit():
    deployment = _read("docs/deployment_modes.md")
    gateway = _read("docs/gateway_security.md")
    supabase = _read("docs/supabase_setup.md")
    combined = "\n".join([deployment, gateway, supabase])

    assert "Remote semantic search is disabled by default" in deployment
    assert "default remote semantic query embedding provider is OpenAI" in deployment
    assert "search query text is sent to OpenAI" in deployment
    assert "safe previews and read handles, not raw memory" in deployment
    assert "health payload reports the query embedding provider/model" in deployment
    assert "defaults to OpenAI" in combined
    assert "query text" in combined


def test_supabase_is_optional_cloud_adapter_with_service_role_boundary():
    supabase = _read("docs/supabase_setup.md")
    deployment = _read("docs/deployment_modes.md")
    readme = _read("README.md")

    assert "Supabase is optional" in supabase
    assert "optional cloud adapter for the Vault Governance Contract" in supabase
    assert "not as the product's only backend" in supabase
    assert "not as an active multi-master memory database" in supabase
    assert "SUPABASE_SERVICE_ROLE_KEY" in supabase
    assert "trusted sync host" in supabase
    assert "never inside Coze" in supabase
    assert "Supabase is a reviewed read copy plus candidate inbox" in deployment
    assert "Supabase Adapter | hosted agents, Coze, n8n, no always-on host" in readme


def test_self_host_runbook_and_migration_docs_are_candidate_first():
    spec = _read("docs/specs/self_host_central_memory_host.md")
    readme = _read("README.md")
    cli_ref = _read("docs/cli_reference.md")

    assert "Trusted Local Central Memory Host" in spec
    assert "Tailscale / VPN first" in spec
    assert "candidate submission: immediate" in spec
    assert "approved-memory search/read: immediate" in spec
    assert "daily-loop report: once per day" in spec
    assert "backup: daily" in spec
    assert "vault memory-sync migrate-candidates" in spec
    assert "vault memory-sync export-snapshots" in spec
    assert "vault memory-sync verify-snapshots" in spec
    assert "vault memory-sync import-snapshots" in spec
    assert "writes local `memory_candidates` for review, not active `knowledge`" in spec
    assert "review; it does not write active `knowledge` or promote memory" in readme
    assert "It does not write active `knowledge`, does not promote candidates" in cli_ref


def test_public_claims_keep_benchmark_and_promotion_language_bounded():
    readme = _read("README.md")
    claim_matrix = _read("docs/readme_claim_matrix.md")

    assert "retrieval evidence, not final answer\nquality" in readme
    assert "retrieval-only source-hit" in readme
    assert "not final answer/judge scores" in claim_matrix
    assert "strategic, sensitive,\n  freshness, convergence, and consolidation work stays visible for review" in readme
    assert "multi-master cloud memory database" not in claim_matrix.lower()


def test_architecture_review_records_score_and_non_blocking_limits():
    review = _read("docs/reviews/2026-07-09-memory-foundation-architecture-review.md")
    readme = _read("README.md")
    deployment = _read("docs/deployment_modes.md")

    assert "Architecture score: **93/100**" in review
    assert "No release blockers were found" in review
    assert "Known Limitations" in review
    assert "Future Improvements" in review
    assert "Remote Semantic Search" in review
    assert "Snapshot bundle import is candidate-first only" in review
    assert "not release\nblockers" in review
    assert "Memory foundation architecture review" in readme
    assert "Memory Foundation Architecture Review" in deployment


def test_vault_memory_api_spec_is_additive_and_keeps_vault_standalone():
    spec = _read("docs/specs/vault_memory_api.md")
    architecture = _read("docs/strategy/product-architecture.md")
    positioning = _read("docs/strategy/positioning.md")
    claim_matrix = _read("docs/readme_claim_matrix.md")
    zh_readme = _read("README.zh-Hant.md")
    zh_cn_readme = _read("README.zh-CN.md")

    assert "Vault works standalone" in positioning
    assert "Vault 可以單獨當記憶庫用" in zh_readme
    assert "Vault 可以单独当记忆库用" in zh_cn_readme
    assert "standalone: agents use Vault directly through CLI, MCP, Gateway" in spec
    assert "foundation: other agent or memory frameworks use Vault" in spec
    assert "The API is additive" in spec
    assert "must not remove or break the existing CLI, MCP tools" in spec
    assert "POST   /memory/create" in spec
    assert "DELETE /memory/{id}" in spec
    assert "remote or untrusted `create` writes candidates, not active memory" in spec
    assert "`DELETE /memory/{id}` is a soft tombstone by default" in spec
    assert "`DELETE /memory/{id}` submits a soft-delete review candidate" in spec
    assert "candidate\nactive\narchived\ndeprecated\ndeleted" in spec
    assert "`active` is the official readable state" in spec
    assert "`approved` should be represented as a\nreview decision or audit event" in spec
    assert "`vault.memory_provider.MemoryProvider` defines the provider protocol" in spec
    assert "`vault.memory_provider.SQLiteMemoryProvider` is the default local-first" in spec
    assert "Gateway health and OpenAPI expose the active provider contract" in spec
    assert "`/memory/search` and `/memory/{id}` now attach provider-read adoption metadata" in spec
    assert "legacy Gateway policy gate" in spec
    assert "do not leak hidden\n  private/sensitive result counts" in spec
    assert "SQLite provider now applies the same read-policy semantics" in spec
    assert "`result_adapter=provider`" in spec
    assert "It is not\n  the default result authority yet" in spec
    assert "`/memory/{id}` also has an opt-in preview bounded-read adapter" in spec
    assert "does not return the provider raw row\n  or full raw memory content" in spec
    assert "`vault.memory_provider_parity.provider_adapter_parity_report(...)`" in spec
    assert "gate for any future default-authority\n  switch" in spec
    assert "`vault memory-api parity-report --agent-id AGENT --search-query TEXT" in spec
    assert "does\n  not change Gateway or provider authority" in spec
    assert "semantic index providers, not default\nsource-of-truth memory providers" in spec
    assert "provider_adapter_default_promotion.md" in spec
    assert "before they can become the\n  default Gateway result authority" in spec
    assert "remain opt-in preview\n  adapters" in spec
    assert "legacy Gateway result authority remains the default" in spec
    assert "Provider-backed Memory API adapters 目前仍是 opt-in preview" in zh_readme
    assert "才可以成為預設 Gateway result authority" in zh_readme
    assert "Provider-backed Memory API adapters 目前仍是 opt-in preview" in zh_cn_readme
    assert "才可以成为默认 Gateway result authority" in zh_cn_readme
    assert "Remote Semantic Search 預設關閉" in zh_readme
    assert "搜尋文字會送到 OpenAI" in zh_readme
    assert "Remote Semantic Search 默认关闭" in zh_cn_readme
    assert "搜索文字会送到 OpenAI" in zh_cn_readme
    assert "Vault Cloud 是未來 managed backend" in zh_readme
    assert "Vault Cloud 是未来 managed backend" in zh_cn_readme
    assert "Vault Memory API plus MCP / Gateway / OpenAPI adapters" in architecture
    assert "Memory Provider Interface / Backend adapter" in architecture
    assert "compatibility facade over current governed behavior" in architecture
    assert "C38" in claim_matrix
    assert "not as a requirement to install Letta, mem0, Supabase" in claim_matrix


def test_release_notes_promote_memory_foundation_followup_to_010():
    changelog = _read("CHANGELOG.md")
    announcement_010 = _read("docs/announcements/v0.10.0-short.md")
    announcement_090 = _read("docs/announcements/v0.9.0-short.md")
    followup = _read("docs/announcements/v0.9.x-memory-foundation-followup.md")

    assert "## [0.10.0] - 2026-07-10" in changelog
    assert "Promoted the post-`v0.9.0` memory-foundation follow-up" in changelog
    assert "backend-agnostic memory governance layer" in changelog
    assert "vault-for-llm==0.10.0" in changelog
    assert "Provider-backed Memory API adapters remain opt-in preview paths" in changelog
    assert "v0.10.0 is the memory-foundation release" in announcement_010
    assert "vault-for-llm[mcp,supabase]==0.10.0" in announcement_010
    assert "provider adapter default-promotion criteria" in announcement_010
    assert "Default `/memory/search` and `/memory/{id}` authority remains the legacy" in announcement_010
    assert "## [0.9.0] - 2026-07-09" in changelog
    assert "do not assume every main-branch Gateway/API facade is" in announcement_090
    assert "present in the already-published `0.9.0` wheel" in announcement_090
    assert "promoted into `docs/announcements/v0.10.0-short.md`" in followup
    assert "basis of `v0.10.0`" in followup
    assert "runtime Memory Provider Interface and default SQLite provider" in followup
    assert "SQLite provider facade preserves candidate-first remote writes" in followup
    assert "shadow metadata probe while keeping the legacy Gateway policy gate" in followup
    assert "does not return provider raw rows or raw content" in followup
    assert "avoids hidden-result\n  count side channels" in followup
    assert "opt-in provider-backed `/memory/search` result adapter" in followup
    assert "default `/memory/search` authority remains the legacy Gateway" in followup
    assert "opt-in provider-backed `/memory/{id}` bounded-read adapter" in followup
    assert "not the full provider\n  raw row or full memory body" in followup
    assert "metadata-only provider adapter parity report helper" in followup
    assert "without returning raw memory\n  content, raw query text, or changing the default Gateway authority" in followup
    assert "`vault memory-api parity-report`" in followup
    assert "empty report cannot be mistaken for a passing gate" in followup
    assert "provider adapter default-promotion criteria" in followup
    assert "parity, security, rollback, CI, and release-note\n  evidence" in followup
    assert "cannot become the default Gateway result authority" in followup
    assert "security-misleading behavior" in followup
    assert "read-policy filtering to the default SQLite provider" in followup
    assert "candidate-first" in followup
    assert "DELETE is not a hard delete" in followup
    assert "Vault is a multi-master cloud memory database" in followup


def test_provider_adapter_default_promotion_criteria_are_explicit():
    criteria = _read("docs/specs/provider_adapter_default_promotion.md")
    changelog = _read("CHANGELOG.md")

    assert "required release-readiness checklist" in criteria
    assert "That report is a promotion gate. It is not a promotion switch." in criteria
    assert "Current Authority" in criteria
    assert "legacy Gateway policy-filtered result authority" in criteria
    assert "Provider-backed adapters stay opt-in preview paths" in criteria
    assert "No backend adapter may bypass candidate-first writes" in criteria
    assert "Required Evidence Before Default Promotion" in criteria
    assert "public, shared, private, high-sensitivity, and denied-read cases" in criteria
    assert "at least one search probe and one bounded-read probe" in criteria
    assert "does not return raw query text" in criteria
    assert "does not return raw memory content" in criteria
    assert "Provider adapters do not create hidden-result count side channels" in criteria
    assert "rollback path" in criteria
    assert "Full pytest passes" in criteria
    assert "Release parity passes" in criteria
    assert "GitHub Actions for the pull request and main branch pass" in criteria
    assert "Release-Blocker Boundary" in criteria
    assert "installation failure" in criteria
    assert "data corruption or irreversible active-memory mutation" in criteria
    assert "security-misleading behavior" in criteria
    assert "core read, write, review, promotion, or audit flow becoming unusable" in criteria
    assert "Provider default promotion evidence" in criteria
    assert "provider adapter default-promotion criteria" in changelog
