#!/usr/bin/env python3
"""Run the pinned five-repeat mem0 external-reproduction protocol."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.preflight_external_reproduction import run_preflight
except ModuleNotFoundError:  # Direct execution from the scripts directory.
    from preflight_external_reproduction import run_preflight


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "benchmarks/vault_gov_bench/retrieval_v0.1.json"
CLAIM_BOUNDARY = (
    "Six-case public synthetic controlled retrieval-only governance contract; "
    "not end-to-end answer quality, production scale, or an official LoCoMo/LongMemEval leaderboard."
)


def _run(command: list[str], *, env: dict[str, str] | None = None, capture: bool = False) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return completed.stdout if capture else ""


def _git(*args: str) -> str:
    return _run(["git", *args], capture=True).strip()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_checksums(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    content = "".join(f"{_sha(path)}  {path.relative_to(root).as_posix()}\n" for path in files)
    (root / "SHA256SUMS").write_text(content, encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", args.github_handle):
        raise ValueError("github handle must use GitHub-compatible letters, numbers, or hyphens")
    output = Path(args.output_dir).resolve()
    preflight = run_preflight(
        output_dir=output,
        model_cache_dir=getattr(args, "model_cache_dir", None),
        min_free_disk_gb=getattr(args, "min_free_disk_gb", 8.0),
        min_memory_gb=getattr(args, "min_memory_gb", 4.0),
    )
    if not preflight["ok"]:
        raise ValueError(f"external reproduction preflight blocked: {preflight['blocked_checks']}")
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output directory must be absent or empty: {output}")
    revision = _git("rev-parse", "HEAD")
    dirty = bool(_git("status", "--porcelain"))
    if dirty:
        raise ValueError("reproduction requires a clean worktree")
    if importlib.metadata.version("mem0ai") != "2.0.12":
        raise ValueError("install the pinned mem0ai==2.0.12 reproduction environment first")
    output.mkdir(parents=True, exist_ok=True)

    provider_input = output / "provider-input.json"
    _run([sys.executable, "benchmarks/external_memory_compare.py", "export-provider-input", "--fixture", str(FIXTURE), "--output", str(provider_input)])
    freeze = _run([sys.executable, "-m", "pip", "freeze"], capture=True)
    (output / "environment.freeze.txt").write_text(freeze, encoding="utf-8")

    state_temp = tempfile.TemporaryDirectory(prefix="vault-external-reproduction-state-")
    state_root = Path(state_temp.name)
    model_cache = Path(getattr(args, "model_cache_dir", None) or state_root / "model-cache").resolve()
    env = os.environ.copy()
    env["FASTEMBED_CACHE_PATH"] = str(model_cache)
    env["PYTHONPATH"] = str(ROOT)
    try:
        _run(
            [sys.executable, "-c", "from fastembed import TextEmbedding, SparseTextEmbedding; list(TextEmbedding(model_name='thenlper/gte-large').embed(['prewarm'])); list(SparseTextEmbedding(model_name='Qdrant/bm25').embed(['prewarm']))"],
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        state_temp.cleanup()
        raise RuntimeError(
            "FastEmbed model prewarm failed. Confirm outbound HTTPS access to "
            "huggingface.co and available disk/memory. If an external environment "
            "constraint caused the failure, report Environment blocked; this is not "
            "a Contract validated result."
        ) from exc

    pairs: list[Path] = []
    runs: list[Path] = []
    for repeat in range(1, 6):
        repeat_root = output / f"repeat-{repeat}"
        run_path = repeat_root / "A-mem0.json"
        guard_path = repeat_root / "A-plus-Vault-guard.json"
        pair_path = repeat_root / "paired-score.json"
        _run(
            [
                sys.executable, "benchmarks/external_memory_compare.py", "mem0-run",
                "--fixture", str(provider_input), "--limit", "4", "--search-scope", "global",
                "--vector-store-path", str(state_root / f"repeat-{repeat}" / "qdrant"),
                "--history-db-path", str(state_root / f"repeat-{repeat}" / "history.db"),
                "--model-cache-path", str(model_cache),
                "--collection-name", f"vaultgov_external_{args.github_handle}_{repeat}",
                "--run-namespace", f"vaultgov-external-{args.github_handle}-{repeat}",
                "--embedder", "fastembed", "--embed-model", "thenlper/gte-large",
                "--embedding-dims", "1024", "--llm-provider", "ollama", "--threshold", "0",
                "--output", str(run_path),
            ],
            env=env,
        )
        _run([sys.executable, "benchmarks/memory_foundation_compare.py", "augment-run", "--fixture", str(FIXTURE), "--engine-run", str(run_path), "--output", str(guard_path), "--mode", "guard-only", "--top-k", "1", "--candidate-pool-k", "4"])
        _run([sys.executable, "benchmarks/memory_foundation_compare.py", "score-pair", "--fixture", str(FIXTURE), "--baseline-run", str(run_path), "--augmented-run", str(guard_path), "--output", str(pair_path), "--top-k", "1"])
        runs.append(run_path)
        pairs.append(pair_path)

    summary = output / "repeat-summary.json"
    summary_command = [sys.executable, "benchmarks/memory_foundation_compare.py", "summarize-repeats", "--fixture", str(FIXTURE)]
    for pair, run_path in zip(pairs, runs, strict=True):
        summary_command.extend(["--pair", str(pair), "--run", str(run_path)])
    summary_command.extend(["--output", str(summary)])
    _run(summary_command)
    summary_payload = json.loads(summary.read_text(encoding="utf-8"))
    if summary_payload.get("publishable") is not True:
        raise RuntimeError(f"reproduction failed publication gates: {summary_payload.get('release_gate_reasons')}")
    state_temp.cleanup()

    reproduction_id = f"{args.github_handle.lower()}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    operator_mode = getattr(args, "operator_mode", "independent")
    independent = operator_mode == "independent"
    manifest = {
        "schema_version": 1,
        "artifact_type": "external_reproduction_submission" if independent else "owner_operated_reproduction_smoke",
        "reproduction_id": reproduction_id,
        "benchmark": "vaultgovbench-retrieval-v0.1",
        "provider": {"name": "mem0", "version": "2.0.12"},
        "operator": {"github_handle": args.github_handle, "affiliation": args.affiliation, "conflicts": args.conflicts},
        "source": {"revision": revision, "git_dirty": False, "repository": _git("remote", "get-url", "origin")},
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "machine": platform.machine()},
        "protocol": {"repeats": 5, "blinded_provider_input": True, "top_k": 1, "candidate_pool_k": 4},
        "artifacts": {"repeat_summary": "repeat-summary.json", "provider_input": "provider-input.json", "environment_freeze": "environment.freeze.txt"},
        "attestation": {
            "independent_operator": independent,
            "provider_never_received_gold_labels": True,
            "fresh_store_each_repeat": True,
            "no_secrets_or_private_data": True,
            "public_review_consent": True,
        },
        "review_state": "external_submission_pending_review" if independent else "owner_operated_not_external_evidence",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    (output / "submission.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_checksums(output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, help="New or empty directory outside the repository")
    parser.add_argument("--github-handle")
    parser.add_argument("--affiliation", default="independent")
    parser.add_argument("--conflicts", default="none disclosed")
    parser.add_argument("--operator-mode", choices=("independent", "owner-smoke"), default="independent")
    parser.add_argument("--accept-public-attestation", action="store_true")
    parser.add_argument("--model-cache-dir")
    parser.add_argument("--min-free-disk-gb", type=float, default=8.0)
    parser.add_argument("--min-memory-gb", type=float, default=4.0)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.preflight_only:
        result = run_preflight(
            output_dir=args.output_dir,
            model_cache_dir=args.model_cache_dir,
            min_free_disk_gb=args.min_free_disk_gb,
            min_memory_gb=args.min_memory_gb,
        )
        print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"{result['status'].upper()}: blocked={result['blocked_checks']} warnings={result['warnings']}")
        return 0 if result["ok"] else 2
    if not args.github_handle or not args.accept_public_attestation:
        parser.error("a full run requires --github-handle and --accept-public-attestation")
    result = run(args)
    if args.operator_mode == "independent":
        print(f"PASS: reproduction bundle created at {result}")
        print(f"Validate: {sys.executable} scripts/validate_external_reproduction.py {result}")
    else:
        print(f"PASS: owner-operated portability smoke created at {result}")
        print("Claim boundary: this is not an independent external reproduction submission.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
