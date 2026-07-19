from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.external_memory_compare import fixture_digest
from benchmarks.memory_foundation_compare import (
    _generic_digest,
    _provider_execution_evidence_passed,
    _provider_gold_labels_isolated,
    _provider_retrieval_integrity_passed,
    augment_run,
    score_pair,
    summarize_repeats,
)
from vault.access_policy import normalize_read_policy
from vault.governance_read_guard import evaluate_governed_read, superseded_ids_from_snapshot


REPO_ROOT = Path(__file__).parent.parent


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fixture():
    return {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_fixture",
        "benchmark": "vault-gov-retrieval-toy",
        "fixed_clock": "2026-07-19T00:00:00Z",
        "documents": [
            {
                "id": 1,
                "source": "toy/stale",
                "content": "The office used to be in Kaohsiung.",
                "governance": {"valid_until": "2026-07-18T00:00:00Z"},
            },
            {
                "id": 2,
                "source": "toy/private",
                "content": "A private irrelevant note.",
                "governance": {
                    "scope": "private",
                    "owner_agent": "profile-agent",
                    "allowed_agents": [],
                },
            },
            {
                "id": 3,
                "source": "toy/current-a",
                "content": "The current office is in Taipei.",
            },
            {
                "id": 4,
                "source": "toy/current-b",
                "content": "The current floor is seven.",
            },
        ],
        "cases": [
            {
                "id": "case-1",
                "query": "Where is the current office?",
                "agent_id": "product-agent",
                "include_private": False,
                "max_sensitivity": "medium",
                "as_of": "2026-07-19T00:00:00Z",
                "expected_sources": ["toy/current-a", "toy/current-b"],
                "expected_valid_sources": ["toy/current-a", "toy/current-b"],
                "forbidden_sources": ["toy/stale", "toy/private"],
                "expected_block_reasons": {
                    "toy/stale": "temporal_past",
                    "toy/private": "private",
                },
            }
        ],
    }


def _run(fixture, *, system="mem0", sources=None, latency_ms=10.0, pool_k=4):
    sources = sources or ["toy/stale", "toy/private", "toy/current-a", "toy/current-b"]
    return {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_run",
        "benchmark": fixture["benchmark"],
        "fixture_digest": fixture_digest(fixture),
        "system": system,
        "top_k": pool_k,
        "candidate_pool_k": pool_k,
        "cases_total": len(fixture["cases"]),
        "cases": [
            {
                "id": "case-1",
                "latency_ms": latency_ms,
                "results": [
                    {"rank": index, "source": source, "score": 1 / index}
                    for index, source in enumerate(sources, start=1)
                ],
            }
        ],
    }


def test_guard_only_filters_forbidden_results_and_backfills_from_frozen_pool(tmp_path):
    fixture = _fixture()
    baseline = _run(fixture)
    fixture_path = tmp_path / "fixture.json"
    baseline_path = tmp_path / "baseline.json"
    augmented_path = tmp_path / "augmented.json"
    _write(fixture_path, fixture)
    _write(baseline_path, baseline)

    augmented = augment_run(
        fixture_path=fixture_path,
        engine_run_path=baseline_path,
        output_path=augmented_path,
        mode="guard-only",
        top_k=2,
        candidate_pool_k=4,
    )

    case = augmented["cases"][0]
    assert [result["source"] for result in case["results"]] == ["toy/current-a", "toy/current-b"]
    assert case["blocked_by_reason"] == {"private": 1, "temporal_past": 1}
    assert augmented["augmentation"]["mode"] == "guard-only"
    assert augmented["augmentation"]["fixed_candidate_pool"] is True

    paired = score_pair(
        fixture_path=fixture_path,
        baseline_run_path=baseline_path,
        augmented_run_path=augmented_path,
        top_k=2,
    )
    assert paired["baseline"]["valid_recall"] == 0.0
    assert paired["augmented"]["valid_recall"] == 1.0
    assert paired["baseline"]["forbidden_exposures"] == 2
    assert paired["augmented"]["forbidden_exposures"] == 0
    assert paired["delta"]["forbidden_exposures"] == -2
    assert paired["artifact_bindings"]["baseline_run_digest"] == (
        augmented["artifact_bindings"]["engine_run_digest"]
    )


def test_score_pair_rejects_augmented_artifact_bound_to_another_baseline(tmp_path):
    fixture = _fixture()
    fixture_path = tmp_path / "fixture.json"
    original_path = tmp_path / "original.json"
    different_path = tmp_path / "different.json"
    augmented_path = tmp_path / "augmented.json"
    _write(fixture_path, fixture)
    _write(original_path, _run(fixture, latency_ms=10.0))
    _write(different_path, _run(fixture, latency_ms=11.0))
    augment_run(
        fixture_path=fixture_path,
        engine_run_path=original_path,
        output_path=augmented_path,
        top_k=1,
        candidate_pool_k=4,
    )

    with pytest.raises(ValueError, match="not bound to the supplied baseline"):
        score_pair(
            fixture_path=fixture_path,
            baseline_run_path=different_path,
            augmented_run_path=augmented_path,
            top_k=1,
        )


def test_rrf_fusion_is_explicit_and_preserves_contributors(tmp_path):
    fixture = _fixture()
    engine = _run(
        fixture,
        sources=["toy/current-a", "toy/current-b", "toy/stale", "toy/private"],
    )
    vault = _run(
        fixture,
        system="vault",
        sources=["toy/current-b", "toy/current-a", "toy/stale", "toy/private"],
        latency_ms=2.0,
    )
    fixture_path = tmp_path / "fixture.json"
    engine_path = tmp_path / "engine.json"
    vault_path = tmp_path / "vault.json"
    _write(fixture_path, fixture)
    _write(engine_path, engine)
    _write(vault_path, vault)

    result = augment_run(
        fixture_path=fixture_path,
        engine_run_path=engine_path,
        vault_run_path=vault_path,
        mode="rrf-fusion",
        top_k=2,
        candidate_pool_k=4,
        rrf_k=60,
    )

    assert result["augmentation"]["mode"] == "rrf-fusion"
    assert result["cases"][0]["fusion_retrieval_latency_ms"] == 2.0
    assert all(len(item["contributors"]) == 2 for item in result["cases"][0]["results"])


def test_supersession_uses_full_canonical_snapshot_not_only_returned_candidates():
    old = {"id": 10, "source": "old", "status": "active"}
    new = {"id": 11, "source": "new", "status": "active", "supersedes_id": 10}
    superseded = superseded_ids_from_snapshot([old, new])

    decision = evaluate_governed_read(
        old,
        policy=normalize_read_policy(agent_id="agent", allowed_statuses=("active",)),
        as_of="2026-07-19T00:00:00Z",
        superseded_ids=superseded,
        require_provenance=True,
    )

    assert decision.allowed is False
    assert decision.reason_codes == ("superseded",)


def test_future_replacement_does_not_supersede_current_fact_early():
    old = {"id": 10, "source": "old", "status": "active"}
    future = {
        "id": 11,
        "source": "future",
        "status": "active",
        "supersedes_id": 10,
        "valid_from": "2026-08-01T00:00:00Z",
    }

    superseded = superseded_ids_from_snapshot(
        [old, future],
        as_of="2026-07-19T00:00:00Z",
    )
    decision = evaluate_governed_read(
        old,
        as_of="2026-07-19T00:00:00Z",
        superseded_ids=superseded,
        require_provenance=True,
    )

    assert superseded == set()
    assert decision.allowed is True


def test_governance_guard_rejects_invalid_as_of_instead_of_using_wall_clock():
    with pytest.raises(ValueError, match="as_of must be a valid"):
        evaluate_governed_read(
            {"id": 1, "source": "toy/source", "status": "active"},
            as_of="not-a-clock",
        )


def test_strict_guard_does_not_restore_legacy_private_visibility_without_agent():
    row = {
        "id": 1,
        "source": "private/source",
        "status": "active",
        "scope": "private",
        "owner_agent": "profile-agent",
    }
    decision = evaluate_governed_read(
        row,
        as_of="2026-07-19T00:00:00Z",
    )
    explicit_legacy_policy = evaluate_governed_read(
        row,
        policy=normalize_read_policy(),
        as_of="2026-07-19T00:00:00Z",
    )

    assert decision.allowed is False
    assert decision.reason_codes == ("private",)
    assert explicit_legacy_policy.reason_codes == ("private",)


def test_strict_guard_combines_private_and_restricted_requirements():
    decision = evaluate_governed_read(
        {
            "id": 1,
            "source": "private/restricted",
            "status": "active",
            "scope": "private",
            "sensitivity": "restricted",
            "owner_agent": "alice",
        },
        agent_id="alice",
        include_private=False,
        max_sensitivity="restricted",
        as_of="2026-07-19T00:00:00Z",
    )

    assert decision.allowed is False
    assert decision.reason_codes == ("private",)


def test_strict_guard_fails_closed_for_unknown_scope_and_sensitivity():
    decision = evaluate_governed_read(
        {
            "id": 1,
            "source": "unknown/governance",
            "status": "active",
            "scope": "secret-vault",
            "sensitivity": "top-secret",
        },
        agent_id="alice",
        max_sensitivity="low",
        as_of="2026-07-19T00:00:00Z",
    )

    assert decision.allowed is False
    assert decision.reason_codes == ("unknown_scope", "unknown_sensitivity")


def test_strict_guard_fails_closed_for_invalid_requested_sensitivity_cap():
    decision = evaluate_governed_read(
        {
            "id": 1,
            "source": "high/governance",
            "status": "active",
            "scope": "shared",
            "sensitivity": "high",
        },
        agent_id="alice",
        max_sensitivity="medum",
        as_of="2026-07-19T00:00:00Z",
    )

    assert decision.allowed is False
    assert decision.reason_codes == ("invalid_max_sensitivity",)


def test_supersession_accepts_vault_knowledge_id_as_canonical_id():
    old = {"vault_knowledge_id": 10, "source": "old", "status": "active"}
    new = {
        "vault_knowledge_id": 11,
        "source": "new",
        "status": "active",
        "supersedes_id": 10,
    }
    superseded = superseded_ids_from_snapshot(
        [old, new],
        as_of="2026-07-19T00:00:00Z",
    )

    decision = evaluate_governed_read(
        old,
        as_of="2026-07-19T00:00:00Z",
        superseded_ids=superseded,
    )

    assert decision.allowed is False
    assert decision.reason_codes == ("superseded",)
    assert decision.temporal_state == "past"


def test_augment_rejects_candidate_pool_smaller_than_requested(tmp_path):
    fixture = _fixture()
    baseline = _run(fixture, sources=["toy/current-a", "toy/current-b"], pool_k=2)
    fixture_path = tmp_path / "fixture.json"
    baseline_path = tmp_path / "baseline.json"
    _write(fixture_path, fixture)
    _write(baseline_path, baseline)

    with pytest.raises(ValueError, match="candidate pool 2 is smaller"):
        augment_run(
            fixture_path=fixture_path,
            engine_run_path=baseline_path,
            top_k=2,
            candidate_pool_k=4,
        )


def test_public_governance_retrieval_fixture_and_frozen_pool_stay_reproducible(tmp_path):
    fixture_path = REPO_ROOT / "benchmarks" / "vault_gov_bench" / "retrieval_v0.1.json"
    baseline_path = REPO_ROOT / "benchmarks" / "vault_gov_bench" / "frozen_candidate_pool_v0.1.json"
    augmented_path = tmp_path / "augmented.json"

    augmented = augment_run(
        fixture_path=fixture_path,
        engine_run_path=baseline_path,
        output_path=augmented_path,
        mode="guard-only",
        top_k=1,
        candidate_pool_k=4,
    )
    paired = score_pair(
        fixture_path=fixture_path,
        baseline_run_path=baseline_path,
        augmented_run_path=augmented_path,
        top_k=1,
    )

    assert augmented["cases_total"] == 6
    assert paired["baseline"]["forbidden_exposures_by_reason"] == {
        "deleted": 1,
        "expired": 1,
        "privacy_blocked": 1,
        "private": 1,
        "superseded": 1,
        "temporal_past": 1,
    }
    assert paired["augmented"]["forbidden_exposures"] == 0
    assert paired["augmented"]["valid_recall"] == 1.0
    assert augmented["cases"][0]["engine_latency_ms"] is None
    assert augmented["cases"][0]["latency_ms"] is None
    assert augmented["cases"][0]["augmentation_latency_ms"] >= 0
    assert paired["baseline"]["latency"] == {
        "available": False,
        "count": 0,
        "mean_ms": None,
        "p50_ms": None,
        "p95_ms": None,
    }
    assert paired["delta"]["latency_available"] is False
    assert paired["delta"]["latency_mean_ms"] is None
    assert paired["delta"]["cost_available"] is False
    assert paired["delta"]["cost_total_usd"] is None


def test_fusion_total_cost_and_latency_require_both_provider_measurements(tmp_path):
    fixture = _fixture()
    engine = _run(fixture, latency_ms=None)
    engine["cases"][0]["cost_usd"] = 0.01
    vault = _run(fixture, system="vault", latency_ms=2.0)
    fixture_path = tmp_path / "fixture.json"
    engine_path = tmp_path / "engine.json"
    vault_path = tmp_path / "vault.json"
    _write(fixture_path, fixture)
    _write(engine_path, engine)
    _write(vault_path, vault)

    result = augment_run(
        fixture_path=fixture_path,
        engine_run_path=engine_path,
        vault_run_path=vault_path,
        mode="rrf-fusion",
        top_k=2,
        candidate_pool_k=4,
    )
    case = result["cases"][0]

    assert case["engine_latency_ms"] is None
    assert case["fusion_retrieval_latency_ms"] == 2.0
    assert case["augmentation_latency_ms"] >= 0
    assert case["latency_ms"] is None
    assert case["cost_usd"] is None


def test_pair_operational_deltas_use_only_same_case_measurements(tmp_path):
    fixture = _fixture()
    fixture["documents"].append(
        {"id": 5, "source": "toy/current-c", "content": "A second current fact."}
    )
    fixture["cases"].append(
        {
            "id": "case-2",
            "query": "What is the second fact?",
            "expected_sources": ["toy/current-c"],
            "expected_valid_sources": ["toy/current-c"],
            "forbidden_sources": [],
        }
    )
    baseline = _run(fixture, latency_ms=10.0)
    baseline["cases"][0]["cost_usd"] = 1.0
    baseline["cases"].append(
        {
            "id": "case-2",
            "latency_ms": None,
            "cost_usd": None,
            "results": [{"rank": 1, "source": "toy/current-c"}],
        }
    )
    baseline["cases_total"] = 2
    fixture_path = tmp_path / "fixture.json"
    baseline_path = tmp_path / "baseline.json"
    augmented_path = tmp_path / "augmented.json"
    _write(fixture_path, fixture)
    _write(baseline_path, baseline)
    augmented = augment_run(
        fixture_path=fixture_path,
        engine_run_path=baseline_path,
        output_path=augmented_path,
        mode="guard-only",
        top_k=1,
        candidate_pool_k=4,
    )
    augmented["cases"][0]["latency_ms"] = None
    augmented["cases"][0]["cost_usd"] = None
    augmented["cases"][1]["latency_ms"] = 20.0
    augmented["cases"][1]["cost_usd"] = 3.0
    _write(augmented_path, augmented)

    unpaired = score_pair(
        fixture_path=fixture_path,
        baseline_run_path=baseline_path,
        augmented_run_path=augmented_path,
        top_k=1,
    )

    assert unpaired["baseline"]["latency"]["available"] is True
    assert unpaired["augmented"]["latency"]["available"] is True
    assert unpaired["delta"]["latency_available"] is False
    assert unpaired["delta"]["latency_paired_cases"] == 0
    assert unpaired["delta"]["latency_mean_ms"] is None
    assert unpaired["delta"]["latency_p95_ms"] is None
    assert unpaired["delta"]["cost_available"] is False
    assert unpaired["delta"]["cost_paired_cases"] == 0
    assert unpaired["delta"]["cost_total_usd"] is None

    augmented["cases"][0]["latency_ms"] = 15.0
    augmented["cases"][0]["cost_usd"] = 1.5
    _write(augmented_path, augmented)
    one_pair = score_pair(
        fixture_path=fixture_path,
        baseline_run_path=baseline_path,
        augmented_run_path=augmented_path,
        top_k=1,
    )

    assert one_pair["delta"]["latency_available"] is True
    assert one_pair["delta"]["latency_paired_cases"] == 1
    assert one_pair["delta"]["latency_mean_ms"] == 5.0
    assert one_pair["delta"]["latency_p95_ms"] == 5.0
    assert one_pair["delta"]["cost_available"] is True
    assert one_pair["delta"]["cost_paired_cases"] == 1
    assert one_pair["delta"]["cost_total_usd"] == 0.5
    assert one_pair["delta"]["cost_mean_usd"] == 0.5


def test_pair_metrics_use_only_eligible_retrieval_and_exposure_denominators(tmp_path):
    fixture = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_fixture",
        "benchmark": "eligible-denominators",
        "documents": [
            {"source": "expected", "content": "Expected current evidence."},
            {"source": "forbidden", "content": "Forbidden stale evidence."},
        ],
        "cases": [
            {
                "id": "evidence",
                "query": "Find evidence",
                "expected_sources": ["expected"],
                "expected_valid_sources": ["expected"],
                "forbidden_sources": ["forbidden"],
            },
            {
                "id": "abstain",
                "query": "No answer exists",
                "expected_sources": [],
                "expected_valid_sources": [],
                "forbidden_sources": [],
            },
        ],
    }
    run = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_run",
        "benchmark": fixture["benchmark"],
        "fixture_digest": fixture_digest(fixture),
        "system": "denominator-test",
        "top_k": 1,
        "candidate_pool_k": 1,
        "cases_total": 2,
        "cases": [
            {"id": "evidence", "results": [{"rank": 1, "source": "forbidden"}]},
            {"id": "abstain", "results": []},
        ],
    }
    fixture_path = tmp_path / "fixture.json"
    baseline_path = tmp_path / "baseline.json"
    augmented_path = tmp_path / "augmented.json"
    _write(fixture_path, fixture)
    _write(baseline_path, run)
    augment_run(
        fixture_path=fixture_path,
        engine_run_path=baseline_path,
        output_path=augmented_path,
        mode="guard-only",
        top_k=1,
        candidate_pool_k=1,
    )

    paired = score_pair(
        fixture_path=fixture_path,
        baseline_run_path=baseline_path,
        augmented_run_path=augmented_path,
        top_k=1,
    )

    assert paired["baseline"]["retrieval_eligible_cases"] == 1
    assert paired["baseline"]["valid_recall"] == 0.0
    assert paired["baseline"]["abstention_cases"] == 1
    assert paired["baseline"]["correct_abstention_rate"] == 1.0
    assert paired["baseline"]["forbidden_exposure_eligible_cases"] == 1
    assert paired["baseline"]["forbidden_exposure_case_rate"] == 1.0


def test_summarize_repeats_validates_configuration_and_preserves_missing_values(tmp_path):
    fixture = _fixture()
    fixture_path = tmp_path / "fixture.json"
    _write(fixture_path, fixture)
    run_paths = []
    pair_paths = []
    for repeat in range(5):
        run = _run(fixture, latency_ms=10.0 + repeat)
        run.update(
            {
                "system_version": "2.0.12",
                "collection_name": f"repeat-collection-{repeat}",
                "run_namespace": f"repeat-namespace-{repeat}",
                "track": "controlled_retrieval_raw_insert",
                "retrieval_mode": "mem0:semantic+bm25+entity",
                "search_scope": "global",
                "documents_failed": 0,
                "setup_latency_ms": 100.0 + repeat,
                "ingest_latency_ms": 20.0 + repeat,
                "index_latency_ms": 120.0 + repeat * 2,
                "manifest": {
                    "provider_config": {"embed_model": "thenlper/gte-large"},
                    "effective_retrieval": {"preflight_status": "passed"},
                    "model_cache": {"revisions_after_run": {"dense": "abc", "bm25": "def"}},
                },
            }
        )
        run_path = tmp_path / f"run-{repeat}.json"
        augmented_path = tmp_path / f"augmented-{repeat}.json"
        pair_path = tmp_path / f"pair-{repeat}.json"
        _write(run_path, run)
        augment_run(
            fixture_path=fixture_path,
            engine_run_path=run_path,
            output_path=augmented_path,
            mode="guard-only",
            top_k=1,
            candidate_pool_k=4,
        )
        score_pair(
            fixture_path=fixture_path,
            baseline_run_path=run_path,
            augmented_run_path=augmented_path,
            output_path=pair_path,
            top_k=1,
        )
        run_paths.append(run_path)
        pair_paths.append(pair_path)

    summary = summarize_repeats(
        fixture_path=fixture_path,
        pair_paths=pair_paths,
        run_paths=run_paths,
    )

    assert summary["repeats"] == 5
    assert summary["baseline"]["valid_hit_rate"]["mean"] == 0.0
    assert summary["augmented"]["valid_hit_rate"]["mean"] == 1.0
    assert summary["delta"]["valid_hit_rate"]["mean"] == 1.0
    assert summary["delta"]["latency_mean_ms"]["available"] is True
    assert summary["ranking_stability"]["full_ranking_stable_case_rate"] == 1.0
    assert summary["quality_gates"]["missing_metrics_are_not_zero"] is True
    assert summary["quality_gates"]["clean_state_repeats_minimum_met"] is True
    assert summary["quality_gates"]["provider_retrieval_integrity_passed_all_repeats"] is True
    assert summary["quality_gates"]["provider_native_preflight_passed_all_repeats"] is True
    assert summary["quality_gates"]["provider_gold_labels_excluded_all_repeats"] is False
    assert "provider_gold_labels_not_isolated" in summary["release_gate_reasons"]
    assert summary["quality_gates"]["artifact_source_chain_clean_and_bound_all_repeats"] is False
    assert "artifact_source_chain_not_clean_or_not_bound" in summary["release_gate_reasons"]
    assert "benchmark_harness_worktree_dirty" in summary["release_gate_reasons"]


def test_agentmemory_provider_integrity_requires_fresh_store_and_complete_id_mapping():
    fixture = _fixture()
    run = _run(fixture, system="rohitg00/agentmemory")
    run.update(
        {
            "documents_attempted": 4,
            "documents_indexed": 4,
            "documents_failed": 0,
            "manifest": {
                "isolation": {
                    "fresh_store_required": True,
                    "fresh_store_id_digest": f"sha256:{'a' * 64}",
                    "unmapped_result_ids": 0,
                },
                "source_mapping": {
                    "records": [
                        {"memory_id": f"memory-{index}", "source": document["source"]}
                        for index, document in enumerate(fixture["documents"], start=1)
                    ]
                },
            },
        }
    )

    assert _provider_retrieval_integrity_passed(run) is True
    run["manifest"]["isolation"].pop("fresh_store_id_digest")
    assert _provider_retrieval_integrity_passed(run) is False


def test_provider_gold_isolation_requires_bound_distinct_digests():
    fixture = _fixture()
    evaluation_digest = fixture_digest(fixture)
    run = _run(fixture)
    run["manifest"] = {
        "provider_input": {
            "gold_labels_excluded": True,
            "provider_input_digest": f"sha256:{'a' * 64}",
            "evaluation_fixture_digest": evaluation_digest,
        }
    }

    assert _provider_gold_labels_isolated(
        run,
        evaluation_fixture_digest=evaluation_digest,
    ) is True

    run["manifest"]["provider_input"]["provider_input_digest"] = evaluation_digest
    assert _provider_gold_labels_isolated(
        run,
        evaluation_fixture_digest=evaluation_digest,
    ) is False

    run["manifest"]["provider_input"]["provider_input_digest"] = "sha256:not-a-digest"
    assert _provider_gold_labels_isolated(
        run,
        evaluation_fixture_digest=evaluation_digest,
    ) is False


def test_agentmemory_execution_evidence_requires_observed_runtime_and_teardown():
    fixture = _fixture()
    store_digest = f"sha256:{'a' * 64}"
    run = _run(fixture, system="rohitg00/agentmemory")
    run.update(
        {
            "system_version": "0.9.27",
            "run_id": "agentmemory-repeat-1",
            "manifest": {
                "provider_config": {
                    "embedding_provider": "local",
                    "embedding_model": "Xenova/all-MiniLM-L6-v2",
                    "embedding_dims": 384,
                },
                "isolation": {"fresh_store_id_digest": store_digest},
            },
        }
    )
    run_digest = _generic_digest(run)
    evidence = {
        "schema_version": 1,
        "artifact_type": "provider_execution_evidence",
        "system": "rohitg00/agentmemory",
        "run_artifact_digest": run_digest,
        "run_id": "agentmemory-repeat-1",
        "provider_observed": {
            "version": "0.9.27",
            "embedding_provider": "local",
            "embedding_model": "Xenova/all-MiniLM-L6-v2",
            "embedding_dims": 384,
        },
        "isolation": {
            "fresh_store_id_digest": store_digest,
            "store_root_digest": f"sha256:{'b' * 64}",
            "worker_registration_id_digest": f"sha256:{'c' * 64}",
            "memory_count_before": 0,
            "fresh_store_created": True,
        },
        "dependencies": {
            "provider_lock_digest": f"sha256:{'d' * 64}",
            "provider_tree_digest": f"sha256:{'e' * 64}",
        },
        "lifecycle": {
            "server_started": True,
            "readiness_passed": True,
            "adapter_errors": 0,
            "adapter_timeouts": 0,
            "server_stopped": True,
            "ports_closed": True,
        },
    }

    assert _provider_execution_evidence_passed(
        run, run_digest=run_digest, evidence=evidence
    ) is True
    evidence["lifecycle"]["ports_closed"] = False
    assert _provider_execution_evidence_passed(
        run, run_digest=run_digest, evidence=evidence
    ) is False


def test_summarize_repeats_rejects_one_artifact_reused_five_times(tmp_path):
    fixture = _fixture()
    fixture_path = tmp_path / "fixture.json"
    run_path = tmp_path / "run.json"
    augmented_path = tmp_path / "augmented.json"
    pair_path = tmp_path / "pair.json"
    run = _run(fixture)
    run.update(
        {
            "collection_name": "one-collection",
            "run_namespace": "one-namespace",
            "documents_failed": 0,
            "manifest": {"effective_retrieval": {"preflight_status": "passed"}},
        }
    )
    _write(fixture_path, fixture)
    _write(run_path, run)
    augment_run(
        fixture_path=fixture_path,
        engine_run_path=run_path,
        output_path=augmented_path,
        top_k=1,
        candidate_pool_k=4,
    )
    score_pair(
        fixture_path=fixture_path,
        baseline_run_path=run_path,
        augmented_run_path=augmented_path,
        output_path=pair_path,
        top_k=1,
    )

    with pytest.raises(ValueError, match="duplicate run artifact"):
        summarize_repeats(
            fixture_path=fixture_path,
            pair_paths=[pair_path] * 5,
            run_paths=[run_path] * 5,
        )
