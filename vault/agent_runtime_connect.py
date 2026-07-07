"""Safe runtime config connectors for local Agent adapters."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def connect_openclaw_runtime(
    *,
    project_dir: str | Path,
    config_path: str | Path | None = None,
    wrapper_path: str | Path | None = None,
    apply: bool = False,
    backup: bool = True,
) -> dict[str, Any]:
    """Preview or apply OpenClaw's Vault plugin projectDir wiring.

    The returned payload intentionally excludes the full OpenClaw config because
    it may contain unrelated plugin API keys.
    """
    target_project = Path(project_dir).expanduser().resolve()
    path = Path(config_path).expanduser() if config_path else Path.home() / ".openclaw" / "openclaw.json"
    path = path.resolve()
    old_payload: dict[str, Any] = {}
    existed = path.exists()
    if existed:
        try:
            old_payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid OpenClaw config JSON: {path}") from exc
        if not isinstance(old_payload, dict):
            raise ValueError(f"OpenClaw config must be a JSON object: {path}")

    payload = json.loads(json.dumps(old_payload))
    plugins = payload.setdefault("plugins", {})
    if not isinstance(plugins, dict):
        raise ValueError("OpenClaw config plugins must be an object")
    entries = plugins.setdefault("entries", {})
    if not isinstance(entries, dict):
        raise ValueError("OpenClaw config plugins.entries must be an object")
    allow = plugins.setdefault("allow", [])
    if not isinstance(allow, list):
        raise ValueError("OpenClaw config plugins.allow must be a list")
    if "vault-for-llm" not in allow:
        allow.append("vault-for-llm")

    entry = entries.setdefault("vault-for-llm", {})
    if not isinstance(entry, dict):
        raise ValueError("OpenClaw vault-for-llm entry must be an object")
    entry["enabled"] = True
    config = entry.setdefault("config", {})
    if not isinstance(config, dict):
        raise ValueError("OpenClaw vault-for-llm config must be an object")

    previous_project_dir = str(config.get("projectDir") or "")
    if wrapper_path:
        config["wrapperPath"] = str(Path(wrapper_path).expanduser())
    else:
        config.setdefault(
            "wrapperPath",
            str(Path.home() / ".openclaw" / "skills" / "vault-for-llm" / "bin" / "vault-openclaw"),
        )
    config["projectDir"] = str(target_project)
    config.setdefault("autoRecall", False)
    config.setdefault("autoRecallResults", 3)

    new_text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    old_text = json.dumps(old_payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n" if existed else ""
    changed = (not existed) or old_text != new_text
    backup_path = ""
    if apply and changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        if backup and existed:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_file = path.with_name(f"{path.name}.bak-{timestamp}")
            backup_file.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            backup_path = str(backup_file)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            handle.write(new_text)
            temp_name = handle.name
        Path(temp_name).replace(path)

    return {
        "ok": True,
        "runtime": "openclaw",
        "apply": apply,
        "changed": changed,
        "config_path": str(path),
        "config_exists": existed,
        "backup_path": backup_path,
        "previous_project_dir": previous_project_dir,
        "project_dir": str(target_project),
        "wrapper_path": str(config.get("wrapperPath") or ""),
        "plugin_enabled": True,
        "allow_contains_vault": "vault-for-llm" in allow,
        "next_actions": [
            "Restart OpenClaw after applying the config change.",
            "Run the OpenClaw Vault adapter smoke test.",
        ],
    }


def connect_runtime(
    *,
    runtime: str,
    project_dir: str | Path,
    config_path: str | Path | None = None,
    wrapper_path: str | Path | None = None,
    apply: bool = False,
    backup: bool = True,
) -> dict[str, Any]:
    normalized = str(runtime or "").strip().lower().replace("_", "-")
    if normalized == "openclaw":
        return connect_openclaw_runtime(
            project_dir=project_dir,
            config_path=config_path,
            wrapper_path=wrapper_path,
            apply=apply,
            backup=backup,
        )
    raise ValueError("runtime connect currently supports: openclaw")
