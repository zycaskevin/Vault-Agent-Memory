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
import hashlib
import json
import math
import os
import platform
import re
import statistics
import subprocess
import sys
import tempfile
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

PROVIDER_GOVERNANCE_FIELDS = (
    "approval_state",
    "status",
    "scope",
    "sensitivity",
    "owner_agent",
    "allowed_agents",
    "memory_type",
    "expires_at",
    "valid_from",
    "valid_until",
    "privacy_status",
    "supersedes_id",
)
PROVIDER_DOCUMENT_FIELDS = (
    "id",
    "source",
    "source_ref",
    "title",
    "content",
    "category",
    "tags",
    "layer",
    "trust",
    *PROVIDER_GOVERNANCE_FIELDS,
)
PROVIDER_CASE_FIELDS = (
    "id",
    "query",
    "search_category",
    "agent_id",
    "include_private",
    "max_sensitivity",
    "as_of",
)


def benchmark_source_manifest(adapter_path: str | Path) -> dict[str, Any]:
    """Capture the benchmark source state at provider-run creation time."""
    git_sha = ""
    git_dirty: bool | None = None
    try:
        git_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        git_dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        pass
    adapter = Path(adapter_path)
    lock_path = REPO_ROOT / "uv.lock"
    return {
        "git_sha": git_sha,
        "git_dirty": git_dirty,
        "adapter_file": adapter.name,
        "adapter_digest": _file_digest(adapter) if adapter.exists() else "",
        "dependency_lock_digest": _file_digest(lock_path) if lock_path.exists() else "",
    }


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
        "input_file_name": Path(input_path).name,
        "input_file_digest": _file_digest(Path(input_path)),
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
    payload["fixture_digest"] = fixture_digest(payload)
    if output_path:
        write_json(output_path, payload)
    return payload


def export_provider_input(
    *,
    fixture_path: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Create an adapter input that excludes scorer gold labels and answers."""
    fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    _validate_fixture_integrity(fixture)
    evaluation_digest = str(fixture.get("fixture_digest") or fixture_digest(fixture))
    payload = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_fixture",
        "generated_at": _utc_now(),
        "benchmark": fixture.get("benchmark"),
        "fixture_version": fixture.get("fixture_version"),
        "fixed_clock": fixture.get("fixed_clock"),
        "granularity": fixture.get("granularity"),
        "provider_input": True,
        "gold_labels_excluded": True,
        "fixture_digest": evaluation_digest,
        "documents": [_provider_document(document) for document in fixture.get("documents", [])],
        "cases": [
            {field: case[field] for field in PROVIDER_CASE_FIELDS if field in case}
            for case in fixture.get("cases", [])
        ],
        "documents_total": len(fixture.get("documents", [])),
        "cases_total": len(fixture.get("cases", [])),
        "notes": [
            "Provider-process input only; expected answers, expected sources, forbidden sources, and scorer metadata are excluded.",
            "fixture_digest identifies the separate gold evaluation fixture; provider_input_digest identifies this redacted file.",
        ],
    }
    payload["provider_input_digest"] = fixture_digest(payload)
    _validate_fixture_integrity(payload)
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
    semantic_vector_kind: str = "node",
    embed_provider: str = "",
    embed_model: str = "mix",
    allow_hash: bool = False,
    hash_dim: int = 32,
) -> dict[str, Any]:
    fixture = export_fixture(
        benchmark=benchmark,
        input_path=input_path,
        max_cases=max_cases,
        granularity=granularity,
    )
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
        semantic_vector_kind=semantic_vector_kind,
        embed_provider=embed_provider,
        embed_model=embed_model,
        allow_hash=allow_hash,
        hash_dim=hash_dim,
    )
    payload = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_run",
        "generated_at": _utc_now(),
        "system": "vault",
        "system_version": _vault_version(),
        "benchmark": benchmark,
        "fixture_digest": fixture["fixture_digest"],
        "top_k": limit,
        "candidate_pool_k": limit,
        "retrieval_mode": mode,
        "granularity": granularity,
        "search_scope": search_scope,
        "semantic_vector_kind": semantic_vector_kind,
        "embed_provider": embed_provider or None,
        "embed_model": embed_model if embed_provider else None,
        "allow_hash": bool(allow_hash),
        "hash_dim": int(hash_dim) if allow_hash else None,
        "documents_total": report.get("documents_indexed"),
        "index_latency_ms": report.get("index_latency_ms"),
        "storage_index_latency_ms": report.get("storage_index_latency_ms"),
        "semantic_index_latency_ms": report.get("semantic_index_latency_ms"),
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
    _validate_run_for_fixture(fixture, payload)
    if output_path:
        write_json(output_path, payload)
    return payload


def run_vault_mode_comparison(
    *,
    benchmark: str,
    input_path: str | Path,
    output_path: str | Path | None = None,
    db_path: str | Path | None = None,
    max_cases: int | None = None,
    limit: int = 10,
    modes: list[str] | tuple[str, ...] | str = ("keyword", "hybrid", "semantic"),
    granularity: str = "session",
    search_scope: str = "case",
    reuse_db: bool = False,
    progress_every: int = 0,
    semantic_vector_kind: str = "node",
    embed_provider: str = "",
    embed_model: str = "mix",
    allow_hash: bool = False,
    hash_dim: int = 32,
) -> dict[str, Any]:
    mode_order = _normalize_retrieval_modes(modes)
    generated_at = _utc_now()
    with tempfile.TemporaryDirectory(prefix="vault-mode-compare-") as tmp:
        tmp_dir = Path(tmp)
        fixture_path = tmp_dir / "fixture.json"
        fixture = export_fixture(
            benchmark=benchmark,
            input_path=input_path,
            output_path=fixture_path,
            max_cases=max_cases,
            granularity=granularity,
        )
        shared_db = Path(db_path) if db_path else tmp_dir / "vault-mode-comparison.db"
        runs: dict[str, dict[str, Any]] = {}
        scores: dict[str, dict[str, Any]] = {}
        for index, mode in enumerate(mode_order):
            run_path = tmp_dir / f"vault-{mode}-run.json"
            score_path = tmp_dir / f"vault-{mode}-score.json"
            run = run_vault_comparison(
                benchmark=benchmark,
                input_path=input_path,
                output_path=run_path,
                db_path=shared_db,
                max_cases=max_cases,
                limit=limit,
                mode=mode,
                granularity=granularity,
                search_scope=search_scope,
                reuse_db=bool(reuse_db or index > 0),
                progress_every=progress_every,
                semantic_vector_kind=semantic_vector_kind,
                embed_provider=embed_provider,
                embed_model=embed_model,
                allow_hash=allow_hash,
                hash_dim=hash_dim,
            )
            score = score_run(fixture_path=fixture_path, run_path=run_path, output_path=score_path)
            runs[mode] = run
            scores[mode] = score
    baseline_mode = mode_order[0]
    payload = {
        "schema_version": 1,
        "artifact_type": "external_memory_vault_mode_comparison",
        "generated_at": generated_at,
        "system": "vault",
        "system_version": _vault_version(),
        "benchmark": benchmark,
        "fixture_digest": fixture["fixture_digest"],
        "input_file_name": Path(input_path).name,
        "input_file_digest": _file_digest(Path(input_path)),
        "top_k": limit,
        "mode_order": mode_order,
        "baseline_mode": baseline_mode,
        "granularity": granularity,
        "search_scope": search_scope,
        "semantic_vector_kind": semantic_vector_kind,
        "embed_provider": embed_provider or None,
        "embed_model": embed_model if embed_provider else None,
        "allow_hash": bool(allow_hash),
        "hash_dim": int(hash_dim) if allow_hash else None,
        "documents_total": fixture.get("documents_total"),
        "cases_total": fixture.get("cases_total"),
        "aggregate_by_mode": {
            mode: _external_mode_score_summary(score)
            for mode, score in scores.items()
        },
        "comparisons_vs_baseline": _compare_external_mode_scores(
            scores_by_mode=scores,
            baseline_mode=baseline_mode,
        ),
        "runs_by_mode": runs,
        "scores_by_mode": scores,
        "notes": [
            "Retrieval-only evidence matching; this is not final-answer QA or an official leaderboard score.",
            "All modes use the same benchmark data, top-k, search scope, and exact source-id scorer.",
            "Deterministic hash embeddings are plumbing test doubles when allow_hash is true.",
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
    vector_store_path: str | Path | None = None,
    collection_name: str = "",
    run_namespace: str = "",
    embedder: str = "fastembed",
    embed_model: str = "",
    embedding_dims: int | None = None,
    llm_provider: str = "ollama",
    threshold: float = 0.0,
    history_db_path: str | Path | None = None,
    model_cache_path: str | Path | None = None,
    enable_telemetry: bool = False,
    require_native_retrieval_assets: bool = True,
    include_content: bool = False,
    memory_factory: Any | None = None,
) -> dict[str, Any]:
    if search_scope not in {"case", "global"}:
        raise ValueError(f"unsupported search scope: {search_scope}")
    if limit <= 0:
        raise ValueError("limit must be positive")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    _validate_fixture_integrity(fixture)
    if search_scope == "case":
        _validate_case_search_scope(fixture)
    fixture_hash = (fixture.get("fixture_digest") or fixture_digest(fixture)).removeprefix("sha256:")
    actual_run_namespace = str(run_namespace or "").strip() or (
        f"external-memory-{fixture_hash[:12]}-{time.time_ns()}"
    )
    actual_collection_name = str(collection_name or "").strip() or actual_run_namespace.replace("-", "_")
    actual_embed_model = str(embed_model or "").strip() or _default_mem0_embed_model(embedder)
    actual_embedding_dims = _mem0_embedding_dims(
        embedder=embedder,
        embed_model=actual_embed_model,
        embedding_dims=embedding_dims,
    )
    vector_path = (
        Path(vector_store_path)
        if vector_store_path
        else Path(tempfile.gettempdir()) / f"{actual_collection_name}.qdrant"
    )
    actual_history_db_path = Path(history_db_path) if history_db_path else (
        vector_path.parent / f"{actual_collection_name}.history.sqlite3"
    )
    actual_mem0_dir = vector_path.parent / f".{actual_collection_name}.mem0"
    actual_model_cache_path = Path(
        model_cache_path
        or os.environ.get("FASTEMBED_CACHE_PATH")
        or (Path(tempfile.gettempdir()) / "fastembed_cache")
    )
    clean_state_paths = (vector_path, actual_history_db_path, actual_mem0_dir)
    if memory_factory is None:
        existing_paths = [path.name for path in clean_state_paths if path.exists()]
        if existing_paths:
            raise RuntimeError(
                "mem0 clean-state run requires new vector, history, and MEM0_DIR paths; "
                f"already present: {', '.join(sorted(existing_paths))}"
            )
    model_revisions_before = _fastembed_cache_revisions(actual_model_cache_path)
    previous_env: dict[str, str | None] = {}
    memory = None
    cleanup_succeeded = False
    index_start = time.perf_counter()
    try:
        if memory_factory is None:
            if "mem0" in sys.modules:
                raise RuntimeError(
                    "mem0-run requires a fresh process so MEM0_DIR and telemetry settings "
                    "take effect before mem0 is imported"
                )
            previous_env = _set_process_env(
                {
                    "MEM0_DIR": str(actual_mem0_dir),
                    "MEM0_TELEMETRY": "true" if enable_telemetry else "false",
                    "FASTEMBED_CACHE_PATH": str(actual_model_cache_path),
                }
            )
            memory = _create_mem0_memory(
                vector_store_path=vector_path,
                collection_name=actual_collection_name,
                embedder=embedder,
                embed_model=actual_embed_model,
                embedding_dims=actual_embedding_dims,
                llm_provider=llm_provider,
                history_db_path=actual_history_db_path,
            )
        else:
            memory = memory_factory()
        effective_retrieval = _mem0_retrieval_preflight(
            memory,
            expected_embedding_dims=actual_embedding_dims,
            limit=limit,
            require_native_assets=require_native_retrieval_assets and memory_factory is None,
            test_double=memory_factory is not None,
        )
        setup_latency_ms = round((time.perf_counter() - index_start) * 1000, 3)
        ingest_start = time.perf_counter()
        indexing = _index_mem0_documents(
            memory,
            fixture.get("documents", []),
            run_namespace=actual_run_namespace,
            require_provider_confirmation=memory_factory is None,
        )
        ingest_latency_ms = round((time.perf_counter() - ingest_start) * 1000, 3)
        index_latency_ms = round((time.perf_counter() - index_start) * 1000, 3)
        cases = [
            _search_mem0_case(
                memory=memory,
                case=case,
                limit=limit,
                search_scope=search_scope,
                threshold=threshold,
                run_namespace=actual_run_namespace,
                include_content=include_content,
            )
            for case in fixture.get("cases", [])
        ]
    finally:
        if memory is not None:
            _close_mem0_memory(memory)
            cleanup_succeeded = True
        if previous_env:
            _restore_process_env(previous_env)
    model_revisions_after = _fastembed_cache_revisions(actual_model_cache_path)
    payload = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_run",
        "generated_at": _utc_now(),
        "system": "mem0",
        "system_version": _module_version("mem0") or _module_version("mem0ai"),
        "benchmark": fixture.get("benchmark"),
        "fixture_digest": fixture.get("fixture_digest") or fixture_digest(fixture),
        "top_k": limit,
        "candidate_pool_k": limit,
        "retrieval_mode": effective_retrieval["effective_retrieval_mode"],
        "track": "controlled_retrieval_raw_insert",
        "native_memory_features_exercised": False,
        "embed_model": actual_embed_model,
        "embedding_dims": actual_embedding_dims,
        "llm_provider": llm_provider,
        "collection_name": actual_collection_name,
        "run_namespace": actual_run_namespace,
        "search_scope": search_scope,
        "documents_total": indexing["attempted"],
        "documents_attempted": indexing["attempted"],
        "documents_indexed": indexing["indexed"],
        "documents_failed": indexing["failed"],
        "index_latency_ms": index_latency_ms,
        "setup_latency_ms": setup_latency_ms,
        "ingest_latency_ms": ingest_latency_ms,
        "cases_total": len(cases),
        "cases": cases,
        "manifest": {
            "benchmark_source": benchmark_source_manifest(__file__),
            "provider_input": _provider_input_provenance(fixture),
            "python_version": platform.python_version(),
            "os": platform.system(),
            "os_release": platform.release(),
            "machine": platform.machine(),
            "provider_dependencies": {
                "mem0ai": _module_version("mem0ai") or None,
                "fastembed": _module_version("fastembed") or None,
                "qdrant-client": _module_version("qdrant-client") or None,
                "ollama": _module_version("ollama") or None,
                "onnxruntime": _module_version("onnxruntime") or None,
                "spacy": _module_version("spacy") or None,
                "en-core-web-sm": _module_version("en-core-web-sm") or None,
            },
            "provider_config": {
                "embedder": embedder,
                "embed_model": actual_embed_model,
                "embedding_dims": actual_embedding_dims,
                "vector_store": "qdrant-local",
                "llm_provider": llm_provider,
                "llm_used_for_ingestion": False,
                "infer": False,
                "telemetry_enabled": enable_telemetry,
                "history_db_isolated": memory_factory is None,
                "mem0_dir_isolated": memory_factory is None,
                "index_latency_includes_initialization": True,
                "retrieval_text_template": "title: {title}\\ncontent: {content}",
                "content_in_run_artifact": include_content,
                "require_native_retrieval_assets": require_native_retrieval_assets,
            },
            "isolation": {
                "clean_state_paths_checked_before_run": memory_factory is None,
                "clean_state_paths_absent_before_run": memory_factory is None,
                "vector_store_identity_digest": _opaque_value_digest(str(vector_path)),
                "history_db_identity_digest": _opaque_value_digest(
                    str(actual_history_db_path)
                ),
                "mem0_dir_identity_digest": _opaque_value_digest(str(actual_mem0_dir)),
                "collection_name": actual_collection_name,
                "run_namespace": actual_run_namespace,
                "provider_handles_closed": cleanup_succeeded,
            },
            "effective_retrieval": effective_retrieval,
            "model_cache": {
                "state_before_run": "warm" if model_revisions_before else "cold_or_empty",
                "revisions_before_run": model_revisions_before,
                "revisions_after_run": model_revisions_after,
            },
        },
        "engineering": _mem0_engineering_profile(),
        "notes": [
            "mem0 adapter run artifact. Score with score-run against the same fixture.",
            "Documents are inserted with infer=False so retrieval-only runs do not require an LLM extraction pass.",
            "This controlled raw-insert track does not measure mem0 extraction, consolidation, deduplication, or lifecycle decisions.",
            "Each run uses an isolated namespace and does not reset or delete an existing collection.",
            "Index latency includes embedder/vector-store initialization, model loading, and document ingestion.",
            "The default benchmark path isolates MEM0_DIR and the history SQLite database; telemetry is disabled unless explicitly enabled.",
            "Publish runs fail closed when mem0 native Qdrant BM25 or spaCy retrieval assets are unavailable.",
        ],
    }
    _validate_run_for_fixture(fixture, payload)
    if output_path:
        write_json(output_path, payload)
    return payload


def run_letta_comparison(
    *,
    fixture_path: str | Path,
    output_path: str | Path | None = None,
    api_key: str | None = None,
    base_url: str = "https://api.letta.com",
    run_id: str | None = None,
    embedding: str = "ollama/bge-m3:latest",
    server_version: str = "",
    limit: int = 10,
    search_scope: str = "case",
    include_content: bool = False,
    transport: Any | None = None,
) -> dict[str, Any]:
    if search_scope not in {"case", "global"}:
        raise ValueError(f"unsupported search scope: {search_scope}")
    if limit <= 0 or limit > 100:
        raise ValueError("Letta limit must be between 1 and 100")
    fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    _validate_fixture_integrity(fixture)
    if search_scope == "case":
        _validate_case_search_scope(fixture)
    actual_run_id = run_id or f"external-memory-{time.time_ns()}"
    api_key = api_key or os.environ.get("LETTA_API_KEY")
    request = transport or _letta_json_request
    archive_id = ""
    cleanup_succeeded = False
    cleanup_error = ""
    primary_error: Exception | None = None
    index_start = time.perf_counter()
    try:
        archive = request(
            method="POST",
            url=f"{base_url.rstrip('/')}/v1/archives/",
            api_key=api_key,
            payload={"name": actual_run_id, "embedding": embedding},
        )
        archive_id = str(archive.get("id") or "") if isinstance(archive, dict) else ""
        if not archive_id:
            raise RuntimeError("Letta archive create response did not include an id")
        indexed = 0
        for document in fixture.get("documents", []):
            passage = _create_letta_passage(
                request=request,
                base_url=base_url,
                api_key=api_key,
                archive_id=archive_id,
                document=document,
                run_id=actual_run_id,
            )
            if not str(passage.get("id") or ""):
                raise RuntimeError("Letta passage create response did not include an id")
            indexed += 1
        index_latency_ms = round((time.perf_counter() - index_start) * 1000, 3)
        cases = [
            _search_letta_case(
                request=request,
                base_url=base_url,
                api_key=api_key,
                archive_id=archive_id,
                case=case,
                run_id=actual_run_id,
                limit=limit,
                search_scope=search_scope,
                include_content=include_content,
            )
            for case in fixture.get("cases", [])
        ]
    except Exception as exc:
        primary_error = exc
    finally:
        if archive_id:
            try:
                request(
                    method="DELETE",
                    url=f"{base_url.rstrip('/')}/v1/archives/{archive_id}",
                    api_key=api_key,
                )
                cleanup_succeeded = True
            except Exception as exc:
                cleanup_error = f"{type(exc).__name__}: {exc}"
    if primary_error is not None:
        if cleanup_error:
            raise RuntimeError(
                f"Letta run failed ({type(primary_error).__name__}: {primary_error}); "
                f"archive cleanup also failed ({cleanup_error})"
            ) from primary_error
        raise primary_error
    if not cleanup_succeeded:
        raise RuntimeError(f"Letta archive cleanup failed: {cleanup_error or 'unknown error'}")
    payload = {
        "schema_version": 1,
        "artifact_type": "external_memory_comparison_run",
        "generated_at": _utc_now(),
        "system": "letta",
        "system_version": server_version,
        "benchmark": fixture.get("benchmark"),
        "fixture_digest": fixture.get("fixture_digest") or fixture_digest(fixture),
        "top_k": limit,
        "candidate_pool_k": limit,
        "retrieval_mode": "letta:archive-passages",
        "track": "controlled_retrieval_raw_insert",
        "native_memory_features_exercised": False,
        "search_scope": search_scope,
        "archive_id": archive_id,
        "run_id": actual_run_id,
        "embedding": embedding,
        "documents_total": indexed,
        "documents_attempted": len(fixture.get("documents", [])),
        "documents_indexed": indexed,
        "documents_failed": len(fixture.get("documents", [])) - indexed,
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
            "provider_dependencies": {
                "letta-client": _module_version("letta-client") or None,
            },
            "provider_config": {
                "base_url_kind": "cloud" if base_url.rstrip("/") == "https://api.letta.com" else "self-hosted",
                "embedding": embedding,
                "runtime_config_verified_by_adapter": False,
                "llm_used": False,
                "retrieval_text_template": "title: {title}\\ncontent: {content}",
                "content_in_run_artifact": include_content,
            },
            "cleanup": {
                "resource": "run-scoped archive",
                "attempted": True,
                "succeeded": cleanup_succeeded,
                "error": cleanup_error or None,
            },
        },
        "engineering": _letta_engineering_profile(),
        "notes": [
            "Letta retrieval-only adapter using a run-scoped Archive and Passages API.",
            "The archive was deleted after retrieval so clean-state repeats do not require a pre-existing agent or LLM.",
            "This controlled raw-insert track does not measure Letta agent memory extraction or agent behavior.",
        ],
    }
    _validate_run_for_fixture(fixture, payload)
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
    _validate_run_for_fixture(fixture, run)
    fixture_cases = {str(case["id"]): case for case in fixture.get("cases", [])}
    run_cases = {str(case.get("id")): case for case in run.get("cases", [])}
    scored_cases: list[dict[str, Any]] = []
    answer_cases: list[dict[str, Any]] = []

    for case_id, fixture_case in fixture_cases.items():
        run_case = run_cases.get(case_id, {})
        retrieval = _score_retrieval_case(
            fixture_case,
            run_case,
            top_k=int(run.get("top_k") or 0),
        )
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
        "fixture_digest": fixture.get("fixture_digest") or fixture_digest(fixture),
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


def _score_retrieval_case(
    fixture_case: dict[str, Any],
    run_case: dict[str, Any],
    *,
    top_k: int,
) -> dict[str, Any]:
    expected = {str(source) for source in fixture_case.get("expected_sources", [])}
    ranked = run_case.get("results", [])[:top_k]
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
    if not expected:
        return None
    expected_norm = _normalize_answer(expected)
    predicted_norm = _normalize_answer(predicted)
    return {
        "expected_answer": expected,
        "predicted_answer": predicted,
        "answered": bool(predicted.strip()),
        "normalized_exact_match": bool(predicted_norm and expected_norm == predicted_norm),
        "normalized_contains_expected": bool(
            predicted_norm and expected_norm and expected_norm in predicted_norm
        ),
        "token_f1": _token_f1(expected_norm, predicted_norm) if predicted_norm else 0.0,
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
            "eligible_cases": 0,
            "answered_cases": 0,
            "unanswered_cases": 0,
            "answer_coverage": None,
            "normalized_exact_match_rate": None,
            "normalized_contains_expected_rate": None,
            "mean_token_f1": None,
        }
    answered = sum(1 for item in items if item.get("answered"))
    return {
        "available": True,
        "eligible_cases": total,
        "answered_cases": answered,
        "unanswered_cases": total - answered,
        "answer_coverage": round(answered / total, 6),
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


def _normalize_retrieval_modes(modes: list[str] | tuple[str, ...] | str) -> list[str]:
    valid = {"keyword", "semantic", "hybrid", "vector"}
    raw = modes.split(",") if isinstance(modes, str) else modes
    normalized: list[str] = []
    for mode in raw:
        text = str(mode).strip()
        if not text:
            continue
        if text not in valid:
            raise ValueError(f"unsupported retrieval mode: {text}")
        if text not in normalized:
            normalized.append(text)
    if len(normalized) < 2:
        raise ValueError("mode comparison requires at least two modes")
    return normalized


def _external_mode_score_summary(score: dict[str, Any]) -> dict[str, Any]:
    retrieval = score.get("retrieval") or {}
    latency = score.get("latency") or {}
    index_latency = score.get("index_latency") or {}
    return {
        "retrieval": retrieval,
        "latency": latency,
        "index_latency": index_latency,
        "engineering": {
            "supported_count": (score.get("engineering") or {}).get("supported_count", 0),
            "measured_count": (score.get("engineering") or {}).get("measured_count", 0),
        },
    }


def _compare_external_mode_scores(
    *,
    scores_by_mode: dict[str, dict[str, Any]],
    baseline_mode: str,
) -> dict[str, Any]:
    baseline = _external_mode_metric_values(scores_by_mode.get(baseline_mode, {}))
    comparisons: dict[str, Any] = {}
    for mode, score in scores_by_mode.items():
        if mode == baseline_mode:
            continue
        current = _external_mode_metric_values(score)
        comparisons[mode] = {
            key: {
                "baseline": baseline.get(key),
                "current": current.get(key),
                "delta": _numeric_delta(current.get(key), baseline.get(key)),
            }
            for key in sorted(set(baseline) | set(current))
        }
    return comparisons


def _external_mode_metric_values(score: dict[str, Any]) -> dict[str, int | float | None]:
    retrieval = score.get("retrieval") or {}
    latency = score.get("latency") or {}
    return {
        "hit_rate": _coerce_float(retrieval.get("hit_rate")),
        "top1_hits": _coerce_int(retrieval.get("top1_hits")),
        "top3_hits": _coerce_int(retrieval.get("top3_hits")),
        "top5_hits": _coerce_int(retrieval.get("top5_hits")),
        "mean_reciprocal_rank": _coerce_float(retrieval.get("mean_reciprocal_rank")),
        "mean_latency_ms": _coerce_float(latency.get("mean_ms")),
        "p95_latency_ms": _coerce_float(latency.get("p95_ms")),
    }


def _numeric_delta(current: int | float | None, baseline: int | float | None) -> int | float | None:
    if current is None or baseline is None:
        return None
    delta = current - baseline
    if isinstance(current, int) and isinstance(baseline, int):
        return int(delta)
    return round(float(delta), 6)


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _create_mem0_memory(
    *,
    vector_store_path: str | Path,
    collection_name: str,
    embedder: str,
    embed_model: str,
    embedding_dims: int,
    llm_provider: str,
    history_db_path: str | Path,
):
    Path(history_db_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        from mem0 import Memory
    except ImportError as exc:
        raise RuntimeError(
            "mem0 adapter requires the optional mem0ai package. "
            "Install it in an isolated environment before running mem0-run."
        ) from exc

    config = _mem0_config(
        vector_store_path=vector_store_path,
        collection_name=collection_name,
        embedder=embedder,
        embed_model=embed_model,
        embedding_dims=embedding_dims,
        llm_provider=llm_provider,
        history_db_path=history_db_path,
    )
    return Memory.from_config(config)


def _set_process_env(values: dict[str, str]) -> dict[str, str | None]:
    previous = {key: os.environ.get(key) for key in values}
    for key, value in values.items():
        os.environ[key] = value
    return previous


def _restore_process_env(previous: dict[str, str | None]) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _fastembed_cache_revisions(cache_path: str | Path) -> dict[str, str]:
    root = Path(cache_path)
    if not root.exists():
        return {}
    revisions: dict[str, str] = {}
    for ref in sorted(root.glob("models--*/refs/main")):
        try:
            revision = ref.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if revision:
            revisions[ref.parent.parent.name] = revision
    return revisions


def _mem0_retrieval_preflight(
    memory: Any,
    *,
    expected_embedding_dims: int,
    limit: int,
    require_native_assets: bool,
    test_double: bool,
) -> dict[str, Any]:
    if test_double:
        return {
            "preflight_status": "test_double_not_applicable",
            "effective_retrieval_mode": "mem0:test-double",
            "bm25_available": None,
            "lemmatization_available": None,
            "entity_boost_available": None,
            "embedding_dimensions_verified": None,
            "provider_internal_candidate_pool_k": max(limit * 4, 60),
        }

    vector_store = getattr(memory, "vector_store", None)
    has_bm25_slot = bool(getattr(vector_store, "_has_bm25_slot", False))
    get_bm25_encoder = getattr(vector_store, "_get_bm25_encoder", None)
    bm25_available = bool(callable(get_bm25_encoder) and get_bm25_encoder() is not None)

    try:
        from mem0.utils.spacy_models import get_nlp_full, get_nlp_lemma

        lemmatization_available = get_nlp_lemma() is not None
        entity_boost_available = get_nlp_full() is not None
    except Exception:
        lemmatization_available = False
        entity_boost_available = False

    dense_model = getattr(getattr(memory, "embedding_model", None), "dense_model", None)
    actual_embedding_dims = getattr(dense_model, "embedding_size", None)
    if actual_embedding_dims is None:
        actual_embedding_dims = getattr(getattr(memory, "embedding_model", None), "config", None)
        actual_embedding_dims = getattr(actual_embedding_dims, "embedding_dims", None)
    dimensions_verified = actual_embedding_dims == expected_embedding_dims

    missing: list[str] = []
    if not has_bm25_slot:
        missing.append("qdrant_bm25_slot")
    if not bm25_available:
        missing.append("qdrant_bm25_encoder")
    if not lemmatization_available:
        missing.append("spacy_lemmatizer")
    if not entity_boost_available:
        missing.append("spacy_entity_model")
    if not dimensions_verified:
        missing.append("embedding_dimensions")
    if require_native_assets and missing:
        raise RuntimeError(
            "mem0 native retrieval preflight failed; refusing a publishable artifact: "
            + ", ".join(missing)
        )

    if has_bm25_slot and bm25_available:
        effective_mode = "mem0:semantic+bm25"
        if entity_boost_available:
            effective_mode += "+entity"
    else:
        effective_mode = "mem0:dense-fallback"
    return {
        "preflight_status": "passed" if not missing else "fallback_allowed",
        "effective_retrieval_mode": effective_mode,
        "bm25_slot_available": has_bm25_slot,
        "bm25_available": bm25_available,
        "lemmatization_available": lemmatization_available,
        "entity_boost_available": entity_boost_available,
        "embedding_dimensions_expected": expected_embedding_dims,
        "embedding_dimensions_actual": actual_embedding_dims,
        "embedding_dimensions_verified": dimensions_verified,
        "provider_internal_candidate_pool_k": max(limit * 4, 60),
        "missing_assets": missing,
    }


def _close_mem0_memory(memory: Any) -> None:
    vector_store = getattr(memory, "vector_store", None)
    client = getattr(vector_store, "client", None)
    client_close = getattr(client, "close", None)
    if callable(client_close):
        client_close()
    close = getattr(memory, "close", None)
    if callable(close):
        close()


def _mem0_config(
    *,
    vector_store_path: str | Path,
    collection_name: str,
    embedder: str,
    embed_model: str,
    embedding_dims: int,
    llm_provider: str,
    history_db_path: str | Path,
) -> dict[str, Any]:
    return {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "path": str(vector_store_path),
                "collection_name": collection_name,
                "embedding_model_dims": embedding_dims,
            },
        },
        "embedder": {
            "provider": embedder,
            "config": {
                "model": embed_model,
                "embedding_dims": embedding_dims,
            },
        },
        "llm": {
            "provider": llm_provider,
            "config": {},
        },
        "history_db_path": str(history_db_path),
    }


def _default_mem0_embed_model(embedder: str) -> str:
    if embedder == "fastembed":
        return "thenlper/gte-large"
    if embedder == "openai":
        return "text-embedding-3-small"
    raise ValueError("mem0 ollama embedder requires --embed-model")


def _mem0_embedding_dims(
    *,
    embedder: str,
    embed_model: str,
    embedding_dims: int | None,
) -> int:
    if embedding_dims is not None:
        if embedding_dims <= 0:
            raise ValueError("embedding_dims must be positive")
        return embedding_dims
    if embedder == "fastembed" and embed_model == "thenlper/gte-large":
        return 1024
    if embedder == "openai" and embed_model == "text-embedding-3-small":
        return 1536
    raise ValueError("custom mem0 embed models require --embedding-dims")


def _index_mem0_documents(
    memory: Any,
    documents: list[dict[str, Any]],
    *,
    run_namespace: str,
    require_provider_confirmation: bool,
) -> dict[str, int]:
    indexed = 0
    failed = 0
    for document in documents:
        metadata = {
            "source": document.get("source", ""),
            "title": document.get("title", ""),
            "search_category": document.get("category", ""),
            "tags": document.get("tags", ""),
        }
        response = memory.add(
            _canonical_retrieval_text(document),
            user_id=run_namespace,
            metadata=metadata,
            infer=False,
        )
        if require_provider_confirmation:
            results = response.get("results") if isinstance(response, dict) else None
            if not isinstance(results, list) or not results:
                failed += 1
                continue
        indexed += 1
    if failed:
        raise RuntimeError(f"mem0 failed to confirm {failed} indexed documents")
    return {"attempted": len(documents), "indexed": indexed, "failed": failed}


def _search_mem0_case(
    *,
    memory: Any,
    case: dict[str, Any],
    limit: int,
    search_scope: str,
    threshold: float,
    run_namespace: str,
    include_content: bool,
) -> dict[str, Any]:
    filters = {"user_id": run_namespace}
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
        "results": _normalize_mem0_results(raw, include_content=include_content),
    }


def _normalize_mem0_results(raw: Any, *, include_content: bool) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        if "results" in raw:
            candidates = raw["results"]
        elif "memories" in raw:
            candidates = raw["memories"]
        else:
            raise RuntimeError("mem0 search response did not include results or memories")
    elif isinstance(raw, list):
        candidates = raw
    else:
        raise RuntimeError("mem0 search response must be an object or list")
    if not isinstance(candidates, list):
        raise RuntimeError("mem0 search results must be a list")
    results: list[dict[str, Any]] = []
    for index, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            raise RuntimeError("mem0 search result must be an object")
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        source = str(item.get("source") or metadata.get("source") or "")
        if not source:
            raise RuntimeError("mem0 search result did not include source provenance")
        title = str(item.get("title") or metadata.get("title") or "")
        content = str(item.get("memory") or item.get("content") or item.get("text") or "")
        result = {
            "rank": index,
            "id": item.get("id"),
            "title": title,
            "source": source,
            "score": item.get("score"),
        }
        if include_content:
            result["content"] = content
        results.append(result)
    return results


def _canonical_retrieval_text(document: dict[str, Any]) -> str:
    return "\n".join(
        (
            f"title: {str(document.get('title') or '').strip()}",
            f"content: {str(document.get('content') or '').strip()}",
        )
    )


def _create_letta_passage(
    *,
    request: Any,
    base_url: str,
    api_key: str | None,
    archive_id: str,
    document: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    response = request(
        method="POST",
        url=f"{base_url.rstrip('/')}/v1/archives/{archive_id}/passages",
        api_key=api_key,
        payload={
            "text": _canonical_retrieval_text(document),
            "tags": _letta_document_tags(document, run_id),
        },
    )
    return response if isinstance(response, dict) else {}


def _search_letta_case(
    *,
    request: Any,
    base_url: str,
    api_key: str | None,
    archive_id: str,
    case: dict[str, Any],
    run_id: str,
    limit: int,
    search_scope: str,
    include_content: bool,
) -> dict[str, Any]:
    tags = [f"run:{run_id}"]
    if search_scope == "case":
        tags.append(f"category:{case.get('search_category', '')}")
    payload = {
        "query": str(case.get("query") or ""),
        "archive_id": archive_id,
        "limit": limit,
        "tags": tags,
        "tag_match_mode": "all",
    }
    start = time.perf_counter()
    raw = request(
        method="POST",
        url=f"{base_url.rstrip('/')}/v1/passages/search",
        api_key=api_key,
        payload=payload,
    )
    latency_ms = round((time.perf_counter() - start) * 1000, 3)
    return {
        "id": case.get("id"),
        "query": case.get("query", ""),
        "latency_ms": latency_ms,
        "results": _normalize_letta_results(raw, include_content=include_content),
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


def _normalize_letta_results(raw: Any, *, include_content: bool) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        candidates = raw
    elif isinstance(raw, dict):
        if "results" in raw:
            candidates = raw["results"]
        elif "passages" in raw:
            candidates = raw["passages"]
        else:
            raise RuntimeError("Letta search response did not include results or passages")
    else:
        raise RuntimeError("Letta search response must be an object or list")
    if not isinstance(candidates, list):
        raise RuntimeError("Letta search results must be a list")
    results: list[dict[str, Any]] = []
    for index, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            raise RuntimeError("Letta search result must be an object")
        passage = item.get("passage") if isinstance(item.get("passage"), dict) else item
        tags = passage.get("tags") if isinstance(passage.get("tags"), list) else []
        source = _source_from_tags(tags)
        if not source:
            raise RuntimeError("Letta search result did not include source provenance")
        result = {
            "rank": index,
            "id": passage.get("id"),
            "title": "",
            "source": source,
            "score": item.get("score", passage.get("score")),
        }
        if include_content:
            result["content"] = str(passage.get("content") or passage.get("text") or "")
        results.append(result)
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
    if params:
        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{url}?{query}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers=headers,
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
            "measured": False,
            "evidence": "The run measures source traceability only; mem0 audit lifecycle behavior is not measured.",
        },
    }


def _letta_engineering_profile() -> dict[str, Any]:
    return {
        "local_first": {
            "supported": True,
            "measured": False,
            "evidence": "Letta can be self-hosted; this run records the URL kind but does not prove deployment portability.",
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
            "measured": False,
            "evidence": "The run measures source traceability and archive cleanup, not Letta audit lifecycle behavior.",
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


def fixture_digest(payload: dict[str, Any]) -> str:
    """Return a stable digest for benchmark content, excluding local paths and timestamps."""
    canonical = {
        "schema_version": payload.get("schema_version"),
        "artifact_type": payload.get("artifact_type"),
        "benchmark": payload.get("benchmark"),
        "fixture_version": payload.get("fixture_version"),
        "fixed_clock": payload.get("fixed_clock"),
        "granularity": payload.get("granularity"),
        "documents": payload.get("documents", []),
        "cases": payload.get("cases", []),
        "matching_rule": payload.get("matching_rule", {}),
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _file_digest(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _opaque_value_digest(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _validate_run_for_fixture(fixture: dict[str, Any], run: dict[str, Any]) -> None:
    if fixture.get("schema_version") != 1 or run.get("schema_version") != 1:
        raise ValueError("fixture and run schema_version must be 1")
    if fixture.get("artifact_type") != "external_memory_comparison_fixture":
        raise ValueError("fixture artifact_type must be external_memory_comparison_fixture")
    if run.get("artifact_type") != "external_memory_comparison_run":
        raise ValueError("run artifact_type must be external_memory_comparison_run")
    if fixture.get("benchmark") != run.get("benchmark"):
        raise ValueError("fixture and run benchmark must match")
    if not str(run.get("system") or "").strip():
        raise ValueError("run system must be non-empty")
    top_k = run.get("top_k")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        raise ValueError("run top_k must be a positive integer")
    candidate_pool_k = run.get("candidate_pool_k")
    if (
        not isinstance(candidate_pool_k, int)
        or isinstance(candidate_pool_k, bool)
        or candidate_pool_k < top_k
    ):
        raise ValueError("run candidate_pool_k must be an integer greater than or equal to top_k")

    fixture_ids = [str(case.get("id")) for case in fixture.get("cases", [])]
    run_ids = [str(case.get("id")) for case in run.get("cases", [])]
    if len(fixture_ids) != len(set(fixture_ids)):
        raise ValueError("fixture contains duplicate case ids")
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("run contains duplicate case ids")
    if run_ids != fixture_ids:
        raise ValueError("run cases must exactly match fixture case ids and order")
    if run.get("cases_total") != len(fixture_ids):
        raise ValueError("run cases_total must match fixture cases")
    for case in run.get("cases", []):
        results = case.get("results")
        if not isinstance(results, list):
            raise ValueError(f"run case {case.get('id')} results must be a list")
        if len(results) > candidate_pool_k:
            raise ValueError(f"run case {case.get('id')} exceeds candidate_pool_k")
        if any(not isinstance(result, dict) for result in results):
            raise ValueError(f"run case {case.get('id')} contains a non-object result")
        latency = case.get("latency_ms")
        if latency is not None and not _is_finite_nonnegative_number(latency):
            raise ValueError(f"run case {case.get('id')} latency_ms must be finite and nonnegative")
        cost = case.get("cost_usd")
        if cost is not None and not _is_finite_nonnegative_number(cost):
            raise ValueError(f"run case {case.get('id')} cost_usd must be finite and nonnegative")
        seen_sources: set[str] = set()
        for index, result in enumerate(results, start=1):
            if result.get("rank") != index:
                raise ValueError(f"run case {case.get('id')} result ranks must be contiguous")
            source = str(result.get("source") or "")
            if not source:
                raise ValueError(f"run case {case.get('id')} result source must be non-empty")
            if source in seen_sources:
                raise ValueError(f"run case {case.get('id')} contains duplicate result sources")
            seen_sources.add(source)
            score = result.get("score")
            if score is not None and not _is_finite_nonnegative_number(score):
                raise ValueError(f"run case {case.get('id')} result score must be finite and nonnegative")

    expected_digest = _validated_evaluation_fixture_digest(fixture)
    run_digest = str(run.get("fixture_digest") or "")
    if not run_digest:
        raise ValueError("run fixture_digest is required")
    if run_digest != expected_digest:
        raise ValueError("fixture and run digest must match")


def _is_finite_nonnegative_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and float(value) >= 0
        and math.isfinite(float(value))
    )


def _provider_document(document: dict[str, Any]) -> dict[str, Any]:
    payload = {
        field: document[field]
        for field in PROVIDER_DOCUMENT_FIELDS
        if field in document
    }
    governance = document.get("governance")
    if isinstance(governance, dict):
        payload["governance"] = {
            field: governance[field]
            for field in PROVIDER_GOVERNANCE_FIELDS
            if field in governance
        }
    return payload


def _contains_scorer_only_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).strip().lower()
            if (
                normalized in {"answer", "has_answer", "metadata"}
                or normalized.startswith("expected_")
                or normalized.startswith("forbidden_")
            ):
                return True
            if _contains_scorer_only_key(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_scorer_only_key(item) for item in value)
    return False


def _validate_fixture_integrity(fixture: dict[str, Any]) -> None:
    if fixture.get("schema_version") != 1:
        raise ValueError("fixture schema_version must be 1")
    if fixture.get("artifact_type") != "external_memory_comparison_fixture":
        raise ValueError("fixture artifact_type must be external_memory_comparison_fixture")
    _validated_evaluation_fixture_digest(fixture)
    documents = fixture.get("documents", [])
    cases = fixture.get("cases", [])
    if not isinstance(documents, list) or any(
        not isinstance(document, dict) for document in documents
    ):
        raise ValueError("fixture documents must be a list of objects")
    if not isinstance(cases, list) or any(not isinstance(case, dict) for case in cases):
        raise ValueError("fixture cases must be a list of objects")
    if fixture.get("documents_total") is not None and fixture.get(
        "documents_total"
    ) != len(documents):
        raise ValueError("fixture documents_total must match documents")
    if fixture.get("cases_total") is not None and fixture.get("cases_total") != len(cases):
        raise ValueError("fixture cases_total must match cases")
    document_sources = [str(document.get("source") or "") for document in documents]
    case_ids = [str(case.get("id") or "") for case in cases]
    if not document_sources or any(not source for source in document_sources):
        raise ValueError("fixture documents must have non-empty source ids")
    if len(document_sources) != len(set(document_sources)):
        raise ValueError("fixture contains duplicate document source ids")
    if not case_ids or any(not case_id for case_id in case_ids):
        raise ValueError("fixture cases must have non-empty ids")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("fixture contains duplicate case ids")


def _validated_evaluation_fixture_digest(fixture: dict[str, Any]) -> str:
    actual_digest = fixture_digest(fixture)
    stored_digest = str(fixture.get("fixture_digest") or "")
    if fixture.get("provider_input") is True:
        provider_digest = str(fixture.get("provider_input_digest") or "")
        if provider_digest != actual_digest:
            raise ValueError("provider input digest does not match provider input content")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", stored_digest):
            raise ValueError("provider input requires the gold evaluation fixture digest")
        if fixture.get("gold_labels_excluded") is not True:
            raise ValueError("provider input must attest that gold labels are excluded")
        allowed_document_fields = set(PROVIDER_DOCUMENT_FIELDS) | {"governance"}
        allowed_case_fields = set(PROVIDER_CASE_FIELDS)
        if any(
            not isinstance(document, dict)
            or not set(document).issubset(allowed_document_fields)
            for document in fixture.get("documents", [])
        ):
            raise ValueError("provider input documents contain fields outside the allowlist")
        if any(
            not isinstance(case, dict) or not set(case).issubset(allowed_case_fields)
            for case in fixture.get("cases", [])
        ):
            raise ValueError("provider input cases contain fields outside the allowlist")
        for document in fixture.get("documents", []):
            governance = document.get("governance")
            if governance is not None and (
                not isinstance(governance, dict)
                or not set(governance).issubset(PROVIDER_GOVERNANCE_FIELDS)
            ):
                raise ValueError(
                    "provider input governance contains fields outside the allowlist"
                )
        forbidden_case_fields = {
            "answer",
            "expected_answer",
            "expected_sources",
            "expected_valid_sources",
            "forbidden_sources",
            "expected_block_reasons",
            "metadata",
        }
        if any(forbidden_case_fields.intersection(case) for case in fixture.get("cases", [])):
            raise ValueError("provider input cases contain scorer-only gold fields")
        if any(_contains_scorer_only_key(document) for document in fixture.get("documents", [])):
            raise ValueError("provider input documents contain scorer-only gold fields")
        return stored_digest
    if stored_digest and stored_digest != actual_digest:
        raise ValueError("fixture digest does not match fixture content")
    return actual_digest


def _validate_case_search_scope(fixture: dict[str, Any]) -> None:
    missing_cases = [
        str(case.get("id") or "")
        for case in fixture.get("cases", [])
        if not str(case.get("search_category") or "").strip()
    ]
    missing_documents = [
        str(document.get("source") or "")
        for document in fixture.get("documents", [])
        if not str(document.get("category") or "").strip()
    ]
    if missing_cases or missing_documents:
        raise ValueError(
            "case search scope requires non-empty case search_category and document category; "
            "use --search-scope global for a global fixture"
        )


def _provider_input_provenance(fixture: dict[str, Any]) -> dict[str, Any]:
    is_blinded = fixture.get("provider_input") is True
    return {
        "gold_labels_excluded": is_blinded and fixture.get("gold_labels_excluded") is True,
        "provider_input_digest": (
            fixture.get("provider_input_digest") if is_blinded else None
        ),
        "evaluation_fixture_digest": _validated_evaluation_fixture_digest(fixture),
    }


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

    provider_input = subparsers.add_parser(
        "export-provider-input",
        help="Strip scorer gold labels before giving a fixture to a provider adapter.",
    )
    provider_input.add_argument("--fixture", required=True)
    provider_input.add_argument("--output", required=True)

    vault_run = subparsers.add_parser("vault-run", help="Run Vault and emit a comparison run artifact.")
    vault_run.add_argument("--benchmark", choices=["locomo", "longmemeval"], required=True)
    vault_run.add_argument("--input", required=True)
    vault_run.add_argument("--output", required=True)
    vault_run.add_argument("--db-path")
    vault_run.add_argument("--max-cases", type=int)
    vault_run.add_argument("--limit", type=int, default=10)
    vault_run.add_argument("--mode", default="keyword", choices=["keyword", "semantic", "hybrid", "vector"])
    vault_run.add_argument("--granularity", default="session", choices=["session", "turn"])
    vault_run.add_argument("--search-scope", default="case", choices=["case", "global"])
    vault_run.add_argument("--reuse-db", action="store_true")
    vault_run.add_argument("--progress-every", type=int, default=0)
    vault_run.add_argument("--semantic-vector-kind", default="node", choices=["claim", "node"])
    vault_run.add_argument(
        "--embed-provider",
        default="",
        choices=["", "auto", "onnx", "ollama", "openai", "cohere", "voyage", "sentence-transformers"],
    )
    vault_run.add_argument("--embed-model", default="mix")
    vault_run.add_argument("--allow-hash", action="store_true", help="Allow deterministic hash embeddings.")
    vault_run.add_argument("--hash-dim", type=int, default=32)

    vault_modes = subparsers.add_parser("vault-mode-compare", help="Run Vault across multiple retrieval modes.")
    vault_modes.add_argument("--benchmark", choices=["locomo", "longmemeval"], required=True)
    vault_modes.add_argument("--input", required=True)
    vault_modes.add_argument("--output", required=True)
    vault_modes.add_argument("--db-path")
    vault_modes.add_argument("--max-cases", type=int)
    vault_modes.add_argument("--limit", type=int, default=10)
    vault_modes.add_argument("--modes", default="keyword,hybrid,semantic")
    vault_modes.add_argument("--granularity", default="session", choices=["session", "turn"])
    vault_modes.add_argument("--search-scope", default="case", choices=["case", "global"])
    vault_modes.add_argument("--reuse-db", action="store_true")
    vault_modes.add_argument("--progress-every", type=int, default=0)
    vault_modes.add_argument("--semantic-vector-kind", default="node", choices=["claim", "node"])
    vault_modes.add_argument(
        "--embed-provider",
        default="",
        choices=["", "auto", "onnx", "ollama", "openai", "cohere", "voyage", "sentence-transformers"],
    )
    vault_modes.add_argument("--embed-model", default="mix")
    vault_modes.add_argument("--allow-hash", action="store_true", help="Allow deterministic hash embeddings.")
    vault_modes.add_argument("--hash-dim", type=int, default=32)

    mem0_run = subparsers.add_parser("mem0-run", help="Run mem0 and emit a comparison run artifact.")
    mem0_run.add_argument("--fixture", required=True)
    mem0_run.add_argument("--output", required=True)
    mem0_run.add_argument("--limit", type=int, default=10)
    mem0_run.add_argument("--search-scope", default="case", choices=["case", "global"])
    mem0_run.add_argument(
        "--vector-store-path",
        default="",
        help="Local Qdrant path; defaults to a run-unique path under the system temp directory.",
    )
    mem0_run.add_argument("--collection-name", default="")
    mem0_run.add_argument("--run-namespace", default="")
    mem0_run.add_argument("--embedder", default="fastembed", choices=["fastembed", "openai", "ollama"])
    mem0_run.add_argument("--embed-model", default="")
    mem0_run.add_argument("--embedding-dims", type=int)
    mem0_run.add_argument("--llm-provider", default="ollama", choices=["ollama", "openai", "anthropic"])
    mem0_run.add_argument("--threshold", type=float, default=0.0)
    mem0_run.add_argument("--history-db-path")
    mem0_run.add_argument("--model-cache-path")
    mem0_run.add_argument("--enable-telemetry", action="store_true")
    mem0_run.add_argument(
        "--allow-provider-fallback",
        action="store_true",
        help="Allow a diagnostic artifact when mem0 BM25 or spaCy assets are unavailable.",
    )
    mem0_run.add_argument(
        "--include-content",
        action="store_true",
        help="Include retrieved memory text in the run artifact (debug only).",
    )

    letta_run = subparsers.add_parser(
        "letta-run",
        help="Run Letta Archive/Passages retrieval and emit a comparison artifact.",
    )
    letta_run.add_argument("--fixture", required=True)
    letta_run.add_argument("--output", required=True)
    letta_run.add_argument("--letta-api-key")
    letta_run.add_argument("--base-url", default="https://api.letta.com")
    letta_run.add_argument("--run-id")
    letta_run.add_argument("--embedding", default="ollama/bge-m3:latest")
    letta_run.add_argument("--server-version", default="")
    letta_run.add_argument("--limit", type=int, default=10)
    letta_run.add_argument("--search-scope", default="case", choices=["case", "global"])
    letta_run.add_argument("--include-content", action="store_true")

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
    elif args.command == "export-provider-input":
        payload = export_provider_input(
            fixture_path=args.fixture,
            output_path=args.output,
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
            semantic_vector_kind=args.semantic_vector_kind,
            embed_provider=args.embed_provider,
            embed_model=args.embed_model,
            allow_hash=args.allow_hash,
            hash_dim=args.hash_dim,
        )
    elif args.command == "vault-mode-compare":
        payload = run_vault_mode_comparison(
            benchmark=args.benchmark,
            input_path=args.input,
            output_path=args.output,
            db_path=args.db_path,
            max_cases=args.max_cases,
            limit=args.limit,
            modes=args.modes,
            granularity=args.granularity,
            search_scope=args.search_scope,
            reuse_db=args.reuse_db,
            progress_every=args.progress_every,
            semantic_vector_kind=args.semantic_vector_kind,
            embed_provider=args.embed_provider,
            embed_model=args.embed_model,
            allow_hash=args.allow_hash,
            hash_dim=args.hash_dim,
        )
    elif args.command == "mem0-run":
        payload = run_mem0_comparison(
            fixture_path=args.fixture,
            output_path=args.output,
            limit=args.limit,
            search_scope=args.search_scope,
            vector_store_path=args.vector_store_path,
            collection_name=args.collection_name,
            run_namespace=args.run_namespace,
            embedder=args.embedder,
            embed_model=args.embed_model,
            embedding_dims=args.embedding_dims,
            llm_provider=args.llm_provider,
            threshold=args.threshold,
            history_db_path=args.history_db_path,
            model_cache_path=args.model_cache_path,
            enable_telemetry=args.enable_telemetry,
            require_native_retrieval_assets=not args.allow_provider_fallback,
            include_content=args.include_content,
        )
    elif args.command == "letta-run":
        payload = run_letta_comparison(
            fixture_path=args.fixture,
            output_path=args.output,
            api_key=args.letta_api_key,
            base_url=args.base_url,
            run_id=args.run_id,
            embedding=args.embedding,
            server_version=args.server_version,
            limit=args.limit,
            search_scope=args.search_scope,
            include_content=args.include_content,
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
    if payload.get("artifact_type") == "external_memory_vault_mode_comparison":
        return {
            "artifact_type": payload["artifact_type"],
            "system": payload["system"],
            "benchmark": payload["benchmark"],
            "top_k": payload["top_k"],
            "mode_order": payload["mode_order"],
            "baseline_mode": payload["baseline_mode"],
            "aggregate_by_mode": payload["aggregate_by_mode"],
            "comparisons_vs_baseline": payload["comparisons_vs_baseline"],
        }
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
    provider_provenance = ((payload.get("manifest") or {}).get("provider_input") or {})
    provider_input = payload.get("provider_input")
    if provider_input is None and provider_provenance:
        provider_input = provider_provenance.get("gold_labels_excluded") is True
    provider_input_digest = payload.get("provider_input_digest")
    if provider_input_digest is None:
        provider_input_digest = provider_provenance.get("provider_input_digest")
    return {
        "artifact_type": payload.get("artifact_type"),
        "benchmark": payload.get("benchmark"),
        "cases_total": payload.get("cases_total"),
        "documents_total": payload.get("documents_total"),
        "system": payload.get("system"),
        "provider_input": provider_input,
        "fixture_digest": payload.get("fixture_digest"),
        "provider_input_digest": provider_input_digest,
    }


if __name__ == "__main__":
    raise SystemExit(main())
