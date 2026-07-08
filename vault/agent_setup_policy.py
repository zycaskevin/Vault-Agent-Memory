"""Consumer memory mode and automation policy helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from vault.agent_setup_roster import _deep_merge_dict
from vault.agent_setup_templates import _normalize_automation_mode


def normalize_memory_mode(value: str | None, *, audience: str) -> str:
    text = str(value or "").strip().lower().replace("_", "-")
    if not text:
        return "governed-auto" if audience == "consumer" else "manual"
    aliases = {
        "auto": "governed-auto",
        "governed": "governed-auto",
        "governed-auto": "governed-auto",
        "daily": "daily-review",
        "daily-report": "daily-review",
        "daily-review": "daily-review",
        "review": "daily-review",
        "manual": "manual",
        "developer": "manual",
        "dev": "manual",
    }
    if text in aliases:
        return aliases[text]
    raise ValueError("memory_mode must be governed-auto, daily-review, or manual")


def write_automation_policy_template(
    *,
    project_dir: str | Path,
    mode: str = "balanced",
    auto_promote_low_risk: bool = False,
) -> dict[str, Any]:
    from vault.automation import POLICY_FILE, default_policy

    project = Path(project_dir).expanduser().resolve()
    path = project / POLICY_FILE
    existed = path.exists()
    if existed:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"{POLICY_FILE} must contain a YAML object")
        policy = default_policy(str(loaded.get("mode") or mode))
        policy = _deep_merge_dict(policy, loaded)
    else:
        policy = default_policy(mode)

    policy["mode"] = _normalize_automation_mode(str(policy.get("mode") or mode))
    if auto_promote_low_risk:
        policy["auto_promote_low_risk_candidates"] = True
        policy.setdefault("auto_promote_allowed_sources", ["session_capture"])
        policy.setdefault("auto_promote_allowed_memory_types", ["session_lesson"])
        policy.setdefault("auto_promote_allowed_scopes", ["project", "shared", "public"])
        policy.setdefault("auto_promote_allowed_sensitivities", ["low"])
        policy.setdefault("auto_promote_min_trust", 0.65)
        policy.setdefault("auto_promote_max_per_run", 3)
        policy.setdefault("auto_promote_requires_source_ref", True)
        policy.setdefault("auto_close_low_risk_dream_noise", True)
        policy.setdefault("auto_close_dream_noise_memory_types", ["dream_suggestion"])
        policy.setdefault("auto_close_dream_noise_tags", ["metadata", "dedup"])
        policy.setdefault("auto_close_dream_noise_scopes", ["project", "shared", "public"])
        policy.setdefault("auto_close_dream_noise_sensitivities", ["low"])
        policy.setdefault("auto_close_dream_noise_max_trust", 0.5)
        policy.setdefault("auto_close_dream_noise_max_per_run", 100)

    backup_path = ""
    if existed:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        backup = path.with_name(f"{path.name}.{stamp}.bak")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        backup_path = str(backup)
    path.write_text(yaml.safe_dump(policy, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return {
        "path": str(path),
        "backup_path": backup_path,
        "status": "updated" if existed else "created",
        "mode": policy["mode"],
        "auto_promote_low_risk_candidates": bool(policy.get("auto_promote_low_risk_candidates", False)),
        "next_action": "Review automation_policy.yaml before enabling scheduled --apply runs.",
    }
