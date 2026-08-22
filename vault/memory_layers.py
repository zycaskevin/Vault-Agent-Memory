"""Canonical filesystem labels for the stable L0-L3 memory-depth contract."""

from __future__ import annotations


CANONICAL_MEMORY_DIRECTORIES: tuple[str, ...] = (
    "L0-bootstrap",
    "L1-core-facts",
    "L2-context",
    "L3-knowledge",
)

# Compatibility aliases are read/inference contracts only. New projects must
# never create, rename, or migrate these paths automatically.
LEGACY_MEMORY_DIRECTORY_ALIASES: dict[str, str] = {
    "L0-identity": "L0",
}

MEMORY_DIRECTORY_LAYERS: dict[str, str] = {
    "L0-bootstrap": "L0",
    "L1-core-facts": "L1",
    "L2-context": "L2",
    "L3-knowledge": "L3",
    **LEGACY_MEMORY_DIRECTORY_ALIASES,
}
