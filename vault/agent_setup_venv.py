"""Stable virtualenv setup templates for agent installs."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from vault import __version__


def default_stable_venv_path() -> Path:
    return Path("~/.hermes/venvs/vault-for-llm").expanduser()


def _normalize_install_features(features: list[str]) -> list[str]:
    seen: set[str] = set()
    selected: list[str] = []
    for feature in features or ["core"]:
        name = str(feature or "").strip().lower()
        if name and name not in seen:
            seen.add(name)
            selected.append(name)
    return selected or ["core"]


def _pypi_install_target_for_features(features: list[str]) -> str:
    selected = _normalize_install_features(features)
    extras = [feature for feature in ["mcp", "semantic", "supabase", "dev"] if feature in selected]
    if extras:
        return f"vault-for-llm[{','.join(extras)}]=={__version__}"
    return f"vault-for-llm=={__version__}"


def render_stable_venv_script(
    *,
    venv_path: str | Path,
    project_dir: str | Path,
    agent: str,
    scope: str,
    features: list[str],
    tool_profile: str,
    agent_preset: str = "",
    install_embedding_model: str | None = None,
) -> str:
    selected = _normalize_install_features(features)
    install_target = _pypi_install_target_for_features(selected)
    project_path = Path(project_dir).expanduser()
    venv = Path(venv_path).expanduser()
    setup_command = [
        '"$VENV/bin/vault"',
        "setup-agent",
        "--non-interactive",
        "--agent",
        agent,
    ]
    if agent_preset:
        setup_command.extend(["--agent-preset", agent_preset])
    setup_command.extend(
        [
            "--scope",
            scope,
            "--agent-project-dir",
            str(project_path),
            "--features",
            ",".join(selected),
            "--tool-profile",
            tool_profile,
            "--json",
        ]
    )
    if install_embedding_model:
        setup_command.extend(["--install-embedding-model", install_embedding_model])

    lines = [
        "#!/usr/bin/env sh",
        "set -eu",
        "",
        f"VENV={shlex.quote(str(venv))}",
        f"PROJECT_DIR={shlex.quote(str(project_path))}",
        "",
        "mkdir -p \"$(dirname \"$VENV\")\"",
        "python3 -m venv \"$VENV\"",
        "\"$VENV/bin/python\" -m pip install --upgrade pip",
        f"\"$VENV/bin/python\" -m pip install {shlex.quote(install_target)}",
    ]
    if "headroom" in selected:
        lines.append("\"$VENV/bin/python\" -m pip install headroom-ai")
    lines.extend(
        [
            "\"$VENV/bin/vault\" --version",
            "mkdir -p \"$PROJECT_DIR\"",
            " ".join(shlex.quote(part) if "$" not in part else part for part in setup_command),
            "",
        ]
    )
    return "\n".join(lines)


def render_stable_venv_readme(*, venv_path: str | Path, script_path: str | Path) -> str:
    return "\n".join(
        [
            "# Stable Python Virtualenv",
            "",
            "This template creates a long-lived Python virtualenv for Vault-for-LLM.",
            "Use it for scheduled jobs, MCP commands, Supabase sync, and agent runtimes.",
            "",
            f"Recommended venv path: `{Path(venv_path).expanduser()}`",
            "",
            "Run:",
            "",
            "```bash",
            f"sh {shlex.quote(str(script_path))}",
            "```",
            "",
            "After it succeeds, point scheduled jobs and agent MCP commands at the",
            "`vault` and `vault-mcp` executables inside that venv instead of a",
            "temporary `/tmp/...` virtualenv.",
            "",
        ]
    )


def write_stable_venv_template(
    *,
    output_dir: str | Path,
    project_dir: str | Path,
    venv_path: str | Path,
    agent: str,
    scope: str,
    features: list[str],
    tool_profile: str,
    agent_preset: str = "",
    install_embedding_model: str | None = None,
) -> dict[str, Any]:
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    script_path = out / "setup-stable-venv.sh"
    script_path.write_text(
        render_stable_venv_script(
            venv_path=venv_path,
            project_dir=project_dir,
            agent=agent,
            scope=scope,
            features=features,
            tool_profile=tool_profile,
            agent_preset=agent_preset,
            install_embedding_model=install_embedding_model,
        ),
        encoding="utf-8",
    )
    script_path.chmod(0o755)

    readme_path = out / "README-stable-venv.md"
    readme_path.write_text(
        render_stable_venv_readme(venv_path=venv_path, script_path=script_path),
        encoding="utf-8",
    )
    return {
        "venv_path": str(Path(venv_path).expanduser()),
        "script": str(script_path),
        "readme": str(readme_path),
    }
