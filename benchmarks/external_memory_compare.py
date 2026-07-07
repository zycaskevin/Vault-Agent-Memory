"""Comparison harness for external long-term memory systems.

The harness keeps benchmark fairness outside any one memory implementation:

1. Export a neutral fixture from LoCoMo or LongMemEval.
2. Ask each system adapter to return the same run-artifact schema.
3. Score retrieval evidence recall, final-answer fields, latency, and declared
   engineering capabilities with one shared scorer.

The final-answer scorer is intentionally lightweight and non-official. Official
LoCoMo / LongMemEval QA scores still require the benchmark-specific reader and
judge pipeline.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from benchmarks.external_memory_retrieval import (  # noqa: E402
    ExternalCase,
    ExternalDocument,
    _load_locomo,
    _load_longmemeval,
    _percentile,
    run_external_memory_retrieval,
)
from vault.search_qa import write_json  # noqa: E402


ENGINEERING_CAPABILITIES = (
    "local_first",
    "multi_agent_shared_memory",
    "sync",
    "report",
    "audit",
)


def export_fixture(
    *,
    benchmark: str,
    input_path: str | Path,
    output_path: str | Path | None = None,
    max_cases: int | None = None,
    granularity: str = "session",
) -> dict[str, Any]:
    documents, cases = _load_benchmark(
        benchmark=benchmark,
        input_path=input_path,
        max_cases=max_cases,
        granularity=granularity,
    )
    payload = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_fixture",
        "generated_at": _utc_now(),
        "benchmark": benchmark,
        "input_path": str(Path(input_path)),
        "granularity": granularity,
        "documents_total": len(documents),
        "cases_total": len(cases),
        "documents": [_document_to_payload(doc) for doc in documents],
        "cases": [_case_to_payload(case) for case in cases],
        "matching_rule": {
            "retrieval": "A case is a hit when any returned result.source exactly equals any expected_sources value.",
            "final_qa": "Non-official normalized exact/contains/token-F1 answer metrics.",
        },
    }
    if output_path:
        write_json(output_path, payload)
    return payload


def run_vault_comparison(
    *,
    benchmark: str,
    input_path: str | Path,
    output_path: str | Path | None = None,
    db_path: str | Path | None = None,
    max_cases: int | None = None,
    limit: int = 10,
    mode: str = "keyword",
    granularity: str = "session",
    search_scope: str = "case",
    reuse_db: bool = False,
    progress_every: int = 0,
) -> dict[str, Any]:
    report = run_external_memory_retrieval(
        benchmark=benchmark,
        input_path=input_path,
        db_path=db_path,
        max_cases=max_cases,
        limit=limit,
        mode=mode,
        granularity=granularity,
        search_scope=search_scope,
        reuse_db=reuse_db,
        progress_every=progress_every,
    )
    payload = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_run",
        "generated_at": _utc_now(),
        "system": "vault",
        "system_version": _vault_version(),
        "benchmark": benchmark,
        "top_k": limit,
        "retrieval_mode": mode,
        "granularity": granularity,
        "search_scope": search_scope,
        "documents_total": report.get("documents_indexed"),
        "index_latency_ms": report.get("index_latency_ms"),
        "cases_total": report["cases_total"],
        "cases": [
            {
                "id": case["id"],
                "query": case["query"],
                "latency_ms": case["latency_ms"],
                "results": case["results"],
            }
            for case in report["cases"]
        ],
        "engineering": _vault_engineering_profile(),
        "notes": [
            "Retrieval-only run artifact. It can be scored against an exported comparison fixture.",
            "No reader model was run, so final_qa metrics will be unavailable unless answers are added.",
        ],
    }
    if output_path:
        write_json(output_path, payload)
    return payload


def run_mem0_comparison(
    *,
    fixture_path: str | Path,
    output_path: str | Path | None = None,
    limit: int = 10,
    search_scope: str = "case",
    vector_store_path: str | Path = "/tmp/mem0-comparison-qdrant",
    collection_name: str = "external_memory_comparison",
    embedder: str = "fastembed",
    embedding_dims: int | None = None,
    llm_provider: str = "ollama",
    threshold: float = 0.0,
    memory_factory: Any | None = None,
) -> dict[str, Any]:
    if search_scope not in {"case", "global"}:
        raise ValueError(f"unsupported search scope: {search_scope}")
    fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    memory = memory_factory() if memory_factory else _create_mem0_memory(
        vector_store_path=vector_store_path,
        collection_name=collection_name,
        embedder=embedder,
        embedding_dims=embedding_dims,
        llm_provider=llm_provider,
    )
    try:
        index_start = time.perf_counter()
        _reset_memory(memory)
        _index_mem0_documents(memory, fixture.get("documents", []))
        index_latency_ms = round((time.perf_counter() - index_start) * 1000, 3)
        cases = [
            _search_mem0_case(
                memory=memory,
                case=case,
                limit=limit,
                search_scope=search_scope,
                threshold=threshold,
            )
            for case in fixture.get("cases", [])
        ]
    finally:
        close = getattr(memory, "close", None)
        if callable(close):
            close()
    payload = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_run",
        "generated_at": _utc_now(),
        "system": "mem0",
        "system_version": _module_version("mem0"),
        "benchmark": fixture.get("benchmark"),
        "top_k": limit,
        "retrieval_mode": f"mem0:{embedder}",
        "llm_provider": llm_provider,
        "search_scope": search_scope,
        "documents_total": len(fixture.get("documents", [])),
        "index_latency_ms": index_latency_ms,
        "cases_total": len(cases),
        "cases": cases,
        "engineering": _mem0_engineering_profile(),
        "notes": [
            "mem0 adapter run artifact. Score with score-run against the same fixture.",
            "Documents are inserted with infer=False so retrieval-only runs do not require an LLM extraction pass.",
        ],
    }
    if output_path:
        write_json(output_path, payload)
    return payload


def run_letta_comparison(
    *,
    fixture_path: str | Path,
    agent_id: str,
    output_path: str | Path | None = None,
    api_key: str | None = None,
    base_url: str = "https://api.letta.com",
    run_id: str | None = None,
    limit: int = 10,
    search_scope: str = "case",
    transport: Any | None = None,
) -> dict[str, Any]:
    if search_scope not in {"case", "global"}:
        raise ValueError(f"unsupported search scope: {search_scope}")
    fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    actual_run_id = run_id or f"external-memory-{int(time.time())}"
    api_key = api_key or os.environ.get("LETTA_API_KEY")
    request = transport or _letta_json_request
    index_start = time.perf_counter()
    for document in fixture.get("documents", []):
        _create_letta_passage(
            request=request,
            base_url=base_url,
            api_key=api_key,
            agent_id=agent_id,
            document=document,
            run_id=actual_run_id,
        )
    index_latency_ms = round((time.perf_counter() - index_start) * 1000, 3)
    cases = [
        _search_letta_case(
            request=request,
            base_url=base_url,
            api_key=api_key,
            agent_id=agent_id,
            case=case,
            run_id=actual_run_id,
            limit=limit,
            search_scope=search_scope,
        )
        for case in fixture.get("cases", [])
    ]
    payload = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_run",
        "generated_at": _utc_now(),
        "system": "letta",
        "system_version": "",
        "benchmark": fixture.get("benchmark"),
        "top_k": limit,
        "retrieval_mode": "letta:archival-memory",
        "search_scope": search_scope,
        "agent_id": agent_id,
        "run_id": actual_run_id,
        "documents_total": len(fixture.get("documents", [])),
        "index_latency_ms": index_latency_ms,
        "cases_total": len(cases),
        "cases": cases,
        "engineering": _letta_engineering_profile(),
        "notes": [
            "Letta adapter run artifact using archival-memory create/search endpoints.",
            "Documents are isolated with a generated run-id tag; this adapter does not delete existing Letta memory.",
        ],
    }
    if output_path:
        write_json(output_path, payload)
    return payload


def score_run(
    *,
    fixture_path: str | Path,
    run_path: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    run = json.loads(Path(run_path).read_text(encoding="utf-8"))
    fixture_cases = {str(case["id"]): case for case in fixture.get("cases", [])}
    run_cases = {str(case.get("id")): case for case in run.get("cases", [])}
    scored_cases: list[dict[str, Any]] = []
    answer_cases: list[dict[str, Any]] = []

    for case_id, fixture_case in fixture_cases.items():
        run_case = run_cases.get(case_id, {})
        retrieval = _score_retrieval_case(fixture_case, run_case)
        final_qa = _score_answer_case(fixture_case, run_case)
        payload = {
            "id": case_id,
            "retrieval": retrieval,
            "latency_ms": _coerce_float(run_case.get("latency_ms")),
        }
        if final_qa is not None:
            payload["final_qa"] = final_qa
            answer_cases.append(final_qa)
        scored_cases.append(payload)

    result = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_score",
        "generated_at": _utc_now(),
        "benchmark": fixture.get("benchmark"),
        "system": run.get("system", "unknown"),
        "system_version": run.get("system_version", ""),
        "top_k": run.get("top_k"),
        "cases_total": len(fixture_cases),
        "cases_scored": len(scored_cases),
        "retrieval": _aggregate_retrieval([case["retrieval"] for case in scored_cases]),
        "final_qa": _aggregate_final_qa(answer_cases),
        "index_latency": _run_level_latency(run.get("index_latency_ms"), run.get("documents_total")),
        "latency": _aggregate_latency([case["latency_ms"] for case in scored_cases]),
        "answer_latency": _aggregate_latency(
            [_coerce_float(run_cases.get(case_id, {}).get("answer_latency_ms")) for case_id in fixture_cases]
        ),
        "engineering": _score_engineering(run.get("engineering", {})),
        "cases": scored_cases,
        "notes": [
            "Retrieval metrics use exact source-id evidence matching.",
            "Final QA metrics are non-official normalized answer metrics and should not be reported as leaderboard scores.",
        ],
    }
    if output_path:
        write_json(output_path, result)
    return result


def answer_run(
    *,
    fixture_path: str | Path,
    run_path: str | Path,
    output_path: str | Path | None = None,
    llm_provider: str = "mock",
    llm_model: str | None = None,
    mock_response: str | None = None,
    max_cases: int | None = None,
    evidence_limit: int | None = None,
    max_tokens: int = 160,
    temperature: float = 0.0,
) -> dict[str, Any]:
    fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    run = json.loads(Path(run_path).read_text(encoding="utf-8"))
    documents_by_source = {
        str(document.get("source")): document for document in fixture.get("documents", [])
    }
    fixture_cases = {str(case["id"]): case for case in fixture.get("cases", [])}
    llm = _create_reader_provider(
        llm_provider=llm_provider,
        llm_model=llm_model,
        mock_response=mock_response,
    )

    answered_cases: list[dict[str, Any]] = []
    for index, run_case in enumerate(run.get("cases", []), start=1):
        if max_cases and index > max_cases:
            answered_cases.append(run_case)
            continue
        case_id = str(run_case.get("id"))
        prompt = _build_reader_prompt(
            fixture_case=fixture_cases.get(case_id, {}),
            run_case=run_case,
            documents_by_source=documents_by_source,
            evidence_limit=evidence_limit,
        )
        start = time.perf_counter()
        answer = llm.generate(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=(
                "Answer the question using only the provided evidence. "
                "If the evidence is insufficient, say you do not know."
            ),
        )
        updated = dict(run_case)
        updated["answer"] = answer
        updated["answer_latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
        answered_cases.append(updated)

    payload = dict(run)
    payload["generated_at"] = _utc_now()
    payload["cases"] = answered_cases
    payload["final_qa_reader"] = {
        "provider": llm_provider,
        "provider_name": llm.name,
        "model": llm_model or "",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "evidence_limit": evidence_limit,
        "answered_cases": min(len(run.get("cases", [])), max_cases or len(run.get("cases", []))),
    }
    payload["notes"] = list(payload.get("notes", [])) + [
        "Final answers were generated from the run artifact's retrieved evidence using a fixed reader prompt.",
    ]
    if output_path:
        write_json(output_path, payload)
    return payload


def _load_benchmark(
    *,
    benchmark: str,
    input_path: str | Path,
    max_cases: int | None,
    granularity: str,
) -> tuple[list[ExternalDocument], list[ExternalCase]]:
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if benchmark == "locomo":
        return _load_locomo(data, max_cases=max_cases)
    if benchmark == "longmemeval":
        return _load_longmemeval(data, max_cases=max_cases, granularity=granularity)
    raise ValueError(f"unsupported benchmark: {benchmark}")


def _document_to_payload(doc: ExternalDocument) -> dict[str, Any]:
    return {
        "title": doc.title,
        "content": doc.content,
        "source": doc.source,
        "category": doc.category,
        "tags": doc.tags,
    }


def _case_to_payload(case: ExternalCase) -> dict[str, Any]:
    return {
        "id": case.case_id,
        "query": case.query,
        "expected_sources": list(case.expected_sources),
        "expected_answer": str(case.metadata.get("answer") or ""),
        "search_category": case.category,
        "metadata": case.metadata,
    }


def _score_retrieval_case(fixture_case: dict[str, Any], run_case: dict[str, Any]) -> dict[str, Any]:
    expected = {str(source) for source in fixture_case.get("expected_sources", [])}
    ranked = run_case.get("results", [])
    hit_rank = None
    returned_sources: list[str] = []
    for index, result in enumerate(ranked, start=1):
        if not isinstance(result, dict):
            continue
        source = str(result.get("source") or "")
        returned_sources.append(source)
        if source in expected and hit_rank is None:
            hit_rank = index
    return {
        "expected_sources": sorted(expected),
        "returned_sources": returned_sources,
        "hit": hit_rank is not None,
        "hit_rank": hit_rank,
        "reciprocal_rank": 0.0 if hit_rank is None else round(1.0 / hit_rank, 6),
    }


def _score_answer_case(fixture_case: dict[str, Any], run_case: dict[str, Any]) -> dict[str, Any] | None:
    expected = str(fixture_case.get("expected_answer") or "")
    predicted = str(run_case.get("answer") or "")
    if not expected or not predicted:
        return None
    expected_norm = _normalize_answer(expected)
    predicted_norm = _normalize_answer(predicted)
    return {
        "expected_answer": expected,
        "predicted_answer": predicted,
        "normalized_exact_match": expected_norm == predicted_norm,
        "normalized_contains_expected": bool(expected_norm and expected_norm in predicted_norm),
        "token_f1": _token_f1(expected_norm, predicted_norm),
    }


def _aggregate_retrieval(items: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(items)
    hits = [item for item in items if item.get("hit")]
    ranks = [int(item["hit_rank"]) for item in hits if item.get("hit_rank")]
    return {
        "total_cases": total,
        "hit_cases": len(hits),
        "hit_rate": round(len(hits) / total, 6) if total else 0.0,
        "top1_hits": sum(1 for rank in ranks if rank == 1),
        "top3_hits": sum(1 for rank in ranks if rank <= 3),
        "top5_hits": sum(1 for rank in ranks if rank <= 5),
        "mean_reciprocal_rank": round(
            sum(float(item.get("reciprocal_rank", 0.0)) for item in items) / total,
            6,
        )
        if total
        else 0.0,
    }


def _aggregate_final_qa(items: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(items)
    if not total:
        return {
            "available": False,
            "answered_cases": 0,
            "normalized_exact_match_rate": None,
            "normalized_contains_expected_rate": None,
            "mean_token_f1": None,
        }
    return {
        "available": True,
        "answered_cases": total,
        "normalized_exact_match_rate": round(
            sum(1 for item in items if item.get("normalized_exact_match")) / total,
            6,
        ),
        "normalized_contains_expected_rate": round(
            sum(1 for item in items if item.get("normalized_contains_expected")) / total,
            6,
        ),
        "mean_token_f1": round(statistics.mean(float(item.get("token_f1", 0.0)) for item in items), 6),
    }


def _aggregate_latency(values: list[float | None]) -> dict[str, Any]:
    latencies = [value for value in values if value is not None]
    if not latencies:
        return {"available": False, "mean_ms": None, "p50_ms": None, "p95_ms": None, "max_ms": None}
    return {
        "available": True,
        "mean_ms": round(statistics.mean(latencies), 3),
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(_percentile(latencies, 0.95), 3),
        "max_ms": round(max(latencies), 3),
    }


def _run_level_latency(value: Any, item_count: Any = None) -> dict[str, Any]:
    latency = _coerce_float(value)
    count = int(item_count) if isinstance(item_count, int) else None
    if latency is None:
        return {"available": False, "total_ms": None, "per_item_ms": None, "item_count": count}
    per_item = round(latency / count, 6) if count else None
    return {
        "available": True,
        "total_ms": round(latency, 3),
        "per_item_ms": per_item,
        "item_count": count,
    }


def _score_engineering(engineering: dict[str, Any]) -> dict[str, Any]:
    capabilities: dict[str, Any] = {}
    supported = 0
    measured = 0
    for capability in ENGINEERING_CAPABILITIES:
        raw = engineering.get(capability, {})
        if isinstance(raw, bool):
            item = {"supported": raw, "measured": False, "evidence": ""}
        elif isinstance(raw, dict):
            item = {
                "supported": bool(raw.get("supported")),
                "measured": bool(raw.get("measured")),
                "evidence": str(raw.get("evidence") or ""),
            }
        else:
            item = {"supported": False, "measured": False, "evidence": ""}
        supported += 1 if item["supported"] else 0
        measured += 1 if item["measured"] else 0
        capabilities[capability] = item
    total = len(ENGINEERING_CAPABILITIES)
    return {
        "capabilities": capabilities,
        "supported_count": supported,
        "measured_count": measured,
        "supported_rate": round(supported / total, 6) if total else 0.0,
        "measured_rate": round(measured / total, 6) if total else 0.0,
    }


def _create_mem0_memory(
    *,
    vector_store_path: str | Path,
    collection_name: str,
    embedder: str,
    embedding_dims: int | None,
    llm_provider: str,
):
    try:
        from mem0 import Memory
    except ImportError as exc:
        raise RuntimeError(
            "mem0 adapter requires the optional mem0ai package. "
            "Install it in an isolated environment before running mem0-run."
        ) from exc

    dims = embedding_dims or (1536 if embedder == "openai" else 1024)
    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "path": str(vector_store_path),
                "collection_name": collection_name,
                "embedding_model_dims": dims,
            },
        },
        "embedder": {
            "provider": embedder,
            "config": {},
        },
        "llm": {
            "provider": llm_provider,
            "config": {},
        },
    }
    return Memory.from_config(config)


def _reset_memory(memory: Any) -> None:
    reset = getattr(memory, "reset", None)
    if callable(reset):
        reset()
        return
    delete_all = getattr(memory, "delete_all", None)
    if callable(delete_all):
        delete_all()


def _index_mem0_documents(memory: Any, documents: list[dict[str, Any]]) -> None:
    for document in documents:
        metadata = {
            "source": document.get("source", ""),
            "title": document.get("title", ""),
            "search_category": document.get("category", ""),
            "tags": document.get("tags", ""),
        }
        memory.add(
            str(document.get("content") or ""),
            user_id="external-memory-comparison",
            metadata=metadata,
            infer=False,
        )


def _search_mem0_case(
    *,
    memory: Any,
    case: dict[str, Any],
    limit: int,
    search_scope: str,
    threshold: float,
) -> dict[str, Any]:
    filters = {"user_id": "external-memory-comparison"}
    if search_scope == "case":
        filters["search_category"] = str(case.get("search_category") or "")
    start = time.perf_counter()
    raw = memory.search(
        str(case.get("query") or ""),
        top_k=limit,
        filters=filters,
        threshold=threshold,
        rerank=False,
    )
    latency_ms = round((time.perf_counter() - start) * 1000, 3)
    return {
        "id": case.get("id"),
        "query": case.get("query", ""),
        "latency_ms": latency_ms,
        "results": _normalize_mem0_results(raw),
    }


def _normalize_mem0_results(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        candidates = raw.get("results") or raw.get("memories") or []
    elif isinstance(raw, list):
        candidates = raw
    else:
        candidates = []
    results: list[dict[str, Any]] = []
    for index, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        source = str(item.get("source") or metadata.get("source") or "")
        title = str(item.get("title") or metadata.get("title") or "")
        content = str(item.get("memory") or item.get("content") or item.get("text") or "")
        results.append(
            {
                "rank": index,
                "id": item.get("id"),
                "title": title,
                "source": source,
                "score": item.get("score"),
                "content": content,
            }
        )
    return results


def _create_letta_passage(
    *,
    request: Any,
    base_url: str,
    api_key: str | None,
    agent_id: str,
    document: dict[str, Any],
    run_id: str,
) -> None:
    request(
        method="POST",
        url=f"{base_url.rstrip('/')}/v1/agents/{agent_id}/archival-memory",
        api_key=api_key,
        payload={
            "text": str(document.get("content") or ""),
            "tags": _letta_document_tags(document, run_id),
        },
    )


def _search_letta_case(
    *,
    request: Any,
    base_url: str,
    api_key: str | None,
    agent_id: str,
    case: dict[str, Any],
    run_id: str,
    limit: int,
    search_scope: str,
) -> dict[str, Any]:
    tags = [f"run:{run_id}"]
    if search_scope == "case":
        tags.append(f"category:{case.get('search_category', '')}")
    params = {
        "query": str(case.get("query") or ""),
        "top_k": limit,
        "tags": tags,
        "tag_match_mode": "all",
    }
    start = time.perf_counter()
    raw = request(
        method="GET",
        url=f"{base_url.rstrip('/')}/v1/agents/{agent_id}/archival-memory/search",
        api_key=api_key,
        params=params,
    )
    latency_ms = round((time.perf_counter() - start) * 1000, 3)
    return {
        "id": case.get("id"),
        "query": case.get("query", ""),
        "latency_ms": latency_ms,
        "results": _normalize_letta_results(raw),
    }


def _letta_document_tags(document: dict[str, Any], run_id: str) -> list[str]:
    tags = [
        f"run:{run_id}",
        f"source:{document.get('source', '')}",
        f"category:{document.get('category', '')}",
        "external-memory-comparison",
    ]
    raw_tags = str(document.get("tags") or "")
    tags.extend(f"tag:{tag.strip()}" for tag in raw_tags.split(",") if tag.strip())
    return tags


def _normalize_letta_results(raw: Any) -> list[dict[str, Any]]:
    candidates = raw.get("results", []) if isinstance(raw, dict) else []
    results: list[dict[str, Any]] = []
    for index, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            continue
        tags = item.get("tags") if isinstance(item.get("tags"), list) else []
        source = _source_from_tags(tags)
        results.append(
            {
                "rank": index,
                "id": item.get("id"),
                "title": "",
                "source": source,
                "score": item.get("score"),
                "content": str(item.get("content") or item.get("text") or ""),
            }
        )
    return results


def _source_from_tags(tags: list[Any]) -> str:
    for tag in tags:
        text = str(tag)
        if text.startswith("source:"):
            return text.removeprefix("source:")
    return ""


def _letta_json_request(
    *,
    method: str,
    url: str,
    api_key: str | None,
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> Any:
    if not api_key:
        raise RuntimeError("letta-run requires LETTA_API_KEY or --letta-api-key")
    if params:
        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{url}?{query}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Letta API request failed: {exc.code} {detail}") from exc
    return json.loads(body) if body else {}


def _create_reader_provider(
    *,
    llm_provider: str,
    llm_model: str | None,
    mock_response: str | None,
):
    from vault.llm import create_llm_provider

    kwargs: dict[str, Any] = {}
    if llm_provider == "mock" and mock_response is not None:
        kwargs["response"] = mock_response
    return create_llm_provider(llm_provider, model=llm_model, **kwargs)


def _build_reader_prompt(
    *,
    fixture_case: dict[str, Any],
    run_case: dict[str, Any],
    documents_by_source: dict[str, dict[str, Any]],
    evidence_limit: int | None,
) -> str:
    results = run_case.get("results", [])
    if evidence_limit is not None:
        results = results[:evidence_limit]
    evidence_blocks: list[str] = []
    for result in results:
        if not isinstance(result, dict):
            continue
        source = str(result.get("source") or "")
        document = documents_by_source.get(source, {})
        if not document:
            continue
        evidence_blocks.append(
            "\n".join(
                part
                for part in (
                    f"Source: {source}",
                    f"Title: {document.get('title', '')}",
                    str(document.get("content") or ""),
                )
                if part
            )
        )
    evidence_text = "\n\n---\n\n".join(evidence_blocks) if evidence_blocks else "(no evidence retrieved)"
    return "\n\n".join(
        [
            f"Question: {fixture_case.get('query') or run_case.get('query') or ''}",
            "Evidence:",
            evidence_text,
            "Answer in one concise sentence.",
        ]
    )


def _vault_engineering_profile() -> dict[str, Any]:
    return {
        "local_first": {
            "supported": True,
            "measured": True,
            "evidence": "Vault comparison run indexes and searches a local SQLite database.",
        },
        "multi_agent_shared_memory": {
            "supported": True,
            "measured": False,
            "evidence": "Vault supports shared-scope agent setup; run an install smoke to measure this end-to-end.",
        },
        "sync": {
            "supported": True,
            "measured": False,
            "evidence": "Vault includes Supabase sync surfaces; this retrieval run does not exercise remote sync.",
        },
        "report": {
            "supported": True,
            "measured": False,
            "evidence": "Vault includes daily-loop report surfaces; this retrieval run does not rebuild a daily report.",
        },
        "audit": {
            "supported": True,
            "measured": False,
            "evidence": "Vault stores source ids and review/audit metadata; this run measures evidence source ids.",
        },
    }


def _mem0_engineering_profile() -> dict[str, Any]:
    return {
        "local_first": {
            "supported": True,
            "measured": True,
            "evidence": "Adapter config uses a local Qdrant vector-store path by default.",
        },
        "multi_agent_shared_memory": {
            "supported": True,
            "measured": False,
            "evidence": "mem0 supports user/agent/run ids; shared multi-agent install wiring is not measured here.",
        },
        "sync": {
            "supported": False,
            "measured": False,
            "evidence": "No sync surface is exercised by this local adapter.",
        },
        "report": {
            "supported": False,
            "measured": False,
            "evidence": "No daily report surface is exercised by this local adapter.",
        },
        "audit": {
            "supported": True,
            "measured": True,
            "evidence": "Adapter preserves benchmark source ids in mem0 metadata and output results.",
        },
    }


def _letta_engineering_profile() -> dict[str, Any]:
    return {
        "local_first": {
            "supported": False,
            "measured": False,
            "evidence": "The adapter uses Letta HTTP archival-memory endpoints and does not measure local mode.",
        },
        "multi_agent_shared_memory": {
            "supported": True,
            "measured": False,
            "evidence": "Letta supports memory concepts and agents; this adapter scopes one agent archival memory run.",
        },
        "sync": {
            "supported": True,
            "measured": False,
            "evidence": "Remote Letta API persistence is used, but cross-agent sync is not measured.",
        },
        "report": {
            "supported": False,
            "measured": False,
            "evidence": "No daily report surface is exercised by this adapter.",
        },
        "audit": {
            "supported": True,
            "measured": True,
            "evidence": "Adapter preserves benchmark source ids as passage tags and output result sources.",
        },
    }


def _normalize_answer(value: str) -> str:
    normalized = value.lower()
    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", normalized)
    return " ".join(normalized.split())


def _token_f1(expected: str, predicted: str) -> float:
    expected_tokens = expected.split()
    predicted_tokens = predicted.split()
    if not expected_tokens and not predicted_tokens:
        return 1.0
    if not expected_tokens or not predicted_tokens:
        return 0.0
    common = Counter(expected_tokens) & Counter(predicted_tokens)
    overlap = sum(common.values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(predicted_tokens)
    recall = overlap / len(expected_tokens)
    return round(2 * precision * recall / (precision + recall), 6)


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _vault_version() -> str:
    try:
        import vault

        return str(getattr(vault, "__version__", ""))
    except Exception:
        return ""


def _module_version(module_name: str) -> str:
    try:
        from importlib import metadata

        return metadata.version(module_name)
    except Exception:
        return ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run fair comparison scoring for external memory systems.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fixture = subparsers.add_parser("export-fixture", help="Export a neutral benchmark fixture.")
    fixture.add_argument("--benchmark", choices=["locomo", "longmemeval"], required=True)
    fixture.add_argument("--input", required=True)
    fixture.add_argument("--output", required=True)
    fixture.add_argument("--max-cases", type=int)
    fixture.add_argument("--granularity", default="session", choices=["session", "turn"])

    vault_run = subparsers.add_parser("vault-run", help="Run Vault and emit a comparison run artifact.")
    vault_run.add_argument("--benchmark", choices=["locomo", "longmemeval"], required=True)
    vault_run.add_argument("--input", required=True)
    vault_run.add_argument("--output", required=True)
    vault_run.add_argument("--db-path")
    vault_run.add_argument("--max-cases", type=int)
    vault_run.add_argument("--limit", type=int, default=10)
    vault_run.add_argument("--mode", default="keyword", choices=["keyword", "semantic", "hybrid"])
    vault_run.add_argument("--granularity", default="session", choices=["session", "turn"])
    vault_run.add_argument("--search-scope", default="case", choices=["case", "global"])
    vault_run.add_argument("--reuse-db", action="store_true")
    vault_run.add_argument("--progress-every", type=int, default=0)

    mem0_run = subparsers.add_parser("mem0-run", help="Run mem0 and emit a comparison run artifact.")
    mem0_run.add_argument("--fixture", required=True)
    mem0_run.add_argument("--output", required=True)
    mem0_run.add_argument("--limit", type=int, default=10)
    mem0_run.add_argument("--search-scope", default="case", choices=["case", "global"])
    mem0_run.add_argument("--vector-store-path", default="/tmp/mem0-comparison-qdrant")
    mem0_run.add_argument("--collection-name", default="external_memory_comparison")
    mem0_run.add_argument("--embedder", default="fastembed", choices=["fastembed", "openai", "ollama"])
    mem0_run.add_argument("--embedding-dims", type=int)
    mem0_run.add_argument("--llm-provider", default="ollama", choices=["ollama", "openai", "anthropic"])
    mem0_run.add_argument("--threshold", type=float, default=0.0)

    letta_run = subparsers.add_parser("letta-run", help="Run Letta archival memory and emit a comparison artifact.")
    letta_run.add_argument("--fixture", required=True)
    letta_run.add_argument("--output", required=True)
    letta_run.add_argument("--agent-id", required=True)
    letta_run.add_argument("--letta-api-key")
    letta_run.add_argument("--base-url", default="https://api.letta.com")
    letta_run.add_argument("--run-id")
    letta_run.add_argument("--limit", type=int, default=10)
    letta_run.add_argument("--search-scope", default="case", choices=["case", "global"])

    score = subparsers.add_parser("score-run", help="Score a comparison run artifact against a fixture.")
    score.add_argument("--fixture", required=True)
    score.add_argument("--run", required=True)
    score.add_argument("--output", required=True)

    answer = subparsers.add_parser("answer-run", help="Generate final answers from a retrieval run artifact.")
    answer.add_argument("--fixture", required=True)
    answer.add_argument("--run", required=True)
    answer.add_argument("--output", required=True)
    answer.add_argument("--llm-provider", default="mock", choices=["auto", "ollama", "claude", "openai", "mock"])
    answer.add_argument("--llm-model")
    answer.add_argument("--mock-response")
    answer.add_argument("--max-cases", type=int)
    answer.add_argument("--evidence-limit", type=int)
    answer.add_argument("--max-tokens", type=int, default=160)
    answer.add_argument("--temperature", type=float, default=0.0)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "export-fixture":
        payload = export_fixture(
            benchmark=args.benchmark,
            input_path=args.input,
            output_path=args.output,
            max_cases=args.max_cases,
            granularity=args.granularity,
        )
    elif args.command == "vault-run":
        payload = run_vault_comparison(
            benchmark=args.benchmark,
            input_path=args.input,
            output_path=args.output,
            db_path=args.db_path,
            max_cases=args.max_cases,
            limit=args.limit,
            mode=args.mode,
            granularity=args.granularity,
            search_scope=args.search_scope,
            reuse_db=args.reuse_db,
            progress_every=args.progress_every,
        )
    elif args.command == "mem0-run":
        payload = run_mem0_comparison(
            fixture_path=args.fixture,
            output_path=args.output,
            limit=args.limit,
            search_scope=args.search_scope,
            vector_store_path=args.vector_store_path,
            collection_name=args.collection_name,
            embedder=args.embedder,
            embedding_dims=args.embedding_dims,
            llm_provider=args.llm_provider,
            threshold=args.threshold,
        )
    elif args.command == "letta-run":
        payload = run_letta_comparison(
            fixture_path=args.fixture,
            agent_id=args.agent_id,
            output_path=args.output,
            api_key=args.letta_api_key,
            base_url=args.base_url,
            run_id=args.run_id,
            limit=args.limit,
            search_scope=args.search_scope,
        )
    elif args.command == "score-run":
        payload = score_run(fixture_path=args.fixture, run_path=args.run, output_path=args.output)
    elif args.command == "answer-run":
        payload = answer_run(
            fixture_path=args.fixture,
            run_path=args.run,
            output_path=args.output,
            llm_provider=args.llm_provider,
            llm_model=args.llm_model,
            mock_response=args.mock_response,
            max_cases=args.max_cases,
            evidence_limit=args.evidence_limit,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
    else:
        raise ValueError(f"unsupported command: {args.command}")
    print(json.dumps(_summary(payload), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("artifact_type") == "external_memory_comparison_score":
        return {
            "artifact_type": payload["artifact_type"],
            "system": payload["system"],
            "benchmark": payload["benchmark"],
            "retrieval": payload["retrieval"],
            "final_qa": payload["final_qa"],
            "index_latency": payload["index_latency"],
            "latency": payload["latency"],
            "answer_latency": payload["answer_latency"],
            "engineering": {
                "supported_count": payload["engineering"]["supported_count"],
                "measured_count": payload["engineering"]["measured_count"],
            },
        }
    return {
        "artifact_type": payload.get("artifact_type"),
        "benchmark": payload.get("benchmark"),
        "cases_total": payload.get("cases_total"),
        "documents_total": payload.get("documents_total"),
        "system": payload.get("system"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
