"""Retrieval-only adapters for external long-term memory benchmarks.

This script intentionally evaluates evidence recall, not final-answer quality.
It converts LoCoMo or LongMemEval JSON files into a temporary Vault database,
runs local search, and reports whether the expected evidence source appears in
the top-k results.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from vault.db import VaultDB  # noqa: E402
from vault.search import VaultSearch  # noqa: E402
from vault.search_qa import write_json  # noqa: E402


@dataclass(frozen=True)
class ExternalDocument:
    title: str
    content: str
    source: str
    category: str
    tags: str


@dataclass(frozen=True)
class ExternalCase:
    case_id: str
    query: str
    expected_sources: tuple[str, ...]
    category: str
    metadata: dict[str, Any]


def run_external_memory_retrieval(
    *,
    benchmark: str,
    input_path: str | Path,
    output_path: str | Path | None = None,
    db_path: str | Path | None = None,
    generated_qa_path: str | Path | None = None,
    max_cases: int | None = None,
    limit: int = 10,
    mode: str = "keyword",
    granularity: str = "auto",
    search_scope: str = "case",
    reuse_db: bool = False,
    progress_every: int = 0,
    semantic_vector_kind: str = "claim",
    allow_hash: bool = False,
    hash_dim: int = 32,
) -> dict[str, Any]:
    if search_scope not in {"case", "global"}:
        raise ValueError(f"unsupported search scope: {search_scope}")
    if reuse_db and not db_path:
        raise ValueError("--reuse-db requires --db-path")

    input_file = Path(input_path)
    data = json.loads(input_file.read_text(encoding="utf-8"))
    if benchmark == "locomo":
        documents, cases = _load_locomo(data, max_cases=max_cases)
    elif benchmark == "longmemeval":
        documents, cases = _load_longmemeval(data, max_cases=max_cases, granularity=granularity)
    else:
        raise ValueError(f"unsupported benchmark: {benchmark}")

    if not cases:
        raise ValueError("no evidence-bearing cases found")

    with _maybe_temp_db(db_path) as actual_db_path:
        db_reused = bool(reuse_db and actual_db_path.exists())
        index_latency_ms = 0.0
        if not db_reused:
            index_start = time.perf_counter()
            _build_vault_db(actual_db_path, documents)
            index_latency_ms = round((time.perf_counter() - index_start) * 1000, 3)
        embed_provider = _prepare_semantic_provider(
            db_path=actual_db_path,
            mode=mode,
            allow_hash=allow_hash,
            hash_dim=hash_dim,
        )
        case_results = _evaluate_cases(
            db_path=actual_db_path,
            cases=cases,
            mode=mode,
            limit=limit,
            search_scope=search_scope,
            progress_every=progress_every,
            embed_provider=embed_provider,
            semantic_vector_kind=semantic_vector_kind,
            allow_hash=allow_hash,
        )

    report = {
        "report_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark": benchmark,
        "input_path": str(input_file),
        "mode": mode,
        "limit": limit,
        "granularity": granularity,
        "search_scope": search_scope,
        "semantic_vector_kind": semantic_vector_kind,
        "allow_hash": bool(allow_hash),
        "hash_dim": int(hash_dim) if allow_hash else None,
        "db_path": str(actual_db_path),
        "db_reused": db_reused,
        "documents_indexed": len(documents),
        "index_latency_ms": index_latency_ms,
        "cases_total": len(cases),
        "aggregate": _aggregate(case_results),
        "cases": case_results,
        "notes": [
            "Retrieval-only evidence recall; this is not final-answer QA.",
            "Scores are not comparable to LoCoMo/LongMemEval leaderboard QA unless the same reader and judge harness are run.",
        ],
    }

    if generated_qa_path:
        _write_generated_search_qa(generated_qa_path, benchmark=benchmark, cases=cases)
        report["generated_search_qa_path"] = str(Path(generated_qa_path))

    if output_path:
        write_json(output_path, report)
    return report


def _load_locomo(data: Any, *, max_cases: int | None) -> tuple[list[ExternalDocument], list[ExternalCase]]:
    samples = _as_list(data)
    documents: list[ExternalDocument] = []
    cases: list[ExternalCase] = []
    seen_sources: set[str] = set()

    for sample in samples:
        if not isinstance(sample, dict):
            continue
        sample_id = str(sample.get("sample_id") or sample.get("id") or f"sample-{len(documents)}")
        search_category = f"locomo-dialog:{sample_id}"
        conversation = sample.get("conversation") if isinstance(sample.get("conversation"), dict) else {}
        speaker_a = str(conversation.get("speaker_a") or "speaker_a")
        speaker_b = str(conversation.get("speaker_b") or "speaker_b")
        speaker_names = {"speaker_a": speaker_a, "speaker_b": speaker_b}

        for session_key, turns in sorted(conversation.items()):
            if not session_key.startswith("session_") or session_key.endswith("_date_time"):
                continue
            if not isinstance(turns, list):
                continue
            session_id = session_key.removeprefix("session_")
            session_time = str(conversation.get(f"{session_key}_date_time") or "")
            for idx, turn in enumerate(turns):
                if not isinstance(turn, dict):
                    continue
                dia_id = str(turn.get("dia_id") or f"{session_id}-{idx}")
                source = f"locomo/{sample_id}/dia/{dia_id}"
                if source in seen_sources:
                    continue
                speaker = str(turn.get("speaker") or "")
                speaker = speaker_names.get(speaker, speaker or "speaker")
                text = str(turn.get("text") or "")
                caption = str(turn.get("blip_caption") or "")
                content = "\n".join(
                    part
                    for part in (
                        f"sample_id: {sample_id}",
                        f"session: {session_id}",
                        f"timestamp: {session_time}" if session_time else "",
                        f"dialog_id: {dia_id}",
                        f"speaker: {speaker}",
                        f"text: {text}",
                        f"image_caption: {caption}" if caption else "",
                    )
                    if part
                )
                documents.append(
                    ExternalDocument(
                        title=f"LoCoMo {sample_id} dialog {dia_id}",
                        content=content,
                        source=source,
                        category=search_category,
                        tags=f"locomo,{sample_id},session-{session_id}",
                    )
                )
                seen_sources.add(source)

        qa_items = sample.get("qa") if isinstance(sample.get("qa"), list) else []
        for qa_idx, qa in enumerate(qa_items):
            if not isinstance(qa, dict):
                continue
            evidence = [str(item) for item in _as_list(qa.get("evidence")) if str(item)]
            if not evidence:
                continue
            cases.append(
                ExternalCase(
                    case_id=f"{sample_id}:qa:{qa_idx}",
                    query=str(qa.get("question") or ""),
                    expected_sources=tuple(f"locomo/{sample_id}/dia/{item}" for item in evidence),
                    category=search_category,
                    metadata={
                        "sample_id": sample_id,
                        "category": qa.get("category", ""),
                        "answer": qa.get("answer", ""),
                    },
                )
            )
            if max_cases and len(cases) >= max_cases:
                return documents, cases
    return documents, cases


def _load_longmemeval(
    data: Any,
    *,
    max_cases: int | None,
    granularity: str,
) -> tuple[list[ExternalDocument], list[ExternalCase]]:
    instances = _as_list(data)
    documents: list[ExternalDocument] = []
    cases: list[ExternalCase] = []
    use_turns = granularity == "turn"

    for item in instances:
        if not isinstance(item, dict):
            continue
        question_id = str(item.get("question_id") or item.get("id") or f"question-{len(cases)}")
        search_category = f"longmemeval-{'turn' if use_turns else 'session'}:{question_id}"
        question = str(item.get("question") or "")
        session_ids = [str(value) for value in _as_list(item.get("haystack_session_ids"))]
        session_dates = [str(value) for value in _as_list(item.get("haystack_dates"))]
        sessions = _as_list(item.get("haystack_sessions"))
        answer_session_ids = [str(value) for value in _as_list(item.get("answer_session_ids"))]
        expected_turn_sources: list[str] = []

        for session_idx, session in enumerate(sessions):
            session_id = session_ids[session_idx] if session_idx < len(session_ids) else str(session_idx)
            session_date = session_dates[session_idx] if session_idx < len(session_dates) else ""
            turns = _as_list(session)
            if use_turns:
                for turn_idx, turn in enumerate(turns):
                    if not isinstance(turn, dict):
                        continue
                    source = f"longmemeval/{question_id}/session/{session_id}/turn/{turn_idx}"
                    if turn.get("has_answer") is True:
                        expected_turn_sources.append(source)
                    documents.append(
                        ExternalDocument(
                            title=f"LongMemEval {question_id} session {session_id} turn {turn_idx}",
                            content=_format_turn(question_id, session_id, session_date, turn_idx, turn),
                            source=source,
                            category=search_category,
                            tags=f"longmemeval,{question_id},session-{session_id},turn",
                        )
                    )
            else:
                content = "\n\n".join(
                    _format_turn(question_id, session_id, session_date, turn_idx, turn)
                    for turn_idx, turn in enumerate(turns)
                    if isinstance(turn, dict)
                )
                documents.append(
                    ExternalDocument(
                        title=f"LongMemEval {question_id} session {session_id}",
                        content=content,
                        source=f"longmemeval/{question_id}/session/{session_id}",
                        category=search_category,
                        tags=f"longmemeval,{question_id},session-{session_id}",
                    )
                )

        expected_sources = (
            tuple(expected_turn_sources)
            if use_turns
            else tuple(f"longmemeval/{question_id}/session/{session_id}" for session_id in answer_session_ids)
        )
        if not expected_sources:
            continue
        cases.append(
            ExternalCase(
                case_id=question_id,
                query=question,
                expected_sources=expected_sources,
                category=search_category,
                metadata={
                    "question_type": item.get("question_type", ""),
                    "question_date": item.get("question_date", ""),
                    "answer": item.get("answer", ""),
                    "answer_session_ids": answer_session_ids,
                },
            )
        )
        if max_cases and len(cases) >= max_cases:
            return documents, cases
    return documents, cases


def _format_turn(
    question_id: str,
    session_id: str,
    session_date: str,
    turn_idx: int,
    turn: dict[str, Any],
) -> str:
    return "\n".join(
        part
        for part in (
            f"question_id: {question_id}",
            f"session_id: {session_id}",
            f"session_date: {session_date}" if session_date else "",
            f"turn_index: {turn_idx}",
            f"role: {turn.get('role', '')}",
            f"content: {turn.get('content', '')}",
            "has_answer: true" if turn.get("has_answer") is True else "",
        )
        if part
    )


def _build_vault_db(db_path: Path, documents: list[ExternalDocument]) -> None:
    if db_path.exists():
        db_path.unlink()
    db = VaultDB(str(db_path)).connect()
    try:
        for doc in documents:
            db.add_knowledge(
                title=doc.title,
                content_raw=doc.content,
                category=doc.category,
                tags=doc.tags,
                trust=0.8,
                source=doc.source,
                scope="project",
                sensitivity="low",
                memory_type="benchmark_evidence",
            )
    finally:
        db.close()


def _prepare_semantic_provider(
    *,
    db_path: Path,
    mode: str,
    allow_hash: bool,
    hash_dim: int,
):
    if mode not in {"semantic", "hybrid"} or not allow_hash:
        return None
    from vault.semantic import DeterministicHashEmbeddingProvider, rebuild_semantic_index

    provider = DeterministicHashEmbeddingProvider(dim=hash_dim)
    db = VaultDB(str(db_path)).connect()
    try:
        rebuild_semantic_index(db, provider=provider, allow_hash=True)
    finally:
        db.close()
    return provider


def _evaluate_cases(
    *,
    db_path: Path,
    cases: list[ExternalCase],
    mode: str,
    limit: int,
    search_scope: str,
    progress_every: int,
    embed_provider: Any | None,
    semantic_vector_kind: str,
    allow_hash: bool,
) -> list[dict[str, Any]]:
    db = VaultDB(str(db_path)).connect()
    try:
        search = VaultSearch(db, embed_provider=embed_provider)
        results: list[dict[str, Any]] = []
        total = len(cases)
        for index, case in enumerate(cases, start=1):
            start = time.perf_counter()
            category = case.category if search_scope == "case" else None
            raw = search.search(
                case.query,
                mode=mode,
                limit=limit,
                category=category,
                use_rerank=False,
                semantic_vector_kind=semantic_vector_kind,
                allow_hash=allow_hash,
            )
            latency_ms = round((time.perf_counter() - start) * 1000, 3)
            expected = set(case.expected_sources)
            ranked = [
                {
                    "rank": idx + 1,
                    "id": item.get("id"),
                    "title": item.get("title", ""),
                    "source": item.get("source", ""),
                    "score": item.get("_score", item.get("score", 0)),
                }
                for idx, item in enumerate(raw)
            ]
            hit_rank = None
            for item in ranked:
                if str(item.get("source") or "") in expected:
                    hit_rank = int(item["rank"])
                    break
            results.append(
                {
                    "id": case.case_id,
                    "query": case.query,
                    "expected_sources": list(case.expected_sources),
                    "search_category": category,
                    "hit": hit_rank is not None,
                    "hit_rank": hit_rank,
                    "reciprocal_rank": 0.0 if hit_rank is None else round(1.0 / hit_rank, 6),
                    "latency_ms": latency_ms,
                    "results": ranked,
                    "metadata": case.metadata,
                }
            )
            if progress_every > 0 and (index % progress_every == 0 or index == total):
                print(f"[external-memory] evaluated {index}/{total} cases", file=sys.stderr)
        return results
    finally:
        db.close()


def _aggregate(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(case_results)
    hits = [item for item in case_results if item.get("hit")]
    ranks = [int(item["hit_rank"]) for item in hits if item.get("hit_rank")]
    latencies = [float(item.get("latency_ms", 0.0)) for item in case_results]
    return {
        "total_cases": total,
        "hit_cases": len(hits),
        "hit_rate": round(len(hits) / total, 6) if total else 0.0,
        "top1_hits": sum(1 for rank in ranks if rank == 1),
        "top3_hits": sum(1 for rank in ranks if rank <= 3),
        "top5_hits": sum(1 for rank in ranks if rank <= 5),
        "mean_reciprocal_rank": round(
            sum(float(item.get("reciprocal_rank", 0.0)) for item in case_results) / total,
            6,
        )
        if total
        else 0.0,
        "mean_latency_ms": round(statistics.mean(latencies), 3) if latencies else 0.0,
        "p95_latency_ms": round(_percentile(latencies, 0.95), 3) if latencies else 0.0,
    }


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * percentile))
    return ordered[index]


def _write_generated_search_qa(
    path: str | Path,
    *,
    benchmark: str,
    cases: list[ExternalCase],
) -> None:
    payload = {
        "version": 1,
        "name": f"{benchmark} retrieval evidence QA",
        "description": "Generated external benchmark retrieval cases. Evidence recall only; not final-answer QA.",
        "cases": [
            {
                "id": case.case_id,
                "query": case.query,
                "expected_sources": list(case.expected_sources),
                "search_category": case.category,
                "metadata": case.metadata,
            }
            for case in cases
        ],
    }
    write_json(path, payload)


class _maybe_temp_db:
    def __init__(self, db_path: str | Path | None):
        self.requested = Path(db_path) if db_path else None
        self._tempdir: tempfile.TemporaryDirectory[str] | None = None

    def __enter__(self) -> Path:
        if self.requested:
            self.requested.parent.mkdir(parents=True, exist_ok=True)
            return self.requested
        self._tempdir = tempfile.TemporaryDirectory(prefix="vault-external-memory-")
        return Path(self._tempdir.name) / "benchmark.db"

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._tempdir:
            self._tempdir.cleanup()


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run retrieval-only external memory benchmark adapters.")
    parser.add_argument("--benchmark", choices=["locomo", "longmemeval"], required=True)
    parser.add_argument("--input", required=True, help="Path to LoCoMo or LongMemEval JSON data.")
    parser.add_argument("--output", help="Write JSON report to this path.")
    parser.add_argument("--db-path", help="Optional Vault DB path. Defaults to a temporary DB.")
    parser.add_argument("--generated-qa", help="Optional generated Search QA JSON path.")
    parser.add_argument("--max-cases", type=int, help="Limit evidence-bearing cases for smoke runs.")
    parser.add_argument("--limit", type=int, default=10, help="Search top-k limit.")
    parser.add_argument("--mode", default="keyword", choices=["keyword", "semantic", "hybrid", "vector"])
    parser.add_argument("--semantic-vector-kind", default="claim", choices=["claim", "node"])
    parser.add_argument("--allow-hash", action="store_true", help="Allow deterministic hash embeddings for plumbing tests.")
    parser.add_argument("--hash-dim", type=int, default=32, help="Hash provider dimension when --allow-hash is set.")
    parser.add_argument("--quiet", action="store_true", help="Print only the aggregate summary.")
    parser.add_argument(
        "--search-scope",
        default="case",
        choices=["case", "global"],
        help="case searches only the case evidence pool; global searches the whole benchmark DB.",
    )
    parser.add_argument(
        "--reuse-db",
        action="store_true",
        help="Reuse an existing --db-path instead of rebuilding it.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=0,
        help="Print progress to stderr every N evaluated cases.",
    )
    parser.add_argument(
        "--granularity",
        default="auto",
        choices=["auto", "session", "turn"],
        help="LongMemEval indexing granularity; auto currently uses session.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    granularity = "session" if args.granularity == "auto" else args.granularity
    report = run_external_memory_retrieval(
        benchmark=args.benchmark,
        input_path=args.input,
        output_path=args.output,
        db_path=args.db_path,
        generated_qa_path=args.generated_qa,
        max_cases=args.max_cases,
        limit=args.limit,
        mode=args.mode,
        granularity=granularity,
        search_scope=args.search_scope,
        reuse_db=args.reuse_db,
        progress_every=args.progress_every,
        semantic_vector_kind=args.semantic_vector_kind,
        allow_hash=args.allow_hash,
        hash_dim=args.hash_dim,
    )
    if args.quiet:
        print(json.dumps(report["aggregate"], ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
