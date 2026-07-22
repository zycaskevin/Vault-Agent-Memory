#!/usr/bin/env python3
"""Immutable FastEmbed model identities for the external reproduction track."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


MODEL_PINS = {
    "dense": {
        "logical_name": "thenlper/gte-large",
        "repo_id": "qdrant/gte-large-onnx",
        "cache_key": "models--qdrant--gte-large-onnx",
        "revision": "770e825c74a004f165b78793f7c8fc4a95280878",
        "tree_sha256": "a568a9ed201bd26efe9ff74c0c7691b6ab7c48308a18f0f56683c9f75e6a6e0f",
        "files": 8,
    },
    "sparse": {
        "logical_name": "Qdrant/bm25",
        "repo_id": "Qdrant/bm25",
        "cache_key": "models--Qdrant--bm25",
        "revision": "e499a1f8d6bec960aab5533a0941bf914e70faf9",
        "tree_sha256": "fa66222ca46f7cafd1e2093beca6a99e8d76b474a03b20a3f34e98f29e1af5d6",
        "files": 33,
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_tree_identity(snapshot: Path) -> tuple[str, int]:
    files = sorted(path for path in snapshot.rglob("*") if path.is_file())
    manifest = "".join(
        f"{_sha256(path)}  {path.relative_to(snapshot).as_posix()}\n" for path in files
    )
    return hashlib.sha256(manifest.encode("utf-8")).hexdigest(), len(files)


def inspect_model_cache(cache_dir: str | Path) -> dict[str, Any]:
    cache = Path(cache_dir).resolve()
    models: dict[str, Any] = {}
    exact = True
    complete = True
    for slot, pin in MODEL_PINS.items():
        repo = cache / pin["cache_key"]
        ref = repo / "refs" / "main"
        observed_revision = ref.read_text(encoding="utf-8").strip() if ref.is_file() else None
        snapshot = repo / "snapshots" / pin["revision"]
        if snapshot.is_dir():
            observed_tree, observed_files = snapshot_tree_identity(snapshot)
        else:
            observed_tree, observed_files = None, 0
        model_exact = (
            observed_revision == pin["revision"]
            and observed_tree == pin["tree_sha256"]
            and observed_files == pin["files"]
        )
        model_complete = snapshot.is_dir()
        complete = complete and model_complete
        exact = exact and model_exact
        models[slot] = {
            "logical_name": pin["logical_name"],
            "repo_id": pin["repo_id"],
            "expected_revision": pin["revision"],
            "observed_revision": observed_revision,
            "expected_tree_sha256": pin["tree_sha256"],
            "observed_tree_sha256": observed_tree,
            "expected_files": pin["files"],
            "observed_files": observed_files,
            "exact": model_exact,
        }
    return {"cache_dir": str(cache), "complete": complete, "exact": exact, "models": models}


def prepare_pinned_model_cache(cache_dir: str | Path) -> dict[str, Any]:
    """Download exact Hub revisions and make FastEmbed resolve them offline."""
    from huggingface_hub import snapshot_download

    cache = Path(cache_dir).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    for pin in MODEL_PINS.values():
        snapshot_download(
            repo_id=pin["repo_id"],
            revision=pin["revision"],
            cache_dir=cache,
        )
        ref = cache / pin["cache_key"] / "refs" / "main"
        ref.parent.mkdir(parents=True, exist_ok=True)
        ref.write_text(pin["revision"], encoding="utf-8")
    identity = inspect_model_cache(cache)
    if not identity["exact"]:
        raise RuntimeError("pinned FastEmbed model cache identity mismatch")
    return identity
