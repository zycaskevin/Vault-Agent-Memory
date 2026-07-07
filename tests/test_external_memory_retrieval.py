from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


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
    assert payload["documents_indexed"] == 2
    assert payload["aggregate"]["total_cases"] == 1
    assert payload["aggregate"]["hit_cases"] == 1
    assert payload["cases"][0]["expected_sources"] == ["locomo/sample-1/dia/D1"]
    generated = json.loads(generated_qa.read_text(encoding="utf-8"))
    assert generated["cases"][0]["expected_sources"] == ["locomo/sample-1/dia/D1"]


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
    assert payload["documents_indexed"] == 2
    assert payload["aggregate"]["total_cases"] == 1
    assert payload["aggregate"]["hit_cases"] == 1
    assert payload["cases"][0]["expected_sources"] == ["longmemeval/q1/session/s1"]
