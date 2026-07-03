import json

from vault.db import VaultDB
from vault.export_memory import export_memory_json, export_memory_markdown


def _seed_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with VaultDB(project / "vault.db") as db:
        public_id = db.add_knowledge(
            "Public workflow",
            "Public memory should export by default.",
            category="workflow",
            tags="export,public",
            trust=0.8,
            scope="project",
            sensitivity="low",
        )
        db.add_knowledge(
            "Private note",
            "Private memory should stay out unless explicitly requested.",
            category="profile",
            tags="export,private",
            trust=0.9,
            scope="private",
            sensitivity="low",
        )
        db.add_knowledge(
            "Restricted note",
            "Restricted memory should stay out unless explicitly requested.",
            category="security",
            tags="export,restricted",
            trust=0.9,
            scope="shared",
            sensitivity="restricted",
        )
    return project, public_id


def test_export_memory_markdown_writes_batch_with_manifest(tmp_path):
    project, public_id = _seed_project(tmp_path)
    bundle = tmp_path / "markdown-out"

    payload = export_memory_markdown(project_dir=project, bundle_dir=bundle)

    assert payload["status"] == "ok"
    assert payload["format"] == "markdown"
    assert payload["matched"] == 1
    assert payload["written"] == 2
    assert (bundle / "manifest.json").exists()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "vault.memory.export.manifest.v1"
    assert manifest["entries"][0]["id"] == public_id
    note_path = bundle / manifest["entries"][0]["path"]
    assert note_path.exists()
    note = note_path.read_text(encoding="utf-8")
    assert f"vault_id: {public_id}" in note
    assert "Public memory should export" in note
    assert "Private memory" not in note


def test_export_memory_markdown_dry_run_does_not_write_files(tmp_path):
    project, _public_id = _seed_project(tmp_path)
    bundle = tmp_path / "markdown-dry-run"

    payload = export_memory_markdown(project_dir=project, bundle_dir=bundle, dry_run=True)

    assert payload["status"] == "preview"
    assert payload["written"] == 0
    assert payload["paths"]
    assert not bundle.exists()


def test_export_memory_json_snapshot_filters_and_can_include_protected(tmp_path):
    project, _public_id = _seed_project(tmp_path)
    bundle = tmp_path / "json-out"

    default_payload = export_memory_json(project_dir=project, bundle_dir=bundle / "default")
    override_payload = export_memory_json(
        project_dir=project,
        bundle_dir=bundle / "override",
        include_private=True,
        include_restricted=True,
    )

    assert default_payload["matched"] == 1
    assert override_payload["matched"] == 3
    snapshot = json.loads((bundle / "override" / "knowledge.json").read_text(encoding="utf-8"))
    assert snapshot["schema"] == "vault.memory.export.v1"
    assert snapshot["counts"]["knowledge"] == 3
    assert {row["title"] for row in snapshot["knowledge"]} == {
        "Public workflow",
        "Private note",
        "Restricted note",
    }


def test_export_markdown_and_json_cli_json_contract(tmp_path, capsys):
    from vault.cli import main

    project, _public_id = _seed_project(tmp_path)

    main(
        [
            "export",
            "markdown",
            "--bundle",
            str(tmp_path / "cli-md"),
            "--project-dir",
            str(project),
            "--dry-run",
            "--json",
        ]
    )
    markdown_payload = json.loads(capsys.readouterr().out)
    assert markdown_payload["format"] == "markdown"
    assert markdown_payload["dry_run"] is True
    assert markdown_payload["matched"] == 1
    assert markdown_payload["written"] == 0

    main(
        [
            "export",
            "json",
            "--bundle",
            str(tmp_path / "cli-json"),
            "--project-dir",
            str(project),
            "--json",
            "--pretty",
        ]
    )
    json_payload = json.loads(capsys.readouterr().out)
    assert json_payload["format"] == "json"
    assert json_payload["status"] == "ok"
    assert json_payload["matched"] == 1
    assert (tmp_path / "cli-json" / "knowledge.json").exists()
