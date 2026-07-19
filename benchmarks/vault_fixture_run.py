"""Build a live Vault candidate pool from a neutral comparison fixture.

The runner intentionally starts from ``fixture.documents`` on every invocation:
it creates a fresh temporary Vault database, indexes the canonical documents,
and retrieves candidates with ``VaultSearch``.  Frozen or pre-ranked fixture
candidates are never consumed.

The output is an ``external_memory_comparison_run`` artifact accepted by
``benchmarks/memory_foundation_compare.py augment-run``.  ``results`` is the
machine-facing compatibility field; ``candidate_pool`` is an explicit alias for
humans inspecting the artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from benchmarks.external_memory_compare import (  # noqa: E402
    PROVIDER_GOVERNANCE_FIELDS,
    _provider_input_provenance,
    _validate_run_for_fixture,
    _validated_evaluation_fixture_digest,
    benchmark_source_manifest,
)
from benchmarks.external_memory_retrieval import _prepare_semantic_provider  # noqa: E402
from vault import __version__ as VAULT_VERSION  # noqa: E402
from vault.db import VaultDB  # noqa: E402
from vault.search import VaultSearch  # noqa: E402
from vault.search_qa import write_json  # noqa: E402
from vault.search_utils import MAX_LIMIT  # noqa: E402


RUNNER_VERSION = "0.1.0"
RUN_SCHEMA_VERSION = 1
SUPPORTED_MODES = ("keyword", "semantic", "hybrid")


def run_vault_fixture(
    *,
    fixture_path: str | Path,
    output_path: str | Path | None = None,
    candidate_pool_k: int = 40,
    mode: str = "keyword",
    semantic_vector_kind: str = "node",
    embed_provider: str = "",
    embed_model: str = "mix",
    allow_hash: bool = False,
    hash_dim: int = 32,
    include_content: bool = False,
) -> dict[str, Any]:
    """Return a live Vault candidate-pool run for one neutral fixture."""
    pool_k = _validate_candidate_pool_k(candidate_pool_k)
    normalized_mode = str(mode or "").strip().lower()
    if normalized_mode not in SUPPORTED_MODES:
        raise ValueError(f"mode must be one of: {', '.join(SUPPORTED_MODES)}")
    if semantic_vector_kind not in {"claim", "node"}:
        raise ValueError("semantic_vector_kind must be claim or node")
    if normalized_mode in {"semantic", "hybrid"} and not (embed_provider or allow_hash):
        raise ValueError("semantic and hybrid modes require --embed-provider or --allow-hash")
    if allow_hash and hash_dim <= 0:
        raise ValueError("hash_dim must be positive")

    fixture_file = Path(fixture_path)
    fixture = _read_fixture(fixture_file)
    digest = _validated_evaluation_fixture_digest(fixture)
    _validate_fixture(fixture, digest=digest)

    run_started = time.perf_counter()
    run_id = f"vault-fixture-{uuid.uuid4().hex}"
    with tempfile.TemporaryDirectory(prefix="vault-neutral-fixture-") as temp_dir:
        db_path = Path(temp_dir) / "fixture.db"

        db_init_started = time.perf_counter()
        db = VaultDB(db_path).connect()
        db_init_latency_ms = _elapsed_ms(db_init_started)
        try:
            document_index_started = time.perf_counter()
            indexed = _index_documents(db, fixture.get("documents", []))
            document_index_latency_ms = _elapsed_ms(document_index_started)
        finally:
            db.close()

        semantic_index_started = time.perf_counter()
        semantic_provider = _prepare_semantic_provider(
            db_path=db_path,
            mode=normalized_mode,
            embed_provider_name=str(embed_provider or ""),
            embed_model=embed_model,
            allow_hash=allow_hash,
            hash_dim=hash_dim,
        )
        semantic_index_latency_ms = _elapsed_ms(semantic_index_started)
        if normalized_mode == "keyword":
            semantic_index_latency_ms = 0.0

        cases = _retrieve_cases(
            db_path=db_path,
            fixture_cases=fixture.get("cases", []),
            mode=normalized_mode,
            candidate_pool_k=pool_k,
            semantic_provider=semantic_provider,
            semantic_vector_kind=semantic_vector_kind,
            allow_hash=allow_hash,
            include_content=include_content,
        )

    index_latency_ms = round(
        db_init_latency_ms + document_index_latency_ms + semantic_index_latency_ms,
        3,
    )
    retrieval_latencies = [float(case["latency_ms"]) for case in cases]
    payload = {
        "schema_version": RUN_SCHEMA_VERSION,
        "artifact_type": "external_memory_comparison_run",
        "generated_at": _utc_now(),
        "runner": "benchmarks.vault_fixture_run",
        "runner_version": RUNNER_VERSION,
        "system": "vault",
        "system_version": VAULT_VERSION,
        "benchmark": fixture.get("benchmark"),
        "fixture_digest": digest,
        "top_k": pool_k,
        "candidate_pool_k": pool_k,
        "retrieval_mode": normalized_mode,
        "search_scope": "fixture-global",
        "run_id": run_id,
        "semantic_vector_kind": semantic_vector_kind,
        "embed_provider": str(embed_provider or "")
        or ("deterministic-hash" if allow_hash else None),
        "embed_model": embed_model if embed_provider else None,
        "allow_hash": bool(allow_hash),
        "hash_dim": int(hash_dim) if allow_hash else None,
        "documents_total": indexed,
        "cases_total": len(cases),
        "setup_latency_ms": db_init_latency_ms,
        "ingest_latency_ms": round(document_index_latency_ms + semantic_index_latency_ms, 3),
        "index_latency_ms": index_latency_ms,
        "storage_index_latency_ms": round(
            db_init_latency_ms + document_index_latency_ms,
            3,
        ),
        "semantic_index_latency_ms": semantic_index_latency_ms,
        "timings": {
            "database_init_ms": db_init_latency_ms,
            "document_index_ms": document_index_latency_ms,
            "semantic_index_ms": semantic_index_latency_ms,
            "index_total_ms": index_latency_ms,
            "retrieval": _latency_summary(retrieval_latencies),
            "run_wall_ms": _elapsed_ms(run_started),
        },
        "cases": cases,
        "manifest": _environment_manifest(
            fixture=fixture,
            fixture_file=fixture_file,
            digest=digest,
            mode=normalized_mode,
            candidate_pool_k=pool_k,
            semantic_vector_kind=semantic_vector_kind,
            embed_provider=str(embed_provider or ""),
            embed_model=embed_model,
            allow_hash=allow_hash,
            hash_dim=hash_dim,
            include_content=include_content,
        ),
        "engineering": _engineering_profile(),
        "notes": [
            "Retrieval-only candidate pool; no reader model or final-answer judge was run.",
            "Every candidate came from live VaultSearch over documents indexed in this run.",
            "No frozen or pre-ranked candidate pool was read.",
            "Expected answers and expected/forbidden source labels are never copied into the run artifact.",
            "Retrieved content is omitted by default and only included with an explicit debug flag.",
            "Expired and future temporal candidates remain retrieval-eligible so the downstream "
            "Vault read guard can measure policy filtering on the same pool.",
            "Deterministic hash embeddings are non-publishable plumbing test doubles.",
        ],
    }
    _validate_run_for_fixture(fixture, payload)
    _validate_run_shape(fixture, payload)
    if output_path:
        write_json(output_path, payload)
    return payload


def _read_fixture(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"fixture not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"fixture is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("fixture root must be a JSON object")
    return payload


def _validate_fixture(fixture: dict[str, Any], *, digest: str) -> None:
    if fixture.get("schema_version") != 1:
        raise ValueError("fixture schema_version must be 1")
    if fixture.get("artifact_type") != "external_memory_comparison_fixture":
        raise ValueError("fixture artifact_type must be external_memory_comparison_fixture")
    if not str(fixture.get("benchmark") or "").strip():
        raise ValueError("fixture benchmark is required")

    documents = fixture.get("documents")
    cases = fixture.get("cases")
    if not isinstance(documents, list) or not documents:
        raise ValueError("fixture must contain at least one document")
    if not isinstance(cases, list) or not cases:
        raise ValueError("fixture must contain at least one case")

    sources: list[str] = []
    document_ids: list[str] = []
    for document in documents:
        if not isinstance(document, dict):
            raise ValueError("fixture documents must be JSON objects")
        source = str(document.get("source") or "").strip()
        if not source:
            raise ValueError("fixture documents require source provenance")
        sources.append(source)
        if document.get("id") is not None:
            document_ids.append(str(document["id"]))
    if len(sources) != len(set(sources)):
        raise ValueError("fixture contains duplicate document sources")
    if len(document_ids) != len(set(document_ids)):
        raise ValueError("fixture contains duplicate document ids")

    case_ids: list[str] = []
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("fixture cases must be JSON objects")
        case_id = str(case.get("id") or "").strip()
        if not case_id:
            raise ValueError("fixture cases require ids")
        if not str(case.get("query") or "").strip():
            raise ValueError(f"fixture case {case_id} requires a query")
        case_ids.append(case_id)
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("fixture contains duplicate case ids")

    stored_digest = str(fixture.get("fixture_digest") or "")
    if stored_digest and stored_digest != digest:
        raise ValueError("fixture digest does not match fixture content")


def _index_documents(db: VaultDB, documents: list[dict[str, Any]]) -> int:
    fixture_to_vault_id: dict[str, int] = {}
    pending_updates: list[tuple[int, dict[str, Any]]] = []
    for document in documents:
        governance = {
            field: document[field]
            for field in PROVIDER_GOVERNANCE_FIELDS
            if field in document
        }
        nested_governance = document.get("governance")
        if isinstance(nested_governance, dict):
            governance.update(nested_governance)
        knowledge_id = db.add_knowledge(
            title=str(document.get("title") or document.get("source") or "Untitled"),
            content_raw=str(document.get("content") or ""),
            layer=str(document.get("layer") or "L3"),
            category=str(document.get("category") or "vaultgovbench-neutral-fixture"),
            tags=_normalize_tags(document.get("tags")),
            trust=float(document.get("trust", 0.8)),
            source=str(document.get("source") or ""),
            scope=str(governance.get("scope") or "project"),
            sensitivity=str(governance.get("sensitivity") or "low"),
            owner_agent=str(governance.get("owner_agent") or ""),
            allowed_agents=governance.get("allowed_agents"),
            memory_type=str(governance.get("memory_type") or "benchmark_evidence"),
            expires_at=str(governance.get("expires_at") or ""),
            valid_from=str(governance.get("valid_from") or ""),
            valid_until=str(governance.get("valid_until") or ""),
        )
        if document.get("id") is not None:
            fixture_to_vault_id[str(document["id"])] = knowledge_id
        pending_updates.append((knowledge_id, governance))

    for knowledge_id, governance in pending_updates:
        updates: dict[str, Any] = {}
        status = str(governance.get("status") or "").strip()
        if status:
            updates["status"] = status
        supersedes = governance.get("supersedes_id")
        if supersedes not in {None, ""}:
            resolved = fixture_to_vault_id.get(str(supersedes))
            if resolved is None:
                raise ValueError(f"document supersedes unknown fixture id: {supersedes}")
            updates["supersedes_id"] = resolved
        if updates:
            db.update_knowledge(knowledge_id, **updates)
    return len(pending_updates)


def _retrieve_cases(
    *,
    db_path: Path,
    fixture_cases: list[dict[str, Any]],
    mode: str,
    candidate_pool_k: int,
    semantic_provider: Any | None,
    semantic_vector_kind: str,
    allow_hash: bool,
    include_content: bool,
) -> list[dict[str, Any]]:
    db = VaultDB(db_path).connect()
    try:
        search = VaultSearch(
            db,
            embed_provider=semantic_provider,
            embed_provider_name=("deterministic-hash" if allow_hash else "auto"),
            enable_query_expansion=False,
            enable_rerank=False,
        )
        cases: list[dict[str, Any]] = []
        for fixture_case in fixture_cases:
            started = time.perf_counter()
            raw_results = search.search(
                str(fixture_case.get("query") or ""),
                mode=mode,
                limit=candidate_pool_k,
                use_rerank=False,
                use_query_expansion=False,
                semantic_vector_kind=semantic_vector_kind,
                allow_hash=allow_hash,
                agent_id=str(fixture_case.get("agent_id") or ""),
                include_private=bool(fixture_case.get("include_private", False)),
                max_sensitivity=str(fixture_case.get("max_sensitivity") or ""),
                include_expired_temporal=True,
                include_future_temporal=True,
                temporal_as_of=str(fixture_case.get("as_of") or ""),
            )
            latency_ms = _elapsed_ms(started)
            candidate_pool = [
                _normalize_result(item, rank=index, include_content=include_content)
                for index, item in enumerate(raw_results, start=1)
            ]
            cases.append(
                {
                    "id": str(fixture_case.get("id") or ""),
                    "case_id": str(fixture_case.get("id") or ""),
                    "query": str(fixture_case.get("query") or ""),
                    "latency_ms": latency_ms,
                    "cost_usd": None,
                    "candidate_pool_returned": len(candidate_pool),
                    "candidate_pool": candidate_pool,
                    "results": [dict(item) for item in candidate_pool],
                    "policy_context": {
                        "agent_id": str(fixture_case.get("agent_id") or ""),
                        "include_private": bool(fixture_case.get("include_private", False)),
                        "max_sensitivity": str(fixture_case.get("max_sensitivity") or ""),
                        "as_of": str(fixture_case.get("as_of") or ""),
                        "include_expired_temporal_candidates": True,
                        "include_future_temporal_candidates": True,
                    },
                }
            )
        return cases
    finally:
        db.close()


def _normalize_result(
    item: dict[str, Any], *, rank: int, include_content: bool
) -> dict[str, Any]:
    raw_score = item.get("_score", item.get("score"))
    score = float(raw_score) if isinstance(raw_score, (int, float)) else None
    result = {
        "rank": rank,
        "id": item.get("id"),
        "title": str(item.get("title") or ""),
        "source": str(item.get("source") or ""),
        "score": score,
        "mode": str(item.get("_mode") or ""),
    }
    if include_content:
        result["content"] = str(item.get("content_raw") or item.get("content") or "")
    return result


def _validate_run_shape(fixture: dict[str, Any], run: dict[str, Any]) -> None:
    expected_ids = [str(case.get("id") or "") for case in fixture.get("cases", [])]
    actual_ids = [str(case.get("id") or "") for case in run.get("cases", [])]
    if actual_ids != expected_ids:
        raise RuntimeError("run cases do not preserve fixture case order")
    known_sources = {str(document.get("source") or "") for document in fixture.get("documents", [])}
    pool_k = int(run["candidate_pool_k"])
    for case in run.get("cases", []):
        results = case.get("results")
        candidate_pool = case.get("candidate_pool")
        if results != candidate_pool:
            raise RuntimeError(f"run case {case.get('id')} candidate aliases differ")
        if len(results) > pool_k:
            raise RuntimeError(f"run case {case.get('id')} exceeds candidate_pool_k")
        sources = [str(result.get("source") or "") for result in results]
        if any(not source for source in sources):
            raise RuntimeError(f"run case {case.get('id')} contains missing provenance")
        if len(sources) != len(set(sources)):
            raise RuntimeError(f"run case {case.get('id')} contains duplicate sources")
        if not set(sources).issubset(known_sources):
            raise RuntimeError(f"run case {case.get('id')} contains an unknown fixture source")


def _environment_manifest(
    *,
    fixture: dict[str, Any],
    fixture_file: Path,
    digest: str,
    mode: str,
    candidate_pool_k: int,
    semantic_vector_kind: str,
    embed_provider: str,
    embed_model: str,
    allow_hash: bool,
    hash_dim: int,
    include_content: bool,
) -> dict[str, Any]:
    git_sha, git_dirty = _git_state()
    lock_path = REPO_ROOT / "uv.lock"
    return {
        "benchmark_source": benchmark_source_manifest(__file__),
        "provider_input": _provider_input_provenance(fixture),
        "runner": {
            "module": "benchmarks.vault_fixture_run",
            "version": RUNNER_VERSION,
        },
        "source_control": {
            "git_sha": git_sha,
            "git_dirty": git_dirty,
            "dependency_lock_digest": _file_digest(lock_path) if lock_path.exists() else "",
        },
        "runtime": {
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "sqlite": sqlite3.sqlite_version,
        },
        "dependencies": {
            "vault-for-llm": _distribution_version("vault-for-llm") or VAULT_VERSION,
            "sqlite-vec": _distribution_version("sqlite-vec"),
            "onnxruntime": _distribution_version("onnxruntime"),
            "sentence-transformers": _distribution_version("sentence-transformers"),
        },
        "fixture": {
            "file_name": fixture_file.name,
            "digest": digest,
            "benchmark": fixture.get("benchmark"),
            "fixed_clock": fixture.get("fixed_clock"),
            "documents_total": len(fixture.get("documents", [])),
            "cases_total": len(fixture.get("cases", [])),
            "input": "fixture.documents",
            "frozen_candidate_pool_used": False,
        },
        "database": {
            "backend": "SQLite",
            "vault_schema_version": VaultDB.SCHEMA_VERSION,
            "ephemeral": True,
            "reuse": False,
            "lifecycle": "fresh temporary database deleted after the run",
            "path": "redacted-temporary-path",
        },
        "provider_quality_gate": {
            "passed": True,
            "checks": {
                "fresh_ephemeral_database": True,
                "live_search_execution": True,
                "exact_source_provenance": True,
                "expected_labels_excluded_from_run_cases": True,
            },
        },
        "retrieval": {
            "implementation": "vault.search.VaultSearch.search",
            "mode": mode,
            "candidate_pool_k": candidate_pool_k,
            "search_scope": "fixture-global",
            "rerank": False,
            "query_expansion": False,
            "semantic_vector_kind": semantic_vector_kind,
            "embed_provider": embed_provider or ("deterministic-hash" if allow_hash else None),
            "embed_model": embed_model if embed_provider else None,
            "allow_hash": bool(allow_hash),
            "hash_dim": int(hash_dim) if allow_hash else None,
            "content_in_run_artifact": bool(include_content),
            "seed": None,
            "seed_status": "not_set; provider determinism must be documented separately",
            "publishable": not allow_hash,
        },
        "governance_materialization": {
            "stored_fields": [
                "scope",
                "sensitivity",
                "owner_agent",
                "allowed_agents",
                "memory_type",
                "expires_at",
                "valid_from",
                "valid_until",
                "supersedes_id",
                "status",
            ],
            "canonical_only_fields": ["privacy_status", "approval_state"],
            "downstream_guard_source": "fixture canonical snapshot",
        },
        "timing_scope": {
            "index": "DB initialization, document writes, and semantic index preparation",
            "retrieval": "VaultSearch.search wall time per case",
            "run_wall": (
                "benchmark work from before temporary DB creation through retrieval; "
                "manifest construction and output serialization are excluded"
            ),
            "cost": "unavailable; local compute cost was not estimated",
        },
        "redaction": "expected labels and content are omitted by default; fixture inputs require separate review",
    }


def _engineering_profile() -> dict[str, Any]:
    return {
        "local_first": {
            "supported": True,
            "measured": True,
            "evidence": "This run creates and searches a local temporary SQLite Vault.",
        },
        "multi_agent_shared_memory": {
            "supported": True,
            "measured": False,
            "evidence": "This retrieval run does not exercise shared-agent setup.",
        },
        "sync": {
            "supported": True,
            "measured": False,
            "evidence": "This retrieval run does not exercise remote sync.",
        },
        "report": {
            "supported": True,
            "measured": False,
            "evidence": "This retrieval run does not generate an operations report.",
        },
        "audit": {
            "supported": True,
            "measured": False,
            "evidence": "Source provenance is retained; the audit lifecycle is not exercised.",
        },
    }


def _latency_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "available": False,
            "count": 0,
            "min_ms": None,
            "mean_ms": None,
            "p50_ms": None,
            "p95_ms": None,
            "max_ms": None,
        }
    ordered = sorted(values)
    return {
        "available": True,
        "count": len(ordered),
        "min_ms": round(ordered[0], 3),
        "mean_ms": round(statistics.fmean(ordered), 3),
        "p50_ms": round(_percentile(ordered, 0.50), 3),
        "p95_ms": round(_percentile(ordered, 0.95), 3),
        "max_ms": round(ordered[-1], 3),
    }


def _percentile(values: list[float], percentile: float) -> float:
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] + (values[upper] - values[lower]) * fraction


def _git_state() -> tuple[str, bool | None]:
    try:
        git_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        return git_sha, dirty
    except (OSError, subprocess.CalledProcessError):
        return "", None


def _distribution_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _file_digest(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _normalize_tags(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return ",".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "")


def _validate_candidate_pool_k(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("candidate_pool_k must be a positive integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("candidate_pool_k must be a positive integer") from exc
    if parsed <= 0 or parsed > MAX_LIMIT:
        raise ValueError(f"candidate_pool_k must be between 1 and {MAX_LIMIT}")
    return parsed


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a live Vault candidate pool from a neutral comparison fixture."
    )
    parser.add_argument("--fixture", required=True, help="Neutral comparison fixture JSON.")
    parser.add_argument("--output", required=True, help="Output run-artifact JSON.")
    parser.add_argument(
        "--candidate-pool-k",
        type=int,
        default=40,
        help=f"Maximum live candidates per case (1-{MAX_LIMIT}).",
    )
    parser.add_argument("--mode", choices=SUPPORTED_MODES, default="keyword")
    parser.add_argument("--semantic-vector-kind", choices=("claim", "node"), default="node")
    parser.add_argument(
        "--embed-provider",
        default="",
        choices=(
            "",
            "auto",
            "onnx",
            "ollama",
            "openai",
            "cohere",
            "voyage",
            "sentence-transformers",
        ),
    )
    parser.add_argument("--embed-model", default="mix")
    parser.add_argument(
        "--allow-hash",
        action="store_true",
        help="Allow non-publishable deterministic hash embeddings for plumbing tests.",
    )
    parser.add_argument("--hash-dim", type=int, default=32)
    parser.add_argument(
        "--include-content",
        action="store_true",
        help="Include retrieved content in the artifact for local debugging only.",
    )
    parser.add_argument("--quiet", action="store_true", help="Print only a compact summary.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = run_vault_fixture(
        fixture_path=args.fixture,
        output_path=args.output,
        candidate_pool_k=args.candidate_pool_k,
        mode=args.mode,
        semantic_vector_kind=args.semantic_vector_kind,
        embed_provider=args.embed_provider,
        embed_model=args.embed_model,
        allow_hash=args.allow_hash,
        hash_dim=args.hash_dim,
        include_content=args.include_content,
    )
    if args.quiet:
        printable = {
            "system": payload["system"],
            "system_version": payload["system_version"],
            "fixture_digest": payload["fixture_digest"],
            "documents_total": payload["documents_total"],
            "cases_total": payload["cases_total"],
            "candidate_pool_k": payload["candidate_pool_k"],
            "index_latency_ms": payload["index_latency_ms"],
            "retrieval_latency": payload["timings"]["retrieval"],
        }
    else:
        printable = payload
    print(json.dumps(printable, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
