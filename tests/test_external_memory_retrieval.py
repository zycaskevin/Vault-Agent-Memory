from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from benchmarks.external_memory_retrieval import run_external_memory_retrieval


REPO_ROOT = Path(__file__).parent.parent


def test_locomo_external_memory_retrieval_smoke(tmp_path):
    data_path = tmp_path / "locomo.json"
    output = tmp_path / "report.json"
    generated_qa = tmp_path / "locomo-searchqa.json"
    data_path.write_text(
        json.dumps(
            [
                {
                    "sample_id": "sample-1",
                    "conversation": {
                        "speaker_a": "Angela",
                        "speaker_b": "Brian",
                        "session_1_date_time": "2024-01-01 09:00",
                        "session_1": [
                            {
                                "speaker": "speaker_a",
                                "dia_id": "D1",
                                "text": "I opened a small ceramic gallery next to the gift shop.",
                            },
                            {
                                "speaker": "speaker_b",
                                "dia_id": "D2",
                                "text": "The weather was rainy today.",
                            },
                        ],
                    },
                    "qa": [
                        {
                            "question": "What kind of gallery did Angela open?",
                            "answer": "A small ceramic gallery.",
                            "category": "single-hop",
                            "evidence": ["D1"],
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "benchmarks" / "external_memory_retrieval.py"),
            "--benchmark",
            "locomo",
            "--input",
            str(data_path),
            "--output",
            str(output),
            "--generated-qa",
            str(generated_qa),
            "--limit",
            "3",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["benchmark"] == "locomo"
    assert payload["search_scope"] == "case"
    assert payload["documents_indexed"] == 2
    assert payload["aggregate"]["total_cases"] == 1
    assert payload["aggregate"]["hit_cases"] == 1
    assert payload["cases"][0]["expected_sources"] == ["locomo/sample-1/dia/D1"]
    assert payload["cases"][0]["search_category"] == "locomo-dialog:sample-1"
    generated = json.loads(generated_qa.read_text(encoding="utf-8"))
    assert generated["cases"][0]["expected_sources"] == ["locomo/sample-1/dia/D1"]
    assert generated["cases"][0]["search_category"] == "locomo-dialog:sample-1"


def test_longmemeval_external_memory_retrieval_session_smoke(tmp_path):
    data_path = tmp_path / "longmemeval.json"
    output = tmp_path / "report.json"
    data_path.write_text(
        json.dumps(
            [
                {
                    "question_id": "q1",
                    "question_type": "single-session-user",
                    "question": "Which blue violin did the user mention?",
                    "answer": "A blue violin.",
                    "question_date": "2024-02-02",
                    "haystack_session_ids": ["s1", "s2"],
                    "haystack_dates": ["2024-01-01", "2024-01-02"],
                    "haystack_sessions": [
                        [
                            {"role": "user", "content": "I bought a blue violin yesterday.", "has_answer": True},
                            {"role": "assistant", "content": "That sounds wonderful."},
                        ],
                        [
                            {"role": "user", "content": "I need to buy groceries."},
                            {"role": "assistant", "content": "Make a list."},
                        ],
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
            str(REPO_ROOT / "benchmarks" / "external_memory_retrieval.py"),
            "--benchmark",
            "longmemeval",
            "--input",
            str(data_path),
            "--output",
            str(output),
            "--granularity",
            "session",
            "--limit",
            "3",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["benchmark"] == "longmemeval"
    assert payload["search_scope"] == "case"
    assert payload["documents_indexed"] == 2
    assert payload["aggregate"]["total_cases"] == 1
    assert payload["aggregate"]["hit_cases"] == 1
    assert payload["cases"][0]["expected_sources"] == ["longmemeval/q1/session/s1"]
    assert payload["cases"][0]["search_category"] == "longmemeval-session:q1"


def test_longmemeval_case_scope_isolates_question_haystacks(tmp_path):
    data_path = tmp_path / "longmemeval.json"
    data_path.write_text(
        json.dumps(
            [
                {
                    "question_id": "q1",
                    "question": "Where did I leave the orchid receipt?",
                    "answer": "In the cedar desk drawer.",
                    "haystack_session_ids": ["s1"],
                    "haystack_sessions": [
                        [
                            {
                                "role": "user",
                                "content": "I left the orchid receipt in the cedar desk drawer.",
                                "has_answer": True,
                            }
                        ]
                    ],
                    "answer_session_ids": ["s1"],
                },
                {
                    "question_id": "q2",
                    "question": "Which notebook has the travel stamp?",
                    "answer": "The green notebook.",
                    "haystack_session_ids": ["s9"],
                    "haystack_sessions": [
                        [
                            {
                                "role": "user",
                                "content": (
                                    "Where did I leave the orchid receipt? orchid receipt "
                                    "orchid receipt. This is unrelated noise for another case."
                                ),
                            },
                            {
                                "role": "user",
                                "content": "The travel stamp is inside the green notebook.",
                                "has_answer": True,
                            },
                        ]
                    ],
                    "answer_session_ids": ["s9"],
                },
            ]
        ),
        encoding="utf-8",
    )

    report = run_external_memory_retrieval(
        benchmark="longmemeval",
        input_path=data_path,
        limit=5,
        search_scope="case",
    )

    assert report["aggregate"]["hit_cases"] == 2
    first_case = report["cases"][0]
    assert first_case["id"] == "q1"
    assert first_case["hit"] is True
    assert first_case["search_category"] == "longmemeval-session:q1"
    assert {item["source"] for item in first_case["results"]} == {"longmemeval/q1/session/s1"}


def test_external_memory_retrieval_can_reuse_existing_db(tmp_path):
    data_path = tmp_path / "locomo.json"
    db_path = tmp_path / "benchmark.db"
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
                                "text": "I stored the copper map in the archive cabinet.",
                            }
                        ],
                    },
                    "qa": [
                        {
                            "question": "Where is the copper map?",
                            "answer": "In the archive cabinet.",
                            "evidence": ["D1"],
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    first = run_external_memory_retrieval(
        benchmark="locomo",
        input_path=data_path,
        db_path=db_path,
        limit=3,
    )
    second = run_external_memory_retrieval(
        benchmark="locomo",
        input_path=data_path,
        db_path=db_path,
        reuse_db=True,
        limit=3,
    )

    assert first["db_reused"] is False
    assert second["db_reused"] is True
    assert second["aggregate"]["hit_cases"] == 1
