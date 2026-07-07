from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from benchmarks.external_memory_compare import (
    answer_run,
    export_fixture,
    run_letta_comparison,
    run_mem0_comparison,
    run_vault_mode_comparison,
    score_run,
)


REPO_ROOT = Path(__file__).parent.parent


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
        "top_k": 3,
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
    assert json.loads(fixture_path.read_text(encoding="utf-8"))["matching_rule"]["retrieval"].startswith(
        "A case is a hit"
    )


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
    assert run["index_latency_ms"] >= 0
    assert fake.documents[0]["infer"] is False
    assert fake.search_filters == [
        {"user_id": "external-memory-comparison", "search_category": "case:a"}
    ]
    assert run["cases"][0]["results"][0]["source"] == "toy/source/1"
    assert score["retrieval"]["hit_cases"] == 1
    assert score["index_latency"]["available"] is True
    assert score["index_latency"]["item_count"] == 2
    assert score["engineering"]["capabilities"]["audit"]["measured"] is True


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
        if method == "GET":
            return {
                "count": 1,
                "results": [
                    {
                        "id": "passage-1",
                        "content": "The brass key is in the north drawer.",
                        "tags": ["run:run-1", "source:toy/source/1", "category:case:a"],
                    }
                ],
            }
        return {"id": "passage-1"}

    run = run_letta_comparison(
        fixture_path=fixture_path,
        agent_id="agent-test",
        output_path=run_path,
        api_key="test-key",
        base_url="https://example.letta",
        run_id="run-1",
        limit=5,
        transport=fake_transport,
    )
    score = score_run(fixture_path=fixture_path, run_path=run_path, output_path=score_path)

    assert run["system"] == "letta"
    assert run["documents_total"] == 1
    assert calls[0]["method"] == "POST"
    assert "source:toy/source/1" in calls[0]["payload"]["tags"]
    assert calls[1]["method"] == "GET"
    assert calls[1]["params"]["tags"] == ["run:run-1", "category:case:a"]
    assert calls[1]["params"]["tag_match_mode"] == "all"
    assert run["cases"][0]["results"][0]["source"] == "toy/source/1"
    assert score["retrieval"]["hit_cases"] == 1
    assert score["engineering"]["capabilities"]["audit"]["measured"] is True


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
    run_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifact_type": "external_memory_comparison_run",
                "system": "vault",
                "benchmark": "toy",
                "top_k": 1,
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
