from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.agentmemory_compare import run_agentmemory_comparison
from benchmarks.external_memory_compare import export_provider_input, fixture_digest, score_run


def _fixture() -> dict:
    return {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_fixture",
        "benchmark": "agentmemory-toy",
        "documents": [
            {
                "source": "toy/aurora",
                "title": "Aurora rotation",
                "content": "Aurora rotates credentials every 37 minutes.",
                "tags": "aurora,security",
            },
            {
                "source": "toy/cedar",
                "title": "Cedar retry",
                "content": "Cedar retries invoices with exponential backoff.",
            },
        ],
        "cases": [
            {
                "id": "rotation",
                "query": "credential renewal periodicity",
                "expected_sources": ["toy/aurora"],
            }
        ],
    }


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_agentmemory_adapter_maps_obs_id_before_broken_session_id(tmp_path):
    fixture_path = tmp_path / "fixture.json"
    provider_input_path = tmp_path / "provider-input.json"
    run_path = tmp_path / "run.json"
    score_path = tmp_path / "score.json"
    fixture = _fixture()
    fixture["fixture_digest"] = fixture_digest(fixture)
    _write(fixture_path, fixture)
    export_provider_input(fixture_path=fixture_path, output_path=provider_input_path)
    calls = []
    remember_ids = iter(("mem-aurora", "mem-cedar"))

    def transport(*, method, url, api_key, payload=None):
        calls.append({"method": method, "url": url, "api_key": api_key, "payload": payload})
        if url.endswith("/agentmemory/remember"):
            return {
                "success": True,
                "memory": {
                    "id": next(remember_ids),
                    "isLatest": True,
                    "supersedes": [],
                },
            }
        if url.endswith("/agentmemory/smart-search"):
            return {
                "mode": "compact",
                "results": [
                    {
                        "obsId": "mem-aurora",
                        "sessionId": "memory",
                        "score": 0.01,
                        "title": "Aurora rotation",
                    },
                    {
                        "obsId": "mem-cedar",
                        "sessionId": "memory",
                        "score": 0.009,
                        "title": "Cedar retry",
                    },
                ],
            }
        raise AssertionError(f"unexpected request: {method} {url}")

    run = run_agentmemory_comparison(
        fixture_path=provider_input_path,
        output_path=run_path,
        fresh_store_id="tmp-store-1",
        run_id="run-1",
        limit=2,
        transport=transport,
    )
    score = score_run(fixture_path=fixture_path, run_path=run_path, output_path=score_path)

    assert run["system"] == "rohitg00/agentmemory"
    assert run["system_version"] == "0.9.27"
    assert run["documents_indexed"] == 2
    assert run["cases"][0]["results"][0]["source"] == "toy/aurora"
    assert run["cases"][0]["results"][1]["source"] == "toy/cedar"
    assert "content" not in run["cases"][0]["results"][0]
    assert run["manifest"]["provider_config"]["project_filter_trusted"] is False
    assert run["manifest"]["provider_input"]["gold_labels_excluded"] is True
    assert run["manifest"]["isolation"]["fresh_store_required"] is True
    assert score["retrieval"]["hit_rate"] == 1.0
    assert calls[-1]["payload"]["includeLessons"] is False
    assert calls[0]["payload"]["content"].startswith("title: Aurora rotation\ncontent:")
    assert "expected_sources" not in calls[0]["payload"]["content"]


def test_agentmemory_adapter_fails_closed_on_unmapped_result(tmp_path):
    fixture = _fixture()
    fixture["documents"] = fixture["documents"][:1]
    fixture_path = tmp_path / "fixture.json"
    _write(fixture_path, fixture)

    def transport(*, method, url, api_key, payload=None):
        if url.endswith("/agentmemory/remember"):
            return {"memory": {"id": "mem-aurora"}}
        return {
            "results": [
                {"obsId": "old-store-memory", "sessionId": "memory", "score": 1.0}
            ]
        }

    with pytest.raises(RuntimeError, match="server store may not be fresh"):
        run_agentmemory_comparison(
            fixture_path=fixture_path,
            fresh_store_id="tmp-store-1",
            limit=1,
            transport=transport,
        )


def test_agentmemory_adapter_rejects_case_scope(tmp_path):
    fixture_path = tmp_path / "fixture.json"
    _write(fixture_path, _fixture())

    with pytest.raises(ValueError, match="only supports global fixtures"):
        run_agentmemory_comparison(
            fixture_path=fixture_path,
            fresh_store_id="tmp-store-1",
            search_scope="case",
            transport=lambda **_kwargs: {},
        )


def test_agentmemory_adapter_fails_closed_when_search_results_key_is_missing(tmp_path):
    fixture = _fixture()
    fixture["documents"] = fixture["documents"][:1]
    fixture_path = tmp_path / "fixture.json"
    _write(fixture_path, fixture)

    def transport(*, method, url, api_key, payload=None):
        if url.endswith("/agentmemory/remember"):
            return {"memory": {"id": "mem-aurora"}}
        return {"mode": "compact"}

    with pytest.raises(RuntimeError, match="did not include results"):
        run_agentmemory_comparison(
            fixture_path=fixture_path,
            fresh_store_id="tmp-store-1",
            transport=transport,
        )
