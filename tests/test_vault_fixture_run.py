from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from benchmarks.external_memory_compare import export_provider_input, fixture_digest
from benchmarks.memory_foundation_compare import augment_run
from benchmarks.vault_fixture_run import _index_documents, run_vault_fixture
from vault.db import VaultDB


REPO_ROOT = Path(__file__).parent.parent
BUNDLED_FIXTURE = REPO_ROOT / "benchmarks" / "vault_gov_bench" / "retrieval_v0.1.json"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _toy_fixture() -> dict:
    return {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_fixture",
        "benchmark": "vault-live-fixture-toy",
        "fixed_clock": "2026-07-19T00:00:00Z",
        "documents": [
            {
                "id": "old",
                "source": "toy/office/old",
                "title": "Former office",
                "content": "The office was in Kaohsiung.",
                "governance": {"valid_until": "2026-07-01T00:00:00Z"},
            },
            {
                "id": "current",
                "source": "toy/office/current",
                "title": "Current office",
                "content": "The office is now in Taipei.",
                "governance": {
                    "valid_from": "2026-07-01T00:00:00Z",
                    "supersedes_id": "old",
                },
            },
        ],
        "cases": [
            {
                "id": "office-now",
                "query": "Where is the office now?",
                "agent_id": "work-agent",
                "as_of": "2026-07-19T00:00:00Z",
                "expected_answer": "Taipei",
                "expected_sources": ["toy/office/current"],
                "expected_valid_sources": ["toy/office/current"],
                "forbidden_sources": ["toy/office/old"],
            }
        ],
        "matching_rule": {"retrieval": "exact source id"},
    }


def test_run_vault_fixture_builds_live_candidate_pool_and_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _toy_fixture()
    fixture_path = tmp_path / "fixture.json"
    output_path = tmp_path / "vault-run.json"
    _write_json(fixture_path, fixture)
    original_read_text = Path.read_text

    def reject_frozen_candidate_reads(path: Path, *args, **kwargs):
        if path.name.startswith("frozen_candidate_pool"):
            raise AssertionError("live runner must not read frozen candidates")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", reject_frozen_candidate_reads)

    payload = run_vault_fixture(
        fixture_path=fixture_path,
        output_path=output_path,
        candidate_pool_k=2,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == payload
    assert payload["system"] == "vault"
    assert payload["fixture_digest"] == fixture_digest(fixture)
    assert payload["documents_total"] == 2
    assert payload["cases_total"] == 1
    assert payload["top_k"] == payload["candidate_pool_k"] == 2
    assert payload["index_latency_ms"] == round(
        payload["setup_latency_ms"] + payload["ingest_latency_ms"], 3
    )
    case = payload["cases"][0]
    assert case["id"] == case["case_id"] == "office-now"
    assert "expected_answer" not in case
    assert "expected_sources" not in case
    assert "expected_valid_sources" not in case
    assert "forbidden_sources" not in case
    assert case["candidate_pool"] == case["results"]
    assert {item["source"] for item in case["candidate_pool"]} == {
        "toy/office/old",
        "toy/office/current",
    }
    assert all("content" not in item for item in case["candidate_pool"])
    assert payload["timings"]["retrieval"]["count"] == 1
    assert payload["manifest"]["fixture"]["frozen_candidate_pool_used"] is False
    assert payload["manifest"]["database"]["ephemeral"] is True
    assert payload["manifest"]["database"]["path"] == "redacted-temporary-path"
    assert payload["manifest"]["provider_quality_gate"]["passed"] is True
    assert payload["manifest"]["retrieval"]["implementation"] == ("vault.search.VaultSearch.search")
    assert payload["manifest"]["retrieval"]["content_in_run_artifact"] is False
    assert payload["manifest"]["retrieval"]["publishable"] is True
    assert payload["engineering"]["audit"]["measured"] is False


def test_run_vault_fixture_content_is_explicit_debug_opt_in(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixture.json"
    _write_json(fixture_path, _toy_fixture())

    payload = run_vault_fixture(
        fixture_path=fixture_path,
        candidate_pool_k=2,
        include_content=True,
    )

    assert all(item["content"] for item in payload["cases"][0]["candidate_pool"])
    assert payload["manifest"]["retrieval"]["content_in_run_artifact"] is True


def test_bundled_fixture_run_is_rrf_augmentation_compatible(tmp_path: Path) -> None:
    provider_input_path = tmp_path / "provider-input.json"
    output_path = tmp_path / "vault-run.json"
    augmented_path = tmp_path / "augmented.json"
    export_provider_input(fixture_path=BUNDLED_FIXTURE, output_path=provider_input_path)
    payload = run_vault_fixture(
        fixture_path=provider_input_path,
        output_path=output_path,
        candidate_pool_k=4,
    )

    augmented = augment_run(
        fixture_path=BUNDLED_FIXTURE,
        engine_run_path=output_path,
        vault_run_path=output_path,
        output_path=augmented_path,
        mode="rrf-fusion",
        top_k=1,
        candidate_pool_k=4,
    )

    assert [case["id"] for case in payload["cases"]] == [
        "temporal-correction",
        "private-access",
        "deleted-ghost",
        "ttl-expiry",
        "superseded-revision",
        "privacy-block",
    ]
    assert all(case["candidate_pool"] == case["results"] for case in payload["cases"])
    assert augmented["augmentation"]["mode"] == "rrf-fusion"
    assert augmented["augmentation"]["vault_system"] == "vault"
    assert augmented["fixture_digest"] == payload["fixture_digest"]
    assert payload["manifest"]["provider_input"]["gold_labels_excluded"] is True


def test_blind_vault_run_preserves_top_level_governance_fields(tmp_path: Path) -> None:
    fixture = _toy_fixture()
    fixture["documents"][0]["status"] = "deleted"
    fixture_path = tmp_path / "fixture.json"
    provider_input_path = tmp_path / "provider-input.json"
    _write_json(fixture_path, fixture)
    export_provider_input(
        fixture_path=fixture_path,
        output_path=provider_input_path,
    )

    provider_input = json.loads(provider_input_path.read_text(encoding="utf-8"))
    db = VaultDB(tmp_path / "fixture.db").connect()
    try:
        _index_documents(db, provider_input["documents"])
        row = db.conn.execute(
            "SELECT status FROM knowledge WHERE source = ?",
            ("toy/office/old",),
        ).fetchone()
    finally:
        db.close()

    assert row["status"] == "deleted"


def test_run_vault_fixture_rejects_stale_fixture_digest(tmp_path: Path) -> None:
    fixture = _toy_fixture()
    fixture["fixture_digest"] = "sha256:not-the-current-content"
    fixture_path = tmp_path / "fixture.json"
    _write_json(fixture_path, fixture)

    with pytest.raises(ValueError, match="fixture digest does not match"):
        run_vault_fixture(fixture_path=fixture_path, candidate_pool_k=2)


def test_run_vault_fixture_requires_explicit_semantic_provider(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixture.json"
    _write_json(fixture_path, _toy_fixture())

    with pytest.raises(ValueError, match="require --embed-provider or --allow-hash"):
        run_vault_fixture(
            fixture_path=fixture_path,
            candidate_pool_k=2,
            mode="hybrid",
        )


def test_vault_fixture_run_cli_smoke(tmp_path: Path) -> None:
    output_path = tmp_path / "vault-run.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "benchmarks" / "vault_fixture_run.py"),
            "--fixture",
            str(BUNDLED_FIXTURE),
            "--output",
            str(output_path),
            "--candidate-pool-k",
            "4",
            "--quiet",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary["fixture_digest"] == payload["fixture_digest"]
    assert summary["cases_total"] == payload["cases_total"] == 6
    assert payload["manifest"]["fixture"]["frozen_candidate_pool_used"] is False
