from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from benchmarks.external_memory_compare import (
    _close_mem0_memory,
    _mem0_config,
    _mem0_retrieval_preflight,
    _normalize_letta_results,
    _normalize_mem0_results,
    _restore_process_env,
    _set_process_env,
    _summary,
    _validate_fixture_integrity,
    answer_run,
    export_fixture,
    export_provider_input,
    fixture_digest,
    run_letta_comparison,
    run_mem0_comparison,
    run_vault_mode_comparison,
    score_run,
)


REPO_ROOT = Path(__file__).parent.parent


def _minimal_fixture_and_run():
    fixture = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_fixture",
        "benchmark": "toy-hardening",
        "documents": [{"source": "toy/expected", "content": "Expected evidence."}],
        "cases": [
            {
                "id": "case-1",
                "query": "Where is the evidence?",
                "expected_sources": ["toy/expected"],
            }
        ],
    }
    run = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_run",
        "benchmark": fixture["benchmark"],
        "fixture_digest": fixture_digest(fixture),
        "system": "hardening-test",
        "top_k": 1,
        "candidate_pool_k": 2,
        "cases_total": 1,
        "cases": [
            {
                "id": "case-1",
                "results": [
                    {"rank": 1, "source": "toy/other"},
                    {"rank": 2, "source": "toy/expected"},
                ],
            }
        ],
    }
    return fixture, run


class FakeMem0Memory:
    def __init__(self):
        self.documents = []
        self.search_filters = []
        self.closed = False

    def reset(self):
        self.documents = []

    def add(self, messages, *, user_id=None, metadata=None, infer=True):
        self.documents.append(
            {
                "messages": messages,
                "user_id": user_id,
                "metadata": metadata or {},
                "infer": infer,
            }
        )

    def search(self, query, *, top_k=20, filters=None, threshold=0.1, rerank=False, **kwargs):
        self.search_filters.append(filters)
        docs = self.documents
        if filters:
            docs = [
                doc
                for doc in docs
                if all(
                    doc["user_id"] == value if key == "user_id" else doc["metadata"].get(key) == value
                    for key, value in filters.items()
                )
            ]
        return {
            "results": [
                {
                    "id": idx,
                    "memory": doc["messages"],
                    "metadata": doc["metadata"],
                    "score": 1.0 / idx,
                }
                for idx, doc in enumerate(docs[:top_k], start=1)
            ]
        }

    def close(self):
        self.closed = True


def test_external_memory_compare_scores_retrieval_answer_latency_and_engineering(tmp_path):
    fixture_path = tmp_path / "fixture.json"
    run_path = tmp_path / "run.json"
    score_path = tmp_path / "score.json"
    fixture = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_fixture",
        "benchmark": "toy",
        "cases": [
            {
                "id": "case-1",
                "query": "Where is the blue ticket?",
                "expected_sources": ["toy/source/1"],
                "expected_answer": "blue drawer",
            }
        ],
    }
    run = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_run",
        "system": "example-memory",
        "system_version": "1.2.3",
        "benchmark": "toy",
        "fixture_digest": fixture_digest(fixture),
        "top_k": 3,
        "candidate_pool_k": 3,
        "cases_total": 1,
        "cases": [
            {
                "id": "case-1",
                "latency_ms": 12.5,
                "answer": "The blue ticket is in the blue drawer.",
                "results": [
                    {"rank": 1, "source": "toy/source/other"},
                    {"rank": 2, "source": "toy/source/1"},
                ],
            }
        ],
        "engineering": {
            "local_first": {"supported": True, "measured": True, "evidence": "local sqlite"},
            "multi_agent_shared_memory": True,
            "sync": False,
            "report": False,
            "audit": True,
        },
    }
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    run_path.write_text(json.dumps(run), encoding="utf-8")

    result = score_run(fixture_path=fixture_path, run_path=run_path, output_path=score_path)

    assert result["system"] == "example-memory"
    assert result["retrieval"]["hit_cases"] == 1
    assert result["retrieval"]["top3_hits"] == 1
    assert result["retrieval"]["mean_reciprocal_rank"] == 0.5
    assert result["final_qa"]["available"] is True
    assert result["final_qa"]["normalized_contains_expected_rate"] == 1.0
    assert result["index_latency"]["available"] is False
    assert result["latency"]["mean_ms"] == 12.5
    assert result["answer_latency"]["available"] is False
    assert result["engineering"]["supported_count"] == 3
    assert result["engineering"]["measured_count"] == 1
    assert json.loads(score_path.read_text(encoding="utf-8"))["artifact_type"] == "external_memory_comparison_score"


def test_final_qa_keeps_unanswered_eligible_cases_in_denominator(tmp_path):
    fixture = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_fixture",
        "benchmark": "answer-denominator",
        "documents": [],
        "cases": [
            {"id": "answered", "expected_answer": "blue drawer", "expected_sources": []},
            {"id": "missing", "expected_answer": "red shelf", "expected_sources": []},
        ],
    }
    run = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_run",
        "benchmark": fixture["benchmark"],
        "fixture_digest": fixture_digest(fixture),
        "system": "answer-test",
        "top_k": 1,
        "candidate_pool_k": 1,
        "cases_total": 2,
        "cases": [
            {"id": "answered", "answer": "blue drawer", "results": []},
            {"id": "missing", "results": []},
        ],
    }
    fixture_path = tmp_path / "fixture.json"
    run_path = tmp_path / "run.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    run_path.write_text(json.dumps(run), encoding="utf-8")

    score = score_run(fixture_path=fixture_path, run_path=run_path)

    assert score["final_qa"]["eligible_cases"] == 2
    assert score["final_qa"]["answered_cases"] == 1
    assert score["final_qa"]["unanswered_cases"] == 1
    assert score["final_qa"]["answer_coverage"] == 0.5
    assert score["final_qa"]["normalized_exact_match_rate"] == 0.5


@pytest.mark.parametrize(
    ("normalizer", "payload", "message"),
    [
        (_normalize_mem0_results, {}, "did not include results or memories"),
        (_normalize_letta_results, {}, "did not include results or passages"),
    ],
)
def test_provider_normalizers_fail_closed_on_schema_drift(normalizer, payload, message):
    with pytest.raises(RuntimeError, match=message):
        normalizer(payload, include_content=False)


def test_external_memory_compare_exports_locomo_fixture(tmp_path):
    data_path = tmp_path / "locomo.json"
    fixture_path = tmp_path / "fixture.json"
    data_path.write_text(
        json.dumps(
            [
                {
                    "sample_id": "sample-1",
                    "conversation": {
                        "speaker_a": "Angela",
                        "session_1": [
                            {
                                "speaker": "speaker_a",
                                "dia_id": "D1",
                                "text": "I hid a silver key below the orchid pot.",
                            }
                        ],
                    },
                    "qa": [
                        {
                            "question": "Where is the silver key?",
                            "answer": "Below the orchid pot.",
                            "evidence": ["D1"],
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    fixture = export_fixture(
        benchmark="locomo",
        input_path=data_path,
        output_path=fixture_path,
    )

    assert fixture["documents_total"] == 1
    assert fixture["cases_total"] == 1
    assert fixture["cases"][0]["expected_sources"] == ["locomo/sample-1/dia/D1"]
    assert fixture["cases"][0]["expected_answer"] == "Below the orchid pot."
    assert fixture["input_file_name"] == "locomo.json"
    assert fixture["input_file_digest"].startswith("sha256:")
    assert "input_path" not in fixture
    assert json.loads(fixture_path.read_text(encoding="utf-8"))["matching_rule"]["retrieval"].startswith(
        "A case is a hit"
    )


def test_export_provider_input_excludes_gold_but_keeps_evaluation_digest(tmp_path):
    fixture, _run = _minimal_fixture_and_run()
    fixture["documents"][0]["status"] = "deleted"
    fixture["documents"][0]["governance"] = {
        "scope": "private",
        "expected_sources": ["toy/expected"],
        "metadata": {"answer": "expected"},
    }
    fixture["cases"][0].update(
        {
            "expected_answer": "expected",
            "forbidden_sources": ["toy/forbidden"],
            "metadata": {"answer": "expected", "evidence": ["toy/expected"]},
        }
    )
    fixture["fixture_digest"] = fixture_digest(fixture)
    fixture_path = tmp_path / "fixture.json"
    provider_path = tmp_path / "provider-input.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    provider_input = export_provider_input(
        fixture_path=fixture_path,
        output_path=provider_path,
    )

    assert provider_input["fixture_digest"] == fixture["fixture_digest"]
    assert provider_input["provider_input_digest"] != provider_input["fixture_digest"]
    assert provider_input["gold_labels_excluded"] is True
    document = provider_input["documents"][0]
    assert document["status"] == "deleted"
    assert document["governance"] == {"scope": "private"}
    case = provider_input["cases"][0]
    assert set(case) == {"id", "query"}
    serialized = provider_path.read_text(encoding="utf-8")
    assert "expected_sources" not in serialized
    assert "expected_answer" not in serialized
    assert "forbidden_sources" not in serialized
    assert '"metadata"' not in serialized

    tampered = json.loads(serialized)
    tampered["documents"][0]["governance"]["expected_sources"] = ["toy/expected"]
    tampered["provider_input_digest"] = fixture_digest(tampered)
    with pytest.raises(ValueError, match="governance contains fields outside"):
        _validate_fixture_integrity(tampered)

    tampered_counts = json.loads(serialized)
    tampered_counts["documents_total"] += 1
    with pytest.raises(ValueError, match="documents_total must match"):
        _validate_fixture_integrity(tampered_counts)


def test_run_summary_surfaces_nested_provider_input_provenance():
    provider_digest = f"sha256:{'a' * 64}"
    summary = _summary(
        {
            "artifact_type": "external_memory_comparison_run",
            "fixture_digest": f"sha256:{'b' * 64}",
            "manifest": {
                "provider_input": {
                    "gold_labels_excluded": True,
                    "provider_input_digest": provider_digest,
                }
            },
        }
    )

    assert summary["provider_input"] is True
    assert summary["provider_input_digest"] == provider_digest


def test_external_memory_compare_mem0_run_uses_fixture_and_case_scope(tmp_path):
    fixture_path = tmp_path / "fixture.json"
    run_path = tmp_path / "mem0-run.json"
    score_path = tmp_path / "score.json"
    fixture_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifact_type": "external_memory_comparison_fixture",
                "benchmark": "toy",
                "documents": [
                    {
                        "source": "toy/source/1",
                        "title": "Right source",
                        "content": "The brass key is in the north drawer.",
                        "category": "case:a",
                    },
                    {
                        "source": "toy/source/2",
                        "title": "Other source",
                        "content": "The brass key is not here.",
                        "category": "case:b",
                    },
                ],
                "cases": [
                    {
                        "id": "case-1",
                        "query": "Where is the brass key?",
                        "expected_sources": ["toy/source/1"],
                        "expected_answer": "north drawer",
                        "search_category": "case:a",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    fake = FakeMem0Memory()

    run = run_mem0_comparison(
        fixture_path=fixture_path,
        output_path=run_path,
        limit=5,
        memory_factory=lambda: fake,
    )
    score = score_run(fixture_path=fixture_path, run_path=run_path, output_path=score_path)

    assert run["system"] == "mem0"
    assert run["documents_total"] == 2
    assert run["documents_attempted"] == 2
    assert run["documents_indexed"] == 2
    assert run["documents_failed"] == 0
    assert run["index_latency_ms"] >= 0
    assert fake.documents[0]["infer"] is False
    assert fake.documents[0]["messages"] == (
        "title: Right source\ncontent: The brass key is in the north drawer."
    )
    assert "expected_answer" not in fake.documents[0]["messages"]
    assert run["run_namespace"].startswith("external-memory-")
    assert run["embed_model"] == "thenlper/gte-large"
    assert run["embedding_dims"] == 1024
    assert run["manifest"]["provider_config"]["infer"] is False
    assert run["manifest"]["provider_config"]["telemetry_enabled"] is False
    assert run["manifest"]["provider_config"]["index_latency_includes_initialization"] is True
    assert run["track"] == "controlled_retrieval_raw_insert"
    assert run["native_memory_features_exercised"] is False
    assert run["retrieval_mode"] == "mem0:test-double"
    assert fake.search_filters == [
        {"user_id": run["run_namespace"], "search_category": "case:a"}
    ]
    assert run["cases"][0]["results"][0]["source"] == "toy/source/1"
    assert "content" not in run["cases"][0]["results"][0]
    assert score["retrieval"]["hit_cases"] == 1
    assert score["index_latency"]["available"] is True
    assert score["index_latency"]["item_count"] == 2
    assert score["engineering"]["capabilities"]["audit"]["measured"] is False


def test_external_memory_compare_mem0_case_scope_requires_categories(tmp_path):
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifact_type": "external_memory_comparison_fixture",
                "benchmark": "toy",
                "documents": [{"source": "toy/source/1", "content": "Evidence."}],
                "cases": [{"id": "case-1", "query": "Evidence?"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="use --search-scope global"):
        run_mem0_comparison(
            fixture_path=fixture_path,
            search_scope="case",
            memory_factory=FakeMem0Memory,
        )


def test_external_memory_compare_fixture_does_not_leak_has_answer(tmp_path):
    data_path = tmp_path / "longmemeval.json"
    data_path.write_text(
        json.dumps(
            [
                {
                    "question_id": "q1",
                    "question": "Where is it?",
                    "answer": "west cabinet",
                    "haystack_session_ids": ["s1"],
                    "haystack_sessions": [
                        [{"role": "user", "content": "It is west.", "has_answer": True}]
                    ],
                    "answer_session_ids": ["s1"],
                }
            ]
        ),
        encoding="utf-8",
    )

    fixture = export_fixture(benchmark="longmemeval", input_path=data_path)

    assert all("has_answer" not in document["content"] for document in fixture["documents"])


def test_external_memory_compare_mem0_config_isolates_history_and_pins_embedding():
    config = _mem0_config(
        vector_store_path="/tmp/provider-qdrant",
        collection_name="isolated_collection",
        embedder="fastembed",
        embed_model="thenlper/gte-large",
        embedding_dims=1024,
        llm_provider="ollama",
        history_db_path="/tmp/provider-history.sqlite3",
    )

    assert config["history_db_path"] == "/tmp/provider-history.sqlite3"
    assert config["vector_store"]["config"]["collection_name"] == "isolated_collection"
    assert config["vector_store"]["config"]["embedding_model_dims"] == 1024
    assert config["embedder"]["config"] == {
        "model": "thenlper/gte-large",
        "embedding_dims": 1024,
    }


def test_external_memory_compare_mem0_preflight_fails_closed_without_native_assets():
    class DenseModel:
        embedding_size = 1024

    class EmbeddingModel:
        dense_model = DenseModel()

    class VectorStore:
        _has_bm25_slot = False

    class Memory:
        embedding_model = EmbeddingModel()
        vector_store = VectorStore()

    with pytest.raises(RuntimeError, match="native retrieval preflight failed"):
        _mem0_retrieval_preflight(
            Memory(),
            expected_embedding_dims=1024,
            limit=4,
            require_native_assets=True,
            test_double=False,
        )


def test_external_memory_compare_mem0_cleanup_and_environment_restore(monkeypatch):
    events = []

    class Client:
        def close(self):
            events.append("client")

    class VectorStore:
        client = Client()

    class Memory:
        vector_store = VectorStore()

        def close(self):
            events.append("memory")

    monkeypatch.setenv("MEM0_DIR", "before")
    monkeypatch.delenv("MEM0_TELEMETRY", raising=False)
    previous = _set_process_env({"MEM0_DIR": "during", "MEM0_TELEMETRY": "false"})
    assert previous == {"MEM0_DIR": "before", "MEM0_TELEMETRY": None}

    _close_mem0_memory(Memory())
    _restore_process_env(previous)

    assert events == ["client", "memory"]
    assert os.environ["MEM0_DIR"] == "before"
    assert "MEM0_TELEMETRY" not in os.environ


def test_external_memory_compare_letta_run_uses_tags_and_source_ids(tmp_path):
    fixture_path = tmp_path / "fixture.json"
    run_path = tmp_path / "letta-run.json"
    score_path = tmp_path / "score.json"
    fixture_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifact_type": "external_memory_comparison_fixture",
                "benchmark": "toy",
                "documents": [
                    {
                        "source": "toy/source/1",
                        "title": "Right source",
                        "content": "The brass key is in the north drawer.",
                        "category": "case:a",
                        "tags": "toy,source",
                    }
                ],
                "cases": [
                    {
                        "id": "case-1",
                        "query": "Where is the brass key?",
                        "expected_sources": ["toy/source/1"],
                        "expected_answer": "north drawer",
                        "search_category": "case:a",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def fake_transport(*, method, url, api_key, payload=None, params=None):
        calls.append(
            {
                "method": method,
                "url": url,
                "api_key": api_key,
                "payload": payload,
                "params": params,
            }
        )
        if url.endswith("/v1/archives/"):
            return {"id": "archive-1"}
        if url.endswith("/v1/passages/search"):
            return [
                {
                    "passage": {
                        "id": "passage-1",
                        "text": "The brass key is in the north drawer.",
                        "tags": ["run:run-1", "source:toy/source/1", "category:case:a"],
                    },
                    "score": 0.91,
                }
            ]
        if method == "DELETE":
            return {}
        return {"id": "passage-1"}

    run = run_letta_comparison(
        fixture_path=fixture_path,
        output_path=run_path,
        api_key=None,
        base_url="https://example.letta",
        run_id="run-1",
        embedding="ollama/bge-m3:latest",
        server_version="0.16.8",
        limit=5,
        transport=fake_transport,
    )
    score = score_run(fixture_path=fixture_path, run_path=run_path, output_path=score_path)

    assert run["system"] == "letta"
    assert run["system_version"] == "0.16.8"
    assert run["archive_id"] == "archive-1"
    assert run["documents_total"] == 1
    assert calls[0]["method"] == "POST"
    assert calls[0]["url"].endswith("/v1/archives/")
    assert calls[0]["payload"]["embedding"] == "ollama/bge-m3:latest"
    assert "source:toy/source/1" in calls[1]["payload"]["tags"]
    assert calls[2]["method"] == "POST"
    assert calls[2]["url"].endswith("/v1/passages/search")
    assert calls[2]["payload"]["tags"] == ["run:run-1", "category:case:a"]
    assert calls[2]["payload"]["tag_match_mode"] == "all"
    assert calls[3]["method"] == "DELETE"
    assert calls[3]["url"].endswith("/v1/archives/archive-1")
    assert run["cases"][0]["results"][0]["source"] == "toy/source/1"
    assert "content" not in run["cases"][0]["results"][0]
    assert run["manifest"]["cleanup"]["succeeded"] is True
    assert score["retrieval"]["hit_cases"] == 1
    assert score["engineering"]["capabilities"]["audit"]["measured"] is False


def test_external_memory_compare_letta_cleans_archive_after_search_failure(tmp_path):
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifact_type": "external_memory_comparison_fixture",
                "benchmark": "toy",
                "documents": [{"source": "toy/source/1", "content": "Evidence."}],
                "cases": [{"id": "case-1", "query": "Evidence?"}],
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def failing_transport(*, method, url, api_key, payload=None, params=None):
        calls.append((method, url))
        if url.endswith("/v1/archives/"):
            return {"id": "archive-1"}
        if url.endswith("/v1/archives/archive-1/passages"):
            return {"id": "passage-1"}
        if url.endswith("/v1/passages/search"):
            raise RuntimeError("search failed")
        return {}

    with pytest.raises(RuntimeError, match="search failed"):
        run_letta_comparison(
            fixture_path=fixture_path,
            base_url="http://127.0.0.1:8283",
            run_id="run-1",
            limit=1,
            search_scope="global",
            transport=failing_transport,
        )

    assert calls[-1] == ("DELETE", "http://127.0.0.1:8283/v1/archives/archive-1")


def test_external_memory_compare_letta_reports_primary_and_cleanup_failures(tmp_path):
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifact_type": "external_memory_comparison_fixture",
                "benchmark": "toy",
                "documents": [{"source": "toy/source/1", "content": "Evidence."}],
                "cases": [{"id": "case-1", "query": "Evidence?"}],
            }
        ),
        encoding="utf-8",
    )

    def failing_transport(*, method, url, api_key, payload=None, params=None):
        if url.endswith("/v1/archives/"):
            return {"id": "archive-1"}
        if url.endswith("/v1/archives/archive-1/passages"):
            return {"id": "passage-1"}
        if url.endswith("/v1/passages/search"):
            raise RuntimeError("search failed")
        if method == "DELETE":
            raise RuntimeError("delete failed")
        return {}

    with pytest.raises(RuntimeError, match="search failed.*cleanup also failed.*delete failed"):
        run_letta_comparison(
            fixture_path=fixture_path,
            base_url="http://127.0.0.1:8283",
            run_id="run-1",
            limit=1,
            search_scope="global",
            transport=failing_transport,
        )


def test_external_memory_compare_answer_run_adds_final_answers(tmp_path):
    fixture_path = tmp_path / "fixture.json"
    run_path = tmp_path / "run.json"
    answered_path = tmp_path / "answered.json"
    score_path = tmp_path / "score.json"
    fixture_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifact_type": "external_memory_comparison_fixture",
                "benchmark": "toy",
                "documents": [
                    {
                        "source": "toy/source/1",
                        "title": "Ticket note",
                        "content": "The blue ticket is in the blue drawer.",
                    }
                ],
                "cases": [
                    {
                        "id": "case-1",
                        "query": "Where is the blue ticket?",
                        "expected_sources": ["toy/source/1"],
                        "expected_answer": "blue drawer",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    fixture_hash = fixture_digest(json.loads(fixture_path.read_text(encoding="utf-8")))
    run_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifact_type": "external_memory_comparison_run",
                "system": "vault",
                "benchmark": "toy",
                "fixture_digest": fixture_hash,
                "top_k": 1,
                "candidate_pool_k": 1,
                "cases_total": 1,
                "cases": [
                    {
                        "id": "case-1",
                        "query": "Where is the blue ticket?",
                        "latency_ms": 2.0,
                        "results": [{"rank": 1, "source": "toy/source/1"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    answered = answer_run(
        fixture_path=fixture_path,
        run_path=run_path,
        output_path=answered_path,
        llm_provider="mock",
        mock_response="blue drawer",
    )
    score = score_run(fixture_path=fixture_path, run_path=answered_path, output_path=score_path)

    assert answered["cases"][0]["answer"] == "blue drawer"
    assert answered["cases"][0]["answer_latency_ms"] >= 0
    assert answered["final_qa_reader"]["provider"] == "mock"
    assert score["final_qa"]["available"] is True
    assert score["final_qa"]["normalized_exact_match_rate"] == 1.0
    assert score["index_latency"]["available"] is False
    assert score["answer_latency"]["available"] is True


def test_external_memory_compare_vault_mode_comparison_scores_modes(tmp_path):
    data_path = tmp_path / "longmemeval.json"
    output_path = tmp_path / "mode-compare.json"
    data_path.write_text(
        json.dumps(
            [
                {
                    "question_id": "q1",
                    "question": "Which cabinet stores the amber notebook?",
                    "answer": "The west cabinet.",
                    "haystack_session_ids": ["s1"],
                    "haystack_sessions": [
                        [
                            {
                                "role": "user",
                                "content": "I stored the amber notebook in the west cabinet.",
                                "has_answer": True,
                            }
                        ]
                    ],
                    "answer_session_ids": ["s1"],
                }
            ]
        ),
        encoding="utf-8",
    )

    payload = run_vault_mode_comparison(
        benchmark="longmemeval",
        input_path=data_path,
        output_path=output_path,
        limit=3,
        modes=["keyword", "hybrid"],
        allow_hash=True,
        hash_dim=8,
    )

    assert payload["artifact_type"] == "external_memory_vault_mode_comparison"
    assert payload["mode_order"] == ["keyword", "hybrid"]
    assert payload["baseline_mode"] == "keyword"
    assert set(payload["runs_by_mode"]) == {"keyword", "hybrid"}
    assert set(payload["scores_by_mode"]) == {"keyword", "hybrid"}
    assert payload["runs_by_mode"]["keyword"]["top_k"] == 3
    assert payload["runs_by_mode"]["hybrid"]["top_k"] == 3
    assert payload["scores_by_mode"]["keyword"]["retrieval"]["hit_cases"] == 1
    assert payload["scores_by_mode"]["hybrid"]["retrieval"]["hit_cases"] == 1
    hybrid_run = payload["runs_by_mode"]["hybrid"]
    assert hybrid_run["semantic_index_latency_ms"] > 0
    assert hybrid_run["index_latency_ms"] == round(
        hybrid_run["storage_index_latency_ms"] + hybrid_run["semantic_index_latency_ms"],
        3,
    )
    assert "hybrid" in payload["comparisons_vs_baseline"]
    assert output_path.exists()


def test_external_memory_compare_cli_vault_run_and_score(tmp_path):
    data_path = tmp_path / "longmemeval.json"
    fixture_path = tmp_path / "fixture.json"
    run_path = tmp_path / "vault-run.json"
    score_path = tmp_path / "score.json"
    answered_path = tmp_path / "answered.json"
    data_path.write_text(
        json.dumps(
            [
                {
                    "question_id": "q1",
                    "question": "Which cabinet stores the amber notebook?",
                    "answer": "The west cabinet.",
                    "haystack_session_ids": ["s1"],
                    "haystack_sessions": [
                        [
                            {
                                "role": "user",
                                "content": "I stored the amber notebook in the west cabinet.",
                                "has_answer": True,
                            }
                        ]
                    ],
                    "answer_session_ids": ["s1"],
                }
            ]
        ),
        encoding="utf-8",
    )

    fixture_result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "benchmarks" / "external_memory_compare.py"),
            "export-fixture",
            "--benchmark",
            "longmemeval",
            "--input",
            str(data_path),
            "--output",
            str(fixture_path),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert fixture_result.returncode == 0, fixture_result.stderr

    run_result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "benchmarks" / "external_memory_compare.py"),
            "vault-run",
            "--benchmark",
            "longmemeval",
            "--input",
            str(data_path),
            "--output",
            str(run_path),
            "--limit",
            "3",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert run_result.returncode == 0, run_result.stderr

    answer_result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "benchmarks" / "external_memory_compare.py"),
            "answer-run",
            "--fixture",
            str(fixture_path),
            "--run",
            str(run_path),
            "--output",
            str(answered_path),
            "--llm-provider",
            "mock",
            "--mock-response",
            "The west cabinet.",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert answer_result.returncode == 0, answer_result.stderr

    score_result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "benchmarks" / "external_memory_compare.py"),
            "score-run",
            "--fixture",
            str(fixture_path),
            "--run",
            str(answered_path),
            "--output",
            str(score_path),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert score_result.returncode == 0, score_result.stderr
    score = json.loads(score_path.read_text(encoding="utf-8"))
    assert score["system"] == "vault"
    assert score["retrieval"]["hit_cases"] == 1
    assert score["final_qa"]["available"] is True
    assert score["final_qa"]["normalized_exact_match_rate"] == 1.0
    assert score["index_latency"]["available"] is True
    assert score["latency"]["available"] is True
    assert score["answer_latency"]["available"] is True
    assert score["engineering"]["capabilities"]["local_first"]["measured"] is True


def test_external_memory_compare_cli_vault_mode_compare_smoke(tmp_path):
    data_path = tmp_path / "longmemeval.json"
    output_path = tmp_path / "mode-compare.json"
    data_path.write_text(
        json.dumps(
            [
                {
                    "question_id": "q1",
                    "question": "Which cabinet stores the amber notebook?",
                    "answer": "The west cabinet.",
                    "haystack_session_ids": ["s1"],
                    "haystack_sessions": [
                        [
                            {
                                "role": "user",
                                "content": "I stored the amber notebook in the west cabinet.",
                                "has_answer": True,
                            }
                        ]
                    ],
                    "answer_session_ids": ["s1"],
                }
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "benchmarks" / "external_memory_compare.py"),
            "vault-mode-compare",
            "--benchmark",
            "longmemeval",
            "--input",
            str(data_path),
            "--output",
            str(output_path),
            "--limit",
            "3",
            "--modes",
            "keyword,hybrid",
            "--allow-hash",
            "--hash-dim",
            "8",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "external_memory_vault_mode_comparison"
    assert payload["mode_order"] == ["keyword", "hybrid"]
    assert "aggregate_by_mode" in result.stdout


def test_external_memory_compare_scorer_enforces_declared_top_k(tmp_path):
    fixture, run = _minimal_fixture_and_run()
    fixture_path = tmp_path / "fixture.json"
    run_path = tmp_path / "run.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    run_path.write_text(json.dumps(run), encoding="utf-8")

    result = score_run(fixture_path=fixture_path, run_path=run_path)

    assert result["retrieval"]["hit_cases"] == 0
    assert result["cases"][0]["retrieval"]["returned_sources"] == ["toy/other"]


def test_external_memory_compare_rejects_tampered_fixture_digest(tmp_path):
    fixture, run = _minimal_fixture_and_run()
    fixture["fixture_digest"] = fixture_digest(fixture)
    fixture["cases"][0]["query"] = "Tampered after digest"
    fixture_path = tmp_path / "fixture.json"
    run_path = tmp_path / "run.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    run_path.write_text(json.dumps(run), encoding="utf-8")

    with pytest.raises(ValueError, match="fixture digest does not match"):
        score_run(fixture_path=fixture_path, run_path=run_path)


def test_external_memory_compare_rejects_run_digest_mismatch(tmp_path):
    fixture, run = _minimal_fixture_and_run()
    run["fixture_digest"] = "sha256:" + "0" * 64
    fixture_path = tmp_path / "fixture.json"
    run_path = tmp_path / "run.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    run_path.write_text(json.dumps(run), encoding="utf-8")

    with pytest.raises(ValueError, match="fixture and run digest must match"):
        score_run(fixture_path=fixture_path, run_path=run_path)


def test_external_memory_compare_rejects_duplicate_run_case_ids(tmp_path):
    fixture, run = _minimal_fixture_and_run()
    run["cases"].append(dict(run["cases"][0]))
    fixture_path = tmp_path / "fixture.json"
    run_path = tmp_path / "run.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    run_path.write_text(json.dumps(run), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate case ids"):
        score_run(fixture_path=fixture_path, run_path=run_path)
