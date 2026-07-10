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

    assert "Vault works standalone" in positioning
    assert "Vault 可以單獨當記憶庫用" in zh_readme
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
    assert "semantic index providers, not default\nsource-of-truth memory providers" in spec
    assert "Vault Memory API plus MCP / Gateway / OpenAPI adapters" in architecture
    assert "Memory Provider Interface / Backend adapter" in architecture
    assert "compatibility facade over current governed behavior" in architecture
    assert "C38" in claim_matrix
    assert "not as a requirement to install Letta, mem0, Supabase" in claim_matrix


def test_release_notes_distinguish_published_090_from_main_followup():
    changelog = _read("CHANGELOG.md")
    announcement_090 = _read("docs/announcements/v0.9.0-short.md")
    followup = _read("docs/announcements/v0.9.x-memory-foundation-followup.md")

    assert "## [0.9.0] - 2026-07-09" in changelog
    assert "Main branch follow-up for the next 0.9.x release" in changelog
    assert "already-published `0.9.0` wheel" in changelog
    assert "do not assume every main-branch Gateway/API facade is" in announcement_090
    assert "present in the already-published `0.9.0` wheel" in announcement_090
    assert "These changes are on `main` after the `v0.9.0` tag" in followup
    assert "runtime Memory Provider Interface and default SQLite provider" in followup
    assert "SQLite provider facade preserves candidate-first remote writes" in followup
    assert "shadow metadata probe while keeping the legacy Gateway policy gate" in followup
    assert "does not return provider raw rows or raw content" in followup
    assert "avoids hidden-result\n  count side channels" in followup
    assert "candidate-first" in followup
    assert "DELETE is not a hard delete" in followup
    assert "Vault is a multi-master cloud memory database" in followup
