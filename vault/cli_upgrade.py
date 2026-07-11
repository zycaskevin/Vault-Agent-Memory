"""Safe, check-only package upgrade guidance for the Vault CLI."""

from __future__ import annotations

import json
import shlex
import sys
from importlib import metadata
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from vault import __version__
from vault.agent_registry import fetch_latest_pypi_version, is_newer_version


PACKAGE_NAME = "vault-for-llm"


def _installed_direct_url() -> dict[str, Any]:
    """Read PEP 610 install metadata when the distribution provides it."""
    try:
        raw = metadata.distribution(PACKAGE_NAME).read_text("direct_url.json")
    except metadata.PackageNotFoundError:
        return {}
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _editable_source_path(direct_url: dict[str, Any]) -> str:
    if not bool((direct_url.get("dir_info") or {}).get("editable")):
        return ""
    parsed = urlparse(str(direct_url.get("url") or ""))
    if parsed.scheme != "file":
        return ""
    path = unquote(parsed.path)
    if parsed.netloc:
        path = f"//{parsed.netloc}{path}"
    return str(Path(path))


def detect_installation(
    *,
    executable: str | None = None,
    direct_url: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Detect common Python tool installers without running external commands."""
    python = str(executable or sys.executable)
    direct = _installed_direct_url() if direct_url is None else direct_url
    source_path = _editable_source_path(direct)
    normalized = python.replace("\\", "/").lower()

    if source_path:
        method = "editable"
    elif "/pipx/venvs/" in normalized:
        method = "pipx"
    elif "/uv/tools/" in normalized or "/.local/share/uv/tools/" in normalized:
        method = "uv-tool"
    else:
        method = "pip"

    return {
        "method": method,
        "python_executable": python,
        "editable_source": source_path,
    }


def _upgrade_command(installation: dict[str, Any], latest_version: str) -> list[str]:
    target = f"{PACKAGE_NAME}=={latest_version}"
    method = installation["method"]
    if method == "pipx":
        return ["pipx", "upgrade", PACKAGE_NAME]
    if method == "uv-tool":
        return ["uv", "tool", "upgrade", PACKAGE_NAME]
    if method == "editable":
        source = str(installation.get("editable_source") or ".")
        return [installation["python_executable"], "-m", "pip", "install", "-e", source]
    return [installation["python_executable"], "-m", "pip", "install", "--upgrade", target]


def build_upgrade_check(
    *,
    latest_version: str = "",
    installation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a non-mutating upgrade plan from the installed and PyPI versions."""
    resolved_latest = str(latest_version or "").strip()
    latest_source = "argument" if resolved_latest else "pypi"
    error = ""
    if not resolved_latest:
        try:
            resolved_latest = fetch_latest_pypi_version()
        except RuntimeError as exc:
            error = str(exc)

    install = installation or detect_installation()
    update_available = bool(resolved_latest and is_newer_version(resolved_latest, __version__))
    local_newer = bool(resolved_latest and is_newer_version(__version__, resolved_latest))
    if error:
        status = "check_failed"
    elif update_available:
        status = "update_available"
    elif local_newer:
        status = "local_newer"
    else:
        status = "current"

    command = _upgrade_command(install, resolved_latest) if update_available else []
    if error:
        next_action = "Retry when PyPI is reachable, or pass --latest-version for an offline comparison."
    elif status == "current":
        next_action = "No upgrade is needed."
    elif status == "local_newer":
        next_action = "This runtime is newer than the latest version reported by PyPI."
    elif install["method"] == "editable":
        next_action = "Update the source checkout first, then reinstall the editable package with the command shown."
    else:
        next_action = "Run the recommended command, then verify with `vault --version` and `vault doctor`."

    return {
        "ok": not bool(error),
        "mode": "check",
        "status": status,
        "installed_version": __version__,
        "latest_version": resolved_latest,
        "latest_version_source": latest_source,
        "latest_version_error": error,
        "update_available": update_available,
        "installation": install,
        "automatic_upgrade": False,
        "changes_made": False,
        "upgrade_command": command,
        "upgrade_command_text": shlex.join(command) if command else "",
        "next_action": next_action,
    }


def cmd_upgrade(args, *, json_print) -> None:
    """Run the phase-one, check-only upgrade command."""
    payload = build_upgrade_check(latest_version=getattr(args, "latest_version", ""))
    if getattr(args, "json", False) or getattr(args, "pretty", False):
        json_print(payload, pretty=getattr(args, "pretty", False))
    else:
        print("Vault upgrade check")
        print(f"  installed: {payload['installed_version']}")
        print(f"  latest: {payload['latest_version'] or 'unavailable'}")
        print(f"  status: {payload['status']}")
        print(f"  install method: {payload['installation']['method']}")
        if payload["latest_version_error"]:
            print(f"  error: {payload['latest_version_error']}")
        if payload["upgrade_command_text"]:
            print(f"  recommended: {payload['upgrade_command_text']}")
        print("  changes made: no")
        print(f"Next: {payload['next_action']}")
    if not payload["ok"]:
        raise SystemExit(1)
