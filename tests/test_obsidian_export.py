import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vault.db import VaultDB
from vault.export_obsidian import export_obsidian_vault, slugify_filename


def _make_vault_db(path: Path) -> None:
    with VaultDB(path) as db:
        db.add_knowledge(
            title="Guardrails Document Map Sprint 4A",
            content_raw="# Guardrails Document Map Sprint 4A\n\nTool-gated reading keeps long entries bounded.",
            layer="L3",
            category="technique",
            tags="guardrails, document-map",
            trust=0.8,
            source="unit-test",
            summary="Tool-gated reading keeps long entries bounded.",
        )
        db.add_knowledge(
            title="Private Draft",
            content_raw="Draft body should be filterable.",
            layer="L2",
            category="general",
            tags="draft",
            trust=0.4,
            source="unit-test",
        )


def test_slugify_filename_is_stable_and_path_safe():
    assert slugify_filename('Bad / Name: "Quoted"?') == "Bad-Name-Quoted"
    assert slugify_filename("   ") == "untitled"


def test_export_obsidian_writes_idempotent_markdown_with_frontmatter(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _make_vault_db(project_dir / "vault.db")

    vault_dir = tmp_path / "ObsidianVault"
    result = export_obsidian_vault(
        project_dir=project_dir,
        vault_dir=vault_dir,
        category="technique",
        tag="document-map",
    )

    assert result["written"] == 1
    assert result["matched"] == 1
    assert result["dry_run"] is False
    note = vault_dir / "00-Vault-Knowledge" / "technique" / "0001-Guardrails-Document-Map-Sprint-4A.md"
    assert note.exists()

    content = note.read_text(encoding="utf-8")
    assert "vault_id: 1" in content
    assert 'title: "Guardrails Document Map Sprint 4A"' in content
    assert 'category: "technique"' in content
    assert 'tags: ["guardrails", "document-map"]' in content
    assert "# Guardrails Document Map Sprint 4A" in content
    assert "## Citation\n\nVault #1" in content

    # Running again overwrites the same path rather than creating duplicates.
    second = export_obsidian_vault(project_dir=project_dir, vault_dir=vault_dir, category="technique")
    assert second["written"] == 1
    assert len(list((vault_dir / "00-Vault-Knowledge" / "technique").glob("*.md"))) == 1


def test_export_obsidian_dry_run_does_not_write_files(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _make_vault_db(project_dir / "vault.db")

    vault_dir = tmp_path / "ObsidianVault"
    result = export_obsidian_vault(project_dir=project_dir, vault_dir=vault_dir, dry_run=True, limit=1)

    assert result["matched"] == 1
    assert result["written"] == 0
    assert result["dry_run"] is True
    assert not vault_dir.exists()


def test_export_obsidian_cli_supports_dry_run(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _make_vault_db(project_dir / "vault.db")
    vault_dir = tmp_path / "ObsidianVault"

    env = os.environ.copy()
    repo_root = Path(__file__).parent.parent
    env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "vault.cli",
            "export",
            "obsidian",
            "--vault",
            str(vault_dir),
            "--category",
            "technique",
            "--dry-run",
        ],
        cwd=project_dir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Obsidian export" in result.stdout
    assert "matched=1" in result.stdout
    assert "dry_run=True" in result.stdout
    assert not vault_dir.exists()
