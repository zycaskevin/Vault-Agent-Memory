#!/usr/bin/env python3
"""Fail-closed environment preflight for the external reproduction kit."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from scripts.external_reproduction_models import inspect_model_cache
except ModuleNotFoundError:
    from external_reproduction_models import inspect_model_cache


ROOT = Path(__file__).resolve().parents[1]
HUGGING_FACE_URL = "https://huggingface.co"
GIB = 1024**3
PINNED_PACKAGES = {
    "mem0ai": "2.0.12",
    "fastembed": "0.8.0",
    "qdrant-client": "1.18.0",
    "onnxruntime": "1.27.0",
    "ollama": "0.6.2",
    "spacy": "3.8.14",
    "en-core-web-sm": "3.8.0",
}
SUPPORTED_PYTHON_MIN = (3, 10)
SUPPORTED_PYTHON_MAX_EXCLUSIVE = (3, 14)
CLAIM_BOUNDARY = (
    "Environment readiness only; a pass is not a benchmark run, Contract validated result, "
    "third-party reproduction, or provider security audit."
)


def _inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _nearest_existing(path: Path) -> Path:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def _memory_bytes() -> int | None:
    try:
        if sys.platform == "darwin":
            return int(subprocess.run(["sysctl", "-n", "hw.memsize"], check=True, capture_output=True, text=True).stdout.strip())
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        pages = int(os.sysconf("SC_PHYS_PAGES"))
        return page_size * pages
    except (AttributeError, OSError, ValueError, subprocess.SubprocessError):
        return None


def _package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for package in PINNED_PACKAGES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def _network_reachable(url: str, timeout: float) -> tuple[bool, str]:
    request = Request(url, method="HEAD", headers={"User-Agent": "Vault-Agent-Memory-preflight/1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return True, f"HTTP {response.status}"
    except HTTPError as exc:
        return True, f"HTTP {exc.code} (host reachable)"
    except (URLError, TimeoutError, OSError) as exc:
        return False, f"{type(exc).__name__}: {exc}"


def run_preflight(
    *,
    output_dir: str | Path,
    model_cache_dir: str | Path | None = None,
    min_free_disk_gb: float = 8.0,
    min_memory_gb: float = 4.0,
    network_timeout_seconds: float = 8.0,
    root: Path = ROOT,
    prefix: Path | None = None,
    base_prefix: Path | None = None,
    package_versions: dict[str, str | None] | None = None,
    disk_free_bytes: int | None = None,
    memory_bytes: int | None = None,
    git_revision: str | None = None,
    git_dirty: bool | None = None,
    network_probe: Callable[[str, float], tuple[bool, str]] = _network_reachable,
    python_version: tuple[int, int] | None = None,
    model_cache_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    output = Path(output_dir).resolve()
    cache = Path(model_cache_dir or os.environ.get("FASTEMBED_CACHE_PATH") or Path.home() / ".cache/fastembed").resolve()
    prefix = Path(prefix or sys.prefix).resolve()
    base_prefix = Path(base_prefix or sys.base_prefix).resolve()
    checks: list[dict[str, Any]] = []

    def add(check_id: str, status: str, detail: str, **observed: Any) -> None:
        checks.append({"id": check_id, "status": status, "detail": detail, **observed})

    python_version = python_version or (sys.version_info.major, sys.version_info.minor)
    python_ok = SUPPORTED_PYTHON_MIN <= python_version < SUPPORTED_PYTHON_MAX_EXCLUSIVE
    add(
        "python_version",
        "pass" if python_ok else "block",
        "Python version is supported by the pinned provider environment."
        if python_ok
        else "Pinned provider environment requires Python 3.10 through 3.13.",
        observed=".".join(map(str, python_version)),
        supported=">=3.10,<3.14",
    )

    if git_revision is None:
        git_revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    if git_dirty is None:
        git_dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=root, check=True, capture_output=True, text=True).stdout.strip())
    add("source_revision", "pass" if len(git_revision) == 40 else "block", "Source revision resolved." if len(git_revision) == 40 else "Source revision is not a full commit SHA.", revision=git_revision)
    add("clean_worktree", "block" if git_dirty else "pass", "Worktree contains tracked or untracked changes." if git_dirty else "Worktree is clean.", git_dirty=git_dirty)

    is_venv = prefix != base_prefix
    if not is_venv:
        add("isolated_environment", "block", "Run from a dedicated virtual environment outside the repository.", python_prefix=str(prefix))
    elif _inside(prefix, root):
        add("isolated_environment", "block", "Virtual environment is inside the repository and makes source identity fragile.", python_prefix=str(prefix))
    else:
        add("isolated_environment", "pass", "Virtual environment is isolated outside the repository.", python_prefix=str(prefix))

    if _inside(output, root):
        add("output_location", "block", "Output directory must be outside the repository.", output_dir=str(output))
    elif output.exists() and not output.is_dir():
        add("output_location", "block", "Output path exists and is not a directory.", output_dir=str(output))
    elif output.exists() and any(output.iterdir()):
        add("output_location", "block", "Output directory already exists and is not empty.", output_dir=str(output))
    else:
        add("output_location", "pass", "Output directory is outside the repository and available.", output_dir=str(output))

    versions = package_versions if package_versions is not None else _package_versions()
    mismatches = {name: {"expected": expected, "observed": versions.get(name)} for name, expected in PINNED_PACKAGES.items() if versions.get(name) != expected}
    add("pinned_dependencies", "block" if mismatches else "pass", "Pinned provider dependencies are missing or mismatched." if mismatches else "Pinned provider dependency versions match.", mismatches=mismatches)

    disk_root = _nearest_existing(output)
    free_bytes = disk_free_bytes if disk_free_bytes is not None else shutil.disk_usage(disk_root).free
    add("free_disk", "pass" if free_bytes >= min_free_disk_gb * GIB else "block", f"At least {min_free_disk_gb:g} GiB free disk is required.", free_gb=round(free_bytes / GIB, 2), required_gb=min_free_disk_gb)

    total_memory = memory_bytes if memory_bytes is not None else _memory_bytes()
    if total_memory is None:
        add("system_memory", "warn", "System memory could not be measured; verify it manually.", required_gb=min_memory_gb)
    else:
        add("system_memory", "pass" if total_memory >= min_memory_gb * GIB else "block", f"At least {min_memory_gb:g} GiB system memory is required.", memory_gb=round(total_memory / GIB, 2), required_gb=min_memory_gb)

    cache_identity = model_cache_identity or inspect_model_cache(cache)
    cache_ready = cache_identity["exact"]
    cache_status = "pass" if cache_ready else ("block" if cache_identity["complete"] else "warn")
    cache_detail = (
        "Pinned FastEmbed revisions and tree digests match."
        if cache_ready
        else (
            "Model snapshots exist but do not match the immutable revision and tree-digest contract."
            if cache_identity["complete"]
            else "Pinned model cache is cold or incomplete; exact revisions must be downloaded."
        )
    )
    add("pinned_model_cache", cache_status, cache_detail, **cache_identity)
    network_ok, network_detail = network_probe(HUGGING_FACE_URL, network_timeout_seconds)
    network_status = "pass" if network_ok else ("warn" if cache_ready else "block")
    add("hugging_face_access", network_status, network_detail, url=HUGGING_FACE_URL, cache_ready=cache_ready)

    blocked = [check["id"] for check in checks if check["status"] == "block"]
    warnings = [check["id"] for check in checks if check["status"] == "warn"]
    return {
        "schema_version": 1,
        "artifact_type": "external_reproduction_preflight",
        "status": "pass" if not blocked else "environment_blocked",
        "ok": not blocked,
        "source_revision": git_revision,
        "checks": checks,
        "blocked_checks": blocked,
        "warnings": warnings,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-cache-dir")
    parser.add_argument("--min-free-disk-gb", type=float, default=8.0)
    parser.add_argument("--min-memory-gb", type=float, default=4.0)
    parser.add_argument("--network-timeout-seconds", type=float, default=8.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_preflight(
        output_dir=args.output_dir,
        model_cache_dir=args.model_cache_dir,
        min_free_disk_gb=args.min_free_disk_gb,
        min_memory_gb=args.min_memory_gb,
        network_timeout_seconds=args.network_timeout_seconds,
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status'].upper()}: blocked={result['blocked_checks']} warnings={result['warnings']}")
        print(f"Claim boundary: {result['claim_boundary']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
