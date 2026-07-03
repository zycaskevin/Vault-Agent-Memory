"""Path helpers for Agent setup."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Callable

from vault.agent_setup_roster import _safe_slug


def default_agent_private_dir(agent: str = "generic") -> Path:
    root = os.environ.get("VAULT_AGENT_PRIVATE_ROOT", "").strip()
    base = Path(root).expanduser() if root else Path.home() / "Vaults" / "agents"
    return base / _safe_slug(agent, default="generic") / "private-memory"


def safe_default_agent_private_project(
    agent: str,
    shared_project_dir: Path,
    ensure_project: Callable[[str | Path], Path],
) -> tuple[Path, dict[str, Any] | None]:
    """Create the default private vault, falling back inside the project when home is unavailable."""
    default_path = default_agent_private_dir(agent)
    try:
        return ensure_project(default_path), None
    except (OSError, sqlite3.Error) as exc:
        fallback = shared_project_dir / "agent-private" / _safe_slug(agent, default="generic") / "private-memory"
        return ensure_project(fallback), {
            "kind": "agent_private_dir",
            "from": str(default_path.expanduser()),
            "to": str(fallback),
            "reason": f"{exc.__class__.__name__}: {exc}",
        }
