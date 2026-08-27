from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.replay_memory_admission_corpus import DEFAULT_CORPUS, replay


ROOT = Path(__file__).resolve().parents[1]


def test_synthetic_hermes_corpus_has_exact_closed_shape():
    corpus = json.loads(DEFAULT_CORPUS.read_text(encoding="utf-8"))
    cases = corpus["cases"]

    assert corpus["contract"] == "hermes-memory-admission-shadow"
    assert len(cases) == 55
    assert len({case["id"] for case in cases}) == 55
    assert sum(case["expected_status"] == "warn" for case in cases) == 45
    assert sum(case["expected_status"] == "pass" for case in cases) == 10


def test_synthetic_hermes_shadow_replay_matches_every_expectation():
    report = replay(DEFAULT_CORPUS)

    assert report["case_count"] == 55
    assert report["passed_count"] == 55
    assert report["failed_count"] == 0
    assert report["write_authority"] is False


@pytest.mark.parametrize("payload", [{}, {"cases": []}, {"cases": {}}])
def test_shadow_replay_rejects_missing_empty_or_non_list_cases(tmp_path, payload):
    corpus_path = tmp_path / "invalid-corpus.json"
    corpus_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="non-empty list"):
        replay(corpus_path)


def test_shadow_replay_cli_is_read_only_and_machine_readable():
    completed = subprocess.run(
        [sys.executable, "scripts/replay_memory_admission_corpus.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)

    assert completed.returncode == 0
    assert report["passed_count"] == 55
    assert report["write_authority"] is False
