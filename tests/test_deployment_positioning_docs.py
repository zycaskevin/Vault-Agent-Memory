from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_readme_positions_vault_as_backend_agnostic_governance_layer():
    readme = _read("README.md")
    first_screen = "\n".join(readme.splitlines()[:70])

    assert "Vault is a local-first, backend-agnostic memory governance layer for AI agents." in first_screen
    assert "Vault Governance Contract" in first_screen
    assert "Backend adapter" in first_screen
    assert "Local SQLite / Self-host central host / Supabase / future Vault Cloud" in first_screen
    assert "approved reads, candidate submissions, review, promotion, audit, and daily" in first_screen
    assert "multi-master cloud memory database" not in readme.lower()


def test_deployment_modes_define_contract_modes_and_backend_adapter_boundary():
    deployment = _read("docs/deployment_modes.md")

    for term in [
        "Vault Governance Contract",
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
