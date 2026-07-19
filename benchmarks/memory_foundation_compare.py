"""Paired benchmark for adding Vault governance to a memory engine.

This is not a vendor leaderboard.  It consumes one frozen external-engine
candidate pool, applies Vault's product read guard, and reports paired quality,
policy-exposure, and latency deltas.  Optional RRF fusion is a separate mode so
retrieval changes are not attributed to governance alone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import statistics
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from benchmarks.external_memory_compare import (  # noqa: E402
    _validate_run_for_fixture,
    fixture_digest,
)
from vault.access_policy import (  # noqa: E402
    can_write_memory,
    normalize_read_policy,
    normalize_write_policy,
)
from vault.governance_read_guard import (  # noqa: E402
    evaluate_governed_read,
    superseded_ids_from_snapshot,
)
from vault.db_lifecycle import parse_timestamp  # noqa: E402
from vault.privacy import scan_privacy  # noqa: E402
from vault.search_qa import write_json  # noqa: E402


PAIR_SCHEMA_VERSION = 1
DEFAULT_FIXED_CLOCK = "2026-07-19T00:00:00+00:00"
REASON_CODES = (
    "unapproved",
    "inactive",
    "deleted",
    "expired",
    "temporal_past",
    "temporal_future",
    "superseded",
    "private",
    "restricted",
    "sensitivity_capped",
    "unauthorized",
    "unknown_scope",
    "unknown_sensitivity",
    "privacy_blocked",
    "invalid_expiry",
    "invalid_temporal_metadata",
    "missing_provenance",
    "missing_canonical_memory",
)


def augment_run(
    *,
    fixture_path: str | Path,
    engine_run_path: str | Path,
    output_path: str | Path | None = None,
    vault_run_path: str | Path | None = None,
    mode: str = "guard-only",
    top_k: int = 10,
    candidate_pool_k: int = 40,
    rrf_k: int = 60,
) -> dict[str, Any]:
    """Apply the Vault read guard to a frozen engine candidate pool."""
    fixture = _read_json(fixture_path)
    engine_run = _read_json(engine_run_path)
    normalized_mode = str(mode or "guard-only").strip().lower()
    if normalized_mode not in {"guard-only", "rrf-fusion"}:
        raise ValueError("mode must be guard-only or rrf-fusion")
    if normalized_mode == "rrf-fusion" and not vault_run_path:
        raise ValueError("rrf-fusion requires --vault-run")
    if normalized_mode == "guard-only" and vault_run_path:
        raise ValueError("--vault-run is only valid with --mode rrf-fusion")

    top_k_i = _positive_int(top_k, name="top_k")
    pool_k_i = _positive_int(candidate_pool_k, name="candidate_pool_k")
    if pool_k_i < top_k_i:
        raise ValueError("candidate_pool_k must be greater than or equal to top_k")
    rrf_k_i = _positive_int(rrf_k, name="rrf_k")

    _strict_validate_run(fixture, engine_run, required_pool_k=pool_k_i)
    vault_run = _read_json(vault_run_path) if vault_run_path else None
    if vault_run is not None:
        _strict_validate_run(fixture, vault_run, required_pool_k=pool_k_i)

    documents = [_canonical_document(item) for item in fixture.get("documents", [])]
    documents_by_source = {
        str(document.get("source") or ""): document
        for document in documents
        if str(document.get("source") or "")
    }
    engine_cases = _cases_by_id(engine_run)
    vault_cases = _cases_by_id(vault_run or {})

    output_cases: list[dict[str, Any]] = []
    for fixture_case in fixture.get("cases", []):
        case_id = str(fixture_case.get("id") or "")
        engine_case = engine_cases.get(case_id, {})
        vault_case = vault_cases.get(case_id, {})
        augmentation_started = time.perf_counter()
        engine_candidates = _ranked_results(engine_case)[:pool_k_i]
        if normalized_mode == "rrf-fusion":
            candidates = _rrf_fuse(
                engine_candidates,
                _ranked_results(vault_case)[:pool_k_i],
                rrf_k=rrf_k_i,
                limit=pool_k_i,
            )
        else:
            candidates = [dict(result) for result in engine_candidates]

        read_policy = normalize_read_policy(
            agent_id=_case_value(fixture_case, "agent_id", ""),
            include_private=_case_value(fixture_case, "include_private", False),
            max_sensitivity=_case_value(fixture_case, "max_sensitivity", ""),
            allowed_statuses=("active",),
        )
        as_of = str(
            _case_value(fixture_case, "as_of", _fixture_clock(fixture))
            or _fixture_clock(fixture)
        )
        superseded_ids = superseded_ids_from_snapshot(documents, as_of=as_of)
        kept: list[dict[str, Any]] = []
        decisions: list[dict[str, Any]] = []
        for raw_rank, result in enumerate(candidates, start=1):
            source = str(result.get("source") or "")
            canonical = documents_by_source.get(source)
            if canonical is None:
                reason = "missing_provenance" if not source else "missing_canonical_memory"
                decisions.append(
                    {
                        "source": source,
                        "raw_rank": raw_rank,
                        "allowed": False,
                        "reason_codes": [reason],
                    }
                )
                continue
            decision = evaluate_governed_read(
                canonical,
                policy=read_policy,
                as_of=as_of,
                superseded_ids=superseded_ids,
                require_provenance=True,
            )
            trace = {
                "source": source,
                "canonical_id": canonical.get("id") or canonical.get("vault_knowledge_id"),
                "raw_rank": raw_rank,
                **decision.to_dict(),
            }
            decisions.append(trace)
            if decision.allowed and len(kept) < top_k_i:
                item = dict(result)
                item["original_rank"] = result.get("rank", raw_rank)
                item["rank"] = len(kept) + 1
                item["governance"] = {
                    "allowed": True,
                    "canonical_id": trace["canonical_id"],
                    "evaluated_at": trace["evaluated_at"],
                }
                kept.append(item)
        augmentation_latency_ms = round(
            (time.perf_counter() - augmentation_started) * 1000, 3
        )
        engine_latency = _optional_float(engine_case.get("latency_ms"))
        fusion_latency = _optional_float(vault_case.get("latency_ms")) if vault_run else 0.0
        total_latency = (
            round(engine_latency + fusion_latency + augmentation_latency_ms, 3)
            if engine_latency is not None and fusion_latency is not None
            else None
        )
        engine_cost = _optional_float(engine_case.get("cost_usd"))
        fusion_cost = _optional_float(vault_case.get("cost_usd")) if vault_run else None
        total_cost = (
            round(engine_cost + fusion_cost, 8)
            if vault_run and engine_cost is not None and fusion_cost is not None
            else engine_cost if not vault_run else None
        )
        output_cases.append(
            {
                "id": case_id,
                "query": fixture_case.get("query", engine_case.get("query", "")),
                "latency_ms": total_latency,
                "engine_latency_ms": (
                    round(engine_latency, 3) if engine_latency is not None else None
                ),
                "fusion_retrieval_latency_ms": (
                    round(fusion_latency, 3) if fusion_latency is not None else None
                ),
                "augmentation_latency_ms": augmentation_latency_ms,
                "cost_usd": total_cost,
                "candidate_pool_returned": len(candidates),
                "results": kept,
                "policy_decisions": decisions,
                "blocked_by_reason": dict(
                    sorted(
                        Counter(
                            reason
                            for decision in decisions
                            if not decision.get("allowed")
                            for reason in decision.get("reason_codes", [])
                        ).items()
                    )
                ),
            }
        )

    digest = fixture_digest(fixture)
    engine_run_digest = _generic_digest(engine_run)
    vault_run_digest = _generic_digest(vault_run) if vault_run else None
    payload = {
        "schema_version": PAIR_SCHEMA_VERSION,
        "artifact_type": "external_memory_comparison_run",
        "generated_at": _utc_now(),
        "benchmark": fixture.get("benchmark"),
        "fixture_digest": digest,
        "system": f"{engine_run.get('system', 'external-memory')}+vault",
        "system_version": engine_run.get("system_version", ""),
        "top_k": top_k_i,
        "candidate_pool_k": pool_k_i,
        "cases_total": len(fixture.get("cases", [])),
        "cases": output_cases,
        "artifact_bindings": {
            "engine_run_digest": engine_run_digest,
            "engine_system": engine_run.get("system", ""),
            "engine_system_version": engine_run.get("system_version", ""),
            "vault_run_digest": vault_run_digest,
            "vault_system": vault_run.get("system", "") if vault_run else "",
        },
        "augmentation": {
            "mode": normalized_mode,
            "guard": "vault.governance_read_guard.evaluate_governed_read",
            "source_of_truth": "fixture canonical snapshot (policy replay)",
            "rrf_k": rrf_k_i if normalized_mode == "rrf-fusion" else None,
            "engine_system": engine_run.get("system", ""),
            "vault_system": vault_run.get("system", "") if vault_run else "",
            "fixed_candidate_pool": True,
        },
        "engineering": dict(engine_run.get("engineering") or {}),
        "manifest": _environment_manifest(fixed_clock=_fixture_clock(fixture)),
        "notes": [
            "This artifact is a deterministic policy replay over a frozen candidate pool.",
            "Guard-only and RRF-fusion are separate modes and must be reported as separate rows.",
            "Provider lifecycle claims require governance-run or a live-provider track in addition to this artifact.",
        ],
    }
    if output_path:
        write_json(output_path, payload)
    return payload


def score_pair(
    *,
    fixture_path: str | Path,
    baseline_run_path: str | Path,
    augmented_run_path: str | Path,
    output_path: str | Path | None = None,
    top_k: int | None = None,
) -> dict[str, Any]:
    """Score A and A+B under the same fixture and return explicit deltas."""
    fixture = _read_json(fixture_path)
    baseline = _read_json(baseline_run_path)
    augmented = _read_json(augmented_run_path)
    default_k = int(augmented.get("top_k") or 0)
    top_k_i = _positive_int(top_k if top_k is not None else default_k, name="top_k")
    if top_k_i > default_k:
        raise ValueError("score top_k cannot exceed the augmented run top_k")
    required_pool = int(augmented.get("candidate_pool_k") or top_k_i)
    _strict_validate_run(fixture, baseline, required_pool_k=required_pool)
    _strict_validate_run(fixture, augmented, required_pool_k=top_k_i)
    if baseline.get("fixture_digest") != augmented.get("fixture_digest"):
        raise ValueError("baseline and augmented fixture digests must match")
    baseline_digest = _generic_digest(baseline)
    artifact_bindings = augmented.get("artifact_bindings") or {}
    if artifact_bindings.get("engine_run_digest") != baseline_digest:
        raise ValueError("augmented run is not bound to the supplied baseline artifact digest")
    if artifact_bindings.get("engine_system") != baseline.get("system", ""):
        raise ValueError("augmented run engine system does not match the supplied baseline")
    augmentation = augmented.get("augmentation") or {}
    if augmentation.get("engine_system") != baseline.get("system", ""):
        raise ValueError("augmented run provenance does not match the supplied baseline system")

    baseline_cases = _cases_by_id(baseline)
    augmented_cases = _cases_by_id(augmented)
    paired_cases: list[dict[str, Any]] = []
    for fixture_case in fixture.get("cases", []):
        case_id = str(fixture_case.get("id") or "")
        base_case = baseline_cases.get(case_id, {})
        aug_case = augmented_cases.get(case_id, {})
        base_score = _score_case_at_k(fixture_case, base_case, top_k=top_k_i)
        aug_score = _score_case_at_k(fixture_case, aug_case, top_k=top_k_i)
        paired_cases.append(
            {
                "id": case_id,
                "baseline": base_score,
                "augmented": aug_score,
                "delta": {
                    "valid_recall": _optional_delta(
                        base_score["valid_recall"], aug_score["valid_recall"], precision=6
                    ),
                    "valid_precision": _optional_delta(
                        base_score["valid_precision"], aug_score["valid_precision"], precision=6
                    ),
                    "reciprocal_rank": _optional_delta(
                        base_score["valid_reciprocal_rank"],
                        aug_score["valid_reciprocal_rank"],
                        precision=6,
                    ),
                    "forbidden_exposures": aug_score["forbidden_exposures"]
                    - base_score["forbidden_exposures"],
                    "latency_ms": _optional_delta(
                        base_case.get("latency_ms"), aug_case.get("latency_ms"), precision=3
                    ),
                    "cost_usd": _optional_delta(
                        base_case.get("cost_usd"), aug_case.get("cost_usd"), precision=8
                    ),
                },
            }
        )

    base_aggregate = _aggregate_pair_side(paired_cases, side="baseline", run=baseline)
    aug_aggregate = _aggregate_pair_side(paired_cases, side="augmented", run=augmented)
    paired_latency_base, paired_latency_aug = _paired_numeric_values(
        baseline_cases,
        augmented_cases,
        field="latency_ms",
    )
    paired_cost_base, paired_cost_aug = _paired_numeric_values(
        baseline_cases,
        augmented_cases,
        field="cost_usd",
    )
    paired_base_latency = _latency_summary(paired_latency_base)
    paired_aug_latency = _latency_summary(paired_latency_aug)
    paired_base_cost = _cost_summary(paired_cost_base)
    paired_aug_cost = _cost_summary(paired_cost_aug)
    cutoffs = sorted({cutoff for cutoff in (1, 5, 10, top_k_i) if cutoff <= top_k_i})
    base_at_k = _aggregate_at_cutoffs(fixture, baseline, cutoffs=cutoffs)
    aug_at_k = _aggregate_at_cutoffs(fixture, augmented, cutoffs=cutoffs)
    base_aggregate["at_k"] = base_at_k
    aug_aggregate["at_k"] = aug_at_k
    scorer_manifest = _environment_manifest(fixed_clock=_fixture_clock(fixture))
    payload = {
        "schema_version": PAIR_SCHEMA_VERSION,
        "artifact_type": "memory_foundation_paired_score",
        "generated_at": _utc_now(),
        "benchmark": fixture.get("benchmark"),
        "fixture_digest": fixture_digest(fixture),
        "top_k": top_k_i,
        "candidate_pool_k": required_pool,
        "baseline_system": baseline.get("system", ""),
        "baseline_system_version": baseline.get("system_version", ""),
        "augmented_system": augmented.get("system", ""),
        "augmentation_mode": augmentation.get("mode", ""),
        "artifact_bindings": {
            "baseline_run_digest": baseline_digest,
            "augmented_run_digest": _generic_digest(augmented),
            "augmented_engine_run_digest": artifact_bindings.get("engine_run_digest"),
        },
        "stage_source_state": {
            "baseline": _run_benchmark_source(baseline),
            "augmentation": _foundation_source_state(augmented.get("manifest") or {}),
            "scorer": _foundation_source_state(scorer_manifest),
        },
        "baseline": base_aggregate,
        "augmented": aug_aggregate,
        "delta": {
            "valid_recall": _optional_delta(
                base_aggregate["valid_recall"], aug_aggregate["valid_recall"], precision=6
            ),
            "valid_precision": _optional_delta(
                base_aggregate["valid_precision"], aug_aggregate["valid_precision"], precision=6
            ),
            "valid_hit_rate": _optional_delta(
                base_aggregate["valid_hit_rate"], aug_aggregate["valid_hit_rate"], precision=6
            ),
            "valid_mrr": _optional_delta(
                base_aggregate["valid_mrr"], aug_aggregate["valid_mrr"], precision=6
            ),
            "forbidden_exposures": aug_aggregate["forbidden_exposures"]
            - base_aggregate["forbidden_exposures"],
            "forbidden_exposure_case_rate": _optional_delta(
                base_aggregate["forbidden_exposure_case_rate"],
                aug_aggregate["forbidden_exposure_case_rate"],
                precision=6,
            ),
            "relevant_blocked_by_policy": aug_aggregate["relevant_blocked_by_policy"]
            - base_aggregate["relevant_blocked_by_policy"],
            "latency_available": bool(paired_latency_base),
            "latency_paired_cases": len(paired_latency_base),
            "latency_mean_ms": _summary_delta(
                paired_base_latency, paired_aug_latency, "mean_ms", precision=3
            ),
            "latency_p95_ms": _summary_delta(
                paired_base_latency, paired_aug_latency, "p95_ms", precision=3
            ),
            "cost_available": bool(paired_cost_base),
            "cost_paired_cases": len(paired_cost_base),
            "cost_total_usd": _summary_delta(
                paired_base_cost, paired_aug_cost, "total_usd", precision=8
            ),
            "cost_mean_usd": _summary_delta(
                paired_base_cost, paired_aug_cost, "mean_usd", precision=8
            ),
            "at_k": {
                key: {
                    metric: _optional_delta(
                        base_at_k[key][metric], aug_at_k[key][metric], precision=6
                    )
                    for metric in (
                        "valid_recall",
                        "valid_precision",
                        "valid_hit_rate",
                        "valid_mrr",
                        "forbidden_exposure_case_rate",
                    )
                }
                for key in base_at_k
            },
        },
        "cases_total": len(paired_cases),
        "cases": paired_cases,
        "manifest": scorer_manifest,
        "notes": [
            "Valid Recall requires an expected source to remain policy-valid for the case.",
            "Forbidden-source exposure and latency are reported separately from quality.",
            "This scorer is retrieval-only and is not an official LoCoMo or LongMemEval QA score.",
        ],
    }
    if output_path:
        write_json(output_path, payload)
    return payload


def summarize_repeats(
    *,
    fixture_path: str | Path,
    pair_paths: list[str | Path],
    run_paths: list[str | Path],
    execution_evidence_paths: list[str | Path] | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Aggregate clean-state paired repeats without treating missing values as zero."""
    if len(pair_paths) != len(run_paths):
        raise ValueError("pair_paths and run_paths must have the same length")
    if not pair_paths:
        raise ValueError("at least one repeat is required")
    fixture = _read_json(fixture_path)
    pairs = [_read_json(path) for path in pair_paths]
    runs = [_read_json(path) for path in run_paths]
    run_digests = [_generic_digest(run) for run in runs]
    pair_digests = [_generic_digest(pair) for pair in pairs]
    execution_evidence = _execution_evidence_by_run_digest(execution_evidence_paths or [])
    if len(set(run_digests)) != len(run_digests):
        raise ValueError("repeat inputs contain a duplicate run artifact")
    if len(set(pair_digests)) != len(pair_digests):
        raise ValueError("repeat inputs contain a duplicate pair artifact")
    digest = fixture_digest(fixture)
    expected_benchmark = fixture.get("benchmark")

    reference_signature: str | None = None
    clean_state_identities: list[str] = []
    for index, (pair, run, run_digest) in enumerate(
        zip(pairs, runs, run_digests, strict=True), start=1
    ):
        if pair.get("artifact_type") != "memory_foundation_paired_score":
            raise ValueError(f"repeat {index} pair artifact_type is invalid")
        if pair.get("benchmark") != expected_benchmark or run.get("benchmark") != expected_benchmark:
            raise ValueError(f"repeat {index} benchmark does not match fixture")
        if pair.get("fixture_digest") != digest or run.get("fixture_digest") != digest:
            raise ValueError(f"repeat {index} fixture digest does not match")
        required_pool = int(pair.get("candidate_pool_k") or 0)
        _strict_validate_run(fixture, run, required_pool_k=required_pool)
        bindings = pair.get("artifact_bindings") or {}
        if bindings.get("baseline_run_digest") != run_digest:
            raise ValueError(f"repeat {index} pair is not bound to its supplied run artifact")
        if bindings.get("augmented_engine_run_digest") != run_digest:
            raise ValueError(f"repeat {index} augmented artifact was not derived from its run")
        if pair.get("baseline_system") != run.get("system", ""):
            raise ValueError(f"repeat {index} pair baseline system does not match its run")
        clean_state_identities.append(_provider_clean_state_identity(run))
        signature = json.dumps(
            {
                "system": run.get("system"),
                "system_version": run.get("system_version"),
                "track": run.get("track"),
                "retrieval_mode": run.get("retrieval_mode"),
                "search_scope": run.get("search_scope"),
                "top_k": run.get("top_k"),
                "candidate_pool_k": run.get("candidate_pool_k"),
                "augmentation_mode": pair.get("augmentation_mode"),
                "augmented_system": pair.get("augmented_system"),
                "provider_config": (run.get("manifest") or {}).get("provider_config"),
                "provider_input": (run.get("manifest") or {}).get("provider_input"),
                "model_revisions": ((run.get("manifest") or {}).get("model_cache") or {}).get(
                    "revisions_after_run"
                ),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        if reference_signature is None:
            reference_signature = signature
        elif signature != reference_signature:
            raise ValueError(f"repeat {index} provider configuration does not match repeat 1")

    populated_identities = [identity for identity in clean_state_identities if identity]
    if len(set(populated_identities)) != len(populated_identities):
        raise ValueError("repeat inputs reuse a provider clean-state identity")
    clean_state_identities_complete = len(populated_identities) == len(runs)

    baseline_metrics = _repeat_side_metrics(pairs, side="baseline")
    augmented_metrics = _repeat_side_metrics(pairs, side="augmented")
    delta_metrics = _repeat_delta_metrics(pairs)
    stability = _repeat_ranking_stability(fixture, runs)
    provider_integrity_passed = all(_provider_retrieval_integrity_passed(run) for run in runs)
    provider_gold_isolated = all(
        _provider_gold_labels_isolated(run, evaluation_fixture_digest=digest)
        for run in runs
    )
    provider_execution_verified = all(
        _provider_execution_evidence_passed(
            run,
            run_digest=run_digest,
            evidence=execution_evidence.get(run_digest),
        )
        for run, run_digest in zip(runs, run_digests, strict=True)
    )
    source_chain_clean = all(
        _source_chain_is_clean_and_bound(pair, run)
        for pair, run in zip(pairs, runs, strict=True)
    )
    native_preflight_statuses = [_native_retrieval_preflight_passed(run) for run in runs]
    native_preflight_applicable = any(value is not None for value in native_preflight_statuses)
    native_preflight_passed: bool | None = None
    if native_preflight_applicable:
        native_preflight_passed = all(value is True for value in native_preflight_statuses)
    zero_index_failures = all(int(run.get("documents_failed") or 0) == 0 for run in runs)
    environment = _environment_manifest(fixed_clock=_fixture_clock(fixture))
    release_gate_reasons: list[str] = []
    if len(runs) < 5:
        release_gate_reasons.append("fewer_than_five_clean_state_repeats")
    if not clean_state_identities_complete:
        release_gate_reasons.append("provider_clean_state_identity_missing")
    if not provider_integrity_passed:
        release_gate_reasons.append("provider_retrieval_integrity_not_passed")
    if not provider_gold_isolated:
        release_gate_reasons.append("provider_gold_labels_not_isolated")
    if not provider_execution_verified:
        release_gate_reasons.append("provider_clean_state_execution_not_verified")
    if not source_chain_clean:
        release_gate_reasons.append("artifact_source_chain_not_clean_or_not_bound")
    if not zero_index_failures:
        release_gate_reasons.append("provider_index_failures")
    if environment.get("git_dirty"):
        release_gate_reasons.append("benchmark_harness_worktree_dirty")

    payload = {
        "schema_version": PAIR_SCHEMA_VERSION,
        "artifact_type": "memory_foundation_repeat_summary",
        "generated_at": _utc_now(),
        "benchmark": expected_benchmark,
        "fixture_digest": digest,
        "system": runs[0].get("system", ""),
        "system_version": runs[0].get("system_version", ""),
        "track": runs[0].get("track", ""),
        "retrieval_mode": runs[0].get("retrieval_mode", ""),
        "repeats": len(runs),
        "cases_per_repeat": len(fixture.get("cases", [])),
        "baseline": baseline_metrics,
        "augmented": augmented_metrics,
        "delta": delta_metrics,
        "latency": {
            "setup_ms": _metric_distribution(run.get("setup_latency_ms") for run in runs),
            "ingest_ms": _metric_distribution(run.get("ingest_latency_ms") for run in runs),
            "index_total_ms": _metric_distribution(run.get("index_latency_ms") for run in runs),
        },
        "ranking_stability": stability,
        "quality_gates": {
            "provider_retrieval_integrity_passed_all_repeats": provider_integrity_passed,
            "provider_gold_labels_excluded_all_repeats": provider_gold_isolated,
            "provider_clean_state_execution_verified_all_repeats": provider_execution_verified,
            "artifact_source_chain_clean_and_bound_all_repeats": source_chain_clean,
            "provider_native_preflight_applicable": native_preflight_applicable,
            "provider_native_preflight_passed_all_repeats": native_preflight_passed,
            "zero_index_failures_all_repeats": zero_index_failures,
            "same_provider_configuration": True,
            "unique_run_artifacts": True,
            "unique_pair_artifacts": True,
            "unique_clean_state_identities": clean_state_identities_complete,
            "missing_metrics_are_not_zero": True,
            "clean_state_repeats_minimum_met": len(runs) >= 5,
        },
        "publishable": not release_gate_reasons,
        "release_gate_reasons": release_gate_reasons,
        "manifest": environment,
        "notes": [
            "All quality deltas are paired on the same case ids and frozen candidate pool per repeat.",
            "This is a controlled retrieval-only track, not a full agent answer-quality leaderboard.",
            "Missing latency or cost values remain unavailable and are never converted to zero.",
        ],
    }
    if output_path:
        write_json(output_path, payload)
    return payload


def _native_retrieval_preflight_passed(run: dict[str, Any]) -> bool | None:
    status = (((run.get("manifest") or {}).get("effective_retrieval") or {}).get("preflight_status"))
    if status is None:
        return None
    return status == "passed"


def _provider_clean_state_identity(run: dict[str, Any]) -> str:
    system = str(run.get("system") or "")
    if system == "mem0":
        collection = str(run.get("collection_name") or "").strip()
        namespace = str(run.get("run_namespace") or "").strip()
        return f"mem0:{collection}:{namespace}" if collection and namespace else ""
    if system == "rohitg00/agentmemory":
        isolation = (run.get("manifest") or {}).get("isolation") or {}
        store = str(
            isolation.get("fresh_store_id") or isolation.get("fresh_store_id_digest") or ""
        ).strip()
        run_id = str(run.get("run_id") or "").strip()
        return f"agentmemory:{store}:{run_id}" if store and run_id else ""
    run_id = str(run.get("run_id") or "").strip()
    return f"{system}:{run_id}" if system and run_id else ""


def _execution_evidence_by_run_digest(
    paths: list[str | Path],
) -> dict[str, dict[str, Any]]:
    evidence_by_digest: dict[str, dict[str, Any]] = {}
    for index, path in enumerate(paths, start=1):
        evidence = _read_json(path)
        if evidence.get("schema_version") != 1:
            raise ValueError(f"execution evidence {index} schema_version must be 1")
        if evidence.get("artifact_type") != "provider_execution_evidence":
            raise ValueError(f"execution evidence {index} artifact_type is invalid")
        run_digest = str(evidence.get("run_artifact_digest") or "")
        if not _valid_sha256_digest(run_digest):
            raise ValueError(f"execution evidence {index} run_artifact_digest is invalid")
        if run_digest in evidence_by_digest:
            raise ValueError("execution evidence contains a duplicate run artifact digest")
        evidence_by_digest[run_digest] = evidence
    return evidence_by_digest


def _provider_execution_evidence_passed(
    run: dict[str, Any],
    *,
    run_digest: str,
    evidence: dict[str, Any] | None,
) -> bool:
    system = str(run.get("system") or "")
    manifest = run.get("manifest") or {}
    if system == "mem0":
        isolation = manifest.get("isolation") or {}
        return (
            isolation.get("clean_state_paths_checked_before_run") is True
            and isolation.get("clean_state_paths_absent_before_run") is True
            and isolation.get("provider_handles_closed") is True
            and isolation.get("collection_name") == run.get("collection_name")
            and isolation.get("run_namespace") == run.get("run_namespace")
            and all(
                _valid_sha256_digest(str(isolation.get(field) or ""))
                for field in (
                    "vector_store_identity_digest",
                    "history_db_identity_digest",
                    "mem0_dir_identity_digest",
                )
            )
        )
    if system == "vault":
        database = manifest.get("database") or {}
        quality_gate = manifest.get("provider_quality_gate") or {}
        return (
            quality_gate.get("passed") is True
            and database.get("ephemeral") is True
            and database.get("reuse") is False
            and bool(run.get("run_id"))
        )
    if evidence is None:
        return False
    if evidence.get("system") != system:
        return False
    if evidence.get("run_artifact_digest") != run_digest:
        return False
    if str(evidence.get("run_id") or "") != str(run.get("run_id") or ""):
        return False
    observed = evidence.get("provider_observed") or {}
    lifecycle = evidence.get("lifecycle") or {}
    isolation = evidence.get("isolation") or {}
    dependencies = evidence.get("dependencies") or {}
    if str(observed.get("version") or "") != str(run.get("system_version") or ""):
        return False
    if not (
        lifecycle.get("server_started") is True
        and lifecycle.get("readiness_passed") is True
        and int(lifecycle.get("adapter_errors") or 0) == 0
        and int(lifecycle.get("adapter_timeouts") or 0) == 0
        and lifecycle.get("server_stopped") is True
        and lifecycle.get("ports_closed") is True
    ):
        return False
    if int(isolation.get("memory_count_before", -1)) != 0:
        return False
    if isolation.get("fresh_store_created") is not True:
        return False
    if not _valid_sha256_digest(str(isolation.get("store_root_digest") or "")):
        return False
    if not _valid_sha256_digest(str(isolation.get("worker_registration_id_digest") or "")):
        return False
    if not all(
        _valid_sha256_digest(str(dependencies.get(field) or ""))
        for field in ("provider_lock_digest", "provider_tree_digest")
    ):
        return False
    if system != "rohitg00/agentmemory":
        return True
    provider_config = manifest.get("provider_config") or {}
    expected_store_digest = str(
        (manifest.get("isolation") or {}).get("fresh_store_id_digest") or ""
    )
    raw_store_id = str((manifest.get("isolation") or {}).get("fresh_store_id") or "")
    if not expected_store_digest and raw_store_id:
        expected_store_digest = f"sha256:{hashlib.sha256(raw_store_id.encode('utf-8')).hexdigest()}"
    return (
        isolation.get("fresh_store_id_digest") == expected_store_digest
        and observed.get("embedding_provider") == provider_config.get("embedding_provider")
        and observed.get("embedding_model") == provider_config.get("embedding_model")
        and int(observed.get("embedding_dims") or 0)
        == int(provider_config.get("embedding_dims") or 0)
    )


def _valid_sha256_digest(value: str) -> bool:
    return bool(re.fullmatch(r"sha256:[0-9a-f]{64}", value))


def _provider_gold_labels_isolated(
    run: dict[str, Any],
    *,
    evaluation_fixture_digest: str,
) -> bool:
    provenance = ((run.get("manifest") or {}).get("provider_input") or {})
    provider_input_digest = str(provenance.get("provider_input_digest") or "")
    recorded_evaluation_digest = str(
        provenance.get("evaluation_fixture_digest") or ""
    )
    return (
        provenance.get("gold_labels_excluded") is True
        and _valid_sha256_digest(provider_input_digest)
        and provider_input_digest != evaluation_fixture_digest
        and recorded_evaluation_digest == evaluation_fixture_digest
        and str(run.get("fixture_digest") or "") == evaluation_fixture_digest
    )


def _run_benchmark_source(run: dict[str, Any]) -> dict[str, Any]:
    manifest = run.get("manifest") or {}
    source = manifest.get("benchmark_source")
    if isinstance(source, dict):
        return dict(source)
    legacy = manifest.get("source_control")
    if isinstance(legacy, dict):
        return {
            "git_sha": legacy.get("git_sha"),
            "git_dirty": legacy.get("git_dirty"),
            "adapter_file": "",
            "adapter_digest": "",
            "dependency_lock_digest": legacy.get("dependency_lock_digest"),
        }
    return {}


def _foundation_source_state(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "git_sha": manifest.get("git_sha"),
        "git_dirty": manifest.get("git_dirty"),
        "adapter_file": Path(__file__).name,
        "adapter_digest": manifest.get("adapter_digest"),
        "dependency_lock_digest": manifest.get("dependency_lock_digest"),
    }


def _source_chain_is_clean_and_bound(pair: dict[str, Any], run: dict[str, Any]) -> bool:
    stages = pair.get("stage_source_state") or {}
    baseline = stages.get("baseline") or {}
    augmentation = stages.get("augmentation") or {}
    scorer = stages.get("scorer") or {}
    run_source = _run_benchmark_source(run)
    if baseline != run_source:
        return False
    values = (baseline, augmentation, scorer)
    if any(value.get("git_dirty") is not False for value in values):
        return False
    if any(not str(value.get("git_sha") or "") for value in values):
        return False
    if any(not str(value.get("adapter_digest") or "") for value in values):
        return False
    if any(not str(value.get("dependency_lock_digest") or "") for value in values):
        return False
    git_shas = {str(value["git_sha"]) for value in values}
    lock_digests = {str(value["dependency_lock_digest"]) for value in values}
    return len(git_shas) == 1 and len(lock_digests) == 1


def _provider_retrieval_integrity_passed(run: dict[str, Any]) -> bool:
    """Apply a provider-specific fail-closed retrieval integrity gate.

    mem0 exposes a native retrieval preflight.  The AgentMemory adapter cannot
    inspect its internal model objects, so its equivalent gate is complete
    run-local id provenance plus an explicit fresh-store attestation.  Unknown
    providers must add ``manifest.provider_quality_gate.passed`` rather than
    being accepted implicitly.
    """
    manifest = run.get("manifest") or {}
    explicit = manifest.get("provider_quality_gate") or {}
    if isinstance(explicit.get("passed"), bool):
        return bool(explicit["passed"])

    native_preflight = _native_retrieval_preflight_passed(run)
    if native_preflight is not None:
        return native_preflight

    if run.get("system") != "rohitg00/agentmemory":
        return False
    isolation = manifest.get("isolation") or {}
    source_mapping = manifest.get("source_mapping") or {}
    records = source_mapping.get("records")
    if not isinstance(records, list):
        return False
    attempted = int(run.get("documents_attempted") or 0)
    indexed = int(run.get("documents_indexed") or 0)
    if attempted <= 0 or attempted != indexed or int(run.get("documents_failed") or 0) != 0:
        return False
    if isolation.get("fresh_store_required") is not True:
        return False
    if not str(isolation.get("fresh_store_id") or isolation.get("fresh_store_id_digest") or "").strip():
        return False
    if int(isolation.get("unmapped_result_ids") or 0) != 0 or len(records) != indexed:
        return False
    memory_ids = [str(record.get("memory_id") or "") for record in records if isinstance(record, dict)]
    sources = [str(record.get("source") or "") for record in records if isinstance(record, dict)]
    return (
        len(memory_ids) == indexed
        and all(memory_ids)
        and all(sources)
        and len(set(memory_ids)) == indexed
        and len(set(sources)) == indexed
    )


def _repeat_side_metrics(pairs: list[dict[str, Any]], *, side: str) -> dict[str, Any]:
    return {
        field: _metric_distribution(pair.get(side, {}).get(field) for pair in pairs)
        for field in (
            "valid_hit_rate",
            "valid_mrr",
            "valid_precision",
            "valid_recall",
            "forbidden_exposure_case_rate",
        )
    } | {
        "query_latency_mean_ms": _metric_distribution(
            (pair.get(side, {}).get("latency") or {}).get("mean_ms") for pair in pairs
        ),
        "query_latency_p95_ms": _metric_distribution(
            (pair.get(side, {}).get("latency") or {}).get("p95_ms") for pair in pairs
        ),
    }


def _repeat_delta_metrics(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        field: _metric_distribution(pair.get("delta", {}).get(field) for pair in pairs)
        for field in (
            "valid_hit_rate",
            "valid_mrr",
            "valid_precision",
            "valid_recall",
            "forbidden_exposure_case_rate",
            "latency_mean_ms",
            "latency_p95_ms",
        )
    }


def _metric_distribution(values: Iterable[Any]) -> dict[str, Any]:
    items = [value for value in (_optional_float(item) for item in values) if value is not None]
    if not items:
        return {
            "available": False,
            "count": 0,
            "mean": None,
            "stdev": None,
            "min": None,
            "max": None,
        }
    return {
        "available": True,
        "count": len(items),
        "mean": round(statistics.fmean(items), 6),
        "stdev": round(statistics.pstdev(items), 6),
        "min": round(min(items), 6),
        "max": round(max(items), 6),
    }


def _repeat_ranking_stability(
    fixture: dict[str, Any],
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    run_cases = [_cases_by_id(run) for run in runs]
    per_case: list[dict[str, Any]] = []
    for fixture_case in fixture.get("cases", []):
        case_id = str(fixture_case.get("id") or "")
        rankings = [
            tuple(str(result.get("source") or "") for result in _ranked_results(cases[case_id]))
            for cases in run_cases
        ]
        top1_values = [ranking[0] if ranking else "" for ranking in rankings]
        top1_count = max(Counter(top1_values).values()) if top1_values else 0
        per_case.append(
            {
                "id": case_id,
                "top1_agreement_rate": round(top1_count / len(runs), 6),
                "unique_full_rankings": len(set(rankings)),
                "full_ranking_stable": len(set(rankings)) == 1,
            }
        )
    return {
        "cases": per_case,
        "mean_top1_agreement_rate": _mean(item["top1_agreement_rate"] for item in per_case),
        "min_top1_agreement_rate": min(
            (item["top1_agreement_rate"] for item in per_case),
            default=None,
        ),
        "full_ranking_stable_case_rate": (
            round(sum(item["full_ranking_stable"] for item in per_case) / len(per_case), 6)
            if per_case
            else None
        ),
    }


def run_governance_suite(
    *,
    fixture_path: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run deterministic policy-helper cases in a public governance fixture.

    Event-sequence cases backed by a temporary SQLite provider are dispatched by
    ``scenario.kind``.  Simple read/write/privacy cases use the same core policy
    helpers and are labelled ``policy_replay`` in their trace.
    """
    fixture = _read_json(fixture_path)
    cases = list(fixture.get("cases") or [])
    if not cases:
        cases = _legacy_governance_cases(fixture)
    fixed_clock = str(fixture.get("fixed_clock") or "")
    if not fixed_clock or parse_timestamp(fixed_clock) is None:
        raise ValueError("governance fixture requires a valid fixed_clock")
    case_ids = [str(case.get("id") or "") for case in cases]
    if any(not case_id for case_id in case_ids):
        raise ValueError("governance fixture case ids must be non-empty")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("governance fixture contains duplicate case ids")
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="vault-gov-bench-") as temp_dir:
        for case in cases:
            results.append(_run_governance_case(case, Path(temp_dir)))
    failed = sum(1 for item in results if item.get("status") == "fail")
    expected_gaps = sum(1 for item in results if item.get("status") == "expected_gap")
    passed = sum(1 for item in results if item.get("status") == "pass")
    payload = {
        "schema_version": PAIR_SCHEMA_VERSION,
        "artifact_type": "vault_governance_benchmark_run",
        "generated_at": _utc_now(),
        "benchmark": fixture.get("benchmark", "VaultGovBench"),
        "fixture_version": fixture.get("fixture_version", fixture.get("version", "")),
        "fixture_digest": _generic_digest(fixture),
        "status": "pass" if failed == 0 else "fail",
        "fixed_clock": _fixture_clock(fixture),
        "cases_total": len(results),
        "cases_passed": passed,
        "cases_failed": failed,
        "capability_gaps_total": expected_gaps,
        "cases": results,
        "manifest": _environment_manifest(fixed_clock=_fixture_clock(fixture)),
        "notes": [
            "Expected capability gaps are reported and do not count as passing capabilities.",
            "Policy replay cases and live SQLite provider cases are labelled separately.",
        ],
    }
    if output_path:
        write_json(output_path, payload)
    return payload


def _run_governance_case(case: dict[str, Any], temp_root: Path) -> dict[str, Any]:
    kind = str(case.get("kind") or case.get("type") or "").strip().lower()
    if kind in {"read", "read_policy"}:
        row = _canonical_document(case.get("memory") or case.get("row") or {})
        query = case.get("query_policy") or case.get("policy") or {}
        decision = evaluate_governed_read(
            row,
            agent_id=str(query.get("agent_id") or ""),
            include_private=bool(query.get("include_private")),
            max_sensitivity=str(query.get("max_sensitivity") or ""),
            as_of=str(case.get("as_of") or DEFAULT_FIXED_CLOCK),
            superseded_ids={int(value) for value in case.get("superseded_ids", [])},
            require_provenance=bool(case.get("require_provenance", True)),
        )
        observed = {"allowed": decision.allowed, "reason_codes": list(decision.reason_codes)}
        expected_allowed = bool(case.get("expected_allowed", case.get("expected_visible", False)))
        expected_reason = str(case.get("expected_reason") or "")
        fallback_match = decision.allowed == expected_allowed and (
            not expected_reason or expected_reason in decision.reason_codes
        )
        matched = _matches_expected(case, observed, fallback=fallback_match)
        return _case_result(
            case,
            matched=matched,
            observed=observed,
            execution=str(case.get("execution_mode") or "policy_replay"),
        )
    if kind in {"write", "write_policy"}:
        metadata = case.get("memory") or case.get("metadata") or {}
        policy_data = case.get("write_policy") or case.get("policy") or {}
        policy = normalize_write_policy(**policy_data)
        allowed, reason = can_write_memory(metadata, policy)
        privacy = scan_privacy(str(metadata.get("content") or ""))
        observed_allowed = allowed and privacy["status"] != "fail"
        observed = {
            "allowed": observed_allowed,
            "write_policy_allowed": allowed,
            "write_policy_reason": reason,
            "privacy_status": privacy["status"],
        }
        fallback_match = observed_allowed == bool(case.get("expected_allowed", False))
        matched = _matches_expected(case, observed, fallback=fallback_match)
        return _case_result(
            case,
            matched=matched,
            observed=observed,
            execution=str(case.get("execution_mode") or "policy_replay"),
        )
    if kind in {"privacy", "privacy_gate"}:
        privacy = scan_privacy(str(case.get("content") or ""))
        observed = {"privacy_status": privacy["status"], "findings_total": len(privacy["findings"])}
        fallback_match = privacy["status"] == str(case.get("expected_status") or "")
        matched = _matches_expected(case, observed, fallback=fallback_match)
        return _case_result(
            case,
            matched=matched,
            observed=observed,
            execution=str(case.get("execution_mode") or "policy_replay"),
        )

    # Dynamic fixture kinds are implemented against the real provider in a
    # dedicated helper to keep this scorer readable.
    observed = _run_dynamic_provider_case(case, temp_root)
    expected_outcome = case.get("expected_outcome")
    fallback_match = (
        observed.get("outcome") == expected_outcome
        if expected_outcome is not None
        else bool(observed.get("ok"))
    )
    matched = _matches_expected(case, observed, fallback=fallback_match)
    return _case_result(
        case,
        matched=matched,
        observed=observed,
        execution=str(case.get("execution_mode") or "sqlite_provider"),
    )


def _matches_expected(
    case: dict[str, Any],
    observed: dict[str, Any],
    *,
    fallback: bool,
) -> bool:
    """Match every published expectation in addition to the legacy contract."""
    expected = case.get("expected")
    if expected is None:
        return fallback
    if not isinstance(expected, dict):
        return False
    return fallback and all(observed.get(key) == value for key, value in expected.items())


def _run_dynamic_provider_case(case: dict[str, Any], temp_root: Path) -> dict[str, Any]:
    """Execute a supported dynamic case; unknown cases fail visibly."""
    from vault.db import VaultDB
    from vault.memory_provider import SQLiteMemoryProvider

    kind = str(case.get("kind") or "").strip().lower()
    case_root = temp_root / str(case.get("id") or kind or "case")
    case_root.mkdir(parents=True, exist_ok=True)
    provider = SQLiteMemoryProvider(case_root / "vault.db", project_dir=case_root)
    if kind in {"candidate_visibility_transition", "candidate_promote"}:
        candidate = provider.create_candidate(**_candidate_kwargs(case))
        candidate_id = str(candidate.get("candidate_id") or "")
        before = provider.search_active(str(case.get("query") or "foundation"), limit=20)
        promoted = provider.promote_candidate(candidate_id, confirm=True)
        after = provider.search_active(str(case.get("query") or "foundation"), limit=20)
        visible_id = promoted.get("knowledge_id")
        ok = not before and any(row.get("id") == visible_id for row in after)
        return {
            "ok": ok,
            "outcome": "blocked_then_visible" if ok else "transition_failed",
            "candidate_status": candidate.get("status"),
            "promotion_status": promoted.get("status"),
            "before_count": len(before),
            "after_count": len(after),
        }
    if kind in {"privacy_candidate_rejected", "secret_candidate_rejected"}:
        candidate = provider.create_candidate(**_candidate_kwargs(case))
        candidate_row = candidate.get("candidate") or {}
        visible = provider.search_active(str(case.get("query") or "foundation"), limit=20)
        ok = (
            candidate.get("status") == "rejected"
            and candidate_row.get("status") == "rejected"
            and candidate_row.get("privacy_status") == "fail"
            and not visible
            and candidate.get("knowledge_id") is None
        )
        return {
            "ok": ok,
            "outcome": "rejected_not_visible" if ok else "privacy_rejection_failed",
            "candidate_status": candidate.get("status"),
            "stored_candidate_status": candidate_row.get("status"),
            "privacy_status": candidate_row.get("privacy_status"),
            "active_results": len(visible),
            "knowledge_id": candidate.get("knowledge_id"),
        }
    if kind in {"stale_derived_ghost_soft_delete", "soft_delete_ghost"}:
        with VaultDB(provider.resolved_db_path) as db:
            memory_id = db.add_knowledge(**_knowledge_kwargs(case))
        derived_hit = {"vault_knowledge_id": memory_id, "source": f"vault:{memory_id}"}
        deleted = provider.soft_delete_memory(memory_id, actor_agent="vault-gov-bench", reason="fixture")
        canonical = deleted.get("memory") or {}
        decision = evaluate_governed_read(
            canonical,
            as_of=str(case.get("as_of") or DEFAULT_FIXED_CLOCK),
            require_provenance=False,
        )
        ok = bool(derived_hit) and not decision.allowed and "deleted" in decision.reason_codes
        return {
            "ok": ok,
            "outcome": "ghost_blocked" if ok else "ghost_visible",
            "memory_id": memory_id,
            "reason_codes": list(decision.reason_codes),
            "audit_events": len(provider.list_audit(memory_id=memory_id)),
        }
    if kind in {"tombstone_reactivation", "reactivate"}:
        with VaultDB(provider.resolved_db_path) as db:
            memory_id = db.add_knowledge(**_knowledge_kwargs(case))
        provider.soft_delete_memory(memory_id, actor_agent="vault-gov-bench", reason="fixture")
        before = provider.get_memory(memory_id, agent_id="vault-gov-bench")
        restored = provider.update_memory(memory_id, status="active", actor_agent="vault-gov-bench")
        after = provider.get_memory(memory_id, agent_id="vault-gov-bench")
        ok = before is None and restored.get("status") == "ok" and bool(after)
        return {
            "ok": ok,
            "outcome": "reactivated" if ok else "reactivation_failed",
            "memory_id": memory_id,
            "audit_events": len(provider.list_audit(memory_id=memory_id)),
        }
    if kind in {"temporal_supersession", "supersession"}:
        with VaultDB(provider.resolved_db_path) as db:
            old_id = db.add_knowledge(
                title="Old governed fact",
                content_raw="Foundation supersession old fact.",
                source="vault-gov-bench/old",
            )
            new_id = db.add_knowledge(
                title="New governed fact",
                content_raw="Foundation supersession new fact.",
                source="vault-gov-bench/new",
                supersedes_id=old_id,
            )
            rows = [db.get_knowledge(old_id), db.get_knowledge(new_id)]
        snapshot = [row for row in rows if row]
        superseded = superseded_ids_from_snapshot(snapshot, as_of=_fixture_case_clock(case))
        old_decision = evaluate_governed_read(snapshot[0], as_of=_fixture_case_clock(case), superseded_ids=superseded)
        new_decision = evaluate_governed_read(snapshot[1], as_of=_fixture_case_clock(case), superseded_ids=superseded)
        ok = not old_decision.allowed and "superseded" in old_decision.reason_codes and new_decision.allowed
        return {
            "ok": ok,
            "outcome": "old_blocked_new_visible" if ok else "supersession_failed",
            "old_reason_codes": list(old_decision.reason_codes),
            "new_reason_codes": list(new_decision.reason_codes),
        }
    if kind in {"ttl_lifecycle_enforcement", "ttl_archive"}:
        with VaultDB(provider.resolved_db_path) as db:
            memory_id = db.add_knowledge(
                **_knowledge_kwargs(case),
                expires_at=str(case.get("expires_at") or "2026-07-18T00:00:00Z"),
            )
            before = db.get_knowledge(memory_id) or {}
            strict_before = evaluate_governed_read(before, as_of=_fixture_case_clock(case))
            lifecycle = db.archive_expired_knowledge(now=_fixture_case_clock(case))
            after = db.get_knowledge(memory_id) or {}
        strict_after = evaluate_governed_read(after, as_of=_fixture_case_clock(case))
        ok = (
            not strict_before.allowed
            and "expired" in strict_before.reason_codes
            and lifecycle.get("archived_count") == 1
            and not strict_after.allowed
        )
        return {
            "ok": ok,
            "outcome": "strict_block_and_archived" if ok else "ttl_enforcement_failed",
            "before_reason_codes": list(strict_before.reason_codes),
            "after_reason_codes": list(strict_after.reason_codes),
            "archived_count": lifecycle.get("archived_count"),
            "native_provider_immediate_ttl_filter": False,
        }
    if kind in {"duplicate_candidate_idempotency_gap", "out_of_order_update_gap"}:
        # The current provider has no external event-id/revision precondition in
        # its public contract.  Preserve the gap rather than simulate support.
        return {
            "ok": False,
            "outcome": "capability_gap",
            "capability": (
                "event_id_idempotency" if kind.startswith("duplicate") else "revision_precondition"
            ),
        }
    return {"ok": False, "outcome": "unsupported_case_kind", "kind": kind}


def _case_result(
    case: dict[str, Any],
    *,
    matched: bool,
    observed: dict[str, Any],
    execution: str,
) -> dict[str, Any]:
    expected_gap = bool(case.get("expected_capability_gap"))
    if expected_gap:
        status = "expected_gap" if matched else "fail"
    else:
        status = "pass" if matched else "fail"
    return {
        "id": str(case.get("id") or ""),
        "kind": str(case.get("kind") or case.get("type") or ""),
        "status": status,
        "expected_outcome": case.get("expected_outcome"),
        "expected": case.get("expected"),
        "expected_capability_gap": expected_gap,
        "capability_gap": case.get("expected_capability_gap") if expected_gap else None,
        "execution": execution,
        "observed": observed,
    }


def _legacy_governance_cases(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for case in fixture.get("read_cases", []):
        cases.append({"kind": "read", **case})
    for case in fixture.get("write_cases", []):
        cases.append({"kind": "write", **case})
    return cases


def _canonical_document(document: dict[str, Any]) -> dict[str, Any]:
    governance = document.get("governance") if isinstance(document.get("governance"), dict) else {}
    row = dict(document)
    row.update(governance)
    row.pop("governance", None)
    row.setdefault("approval_state", "approved")
    row.setdefault("status", "active")
    row.setdefault("scope", "project")
    row.setdefault("sensitivity", "low")
    row.setdefault("privacy_status", "pass")
    return row


def _score_case_at_k(
    fixture_case: dict[str, Any],
    run_case: dict[str, Any],
    *,
    top_k: int,
) -> dict[str, Any]:
    results = _ranked_results(run_case)[:top_k]
    returned = [str(item.get("source") or "") for item in results]
    expected_raw = {str(value) for value in fixture_case.get("expected_sources", [])}
    expected_valid = {
        str(value)
        for value in fixture_case.get("expected_valid_sources", fixture_case.get("expected_sources", []))
    }
    forbidden = {str(value) for value in fixture_case.get("forbidden_sources", [])}
    valid_hits = [source for source in returned if source in expected_valid]
    first_rank = next((index for index, source in enumerate(returned, start=1) if source in expected_valid), None)
    exposed = [source for source in returned if source in forbidden]
    expected_reasons = fixture_case.get("expected_block_reasons") or {}
    policy_decisions = run_case.get("policy_decisions", [])
    relevant_blocked = {
        str(decision.get("source") or "")
        for decision in policy_decisions
        if isinstance(decision, dict)
        and not decision.get("allowed")
        and str(decision.get("source") or "") in expected_valid
    }
    return {
        "returned_sources": returned,
        "expected_valid_total": len(expected_valid),
        "retrieval_eligible": bool(expected_valid),
        "forbidden_exposure_eligible": bool(forbidden),
        "raw_hit": any(source in expected_raw for source in returned),
        "valid_hit": first_rank is not None if expected_valid else None,
        "valid_hit_rank": first_rank,
        "valid_reciprocal_rank": (
            (0.0 if first_rank is None else round(1 / first_rank, 6))
            if expected_valid
            else None
        ),
        "valid_recall": (
            round(len(set(valid_hits)) / len(expected_valid), 6) if expected_valid else None
        ),
        "valid_precision": (
            round(len(set(valid_hits)) / len(returned), 6)
            if expected_valid and returned
            else (0.0 if expected_valid else None)
        ),
        "correct_abstention": (not returned) if not expected_valid else None,
        "forbidden_exposures": len(exposed),
        "forbidden_sources_returned": exposed,
        "forbidden_exposure_reasons": dict(
            sorted(Counter(str(expected_reasons.get(source) or "unspecified") for source in exposed).items())
        ),
        "relevant_blocked_by_policy": len(relevant_blocked),
        "relevant_blocked_sources": sorted(relevant_blocked),
    }


def _aggregate_pair_side(
    paired_cases: list[dict[str, Any]],
    *,
    side: str,
    run: dict[str, Any],
) -> dict[str, Any]:
    scores = [case[side] for case in paired_cases]
    total = len(scores)
    retrieval_cases = [score for score in scores if score.get("retrieval_eligible")]
    forbidden_cases = [score for score in scores if score.get("forbidden_exposure_eligible")]
    latencies = [
        value
        for case in _cases_by_id(run).values()
        for value in [_optional_float(case.get("latency_ms"))]
        if value is not None
    ]
    costs = [
        value
        for case in _cases_by_id(run).values()
        for value in [_optional_float(case.get("cost_usd"))]
        if value is not None
    ]
    exposures_by_reason = Counter(
        reason
        for score in scores
        for reason, count in score.get("forbidden_exposure_reasons", {}).items()
        for _ in range(int(count))
    )
    abstention_cases = [score for score in scores if not score.get("retrieval_eligible")]
    return {
        "system": run.get("system", ""),
        "cases_total": total,
        "retrieval_eligible_cases": len(retrieval_cases),
        "valid_recall": _mean(score["valid_recall"] for score in retrieval_cases),
        "valid_precision": _mean(score["valid_precision"] for score in retrieval_cases),
        "valid_hit_rate": (
            round(sum(bool(score["valid_hit"]) for score in retrieval_cases) / len(retrieval_cases), 6)
            if retrieval_cases
            else None
        ),
        "valid_mrr": _mean(score["valid_reciprocal_rank"] for score in retrieval_cases),
        "abstention_cases": len(abstention_cases),
        "correct_abstention_rate": (
            round(
                sum(bool(score["correct_abstention"]) for score in abstention_cases)
                / len(abstention_cases),
                6,
            )
            if abstention_cases
            else None
        ),
        "forbidden_exposures": sum(int(score["forbidden_exposures"]) for score in scores),
        "forbidden_exposure_eligible_cases": len(forbidden_cases),
        "forbidden_exposure_cases": sum(
            bool(score["forbidden_exposures"]) for score in forbidden_cases
        ),
        "forbidden_exposure_case_rate": (
            round(
                sum(bool(score["forbidden_exposures"]) for score in forbidden_cases)
                / len(forbidden_cases),
                6,
            )
            if forbidden_cases
            else None
        ),
        "forbidden_exposures_by_reason": dict(sorted(exposures_by_reason.items())),
        "relevant_blocked_by_policy": sum(int(score["relevant_blocked_by_policy"]) for score in scores),
        "relevant_blocked_case_rate": (
            round(
                sum(bool(score["relevant_blocked_by_policy"]) for score in retrieval_cases)
                / len(retrieval_cases),
                6,
            )
            if retrieval_cases
            else None
        ),
        "latency": _latency_summary(latencies),
        "cost": _cost_summary(costs),
    }


def _paired_numeric_values(
    baseline_cases: dict[str, dict[str, Any]],
    augmented_cases: dict[str, dict[str, Any]],
    *,
    field: str,
) -> tuple[list[float], list[float]]:
    """Return values only for case ids measured on both sides of a pair."""
    baseline_values: list[float] = []
    augmented_values: list[float] = []
    for case_id in sorted(baseline_cases.keys() & augmented_cases.keys()):
        baseline_value = _optional_float(baseline_cases[case_id].get(field))
        augmented_value = _optional_float(augmented_cases[case_id].get(field))
        if baseline_value is None or augmented_value is None:
            continue
        baseline_values.append(baseline_value)
        augmented_values.append(augmented_value)
    return baseline_values, augmented_values


def _aggregate_at_cutoffs(
    fixture: dict[str, Any],
    run: dict[str, Any],
    *,
    cutoffs: list[int],
) -> dict[str, dict[str, Any]]:
    run_cases = _cases_by_id(run)
    out: dict[str, dict[str, Any]] = {}
    for cutoff in cutoffs:
        synthetic_pairs = []
        for fixture_case in fixture.get("cases", []):
            case_id = str(fixture_case.get("id") or "")
            score = _score_case_at_k(fixture_case, run_cases.get(case_id, {}), top_k=cutoff)
            synthetic_pairs.append({"side": score})
        aggregate = _aggregate_pair_side(synthetic_pairs, side="side", run=run)
        out[str(cutoff)] = {
            key: aggregate[key]
            for key in (
                "valid_recall",
                "valid_precision",
                "valid_hit_rate",
                "valid_mrr",
                "correct_abstention_rate",
                "forbidden_exposures",
                "forbidden_exposure_case_rate",
            )
        }
    return out


def _rrf_fuse(
    engine_results: list[dict[str, Any]],
    vault_results: list[dict[str, Any]],
    *,
    rrf_k: int,
    limit: int,
) -> list[dict[str, Any]]:
    combined: dict[str, dict[str, Any]] = {}
    for contributor, results in (("engine", engine_results), ("vault", vault_results)):
        for rank, item in enumerate(results, start=1):
            source = str(item.get("source") or "")
            key = source or f"missing:{contributor}:{rank}"
            entry = combined.setdefault(
                key,
                {**item, "source": source, "rrf_score": 0.0, "contributors": []},
            )
            entry["rrf_score"] += 1.0 / (rrf_k + rank)
            entry["contributors"].append({"system": contributor, "rank": rank})
    ranked = sorted(
        combined.values(),
        key=lambda item: (-float(item["rrf_score"]), str(item.get("source") or "")),
    )[:limit]
    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank
        item["rrf_score"] = round(float(item["rrf_score"]), 9)
    return ranked


def _strict_validate_run(
    fixture: dict[str, Any],
    run: dict[str, Any],
    *,
    required_pool_k: int,
) -> None:
    documents = fixture.get("documents", [])
    if not isinstance(documents, list) or not documents:
        raise ValueError("paired fixture must contain canonical documents")
    document_sources = [
        str(document.get("source") or "")
        for document in documents
        if isinstance(document, dict)
    ]
    if len(document_sources) != len(documents) or any(not source for source in document_sources):
        raise ValueError("paired fixture documents require source provenance")
    if len(document_sources) != len(set(document_sources)):
        raise ValueError("paired fixture contains duplicate document sources")
    has_lifecycle_metadata = any(
        str(_canonical_document(document).get(field) or "").strip()
        for document in documents
        for field in ("expires_at", "valid_from", "valid_until", "supersedes_id")
    )
    if has_lifecycle_metadata and not fixture.get("fixed_clock"):
        cases = fixture.get("cases", [])
        if any(not _case_value(case, "as_of", "") for case in cases):
            raise ValueError("governance-aware fixture requires fixed_clock or per-case as_of")
    _validate_run_for_fixture(fixture, run)
    actual_digest = fixture_digest(fixture)
    if not run.get("fixture_digest"):
        raise ValueError("paired runs must include fixture_digest")
    if run.get("fixture_digest") != actual_digest:
        raise ValueError("paired run fixture_digest does not match fixture content")
    declared_pool = int(run.get("candidate_pool_k") or run.get("top_k") or 0)
    if declared_pool < required_pool_k:
        raise ValueError(
            f"run candidate pool {declared_pool} is smaller than required candidate_pool_k {required_pool_k}"
        )
    for case in run.get("cases", []):
        results = case.get("results", [])
        if not isinstance(results, list):
            raise ValueError(f"run case {case.get('id')} results must be a list")
        if len(results) > declared_pool:
            raise ValueError(f"run case {case.get('id')} exceeds its declared candidate pool")
        for result in results:
            if not isinstance(result, dict):
                raise ValueError(f"run case {case.get('id')} contains a non-object result")
        sources = [str(result.get("source") or "") for result in results]
        if any(not source for source in sources):
            raise ValueError(f"run case {case.get('id')} contains a result without source provenance")
        if len(sources) != len(set(sources)):
            raise ValueError(f"run case {case.get('id')} contains duplicate source results")


def _cases_by_id(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(case.get("id") or ""): case for case in run.get("cases", [])}


def _ranked_results(case: dict[str, Any]) -> list[dict[str, Any]]:
    results = case.get("results", [])
    return [dict(item) for item in results if isinstance(item, dict)] if isinstance(results, list) else []


def _case_value(case: dict[str, Any], key: str, default: Any) -> Any:
    if key in case:
        return case[key]
    metadata = case.get("metadata") if isinstance(case.get("metadata"), dict) else {}
    return metadata.get(key, default)


def _candidate_kwargs(case: dict[str, Any]) -> dict[str, Any]:
    supplied = dict(case.get("candidate") or {})
    defaults = {
        "title": "Foundation candidate transition",
        "content": "Decision: foundation candidate stays hidden until explicit promotion.",
        "reason": "VaultGovBench candidate visibility transition.",
        "tags": "benchmark,foundation",
        "source": "vault-gov-bench",
        "source_ref": str(case.get("id") or "candidate-transition"),
        "owner_agent": "vault-gov-bench",
    }
    defaults.update(supplied)
    return defaults


def _knowledge_kwargs(case: dict[str, Any]) -> dict[str, Any]:
    supplied = dict(case.get("memory") or {})
    defaults = {
        "title": "Foundation lifecycle memory",
        "content_raw": "Foundation lifecycle derived-index ghost fixture.",
        "source": f"vault-gov-bench/{case.get('id') or 'lifecycle'}",
        "trust": 0.9,
    }
    defaults.update(supplied)
    return defaults


def _fixture_case_clock(case: dict[str, Any]) -> str:
    return str(case.get("as_of") or case.get("fixed_clock") or DEFAULT_FIXED_CLOCK)


def _fixture_clock(fixture: dict[str, Any]) -> str:
    return str(fixture.get("fixed_clock") or DEFAULT_FIXED_CLOCK)


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return parsed


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_delta(baseline: Any, augmented: Any, *, precision: int) -> float | None:
    baseline_value = _optional_float(baseline)
    augmented_value = _optional_float(augmented)
    if baseline_value is None or augmented_value is None:
        return None
    return round(augmented_value - baseline_value, precision)


def _summary_delta(
    baseline: dict[str, Any],
    augmented: dict[str, Any],
    field: str,
    *,
    precision: int,
) -> float | None:
    if not baseline.get("available") or not augmented.get("available"):
        return None
    return round(float(augmented[field]) - float(baseline[field]), precision)


def _mean(values: Iterable[float]) -> float | None:
    items = [float(value) for value in values]
    return round(statistics.fmean(items), 6) if items else None


def _latency_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "available": False,
            "count": 0,
            "mean_ms": None,
            "p50_ms": None,
            "p95_ms": None,
        }
    ordered = sorted(values)
    return {
        "available": True,
        "count": len(ordered),
        "mean_ms": round(statistics.fmean(ordered), 3),
        "p50_ms": round(_percentile(ordered, 0.50), 3),
        "p95_ms": round(_percentile(ordered, 0.95), 3),
    }


def _cost_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"available": False, "count": 0, "total_usd": None, "mean_usd": None}
    return {
        "available": True,
        "count": len(values),
        "total_usd": round(sum(values), 8),
        "mean_usd": round(statistics.fmean(values), 8),
    }


def _percentile(values: list[float], percentile: float) -> float:
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] + (values[upper] - values[lower]) * fraction


def _read_json(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        raise ValueError("artifact path is required")
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("artifact root must be a JSON object")
    return payload


def _generic_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _environment_manifest(*, fixed_clock: str) -> dict[str, Any]:
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
    lock_path = REPO_ROOT / "uv.lock"
    lock_digest = f"sha256:{hashlib.sha256(lock_path.read_bytes()).hexdigest()}" if lock_path.exists() else ""
    return {
        "git_sha": git_sha,
        "git_dirty": git_dirty,
        "adapter_digest": f"sha256:{hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}",
        "python": platform.python_version(),
        "os": platform.system(),
        "architecture": platform.machine(),
        "dependency_lock_digest": lock_digest,
        "seed": None,
        "seed_status": "not_applicable_to_deterministic_policy_replay",
        "fixed_clock": fixed_clock,
        "redaction": "default artifact fields omit credentials and local paths; fixtures require separate input review",
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark Vault as a memory governance foundation.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    augment = subparsers.add_parser("augment-run", help="Guard a frozen external-engine candidate pool.")
    augment.add_argument("--fixture", required=True)
    augment.add_argument("--engine-run", required=True)
    augment.add_argument("--vault-run")
    augment.add_argument("--output", required=True)
    augment.add_argument("--mode", choices=("guard-only", "rrf-fusion"), default="guard-only")
    augment.add_argument("--top-k", type=int, default=10)
    augment.add_argument("--candidate-pool-k", "--prefilter-k", dest="candidate_pool_k", type=int, default=40)
    augment.add_argument("--rrf-k", type=int, default=60)

    pair = subparsers.add_parser("score-pair", help="Score external-only versus external-plus-Vault.")
    pair.add_argument("--fixture", required=True)
    pair.add_argument("--baseline-run", required=True)
    pair.add_argument("--augmented-run", required=True)
    pair.add_argument("--output", required=True)
    pair.add_argument("--top-k", type=int)

    repeats = subparsers.add_parser(
        "summarize-repeats",
        help="Aggregate clean-state paired repeat artifacts.",
    )
    repeats.add_argument("--fixture", required=True)
    repeats.add_argument("--pair", action="append", required=True)
    repeats.add_argument("--run", action="append", required=True)
    repeats.add_argument(
        "--execution-evidence",
        action="append",
        default=[],
        help="Provider lifecycle evidence bound to one raw run digest; repeat as needed.",
    )
    repeats.add_argument("--output", required=True)

    governance = subparsers.add_parser("governance-run", help="Run the deterministic VaultGovBench suite.")
    governance.add_argument("--fixture", required=True)
    governance.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "augment-run":
        augment_run(
            fixture_path=args.fixture,
            engine_run_path=args.engine_run,
            vault_run_path=args.vault_run,
            output_path=args.output,
            mode=args.mode,
            top_k=args.top_k,
            candidate_pool_k=args.candidate_pool_k,
            rrf_k=args.rrf_k,
        )
    elif args.command == "score-pair":
        score_pair(
            fixture_path=args.fixture,
            baseline_run_path=args.baseline_run,
            augmented_run_path=args.augmented_run,
            output_path=args.output,
            top_k=args.top_k,
        )
    elif args.command == "summarize-repeats":
        summarize_repeats(
            fixture_path=args.fixture,
            pair_paths=args.pair,
            run_paths=args.run,
            execution_evidence_paths=args.execution_evidence,
            output_path=args.output,
        )
    else:
        run_governance_suite(fixture_path=args.fixture, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
