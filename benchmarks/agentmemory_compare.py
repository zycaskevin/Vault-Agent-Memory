"""Neutral retrieval adapter for rohitg00/agentmemory.

The project name is intentionally part of the system id because several
unrelated packages use the name ``AgentMemory``.  This adapter targets the
v0.9.27 REST server and its ``remember`` / ``smart-search`` endpoints.

AgentMemory v0.9.27 does not apply the request ``project`` to ordinary memory
results.  A benchmark process must therefore start the server with a fresh,
isolated store and stop it after the run.  Unmapped result ids fail closed so a
contaminated store cannot silently produce a scoreable artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from benchmarks.external_memory_compare import (  # noqa: E402
    _canonical_retrieval_text,
    _provider_input_provenance,
    _validate_fixture_integrity,
    _validate_run_for_fixture,
    benchmark_source_manifest,
    fixture_digest,
)
from vault.search_qa import write_json  # noqa: E402


SYSTEM_ID = "rohitg00/agentmemory"
DEFAULT_VERSION = "0.9.27"


def run_agentmemory_comparison(
    *,
    fixture_path: str | Path,
    fresh_store_id: str,
    output_path: str | Path | None = None,
    base_url: str = "http://127.0.0.1:3911",
    api_key: str | None = None,
    run_id: str | None = None,
    limit: int = 10,
    search_scope: str = "global",
    provider_version: str = DEFAULT_VERSION,
    embedding_provider: str = "local",
    embedding_model: str = "Xenova/all-MiniLM-L6-v2",
    embedding_dims: int = 384,
    include_content: bool = False,
    transport: Any | None = None,
) -> dict[str, Any]:
    if search_scope != "global":
        raise ValueError(
            "AgentMemory v0.9.27 only supports global fixtures in this adapter; "
            "its smart-search project field does not filter ordinary memory results"
        )
    if limit <= 0:
        raise ValueError("limit must be positive")
    if not str(fresh_store_id or "").strip():
        raise ValueError("fresh_store_id is required")
    if embedding_dims <= 0:
        raise ValueError("embedding_dims must be positive")

    fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    _validate_fixture_integrity(fixture)
    actual_run_id = str(run_id or f"vault-benchmark-{time.time_ns()}")
    request = transport or _agentmemory_json_request
    api_key = api_key or os.environ.get("AGENTMEMORY_SECRET")
    memory_to_source: dict[str, str] = {}
    ingestion_records: list[dict[str, Any]] = []

    index_started = time.perf_counter()
    for document in fixture.get("documents", []):
        response = request(
            method="POST",
            url=f"{base_url.rstrip('/')}/agentmemory/remember",
            api_key=api_key,
            payload={
                "content": _canonical_retrieval_text(document),
                "type": "architecture",
                "concepts": _document_concepts(document),
                "project": actual_run_id,
            },
        )
        memory = response.get("memory") if isinstance(response, dict) else None
        memory = memory if isinstance(memory, dict) else {}
        memory_id = str(memory.get("id") or "")
        source = str(document.get("source") or "")
        if not memory_id:
            raise RuntimeError(f"AgentMemory remember response for {source} did not include memory.id")
        if memory_id in memory_to_source:
            raise RuntimeError(f"AgentMemory returned duplicate memory id: {memory_id}")
        memory_to_source[memory_id] = source
        ingestion_records.append(
            {
                "memory_id": memory_id,
                "source": source,
                "is_latest": memory.get("isLatest"),
                "supersedes": memory.get("supersedes") or [],
            }
        )
    index_latency_ms = round((time.perf_counter() - index_started) * 1000, 3)

    cases = [
        _search_case(
            request=request,
            base_url=base_url,
            api_key=api_key,
            case=case,
            run_id=actual_run_id,
            limit=limit,
            memory_to_source=memory_to_source,
            include_content=include_content,
        )
        for case in fixture.get("cases", [])
    ]
    payload = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_run",
        "generated_at": _utc_now(),
        "system": SYSTEM_ID,
        "system_version": provider_version,
        "benchmark": fixture.get("benchmark"),
        "fixture_digest": fixture.get("fixture_digest") or fixture_digest(fixture),
        "top_k": limit,
        "candidate_pool_k": limit,
        "retrieval_mode": "agentmemory:smart-search-hybrid",
        "track": "controlled_retrieval_raw_insert",
        "native_memory_features_exercised": False,
        "search_scope": "global",
        "run_id": actual_run_id,
        "documents_total": len(ingestion_records),
        "documents_attempted": len(fixture.get("documents", [])),
        "documents_indexed": len(ingestion_records),
        "documents_failed": len(fixture.get("documents", [])) - len(ingestion_records),
        "index_latency_ms": index_latency_ms,
        "cases_total": len(cases),
        "cases": cases,
        "manifest": {
            "benchmark_source": benchmark_source_manifest(__file__),
            "provider_input": _provider_input_provenance(fixture),
            "python_version": platform.python_version(),
            "os": platform.system(),
            "os_release": platform.release(),
            "machine": platform.machine(),
            "provider_config": {
                "repository": "rohitg00/agentmemory",
                "provider_version": provider_version,
                "embedding_provider": embedding_provider,
                "embedding_model": embedding_model,
                "embedding_dims": embedding_dims,
                "runtime_config_verified_by_adapter": False,
                "include_lessons": False,
                "project_filter_trusted": False,
                "retrieval_text_template": "title: {title}\\ncontent: {content}",
                "content_in_run_artifact": include_content,
            },
            "isolation": {
                "fresh_store_required": True,
                "fresh_store_id_digest": _opaque_id_digest(str(fresh_store_id)),
                "server_process_teardown_required_after_run": True,
                "server_process_teardown_verified": False,
                "unmapped_result_ids": 0,
            },
            "source_mapping": {
                "strategy": "remember memory.id -> fixture source; mapping wins over row.sessionId",
                "records": ingestion_records,
            },
        },
        "engineering": _engineering_profile(),
        "notes": [
            "This adapter targets rohitg00/agentmemory v0.9.27, not another package with the same name.",
            "Index and query wall time are measured separately.",
            "The provider project field is not treated as an isolation boundary for ordinary memory results.",
            "Every smart-search obsId must map to an id returned by this run's remember calls.",
            "Fresh-store identity is stored only as a digest; teardown requires separate execution evidence.",
        ],
    }
    _validate_run_for_fixture(fixture, payload)
    if output_path:
        write_json(output_path, payload)
    return payload


def _search_case(
    *,
    request: Any,
    base_url: str,
    api_key: str | None,
    case: dict[str, Any],
    run_id: str,
    limit: int,
    memory_to_source: dict[str, str],
    include_content: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    raw = request(
        method="POST",
        url=f"{base_url.rstrip('/')}/agentmemory/smart-search",
        api_key=api_key,
        payload={
            "query": str(case.get("query") or ""),
            "limit": limit,
            "project": run_id,
            "includeLessons": False,
        },
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    if not isinstance(raw, dict) or "results" not in raw:
        raise RuntimeError("AgentMemory smart-search response did not include results")
    rows = raw.get("results")
    if not isinstance(rows, list):
        raise RuntimeError("AgentMemory smart-search results must be a list")
    results: list[dict[str, Any]] = []
    for rank, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        memory_id = str(row.get("obsId") or row.get("id") or row.get("observationId") or "")
        source = memory_to_source.get(memory_id, "")
        if not source:
            raise RuntimeError(
                f"AgentMemory returned unmapped result id {memory_id or '<empty>'}; "
                "the server store may not be fresh"
            )
        result = {
            "rank": rank,
            "id": memory_id,
            "title": str(row.get("title") or ""),
            "source": source,
            "score": row.get("score"),
        }
        if include_content:
            detail = request(
                method="GET",
                url=f"{base_url.rstrip('/')}/agentmemory/memories/{memory_id}",
                api_key=api_key,
            )
            memory = detail.get("memory") if isinstance(detail, dict) else None
            memory = memory if isinstance(memory, dict) else {}
            result["content"] = str(memory.get("content") or "")
        results.append(result)
    return {
        "id": str(case.get("id") or ""),
        "query": str(case.get("query") or ""),
        "latency_ms": latency_ms,
        "results": results,
    }


def _document_concepts(document: dict[str, Any]) -> list[str]:
    concepts = [str(document.get("title") or "").strip()]
    raw_tags = document.get("tags")
    if isinstance(raw_tags, list):
        concepts.extend(str(tag).strip() for tag in raw_tags)
    else:
        concepts.extend(part.strip() for part in str(raw_tags or "").split(","))
    return [value for value in dict.fromkeys(concepts) if value]


def _agentmemory_json_request(
    *,
    method: str,
    url: str,
    api_key: str | None,
    payload: dict[str, Any] | None = None,
) -> Any:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"AgentMemory API request failed: {exc.code} {detail}") from exc
    return json.loads(body) if body else {}


def _engineering_profile() -> dict[str, Any]:
    return {
        "local_first": {
            "supported": True,
            "measured": True,
            "evidence": "The adapter targets a local REST server and records fresh-store isolation.",
        },
        "multi_agent_shared_memory": {
            "supported": True,
            "measured": False,
            "evidence": "Multi-agent sharing is outside this retrieval-only track.",
        },
        "sync": {"supported": False, "measured": False, "evidence": "Not exercised."},
        "report": {"supported": False, "measured": False, "evidence": "Not exercised."},
        "audit": {
            "supported": True,
            "measured": False,
            "evidence": "Source traceability is measured; audit lifecycle behavior is not.",
        },
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _opaque_id_digest(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run rohitg00/agentmemory against a neutral global fixture."
    )
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fresh-store-id", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:3911")
    parser.add_argument("--api-key")
    parser.add_argument("--run-id")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--search-scope", default="global", choices=["global", "case"])
    parser.add_argument("--provider-version", default=DEFAULT_VERSION)
    parser.add_argument("--embedding-provider", default="local")
    parser.add_argument("--embedding-model", default="Xenova/all-MiniLM-L6-v2")
    parser.add_argument("--embedding-dims", type=int, default=384)
    parser.add_argument("--include-content", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = run_agentmemory_comparison(
        fixture_path=args.fixture,
        fresh_store_id=args.fresh_store_id,
        output_path=args.output,
        base_url=args.base_url,
        api_key=args.api_key,
        run_id=args.run_id,
        limit=args.limit,
        search_scope=args.search_scope,
        provider_version=args.provider_version,
        embedding_provider=args.embedding_provider,
        embedding_model=args.embedding_model,
        embedding_dims=args.embedding_dims,
        include_content=args.include_content,
    )
    print(
        json.dumps(
            {
                "artifact_type": payload["artifact_type"],
                "system": payload["system"],
                "system_version": payload["system_version"],
                "benchmark": payload["benchmark"],
                "documents_total": payload["documents_total"],
                "cases_total": payload["cases_total"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
